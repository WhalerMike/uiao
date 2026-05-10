---
id: ADR-060
title: "Flatten MOD_xxx Namespace into UIAO_NNN Canon — Single-Registry Consolidation"
status: proposed
date: 2026-05-10
accepted: null
deciders:
  - governance-steward
  - identity-engineer
  - canon-curator
supersedes: []
related_adrs:
  - ADR-032  # Single-package consolidation (predicate for one-canon, one-registry)
  - ADR-035  # OrgPath codebook binding (binds adapter to MOD_A)
  - ADR-036  # Dynamic group provisioning (binds adapter to MOD_B)
  - ADR-037  # Admin unit provisioning (binds adapter to MOD_D)
  - ADR-038  # Device-plane OrgPath (binds adapter to MOD_C)
  - ADR-039  # Policy targeting (binds adapter to MOD_N)
  - ADR-040  # Drift engine (cites MOD_M classification model)
  - ADR-042  # AD computer conversion guide integration
  - ADR-044  # Substrate governance realignment (promoted MOD_xxx to canon)
  - ADR-049  # Microsoft adapter coverage expansion (cites MOD_B/C/D/N)
canon_refs:
  - UIAO_007  # OrgTree Migration Guide — actual conceptual parent of the MOD_* corpus
  - UIAO_009  # Microsoft Coverage and Gap Doctrine — cites MOD_xxx structurally
  - UIAO_135  # Identity & Directory Transformation Inventory — Track 2 sister
  - UIAO_136  # Priority 1 Transformation Specs — Track 2 sister
  - UIAO_200  # Substrate Manifest — registry resolver
  - UIAO_201  # Workspace Contract — registry resolver
---

# ADR-060: Flatten MOD_xxx Namespace into UIAO_NNN Canon — Single-Registry Consolidation

## Status

PROPOSED — 2026-05-10

## Context

The repository currently carries the AD-to-Entra-ID modernization corpus
across two parallel tracks at different abstraction layers:

- **Track 1 — Structural / target-state.** The `MOD_*` corpus under
  `src/uiao/modernization/orgtree/` (22 artifacts: `MOD_001`,
  `MOD_A`–`MOD_V`). Originated from `inbox/EntraID Governance/AD to
  EntraID Tree.docx` on 2026-04-18, promoted to canon by ADR-044, and
  registered in its own
  `src/uiao/modernization/orgtree/document-registry` (the `.yaml` registry retired by this ADR) under a
  dedicated `MOD` namespace. Owns the OrgPath codebook, dynamic-group
  library, AU/role delegation, OU-to-Entra migration runbook, and drift
  detection model.
- **Track 2 — Lifecycle / execution.** `UIAO_135` + `UIAO_136` plus the
  Spec2-D*.md deliverable corpus under `src/uiao/canon/specs/`, all
  registered in the main `src/uiao/canon/document-registry.yaml`. Owns
  HR-attribute schema, JML workflows, SCIM/bulkUpload architecture,
  middleware/agent deployment, testing, cutover, and provisioning
  governance.

The two tracks are **complementary, not contradictory**, but the parallel
registries create three real problems:

1. **Two sources of truth for "which docs is canon?"** Tooling that
   resolves canon (substrate walker, drift engine, sync-canon-check
   workflow) reads `src/uiao/canon/document-registry.yaml` as primary;
   the `MOD` registry is a sibling resolved through a separate code path
   in the orgtree module. Adding a doc, renaming a doc, or retiring a
   doc requires touching the right registry — which has been a
   recurring footgun.
2. **`parent_canon: UIAO_008` is incorrect.** Every `MOD_*` document and
   the orgtree registry list `UIAO_008` (the CLI Reference) as parent
   canon. The actual conceptual parent is `UIAO_007` (OrgTree Migration
   Guide). This appears to be a copy-paste error from the ADR-044
   promotion and has been latent ever since.
3. **Cross-references are slug-fragile.** 41 files outside the orgtree
   module reference `MOD_*` slugs (9 ADRs, 5 adapters, 2 governance
   modules, 3 Spec2 specs, 6 schemas, 6 orgpath data YAMLs, the
   modernization-registry, UIAO_007, and UIAO_009). The slugs are
   prose-shaped (`MOD_A`, `MOD_B`, …) rather than the registry-resolved
   `UIAO_NNN` form, so they bypass the canon-id integrity gate that
   covers the rest of the corpus.

