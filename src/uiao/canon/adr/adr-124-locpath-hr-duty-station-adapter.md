---
adr: ADR-124
title: "LocPath HR Duty-Station Adapter — Read-Only Conformance Adapter for Primary LocPath Assignment"
status: Proposed
date: "2026-06-25"
author: WhalerMike
supersedes: []
superseded_by: null
related:
  - ADR-088   # HR as OrgTree truth source (doctrine extended here to physical placement)
  - ADR-092   # Active governance — control/data-plane boundary governs adapter posture
  - ADR-102   # LocPath location addressing — authorizes this implementation phase
  - ADR-108   # Addressing-plane drift gate — drift classes produced by this adapter route here
  - ADR-125   # LocPath drift taxonomy extension — drift classes this adapter triggers
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-124-locpath-hr-duty-station-adapter.html
---

# ADR-124: LocPath HR Duty-Station Adapter

## Context

ADR-102 D6 authorizes a sequenced implementation phase for LocPath. Item 2 in
that sequence is:

> The HR duty-station → LocPath conformance adapter (read-only, provenance-anchored).

ADR-088 established the workforce HR system of record as the authoritative
upstream source for *organizational* placement. ADR-102 D3 extends the same
doctrine to *physical* placement: the HR duty-station/work-location assignment
is the authoritative source for a person's Primary LocPath. This ADR specifies
the adapter that materializes that doctrine — how UIAO reads HR duty-station
data, maps it to a LocPath node, validates that the node exists in the governed
LocPath registry, and surfaces non-conforming assignments as drift.

The adapter is read-only in phase 1. It consumes HR duty-station records and
writes to the UIAO evidence graph; it does not write back to the HR system
(consistent with ADR-092's control-plane/data-plane boundary: UIAO governs and
reconciles, it does not replace the HR system of record).

## Decision

### D1. Adapter identity and registration

The adapter is registered in `src/uiao/adapters/locpath-hr-duty-station/` and
declared in `src/uiao/canon/adapter-registry.yaml` as:

```yaml
- id: locpath-hr-duty-station
  status: active
  phase: 1
  abstract_type: LocPathConformanceAdapter
  source: HR duty-station field (ADR-088 HR system of record)
  plane: addressing
  certificate-anchored: false
```

The adapter follows the conformance-adapter pattern from ADR-035 (OrgPath
codebook binding) applied to the addressing plane: it validates assignments
against the canonical registry, emits conformant assignments as evidence, and
flags non-conforming ones as drift.

### D2. Mapping table: HR duty-station codes → LocPath nodes

HR systems of record express location as a duty-station string or code that is
HR-system-specific (e.g., `HQ-DC`, `FIELD-CHI`, `REMOTE`). These codes have
no canonical hierarchy and differ across HR platforms.

The adapter maintains a **duty-station mapping table** at
`src/uiao/canon/data/locpath/duty-station-map.yaml` that translates HR
duty-station codes to LocPath node paths. A mapping entry is:

```yaml
- hr_code: "HQ-DC"
  locpath: "/US/DC/HQ-Main"
  site_node_id: "site-us-dc-hq-main"
  canonical_since: "2026-06-25"
  notes: "Maps legacy code to canonical site node"
```

The mapping table is governed canon: changes require a PR reviewed by
canon-steward. A duty-station code with no mapping entry is treated as
`DRIFT-LOCPATH-UNMAPPED` (see ADR-125).

The LocPath node referenced in each mapping entry must exist in the LocPath
node registry at `src/uiao/canon/data/locpath/nodes.yaml` (established in
ADR-102 D6 item 1). A mapping that references a non-existent node is itself
a schema violation that blocks the adapter from starting.

### D3. Conformance check: assigned → governed

On each adapter run (scheduled cadence: daily, same as OrgPath conformance
adapters), the adapter:

1. Reads the full duty-station assignment roster from the HR system of record.
2. For each assignment, looks up the HR code in the duty-station mapping table.
3. If found: resolves the LocPath node and validates the node exists in the
   registry and carries the required minimum attributes (E911 civic address,
   `diaApproved` status, `telemetryBoundary` classification per UIAO_194).
