---
adr_id: adr-084
title: "Per-Facet Consumer Architecture for ADR-078 Phase 5"
status: ACCEPTED
decided: 2026-05-24
deciders: Michael Stratton
updated: 2026-05-24
next_review: 2026-11-24
review_trigger: First Phase 5 consumer rebuild PR ships; first non-Microsoft adapter consumes the per-facet Codebook API; PowerShell helper module is rebuilt; the FastAPI /api/v1/orgpath route is restored; a sixth consumer is proposed
impact: 'Locks the design contract for the 5 retired Model A consumer modules (dynamic-groups, admin-units, device-orgpath, policy-targeting, drift-engine) so each rebuild PR can land independently against a stable interface. Establishes Codebook-as-shared-dependency, per-facet plan/apply semantics, and the renderer pattern for boolean composition of facet predicates. Does not write any consumer code itself — those land in separate Phase 5 sub-PRs.'
supersedes: null
superseded_by: null
classification: Controlled
boundary: GCC-Moderate
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-084-phase5-consumer-architecture.html
---

# ADR-084: Per-Facet Consumer Architecture for ADR-078 Phase 5

## Status

**ACCEPTED** — 2026-05-24.

This ADR is doctrine. No code lands in this PR. Each of the 5 consumer rebuilds lands in its own follow-up PR against the contract this ADR establishes.

## Context