The remediation considered and rejected was a **content merge** of
Track 1 into Track 2 (or vice-versa). That is not the right move: the
two tracks live at genuinely different abstraction layers (structural
target-state vs. lifecycle execution), and their content does not
duplicate — the small overlap (`MOD_C` ↔ `Spec2-D1.3`/`D1.4`; `MOD_F` ↔
`Spec2-D5.1`) is a *different view of the same boundary* and is
correctly authored as two documents.

What the situation actually calls for is a **namespace flatten**: keep
the content as-is, retire the `MOD_xxx` slug shape, allocate a
contiguous block of `UIAO_NNN` slots, retarget every reference, and
collapse to one registry.

## Decision

Flatten the `MOD_xxx` namespace into the `UIAO_NNN` canon namespace
through a one-time mechanical renaming pass.

### 1. Slot allocation

Allocate the contiguous block **`UIAO_150` through `UIAO_171`** (22
slots) to the `MOD_*` corpus, in document-registry order:

| Current slug | New canon id | Filename (post-flatten) |
|---|---|---|
| `MOD_001` | `UIAO_150` | `UIAO_150_OrgTree_Modernization_Executive_Summary.md` |
| `MOD_A` | `UIAO_151` | `UIAO_151_OrgPath_Codebook.md` |
| `MOD_B` | `UIAO_152` | `UIAO_152_Dynamic_Group_Library.md` |
| `MOD_C` | `UIAO_153` | `UIAO_153_Attribute_Mapping_Table.md` |
| `MOD_D` | `UIAO_154` | `UIAO_154_Delegation_Matrix_AUs_Roles.md` |
| `MOD_E` | `UIAO_155` | `UIAO_155_Governance_Workflow_Catalog.md` |
| `MOD_F` | `UIAO_156` | `UIAO_156_Migration_Runbook_OU_to_Entra.md` |
| `MOD_G` | `UIAO_157` | `UIAO_157_Diagram_Pack.md` |
| `MOD_H` | `UIAO_158` | `UIAO_158_OrgPath_JSON_Schema.md` |
| `MOD_I` | `UIAO_159` | `UIAO_159_PowerShell_Validation_Module.md` |
| `MOD_J` | `UIAO_160` | `UIAO_160_Governance_Enforcement_Test_Suite.md` |
| `MOD_K` | `UIAO_161` | `UIAO_161_Enforcement_Decision_Trees.md` |
| `MOD_L` | `UIAO_162` | `UIAO_162_SLA_Heatmap_Owner_Reliability_Model.md` |
| `MOD_M` | `UIAO_163` | `UIAO_163_Drift_Detection_Engine_Specification.md` |
| `MOD_N` | `UIAO_164` | `UIAO_164_Execution_Substrate_Integration_Layer.md` |
| `MOD_O` | `UIAO_165` | `UIAO_165_Enforcement_Test_Harness_Mock_Tenant.md` |
| `MOD_P` | `UIAO_166` | `UIAO_166_Governance_Boundary_Impact_Model.md` |
| `MOD_Q` | `UIAO_167` | `UIAO_167_SLA_Escalation_Playbooks.md` |
| `MOD_R` | `UIAO_168` | `UIAO_168_Canonical_Repository_Structure.md` |
| `MOD_S` | `UIAO_169` | `UIAO_169_Governance_OS_State_Machine.md` |
| `MOD_T` | `UIAO_170` | `UIAO_170_Identity_Risk_Scoring_Model.md` |
| `MOD_U` | `UIAO_171` | `UIAO_171_Multi-Cloud_Boundary_Model.md` |

`MOD_V` (`Canonical_Contributor_Workflow_PR_to_Validation_to_Merge`) is
not in the orgtree registry as of 2026-05-10 — the registry stops at
`MOD_U`. The flatten pass will resolve this discrepancy by either (a)
adding it to the registry as `UIAO_172` if it is intended canon, or (b)
moving it to `inbox/` if it is staging material. The flatten ADR does
not pre-decide; the disposition is a one-line discussion item in the
implementation PR.

### 2. File-system layout

