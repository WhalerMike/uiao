---
id: ADR-036
title: "Dynamic Group Library — Executable Canon + Entra Provisioning Adapter"
status: accepted
date: 2026-04-20
deciders:
  - governance-steward
  - identity-engineer
supersedes: []
related_adrs:
  - ADR-012
  - ADR-034
  - ADR-035
canon_refs:
  - MOD_A_OrgPath_Codebook
  - MOD_B_Dynamic_Group_Library
  - UIAO_007_OrgTree_Modernization_AD_to_EntraID
---

# ADR-036: Dynamic Group Library — Executable Canon + Entra Provisioning Adapter

## Status

Accepted

## Context

MOD_B (`src/uiao/modernization/orgtree/MOD_B_Dynamic_Group_Library.md`)
enumerates 32 canonical OrgTree-* dynamic groups — the operational bridge
between the OrgPath codebook (MOD_A, bound by ADR-035) and every downstream
governance surface: Conditional Access targeting, AU membership (MOD_D),
licensing, and drift detection (MOD_M).

Before this ADR the library existed only as prose + PowerShell snippets.
There was no machine-readable form, no adapter to provision the groups
into an Entra tenant, and no way for the drift engine to distinguish a
canonical group from a phantom. Three concrete gaps:

1. Every phrase of the form *"Conditional Access targets `OrgTree-EXEC-CA`"*
   across the canon pointed at a group that only existed on paper.
2. A rule in MOD_B could drift from the rule the library text suggested
   with no structural check — the `orgpath_refs` list and the opaque
   membership-rule string were unconnected.
3. The five MOD_B drift categories (Rule / Phantom / Missing / Name /
   Membership) had no implementation; `governance.drift` only handled
   identity-plane drift (MOD_A via ADR-035).

## Decision

1. Publish MOD_B as executable canon at
   `src/uiao/canon/data/orgpath/dynamic-groups.yaml`, shipped with
   `uiao.canon` so `importlib.resources` reads it at runtime.
2. Ship a JSON Schema at
   `src/uiao/schemas/orgpath/dynamic-groups.schema.json` that enforces
   the naming convention, category enum, and rule shape.
3. Provide a loader at
   `src/uiao/modernization/orgtree/dynamic_groups.py` that additionally
   enforces **cross-canon integrity**: every `orgpath_refs` entry must be
   active in the codebook (reuses ADR-035 loader), every ref must also
   appear *verbatim* inside the quoted rule string, and every group name
   must be unique. A reference to a deprecated code is rejected at load.
4. Introduce a modernization adapter
   `uiao.adapters.entra_dynamic_groups.EntraDynamicGroupsAdapter` with
   three verbs:
   - `plan(current_tenant_state=None)` — produces an ordered list of
     `create` / `update` / `delete-phantom` operations; no Graph calls.
   - `apply(plan, dry_run=True)` — dry-run by default; on `dry_run=False`
     issues `POST /groups` and `PATCH /groups/{id}` per operation.
   - `reconcile(...)` — plan + apply in one call.
5. **`delete-phantom` is never auto-applied.** MOD_B §Drift prescribes
   manual governance review for phantom groups; the adapter produces a
   planned op with `status=skipped-manual` and lets the governance
   workflow (MOD_E) decide. Only `create` and `update` are auto-remediated.
6. Register the adapter in `canon/modernization-registry.yaml` (class:
   modernization, mission-class: integration) as a peer of the existing
   `entra-id` entry — the two share a tenant, not a code path.

## Consequences

**Positive**

- The drift engine can now classify all four automatically-remediable
  MOD_B drift types (Rule, Missing, Name, Membership) against a concrete
  enumeration. Phantom groups become governance findings with zero
  ambiguity.
- The `orgpath_refs` ↔ `rule` cross-check at load time means canon changes
  to MOD_A automatically surface as integrity errors in MOD_B if a group
  references a code that was removed or deprecated — upgrade failures
  happen during PR CI, not during a tenant reconcile.
- The adapter is offline-testable: `plan()` and `apply(dry_run=True)` do
  not touch the network, and `current_tenant_state` is a plain list of
  Graph-shaped dicts. Contract fixture lives at
  `tests/fixtures/contract/entra-id/dynamic-groups/tenant-state.json`.
- Opens the door to Phase 3 (Administrative Units, MOD_D) which will
  reuse the same `plan / apply / reconcile` shape against a different
  Graph endpoint.

**Negative / deferred**

- **Membership Drift** (MOD_B §Drift type 5) is not addressed here — it
  requires comparing a computed user population against expected counts,
  which the drift engine (MOD_M, Phase 6) will own. This adapter scopes
  itself to group *definitions*, not their computed populations.
- The adapter does not yet consume output from the EntraCollector's
  user-attribute read (ADR-035, Phase 1). A Phase 3 bridge will feed
  tenant-state into `plan()` rather than requiring callers to inject it.
- Graph throttling / batch submission is not implemented; the current
  `apply()` issues one request per operation. When tenants exceed ~20
  missing groups in a single reconcile, switch to `$batch` — tracked as
  a follow-up.

## Alternatives considered

- **Bicep / Terraform authoring instead of a Python adapter.** Rejected
  because MOD_B's drift categories (especially Phantom and Name Drift)
  require *diffing* against a canonical list, which IaC tools do not
  natively express. A Python adapter also composes cleanly with the
  drift engine (MOD_M) already in-tree.
- **Store rules as structured AST rather than a rule string.** Rejected
  for this phase — the Graph API consumes a string, and the verbatim
  cross-check in the loader catches rule/ref skew without a second
  representation to maintain. Revisit when compound rules exceed two
  branches in practice.

## Related work

- ADR-035 — OrgPath codebook binding (MOD_A). This ADR depends on it;
  the integrity check reuses the ADR-035 codebook loader.
- ADR-034 — Three-plane device model. MOD_B currently targets user
  objects only; device-plane OrgTree groups are reserved for Phase 4.
