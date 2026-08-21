---
adr_id: adr-127
title: "Hybrid OrgPath Model — Model C Facets Plus Derived Canonical Path with Trailing Delimiter"
status: ACCEPTED
decided: 2026-07-07
deciders: Michael Stratton
updated: 2026-07-07
next_review: 2027-01-07
review_trigger: A tenant deployment validates the derived path against a real directory; the Azure Policy `like` literal-pipe footnote is confirmed (or refuted) in a live tenant; a fourth hierarchy facet is proposed for derived_from; directory schema extensions escape the 15-slot cap (would reopen the slot-15 binding)
supersedes: null
superseded_by: null
amends:
  - adr-063-orgpath-storage-slot-binding.md
  - adr-078-orgpath-attribute-schema-15-facet.md
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-127-orgpath-hybrid-derived-path.html
impact: 'Establishes the Hybrid-C+Path model: the ADR-078 Model C facet decomposition stays canonical on extensionAttribute1-14 (governance layer), and a derived canonical OrgPath string lands on extensionAttribute15 (inheritance layer), restoring the subtree-prefix targeting Model C removed. Every segment of the derived path — including the last — is terminated by "|", making -startsWith / `like` prefix matching collision-free. Amends ADR-063 (the composite-path slot binding moves from extensionAttribute1 to extensionAttribute15; extensionAttribute1 remains the region facet per ADR-078) and ADR-121 (attributes written per object rises from 6 to 7). Touches codebook.yaml (+hybrid block, org_path facet), codebook.schema.json (v2.1.0), the Python loader, and ships the UIAO.OrgPath PowerShell module (New-OrgPath, Get-OrgPathPrefix, Test-OrgPathDrift, Update-OrgAttributes).'
---

# ADR-127: Hybrid OrgPath Model — Model C Facets Plus Derived Canonical Path with Trailing Delimiter

## Status

**ACCEPTED** — 2026-07-07

Amends **ADR-063** (OrgPath storage slot binding) and **ADR-078** (Model C
15-facet schema). Neither is superseded outright: ADR-078's facet
decomposition is untouched, and ADR-063's slot-binding *doctrine* (a single
ratified, non-tenant-overridable slot for the composite path) is retained —
only the slot itself moves. See §Reconciliation with ADR-063.

> Planning references to this decision as "ADR-079" predate this record.
> ADR-079 was already allocated (governance principle reconciliation), so
> the hybrid model lands here as ADR-127. The content is unchanged.

## Context

ADR-078 replaced the Model A composite path (`extensionAttribute1 =
"ORG-FIN-AP-EAST"`) with Model C: fifteen slots, one semantic facet per
slot, boolean composition in dynamic groups and Conditional Access. That
fixed everything Model A did badly — per-facet validation, lifecycle
dates as first-class data, clearance/persona targeting — but it silently
dropped the one thing the composite path did well: **subtree
inheritance**. With facets alone there is no single expression for "this
node and everything beneath it." A branch policy must enumerate its
descendant facet combinations, and a reorganization that adds a level
under a division requires touching every rule that approximated the
subtree.

Book 18's capability matrix claims "composable org hierarchy with
inheritance" as a substrate row OrgPath uniquely owns. After ADR-078 that
row was aspiration, not mechanism.

The naive restoration — write a composite path string alongside the
facets and prefix-match it — has a known defect that Model A carried
silently: **prefix collision**. A rule targeting the `East` division with
`-startsWith "Division=East"` also matches `Division=Eastern` and <!-- orgpath-prefix-allow: deliberately shows the broken form -->
`Division=Easton`. Model A's hyphen-delimited paths had exactly this
ambiguity class, and it is unauditable because the rule *looks* correct.

## Decision

**Adopt the Hybrid-C+Path model: two layers over the same fifteen
extensionAttribute slots.**

1. **Governance layer — `extensionAttribute1-14` (unchanged).** The
   ADR-078 Model C facet decomposition remains the canonical schema:
   slots 1-10 carry the named facets, slots 11-14 remain reserved for
   tenant extension, per-facet validation and ADR-121 projection apply
   exactly as before.