Post-flatten, the 22 docs live at `src/uiao/canon/UIAO_15x_*.md` /
`UIAO_16x_*.md` / `UIAO_17x_*.md` alongside the rest of the
`UIAO_NNN` canon. The `src/uiao/modernization/orgtree/` directory
retains its **Python modules** (`codebook.py`, `dynamic_groups.py`,
`admin_units.py`, `device_planes.py`, `policy_targets.py`,
`drift_engine_config.py`, `__init__.py`) — those are code, not
documents, and the package layout established by ADR-032 keeps them
where they are. The directory's `.md` files and
`document-registry.yaml` are removed.

`src/uiao/modernization/README.md` is rewritten to point at the new
`UIAO_15x` entries (no longer claims to be a "separate canon within
UIAO" — it becomes a thin module README documenting the Python-side
orgtree modules).

### 3. Single registry

The orgtree-side `document-registry.yaml` is **deleted**. The 22
allocated entries are inserted into
`src/uiao/canon/document-registry.yaml` in numeric order, with full
frontmatter mirroring the existing `UIAO_007`/`UIAO_009` pattern:
`id`, `path`, `title`, `status`, `classification`. The `MOD` namespace
ceases to exist.

`src/uiao/canon/modernization-registry.yaml` (the *adapter* registry —
distinct from the document registry) keeps its name and its role; this
ADR does not touch adapter declarations. Adapter `canon_refs` strings
are retargeted from `MOD_X` to the new `UIAO_15x` slug as part of the
mechanical pass.

### 4. Cross-reference retarget — full inventory

The renaming pass updates references in **all** of the following
files. Any file in this list that does not get updated produces a
DRIFT-PROVENANCE finding from the substrate walker post-flatten — the
walker becomes the gate that proves the pass was complete.

**ADRs (9):**

- `adr-035-orgpath-codebook-binding.md` (→ `UIAO_151`)
- `adr-036-dynamic-group-provisioning.md` (→ `UIAO_152`)
- `adr-037-admin-unit-provisioning.md` (→ `UIAO_154`)
- `adr-038-device-plane-orgpath.md` (→ `UIAO_153`)
- `adr-039-policy-targeting.md` (→ `UIAO_164`)
- `adr-040-drift-engine.md` (→ `UIAO_163`)
- `adr-042-ad-computer-conversion-guide-integration.md`
- `adr-044-substrate-governance-realignment.md`
- `adr-049-microsoft-adapter-coverage-expansion.md`

**Canon docs (2):**

- `UIAO_007_OrgTree_Modernization_AD_to_EntraID_v1.0.md` — the
  "OrgPath Discovery Feeders" §s reference `MOD_C` and `MOD_N`; both
  retarget.
- `UIAO_009_Microsoft_Coverage_And_Gap_Doctrine_v1.0.md` — narrative
  references to `MOD_B/C/D/N`; retarget.

**Spec2 deliverables (3):**

- `Spec2-D2.2-MoverWorkflowSpecification.md`
- `Spec2-D3.1-APIDrivenInboundProvisioningArchitecture.md`
- `Spec2-D3.5-OrgPathPopulationPipeline.md`

**Adapter code (5):**

- `src/uiao/adapters/entra_adapter.py`
- `src/uiao/adapters/entra_admin_units.py`
- `src/uiao/adapters/entra_device_orgpath.py`
- `src/uiao/adapters/entra_dynamic_groups.py`
- `src/uiao/adapters/entra_policy_targeting.py`

**Governance modules (2):**

- `src/uiao/governance/drift.py`
- `src/uiao/governance/drift_engine.py`

**Collector (1):**

- `src/uiao/collectors/entra/entra_collector.py`

**Adapter registry (1):**

- `src/uiao/canon/modernization-registry.yaml` — `canon_refs` strings
  in five adapter blocks.

**OrgPath data YAML (6):**

- `src/uiao/canon/data/orgpath/admin-units.yaml`
- `src/uiao/canon/data/orgpath/codebook.yaml`
- `src/uiao/canon/data/orgpath/device-planes.yaml`
- `src/uiao/canon/data/orgpath/drift-engine-config.yaml`
- `src/uiao/canon/data/orgpath/dynamic-groups.yaml`
- `src/uiao/canon/data/orgpath/policy-targets.yaml`

**Schemas (6):**