[ADR-078](adr-078-orgpath-attribute-schema-15-facet.md) Phase 1 (atomic schema reset, [PR #650](https://github.com/WhalerMike/uiao/pull/650)) deleted **29 files** comprising the Model A composite-string consumer modules and their tests: `policy_targets.py`, `dynamic_groups.py`, `device_planes.py`, `admin_units.py`, the matching `entra_*` adapter wrappers, the FastAPI `/api/v1/orgpath` route, `governance/drift_engine.py`, `drift_engine_config.py`, and corresponding data files / schemas / test files. The deletion was atomic-with-Phase-1 because preserving speculative Model A consumers as "legacy" would have created dead code paths that no real tenant exercises (UIAO has no production adopters at ratification time).

Phase 5 is the rebuild of those consumers per-facet. The ADR-078 implementation note explicitly defers Phase 5 to a follow-up PR program ("Their Model C rebuilds will be authored in a follow-up Phase 5 PR"). What ADR-078 did **not** specify is the *design contract* the 5 rebuilds share:

- Do they each load the codebook YAML independently, or share a single loader?
- Where does multi-facet boolean composition live — in each consumer, or in a shared renderer?
- What's the plan/apply pattern — pure dataclass return types, side-effecting methods, or both?
- How does each consumer's output flow into the rebuilt drift engine's snapshot/compare loop?
- What's the test fixture surface — per-consumer YAML snippets, or one canonical 10-facet fixture all 5 use?
- Does the FastAPI route return per-facet payloads, composite payloads, or both?
- Does the PowerShell helper validate the codebook YAML, the loaded codebook object, or per-principal facet values?

Picking these answers per-PR risks 5 inconsistent designs that don't compose into a coherent runtime. A doctrine ADR locks the design pattern once so each rebuild PR is a mechanical implementation against the contract.

The per-facet `Codebook` loader at [`src/uiao/modernization/orgtree/codebook.py`](../modernization/orgtree/codebook.py) (shipped in ADR-078 Phase 1) is the only Model C consumer currently in the codebase. It already exposes the per-facet API (`Codebook.facet(name)`, `Facet.is_active(value)`, `Facet.is_deprecated(value)`, `Facet.replacement_for(value)`) and enforces the slot-uniqueness invariant after JSON Schema validation. This ADR builds on that foundation — the 5 consumers depend on `Codebook`, not on the YAML file directly.

## Decision

The 5 Phase 5 consumer rebuilds (plus the FastAPI route and PowerShell helper) share a **per-facet consumer architecture** with the following non-negotiable design contract:

### C1. Codebook-as-shared-dependency

Every consumer accepts a `Codebook` instance as a constructor or function argument. **No consumer parses YAML directly.** This makes consumers offline-testable (pass a programmatically-constructed `Codebook` fixture) and ensures the slot-uniqueness invariant is enforced exactly once (in the loader, before any consumer sees the data).

```python
from uiao.modernization.orgtree.codebook import Codebook

class DynamicGroupRenderer:
    def __init__(self, codebook: Codebook): ...

class AdminUnitPlanner:
    def __init__(self, codebook: Codebook): ...

class DriftEngine:
    def __init__(self, codebook: Codebook, adapters: list[Adapter]): ...
```

### C2. Per-facet operations as the unit of work

Every consumer's `plan()` / `validate()` / `render()` / `emit()` method returns or yields **per-facet operations** — never a single composite operation. A consumer that needs to act on multiple facets emits multiple per-facet operations; the engine composes them.

```python
@dataclass(frozen=True)
class FacetOperation:
    facet: str                       # e.g., "department"
    attribute: str                   # e.g., "extensionAttribute2"
    op: str                          # e.g., "validate", "write", "remove"
    value: str | None                # the per-facet value (None for remove)
    target: str                      # principal id / device id / SP id
    metadata: Mapping[str, Any]      # consumer-specific
```

Per-facet decomposition flows directly to the drift engine's per-facet `DriftFinding` (UIAO_163 v2.0): one operation → one classification → one finding.

### C3. Shared rule renderer for boolean composition

Dynamic group rules, AU membership rules, and Azure Policy assignment scopes all use the same Entra-dynamic-membership-rule grammar with boolean composition over facet predicates (`(attr2 -eq "IT") and (attr3 -eq "CyberOps")`). The composition logic lives in **one shared renderer**, not duplicated in three consumers:

```python
# src/uiao/modernization/orgtree/rule_renderer.py
from dataclasses import dataclass

@dataclass(frozen=True)
class FacetPredicate:
    facet: str                       # name in the Codebook
    op: str                          # "-eq" | "-in" | "-ne" | "-ge" | "-le"
    value: str | list[str]

@dataclass(frozen=True)
class CompositionSpec:
    predicates: tuple[FacetPredicate, ...]
    combinator: str                  # "and" | "or"

def render_rule(codebook: Codebook, spec: CompositionSpec) -> str: ...
```

The renderer:
- Resolves each predicate's `facet` name to its slot via `codebook.facet(...).attribute`
- Validates predicate values against the facet (raises on Value Drift)
- Emits the canonical `(user.onPremisesExtensionAttributes.extensionAttribute2 -eq "IT") and (user.onPremisesExtensionAttributes.extensionAttribute3 -eq "CyberOps")` string

Three consumers (dynamic-groups, admin-units, policy-targeting) call `render_rule`. They differ only in **what they do with the rendered string** (POST to Entra dynamic groups, AU membership, or Azure Policy assignment scope).

### C4. Two-phase plan/apply with dry-run as default

Every consumer separates **planning** (pure, side-effect-free, returns operations) from **applying** (calls Graph / ARM with the planned operations). `dry_run=True` is the runtime default — promotion to `dry_run=False` is an operator decision per consumer per scan.

```python
class Adapter:
    def plan(self, snapshot: Snapshot) -> Iterable[FacetOperation]: ...
    def apply(self, operations: Iterable[FacetOperation], *, dry_run: bool = True) -> ApplyResult: ...
```

Plan/apply is preserved from the retired drift engine pattern (per the historical `drift_engine.py` orchestrator design); the change is that operations are **per-facet** rather than per-composite-string.

### C5. Drift engine as per-facet orchestrator

The rebuilt `DriftEngine` orchestrates over the 4 consumer adapters (dynamic-groups, admin-units, device-orgpath, policy-targeting) and the per-facet `Codebook`. It does not parse YAML, talk to Graph directly, or replicate consumer logic. Its responsibilities:

1. **Snapshot.** Accept pre-fetched tenant state (offline-testable).
2. **Compare.** For each principal × each facet, call `Facet.is_active(value)` / `Facet.is_deprecated(value)`; for each adapter, call `adapter.plan(snapshot)`.
3. **Classify.** Map each diff to one of the 5 per-facet drift categories (Format / Value / Slot / Orphan / Phantom — per UIAO_163 v2.0 §"The Five Drift Categories").
4. **Alert.** Emit `DriftFinding` objects into the Evidence Fabric.
5. **Remediate.** If `dry_run=False` and the finding is auto-remediable per its category and the adapter's governance-review set, dispatch via `adapter.apply()`. Governance-review categories (Slot, Orphan, cross-surface device equality) are **never** auto-remediated.
6. **Verify.** Operator-triggered in v1; future versions close the loop automatically.

The engine reads adapter governance-review sets via a new `Adapter.governance_review_ops -> set[str]` property; honors `auto_remediate: false` flags in a `DriftEngineConfig` per facet; and honors a `halt_on_critical` flag that skips Remediate when any finding at or above the configured halt severity fires (preserved from prior drift_engine.py design).

### C6. Test fixture surface

Each consumer ships:
- One **canonical 10-facet `Codebook` fixture** built programmatically (not from YAML), exposed as a `pytest` fixture in `tests/conftest.py`. All 5 consumers' tests reuse it.
- **Per-consumer golden snapshots** — `plan()` outputs serialized to JSON, committed under `tests/fixtures/`. Test failures show diffs against goldens.
- **Per-facet edge cases** — at minimum: enumerated active value, enumerated deprecated-with-replaced_by, enumerated unknown (Value Drift), typed pattern pass, typed pattern fail (Format Drift), typed empty when `allow_empty=true`, reserved facet with non-empty value (rejected).

No live tenant required. No live Graph mock required (the adapter's `apply()` is mocked via a transport seam; planning is pure).

### C7. FastAPI route returns per-facet payloads

The rebuilt `/api/v1/orgpath` returns per-facet payloads:

- `GET /api/v1/orgpath/codebook` — returns the loaded `Codebook` as JSON (per-facet declarations)
- `GET /api/v1/orgpath/principals/{id}/facets` — returns the principal's 10 facet values
- `GET /api/v1/orgpath/drift` — returns the most recent per-facet `DriftFinding` array (read-only; remediation never via HTTP)
- `POST /api/v1/orgpath/validate` — accepts a `{facet, value}` body, returns `{is_active, is_deprecated, replacement_for}` from `Codebook.facet(facet)`

No "composite OrgPath" endpoint. Clients that need a stitched view compose it client-side from the per-facet endpoints.

### C8. PowerShell helper validates per-facet

`OrgPathTools.psm1` ships `Test-OrgPathFacets -UserPrincipalName <UPN>` returning a per-facet result array (one entry per facet, with `IsValid` / `Reason`). The implementation shells out to the Python loader for codebook semantics (the loader is the canonical validator); the PowerShell module is the operator-friendly wrapper. The Model A `Test-OrgPath` single-string function is **not** restored.

### C9. Sequencing

The 5 consumer rebuilds can ship in parallel branches — none strictly blocks another beyond their shared dependency on:
1. The shared `rule_renderer.py` (C3) shipping first
2. The shared `FacetOperation` / `Snapshot` / `ApplyResult` dataclasses (in `uiao/modernization/orgtree/types.py`) shipping first

Recommended ship order based on dependency graph and operational priority:

| Order | Consumer | Why this order |
|---|---|---|
| **1** | `rule_renderer.py` + shared dataclasses + tests | Foundation for C3-C5; blocks dynamic-groups / admin-units / policy-targeting |
| **2** | `dynamic_groups.py` + `entra_dynamic_groups.py` adapter | Highest-leverage consumer; exercises rule_renderer end-to-end |
| **3** | `admin_units.py` + `entra_admin_units.py` adapter | Same renderer pattern as #2; cheap once #2 lands |
| **4** | `policy_targeting.py` + `entra_policy_targeting.py` adapter | Same renderer pattern; closes the trio that share `rule_renderer` |
| **5** | `device_orgpath.py` + `entra_device_orgpath.py` adapter | Different pattern (PATCH writes per facet, not rule rendering); independent of #2-#4 |
| **6** | `governance/drift_engine.py` + `drift_engine_config.py` | Depends on all 4 adapters above existing to orchestrate over them |
| **7** | FastAPI `/api/v1/orgpath` route | Read-only; depends on Codebook + DriftEngine surfaces |
| **8** | `OrgPathTools.psm1` PowerShell module | Operator wrapper; depends on Codebook validator behavior being stable |

Orders 2, 3, 4 may be done in parallel branches if reviewers can handle the load. Order 5 may ship in parallel with 2-4 since its design is independent.

## Rationale

1. **Locking the contract before the code prevents 5 incompatible designs.** Each Phase 5 PR is a multi-week effort. If the first PR establishes a pattern by accident that the next 4 must conform to (or refactor against), we double the work. A doctrine ADR up-front is the cheapest way to enforce consistency.

2. **The `Codebook` API is already proven.** The loader shipped with ADR-078 Phase 1 exposes a clean per-facet API. Reusing it across all 5 consumers (rather than letting each consumer re-derive the per-facet primitives) is the natural extension.

3. **Boolean composition is the central operational primitive.** Dynamic groups, AUs, and Azure Policy assignments all express selection as boolean composition over facet predicates. A shared renderer (C3) is the obvious factoring — the alternative (per-consumer rule-string construction) would triplicate the predicate-validation logic and create three sources of truth for "what's the canonical Entra dynamic membership syntax."

4. **Per-facet operations flow directly to per-facet drift findings.** UIAO_163 v2.0 already specifies per-facet `DriftFinding` shape. If consumers emit per-facet operations (C2), the engine's classification step (C5.3) is one-to-one — no aggregation, no inference, no glue code that could drift.

5. **Two-phase plan/apply preserves what worked in the retired engine.** The retired `drift_engine.py` orchestrator was the right architecture — its problem was the composite-string operations, not the orchestration pattern. C4 + C5 preserve the orchestration; C2 swaps the operation unit from composite to per-facet.

6. **Test fixture standardization (C6) is mandatory because there are 5 of these.** Without a shared fixture, the 5 PRs ship 5 different "what does a valid 10-facet codebook look like" definitions. Each one becomes a maintenance burden. One canonical fixture amortizes the maintenance.

7. **Sequencing recommendation (C9) is not a hard ordering, but a hint.** It reflects the natural dependency graph: rule_renderer first, then rule-renderer consumers, then the orchestrator that composes them. Mike (or future maintainers) may parallelize aggressively once #1 lands.

## Consequences

### Positive

- **Five Phase 5 PRs become mechanical implementations** against a fixed contract. Each PR's review focuses on "did you follow the ADR" — not "is this design good."
- **No design drift across consumers.** Three of the five (dynamic-groups, admin-units, policy-targeting) literally share the same rule renderer; the other two (device-orgpath, drift-engine) follow the same plan/apply pattern.
- **Drift engine restoration is well-defined.** The orchestrator pattern is preserved; only the operation unit changes from composite-string to per-facet.
- **API surface is per-facet end-to-end.** Codebook → renderer → adapter → engine → drift finding → FastAPI route → PowerShell wrapper — every layer speaks per-facet.
- **Test fixture standardization saves significant maintenance.** One canonical 10-facet fixture serves all 5 consumers' tests.

### Negative

- **`rule_renderer.py` becomes a critical-path dependency.** Three consumers depend on it; a bug in `render_rule` affects three downstream surfaces simultaneously. Mitigation: high test coverage on the renderer, golden snapshots for every supported composition pattern, no consumer ships without the renderer's coverage being at the project's existing coverage threshold.
- **The FastAPI route is read-only.** Operators wanting to remediate via HTTP can't. The deliberate doctrine is that remediation flows via the engine's `apply()` — never via HTTP — to ensure the Evidence Fabric records every write. Mitigation: the engine exposes a CLI for operator-triggered remediation; the FastAPI route is for observability only.
- **PowerShell module shells out to Python.** Operators who can't run Python can't use the module. Mitigation: the module is operator-friendly (PowerShell-native syntax, tab completion); Python is a packaging dependency, not a usage dependency.

### Risks

- **Operation shape change may break offline-archived `plan()` outputs.** If any test fixture or operator runbook captured a Model A composite-operation JSON, it won't round-trip against the new per-facet shape. Mitigation: this is an expected break — Model A consumers are deleted; no archived Model A `plan()` output is expected to round-trip. Search the repo for any committed JSON test fixtures using the old shape and delete them as part of the rebuild PRs.
- **Five PRs may take weeks; operators may need partial functionality sooner.** Mitigation: the recommended sequencing in C9 lets dynamic-groups (#2) ship as a usable feature immediately after #1 — operators get the highest-leverage consumer first, even if AUs and Policy Targeting take longer.
- **The drift engine rebuild (#6) blocks on all 4 adapters.** Operators wanting per-facet drift detection wait for the longest tail. Mitigation: each adapter ships its own offline-testable `plan()` that operators can exercise directly via the CLI; engine restoration is a convenience over the adapters, not a precondition for using them.
- **Reserved facet contract under-specified.** This ADR mentions "reserved facet with non-empty value (rejected)" but doesn't specify the consumer behavior when an operator tries to render a rule against a reserved facet. Decision: `rule_renderer` raises on reserved facets (governance review required before rendering). The future ADR that promotes a reserved facet to enumerated/typed will deal with the runtime semantics.

### Known follow-ups

- **Cross-surface per-facet equality check for devices** is deferred. Documented in UIAO_163 v2.0 §"Drift Considerations." A future ADR (companion to the `DRIFT-SCHEMA::slot-occupied` sub-class deferred in ADR-063) will introduce the runtime check.
- **Codebook hot-reload semantics** are not specified. The current loader caches via `lru_cache`. If operators expect to mutate the codebook YAML at runtime and have the engine pick up changes without restart, that requires a separate ADR addressing cache invalidation, in-flight scan handling, and Slot Drift detection on hot-reloaded codebooks.

## Implementation Phases

This ADR is doctrine. Implementation is sequenced across follow-up PRs per C9:

| Phase | Branch | Scope |
|---|---|---|
| **0** | `canon/adr-084-phase5-consumer-arch` (this PR) | Doctrine ADR. No code. |
| **1** | `code/orgtree-renderer-and-types` | `rule_renderer.py` + shared `FacetOperation`/`Snapshot`/`ApplyResult` dataclasses in `types.py` + canonical 10-facet fixture in `tests/conftest.py` + 100% renderer coverage |
| **2** | `code/orgtree-dynamic-groups-model-c` | Rebuilt `dynamic_groups.py` + `entra_dynamic_groups.py` adapter + per-facet tests + golden snapshots |
| **3** | `code/orgtree-admin-units-model-c` | Rebuilt `admin_units.py` + `entra_admin_units.py` adapter |
| **4** | `code/orgtree-policy-targeting-model-c` | Rebuilt `policy_targets.py` + `entra_policy_targeting.py` adapter |
| **5** | `code/orgtree-device-orgpath-model-c` | Rebuilt `device_orgpath.py` + `entra_device_orgpath.py` adapter (different pattern — per-facet PATCH writes, not rule rendering) |
| **6** | `code/orgtree-drift-engine-model-c` | Rebuilt `governance/drift_engine.py` + `drift_engine_config.py` orchestrating over Phases 2-5 |
| **7** | `code/orgpath-api-route-model-c` | Restored FastAPI `/api/v1/orgpath` route (read-only, per-facet) |
| **8** | `code/orgpathtools-powershell-model-c` | Rebuilt `OrgPathTools.psm1` with `Test-OrgPathFacets` |

Phases 2-5 may ship in parallel branches once Phase 1 merges. Phase 6 blocks on all of 2-5 (orchestrator depends on its adapters). Phases 7 and 8 may ship at any time after Phase 6 (or after the relevant subset of 2-5 if they read only one adapter).

Each phase PR closes a subset of the ~84 `DRIFT-PROVENANCE` P2 findings introduced by ADR-078 Phase 1 (per ADR-078 §"Known `substrate-drift` findings"). The Phase 6 PR closes the drift-engine bucket; the Phase 8 PR closes the PowerShell-helper citations in UIAO_151 v4.0.

## Verification Sources

| Source | Reference | Last Verified |
|---|---|---|
| Per-facet Codebook loader (current SSOT) | [`src/uiao/modernization/orgtree/codebook.py`](../modernization/orgtree/codebook.py) | 2026-05-24 |
| Per-facet drift engine spec | [`UIAO_163_Drift_Detection_Engine_Specification.md`](../UIAO_163_Drift_Detection_Engine_Specification.md) v2.0 | 2026-05-24 |
| Per-facet codebook narrative | [`UIAO_151_OrgPath_Codebook.md`](../UIAO_151_OrgPath_Codebook.md) v4.0 | 2026-05-24 |
| Per-facet JSON Schema appendix | [`UIAO_158_OrgPath_JSON_Schema.md`](../UIAO_158_OrgPath_JSON_Schema.md) v3.0 | 2026-05-24 |
| Retired engine orchestrator pattern (historical) | Pre-deletion `src/uiao/governance/drift_engine.py` at commit `0574aa52` | 2026-05-24 |
| Deleted-file inventory | ADR-078 Phase 1 — [PR #650](https://github.com/WhalerMike/uiao/pull/650) | 2026-05-24 |

## Review Triggers

This ADR must be re-evaluated when any of the following occur:

- [ ] Phase 1 (rule_renderer + types + fixture) ships — review whether the contract is implementable as written or needs refinement before Phases 2-8 begin
- [ ] First non-Microsoft adapter is proposed for the per-facet pattern — review whether the `FacetOperation` shape and the `Adapter` interface generalize beyond Graph/ARM
- [ ] An operator requests a per-facet remediation HTTP endpoint — review whether the read-only FastAPI contract should be relaxed (and how Evidence Fabric recording is preserved if so)
- [ ] PowerShell module ships — review whether the shell-out-to-Python pattern creates packaging friction
- [ ] FastAPI route ships — review whether the per-facet endpoint structure is operator-friendly or needs a composite-view convenience layer
- [ ] A sixth Phase 5 consumer is proposed (e.g., per-facet license assignment, per-facet entitlement management) — review whether C3's renderer pattern needs extension
- [ ] Cross-surface per-facet device equality check ADR is proposed — review whether C5 needs an additional classify step
- [ ] Codebook hot-reload ADR is proposed — review whether the C1 dependency-injection pattern handles cache invalidation
- [ ] 2026-11-24 — scheduled six-month review

## Related Documents

- [ADR-000 — ADR Process and Lifecycle](adr-000-adr-process.md)
- [ADR-078 — OrgPath Attribute Schema 15-Facet](adr-078-orgpath-attribute-schema-15-facet.md) — the doctrine ADR that retired Model A consumers and scheduled Phase 5; this ADR locks the Phase 5 design contract
- [ADR-035 — OrgPath Codebook Binding](adr-035-orgpath-codebook-binding.md) — binding of `codebook.yaml`; the loader this ADR builds on
- [ADR-036 — Dynamic Group Provisioning](adr-036-dynamic-group-provisioning.md) — pre-Model-C dynamic-group doctrine; the Phase 5 #2 rebuild restores its implementation per-facet
- [ADR-037 — Administrative Unit Provisioning](adr-037-admin-unit-provisioning.md) — pre-Model-C AU doctrine; restored by Phase 5 #3
- [ADR-038 — Device Plane OrgPath](adr-038-device-plane-orgpath.md) — pre-Model-C device-plane doctrine; restored by Phase 5 #5
- [ADR-039 — Policy Targeting](adr-039-policy-targeting.md) — pre-Model-C policy-targeting doctrine; restored by Phase 5 #4
- [ADR-040 — Drift Engine](adr-040-drift-engine.md) — pre-Model-C drift-engine doctrine; restored by Phase 5 #6
- [ADR-063 — OrgPath Storage Slot Binding](adr-063-orgpath-storage-slot-binding.md) — slot ratification; the `DRIFT-SCHEMA::slot-occupied` sub-class deferred there is the basis of the future cross-surface equality ADR
- [ADR-074 — Drift SSOT Contention](adr-074-drift-ssot-contention.md) — drift-engine governance considerations preserved per-facet
- [UIAO_151 v4.0 — OrgPath Codebook](../UIAO_151_OrgPath_Codebook.md) — per-facet narrative spec
- [UIAO_158 v3.0 — OrgPath JSON Schema](../UIAO_158_OrgPath_JSON_Schema.md) — per-facet schema spec
- [UIAO_163 v2.0 — Drift Detection Engine Specification](../UIAO_163_Drift_Detection_Engine_Specification.md) — per-facet engine spec