2. **Inheritance layer — `extensionAttribute15`.** Slot 15 (previously
   `reserved_15`) now carries the **derived canonical OrgPath**: a
   string composed from the governance-layer hierarchy facets, in
   order `region`, `department`, `division`, as `Label=value` segments
   delimited by `|`:

   ```
   extensionAttribute15 = "Region=NCR|Department=IT|Division=CyberOps|"
   ```

   The value is **derived data** — never hand-authored, always
   recomputable from the governance layer. Composition truncates at the
   first unpopulated facet (the path is a contiguous hierarchy prefix).
   Any divergence between the stored value and the recomputed value is
   drift (`Test-OrgPathDrift`; the drift engine validates the slot as a
   typed facet, `org_path`).

3. **Trailing delimiter — always present.** Every segment, *including
   the last*, is terminated by `|`. This is the collision fix:

   ```
   prefix "Division=East|"  matches  "…Division=East|"        (the subtree)
   prefix "Division=East|"  misses   "…Division=Eastern|…"    (sibling)
   prefix "Division=East|"  misses   "…Division=Easton|…"     (sibling)
   ```

   Every `-startsWith` (Entra dynamic groups) and `like` (Azure Policy)
   prefix expression against the derived path MUST include the trailing
   delimiter. `Get-OrgPathPrefix` normalizes prefixes (idempotently);
   CI lints policy definitions and dynamic-group-rule files for
   violations and fails the build on a prefix missing its terminator.

4. **Codebook binding.** `codebook.yaml` v2.1.0 declares the model in a
   top-level `hybrid` block (name `Hybrid-C+Path`, status ACCEPTED,
   version 2026-07-07, delimiter `|`, `trailing_delimiter: always
   present`) and binds the `org_path` facet to `extensionAttribute15`
   as `kind: typed` with a pattern requiring the trailing delimiter.
   The loader validates that `derived_from` names declared, projected
   facets and that the layer's slot matches the facet binding.

5. **Write path.** The `UIAO.OrgPath` PowerShell module
   (`tools/powershell/UIAO.OrgPath/`) ships the operator surface:

   - `New-OrgPath` — composes the derived path; output always ends in `|`.
   - `Get-OrgPathPrefix` — normalizes a subtree prefix for
     `-startsWith` / `like` use; idempotent.
   - `Test-OrgPathDrift` — compares stored vs recomputed derived path.
   - `Update-OrgAttributes` — stamps governance facets and the derived
     path in one Graph update, per object type: **users** via
     `Update-MgUser` with `onPremisesExtensionAttributes`; **devices**
     via `Update-MgDevice` with `extensionAttributes` (devices do not
     have `onPremisesExtensionAttributes`; the property differs by
     object type and using the user property against a device is
     wrong).

## Reconciliation with ADR-063

ADR-063 ratified `extensionAttribute1` as the composite OrgPath slot,
with rationale ("first slot maximizes operator legibility") written when
the composite path was the *only* OrgPath expression. ADR-078 then bound
`extensionAttribute1` to the `region` facet without formally amending
ADR-063 — the two ADRs have contradicted each other since 2026-05-22.

This ADR resolves the contradiction by **amending ADR-063 as follows**:

- The composite-path storage slot is `extensionAttribute15`, not
  `extensionAttribute1`. `extensionAttribute1` belongs to the `region`
  facet per ADR-078.
- ADR-063's doctrine survives intact where it does not name the slot:
  single ratified slot, no per-tenant override, the rebind procedure
  for occupied slots (§Decision 3), and the `DRIFT-SCHEMA::slot-occupied`
  follow-up (delivered by ADR-064) now apply to `extensionAttribute15`.
- ADR-063's per-object-type table is corrected by this ADR's write-path
  clause: users store the slots under `onPremisesExtensionAttributes`,
  devices under `extensionAttributes`, and the Azure resource plane
  continues to use the ARM tag named `OrgPath` (whose value is the
  derived path, trailing delimiter included).