- `src/uiao/schemas/orgpath/admin-units.schema.json`
- `src/uiao/schemas/orgpath/codebook.schema.json`
- `src/uiao/schemas/orgpath/device-planes.schema.json`
- `src/uiao/schemas/orgpath/drift-engine-config.schema.json`
- `src/uiao/schemas/orgpath/dynamic-groups.schema.json`
- `src/uiao/schemas/orgpath/policy-targets.schema.json`

**Module README + registry (2):**

- `src/uiao/modernization/README.md` — rewritten per §2.
- `src/uiao/modernization/orgtree/document-registry` (the `.yaml` registry retired by this ADR) — deleted.

**Python module docstrings (6):**

The orgtree `*.py` modules in
`src/uiao/modernization/orgtree/` reference `MOD_*` in module-level
docstrings; those strings get the same retarget treatment as the
adapter code.

**Total touched: 41 files + 22 file moves + 1 file deletion.**

### 5. Frontmatter migration

Each renamed file gets the following frontmatter changes:

```yaml
# Before                               # After
document_id: MOD_A                     document_id: UIAO_151
namespace: MOD                         # (key removed)
parent_canon: UIAO_008                 # (key removed — UIAO_NNN docs do not declare a parent_canon; they are top-level canon)
classification: CANONICAL              classification: CANONICAL  # unchanged
status: DRAFT                          status: Draft  # case-normalize to match the rest of canon
```

Provenance is preserved through a one-line frontmatter addition:

```yaml
provenance:
  prior_id: MOD_A
  flattened_at: "2026-05-10"
  flattened_by: "ADR-060"
```

This makes the rename auditable from inside the document itself and
lets the substrate walker dual-resolve old slugs during the
deprecation window (per §7).

### 6. Tooling changes

- `src/uiao/modernization/orgtree/__init__.py` — drop the
  `DOCUMENT_REGISTRY` resolver that points at the orgtree-side
  registry. The Python modules continue to live there; only the
  doc-registry resolver goes away.
- Substrate walker (`src/uiao/substrate/walker.py`) — its
  `DOCUMENT_REGISTRY` constant already targets
  `src/uiao/canon/document-registry.yaml`; no change needed once the
  22 entries are merged in.
- `sync-canon-check` workflow — already gates the main canon
  registry; gains coverage of the 22 new entries automatically.
- `tests/canon_registry/` — extend the existing parametrized test
  with the 22 new ids.

### 7. Deprecation window — closed early (2026-05-11)

This section originally specified a 30-day deprecation window
(2026-05-10 → 2026-06-09) backed by a `MOD_*` → `UIAO_15x`
slug-resolution table at `src/uiao/canon/data/mod-slug-redirects`
(`.yaml`, since deleted), with a substrate-walker hook that would emit a
P2 advisory whenever a `MOD_*` slug appeared in a scanned file.
**The walker hook was never implemented**; the table existed only as
static reference documentation.

Closed status, recorded by the cleanup PR that removed the table:

- The implementation PR (#352) retargeted every reference inside the
  in-scope inventory in a single landing, so no in-flight PR ever
  needed the redirect table to resolve a missing slug.
- Body prose inside the 27 renamed canon docs (UIAO_150 – UIAO_176)
  retains historical `MOD_*` references — that was the explicit
  out-of-scope decision in §"Out of scope" and remains unchanged. Each
  doc carries a `provenance_flatten:` frontmatter block recording its
  prior slug, which is now the canonical answer for "what MOD slug did
  this used to be?"
- The redirect table and any tooling hook are removed; future ADRs
  proposing slug-redirect tables should also commit the walker
  integration in the same PR, not promise it as a follow-on.

This window was defensive but, in retrospect, redundant: the
implementation PR's atomic retarget made the table unused from the
moment it landed.

## Consequences

### Positive

- **One canon, one registry.** `src/uiao/canon/document-registry.yaml`
  becomes the single resolver for every canon document. The substrate
  walker, sync-canon-check workflow, and drift engine all stop having
  to special-case the orgtree registry.
- **Slug shape matches the rest of canon.** `UIAO_NNN` is the integrity
  unit. Cross-references through this slug shape benefit from the same
  validation gates that protect every other canon doc — typo'd
  `UIAO_152` fails registry resolution; typo'd `MOD_B` did not.
- **`parent_canon: UIAO_008` error eliminated.** The flatten retires
  the field entirely; no copy-paste error to fix because the field
  ceases to exist.
- **Track-1 / Track-2 boundary survives.** Content stays at its
  current abstraction layer; the structural docs do not absorb the
  lifecycle docs and vice-versa. Readers reading
  `UIAO_151_OrgPath_Codebook.md` see the same content they saw in
  `MOD_A_OrgPath_Codebook.md`.
- **Spec2 frontmatter gets cleaner.** The three Spec2 files that cite
  `MOD_*` today swap in `UIAO_15x` ids that match the
  `canonical_docs:` / `canonical_adrs:` shape they already use for
  every other reference.
- **Adapter `canon_refs` integrity becomes machine-checkable.** The
  modernization-registry's `canon_refs` field today carries `MOD_C`
  strings whose resolution is by-convention; post-flatten they
  resolve through the document registry like every other
  `canon_refs` value.

### Negative

- **One large mechanical PR.** The implementation pass is a 41-file
  diff (plus 22 moves and 1 deletion). It is a low-judgment,
  high-volume change — the right shape for a single PR with a clean
  commit message and the substrate-walker run as the test signal,
  but the diff is unavoidably large.
- **Git history readability.** `git log` for `MOD_A_OrgPath_Codebook.md`
  becomes a `git log --follow` for
  `UIAO_151_OrgPath_Codebook.md`. The `--follow` resolution works but
  is one indirection slower than before.
- **External references in `inbox/` and `docs/` may not all retarget
  in this pass.** The 41-file inventory above is `src/uiao/`-only;
  prose references in `inbox/`-staged material or in `docs/` site
  pages are out of scope for the canon-integrity gate and may
  retain `MOD_*` slugs until they themselves are revised. The
  redirect table in §7 is the safety net.
- **ADR-044 becomes partially superseded.** ADR-044 §"Canon-consumer
  rule" promoted the orgtree corpus to canon; ADR-060 changes the
  registry topology that decision implied. ADR-044 is *not* superseded
  in spirit — its substrate-realignment decision stands — but the
  `related_adrs` cross-reference here exists so a future reader can
  see that ADR-060 amends the orgtree-registry portion of ADR-044.

### Neutral

- The MOD_xxx-as-namespace pattern was the right call for the
  inbox-promotion in ADR-044 (it kept the docx-derived corpus
  isolated while it was still being shaped). It became the wrong
  call once the corpus stabilized and the rest of canon caught up.
  ADR-060 retires the namespace, not the choice that created it.

## Implementation steps (for the follow-on PR — not this one)

1. Stage the 22 file moves with `git mv` to preserve history.
2. Apply the frontmatter changes per §5 (sed-driven across the 22
   files; review by hand for the `provenance:` block).
3. Run a single search-and-replace pass across the 41 files in §4 for
   the 22 slugs (longest-first to avoid `MOD_A` matching inside
   `MOD_AS` — none exist today, but the sort-order discipline
   matters).
4. Insert the 22 new entries into
   `src/uiao/canon/document-registry.yaml` at numeric position.
5. Delete `src/uiao/modernization/orgtree/document-registry` (the `.yaml` registry retired by this ADR).
6. Rewrite `src/uiao/modernization/README.md` per §2.
7. Run `uiao substrate walk` and `uiao substrate drift`. Both must
   return clean (zero P1; P2-only output is acceptable per ADR-044's
   gate semantics).
8. Run `pytest tests/canon_registry/` — confirm the parametrized
   registry-integrity test covers all 22 new ids.
9. Land the implementation PR with this ADR cited in the commit
   message and PR body.

## Out of scope

- Any change to `MOD_*` document **content**. Frontmatter and slug
  references only.
- Any change to the Track 2 (UIAO_135 / UIAO_136 / Spec2-*) corpus.
- Any change to adapter behavior. Adapters' `canon_refs` strings are
  retargeted; their inputs, outputs, and `evidence-class` are
  untouched.
- Any change to the orgpath data YAMLs' *structure*. Only the
  `# Bound to MOD_X` style comment headers in those files are
  rewritten.
- The Track 1 / Track 2 reconciliation note. ADR-060 is the
  registry-flatten decision; the cross-track contract (which doc
  wins on conflict for the small overlap surface) is a separate
  concern that can be authored as a §6 of `UIAO_135` or as a
  follow-on ADR. ADR-060 does not pre-decide.