4. If not found: emits `DRIFT-LOCPATH-UNMAPPED` for the identity.
5. For resolved assignments: emits a conformant `PrimaryLocPath` evidence
   record to the UIAO evidence graph, stamped with `detected_at`, the HR
   source system, and the mapping table version used.

The evidence record schema is:

```yaml
subject: "{identity_id}"
dimension: locpath
record_type: PrimaryLocPath
value: "/US/DC/HQ-Main"
source: hr-duty-station-adapter
hr_code: "HQ-DC"
mapping_table_version: "2026-06-25"
detected_at: "2026-06-25T14:00:00Z"
confidence: governed   # governed | inferred | observed
```

### D4. Phase-1 posture: read-only, never-autofix

In phase 1, the adapter never writes to the HR system, never modifies the
LocPath node registry, and never auto-assigns a Primary LocPath to an identity
without an HR source record. These constraints are enforced in code, not just
policy. The adapter's drift posture for all events it emits is `never-autofix`
per the ADR-108 drift gate (addressing-plane drift does not autofix without an
explicit ADR upgrade).

### D5. Assigned vs. observed divergence

When Dynamic Location Context signals (per ADR-102 D2) report a persistent
observed location that differs from the governed Primary LocPath, the adapter
emits `DRIFT-LOCPATH-DIVERGENCE` (defined in ADR-125). Divergence is flagged
only when the observation is stable across at least 3 consecutive collection
cycles (to suppress transient travel noise) and the delta exceeds the
site-level threshold (i.e., the observed location maps to a different LocPath
site node than the assigned Primary LocPath).

The `DRIFT-LOCPATH-DIVERGENCE` event carries:
- `assigned_locpath`: the governed Primary LocPath from the HR record
- `observed_locpath`: the site node the observational signal maps to
- `observation_source`: the Dynamic Location Context source (Wi-Fi, GPS, etc.)
- `consecutive_cycles`: the number of consecutive cycles showing divergence

## Consequences

**Positive.** The Primary LocPath becomes a governed, evidence-backed attribute
for every identity in scope, replacing the implicit "wherever HR last set their
duty station" with a validated, drift-detected assignment. E911 configuration,
TIC 3.0 DIA policy, and telemetry boundary rules gain a reliable policy subject.

**Negative.** The duty-station mapping table is a maintained artifact that grows
with the agency's HR code vocabulary and changes when sites are renamed or
restructured. Stale mapping entries produce silent mis-assignments (the code maps
but to the wrong node); the adapter's node-existence check catches this if the
old node is removed but not if it is renamed. Mitigation: site renames must
trigger a mapping table review as part of the LocPath node registry update PR.

**Neutral.** The adapter does not create or replace any HR system of record
capability. It reads and validates. The HR system continues to hold the
duty-station assignment as the authoritative record.

## Implementation notes

- Adapter entry point: `src/uiao/adapters/locpath-hr-duty-station/__init__.py`
- Mapping table: `src/uiao/canon/data/locpath/duty-station-map.yaml`
- Node registry: `src/uiao/canon/data/locpath/nodes.yaml` (ADR-102 D6 item 1)
- Test fixture: at least one `DRIFT-LOCPATH-UNMAPPED` case and one conformant case
  must be covered in the adapter's test suite.
- The adapter is inactive until `src/uiao/canon/data/locpath/nodes.yaml` exists
  with at least one node entry; it raises `LocPathRegistryEmpty` otherwise.

## Related

- [ADR-102 — LocPath Location Addressing](./adr-102-locpath-location-addressing.md)
- [ADR-125 — LocPath Drift Taxonomy Extension](./adr-125-locpath-drift-taxonomy.md)
- [ADR-088 — HR as OrgTree Truth Source](./adr-088-hr-as-orgtree-truth-source.md)
- [ADR-092 — Active Governance](./adr-092-active-governance.md)
- [UIAO_194 — LocPath Codebook](../UIAO_194_LocPath_Codebook.md)