ADR-063 carries a matching amendment note pointing here.

## Rationale

1. **Facets alone cannot express inheritance; a path alone cannot
   express facet semantics.** The two layers answer different queries.
   "Everyone in IT/CyberOps and below, at any future depth" is one
   prefix predicate against the derived path. "Privileged, cleared,
   NCR-based" is boolean facet composition. Choosing one mechanism
   forfeits the other's queries; deriving the second from the first
   costs one slot and zero new sources of truth.

2. **Derived, not dual-authored.** The failure mode of storing a path
   *and* facets is divergence. The hybrid model forecloses it
   structurally: the path is a pure function of the facets, the writers
   recompute it on every stamp, and the drift engine flags any stored
   value that does not equal the recomputation.

3. **The trailing delimiter is the difference between a mechanism and a
   bug factory.** Prefix matching without a terminator is subtly wrong
   in a way reviews don't catch (`East` vs `Eastern`). Making the
   terminator part of the canonical value — not a convention callers
   must remember — moves the correctness burden from every rule author
   to the one writer, and makes violations lintable.

4. **Slot 15, not slot 1.** ADR-063's "first slot" legibility argument
   is obsolete — under Model C the operator-legible surface is the
   facet layer. The *last* slot is the natural home for the one
   attribute that is machine-derived: it leaves slots 11-14 contiguous
   for tenant extension and avoids renumbering any ADR-078 binding.

## Consequences

### Positive

- Subtree inheritance returns: one dynamic-group rule
  (`device.extensionAttribute15 -startsWith "Region=NCR|Department=IT|"`)
  covers a branch and every future descendant, with no enumeration and
  no reorganization rewrites.
- The Book 18 capability-matrix row "composable org hierarchy with
  inheritance" is a shipping mechanism again, now honestly described as
  the two-layer model.
- Prefix collision (`East`/`Eastern`/`Easton`) is structurally
  impossible for rules that pass the CI lint.
- Governance-layer consumers (per-facet validation, boolean
  composition, ADR-121 projection) are untouched.

### Negative / deferred

- Attributes written per object rises from 6 to 7 (the ADR-121
  projection count plus the derived path). The slot-scarcity ledger
  loses `extensionAttribute15` as tenant-extension headroom.
- Hybrid-synced users' `onPremisesExtensionAttributes` are read-only in
  the cloud (ADR-121's trap): for synced users the derived path must be
  stamped on-prem and allowed to sync, or deferred until cloud-only.
- The derived path duplicates information already in slots 1-3. That
  redundancy is the cost of prefix queries; the drift engine polices
  it.
- `derived_from` is fixed at region/department/division. Deeper
  hierarchies (ADR-062 allowed 8 segments in Model A) need a
  follow-up ADR to extend the composition.

## Footnote: Azure Policy `like` and the literal `|`

The Azure Policy condition grammar documents exactly one wildcard for
`like`/`notLike` — `*` (one occurrence permitted). The pipe character
has no special meaning in that grammar, so
`"like": "Region=NCR|Department=IT|*"` treats every `|` as a literal
and the trailing-delimiter contract holds for Azure Policy consumers
the same way it does for Entra `-startsWith`.

**Verification status:** documented behavior, confirmed against the
Azure Policy condition reference; a live-tenant/sandbox confirmation
(assign a test policy whose `like` value contains `|` and observe
evaluation) could not be run at decision time because no tenant was
attached. This is flagged as a manual verification step in the
delivering PR; record the result here when performed.

## Related work

- ADR-063 ratified the composite-path slot binding this ADR amends.
- ADR-078 established the Model C facet decomposition this ADR builds on.
- ADR-121 defined the projection subset; the derived path joins it as
  the seventh projected attribute.
- ADR-036 / ADR-039 ship the dynamic-group and policy-targeting
  libraries where branch (prefix) rules become expressible again.
