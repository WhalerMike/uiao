---
document_id: UIAO_163
title: "Appendix M — Drift Detection Engine Specification (Model C)"
version: "2.0"
status: Current
classification: CANONICAL
owner: Michael Stratton
created_at: "2026-04-18"
updated_at: "2026-05-24"
boundary: GCC-Moderate
provenance_flatten:
  prior_id: "MOD_M"
  flattened_at: "2026-05-10"
  flattened_by: "ADR-060"
---

# Appendix M — Drift Detection Engine Specification (Model C)

> **Model C — per-facet drift over 10 named attribute slots (per [ADR-078](adr/adr-078-orgpath-attribute-schema-15-facet.md)).** The drift engine validates each principal's 10 named facet values independently against the codebook (per-facet enumeration membership for enumerated facets; `value_pattern` regex for typed facets; null check for reserved facets). The five drift categories — **Format**, **Value**, **Slot** (Model C codebook integrity), **Orphan**, **Phantom** — operate per-facet: a finding names the specific slot and facet that disagrees. The customer-facing prose tour is the [Drift Walk-through](../../docs/customer-documents/reference-architecture/drift-walkthrough.qmd). The runtime drift engine implementation (`src/uiao/governance/drift_engine.py`) was retired by ADR-078 Phase 1; the per-facet rebuild is scheduled in Phase 5. This appendix is the v2.0 Model C rewrite; the prior Model A composite-string spec is fully superseded.

## Purpose

This appendix defines the complete specification for the automated drift detection engine under Model C, including its architecture, the five per-facet drift categories, detection rules, snapshot schema, comparison algorithm, and alert routing.

## Scope

The engine monitors all identity objects (users, service principals), dynamic groups, administrative units, and devices within the M365 GCC-Moderate boundary. It compares observed tenant state against the canonical baseline continuously, with **per-facet validation** as the central operational unit: each principal's 10 named `extensionAttribute*` slot values are validated independently against their facets' enumerations or typed patterns.

## Canonical Structure

The engine operates as a six-phase loop, unchanged from prior versions:

```
Snapshot ──▶ Compare ──▶ Classify ──▶ Alert ──▶ Remediate ──▶ Verify
   │                                                              │
   └──────────────────────── re-scan ◀────────────────────────────┘
```

1. **Snapshot.** Pull current tenant state via Microsoft Graph — users, groups, AUs, role assignments, device records. For each principal, capture all 10 named facet slot values (`extensionAttribute1`–`extensionAttribute10`).
2. **Compare.** Diff each principal's 10 facet values against the loaded codebook (per-facet enumeration membership for enumerated facets; typed-facet pattern match for typed facets).
3. **Classify.** Map each per-facet diff to one of the five categories below, with severity (P1–P4) and an auto-fix policy.
4. **Alert.** Emit `DriftFinding` objects into the Evidence Fabric for immutable, hash-chained recording.
5. **Remediate.** If `dry_run=false` and the finding is auto-remediable, apply the fix via the Execution Substrate. Governance-review ops (phantom deletions, AU cascades, cross-surface device equality) are never auto-applied.
6. **Verify.** Re-snapshot to confirm. Operator-triggered in v1; future versions close the loop automatically.

## The Five Drift Categories (Per-Facet)

| Category | What broke | Severity | Auto-fix? |
|---|---|---|---|
| **Format** | A typed facet's value fails its `value_pattern` regex (or `value_type` constraint) | P1 | No — typed-pattern failures usually indicate upstream script bugs that should be debugged, not patched |
| **Value** | An enumerated facet's value is not in the facet's `enumeration` list (or is in the list with `status: deprecated` without a `replaced_by` successor) | P2 | Sometimes — when the HR source is authoritative, write-back from HR is applied; for non-HR-driven principals (devices, SPs) the finding flags for human review |
| **Slot** | A facet's `attribute:` was rebound without a superseding ADR, or two facets in the loaded codebook bind the same `extensionAttribute*` slot | P1 | No — codebook integrity issue requiring governance action, never auto-remediated |
| **Orphan** | A facet enumeration value has zero matching principals across the tenant | P3 | Flag only — the enumeration entry might be a placeholder for an expected hire; deletion requires governed PR |
| **Phantom** | A principal carries a value that's been deprecated in the codebook (`status: deprecated`) | P3 | Reassign when `replaced_by` is set; flag for manual reassignment when not |

### Format Drift detail

Format Drift applies only to typed facets (currently `HireDate` at `extensionAttribute7` and `TermDate` at `extensionAttribute8`; tenant-declared typed facets in slots 11–15 also qualify). The check is the facet's `value_pattern` regex plus the `allow_empty` flag.

### Value Drift detail

Value Drift applies to enumerated facets (8 of the 10 named facets, plus tenant-declared enumerated facets in slots 11–15). A value present in the enumeration with `status: active` validates cleanly. A value present with `status: deprecated` is classified as **Phantom**, not Value Drift. A value not in the enumeration at all is Value Drift.

### Slot Drift detail

Slot Drift is the **codebook integrity** category introduced by Model C. Two manifestations:

1. **Slot rebinding without ADR.** The loaded codebook declares a facet's `attribute:` pointing at a different slot than the version of the codebook signed by the most recent ADR-078-class governance action. Surfaces as a Slot Drift on the rebound facet.
2. **Slot collision.** Two facets in the loaded codebook bind the same `extensionAttribute*` slot. Caught by the Python loader's `_validate_integrity` step before the engine even runs Compare — but if a runtime mutation introduces the collision after load (e.g., hot-reload from disk), the engine surfaces it as Slot Drift.

Slot Drift cannot be auto-remediated. The fix is always a governance action: either a superseding ADR (intentional rebinding) or a PR reverting the unsanctioned change (accidental rebinding).

### Orphan Drift detail

Orphan Drift is detected once per facet enumeration value per scan. A facet value with zero matching principals across the tenant flags as Orphan. The engine never auto-deletes — the enumeration entry might be a placeholder for an expected hire, a structural reservation for a planned reorganization, or a value used only by service accounts that the scan deliberately excluded.

### Phantom Drift detail

Phantom Drift is the inverse of Orphan: a principal carries an enumeration value whose codebook entry now has `status: deprecated`. When the codebook entry has `replaced_by` set, the engine auto-reassigns the principal to the successor value (and emits the auto-fix into the Evidence Fabric). When `replaced_by` is absent, the engine flags for manual reassignment.

## Detection Rules (Per-Facet)

The engine's detection logic iterates every principal × every facet:

```text
FOR EACH principal IN snapshot.principals:
    FOR EACH facet IN codebook.facets:
        value = principal.attributes[facet.attribute]
        result = ClassifyFacet(facet, value)
        IF result.is_drift:
            ADD DriftFinding(principal, facet, result) TO findings
```

`ClassifyFacet` per facet kind:

```text
FUNCTION ClassifyFacet(facet, value):
    SWITCH facet.kind:
        CASE 'enumerated':
            entry = facet.enumeration.find(e => e.value == value)
            IF entry IS NULL:
                RETURN ValueDrift(facet, value)
            IF entry.status == 'deprecated':
                RETURN PhantomDrift(facet, value, entry.replaced_by)
            RETURN OK
        CASE 'typed':
            IF value IS NULL OR value == '':
                RETURN facet.allow_empty ? OK : FormatDrift(facet, value)
            IF NOT value MATCHES facet.value_pattern:
                RETURN FormatDrift(facet, value)
            RETURN OK
        CASE 'reserved':
            IF value IS NOT NULL AND value != '':
                RETURN ValueDrift(facet, value, reason='reserved slot has value')
            RETURN OK
```

Orphan detection runs once per scan across the populated facet:

```text
FOR EACH facet IN codebook.facets WHERE facet.kind == 'enumerated':
    FOR EACH entry IN facet.enumeration WHERE entry.status == 'active':
        IF NO principal HAS principal.attributes[facet.attribute] == entry.value:
            ADD OrphanDrift(facet, entry.value) TO findings
```

Slot Drift runs once per scan across the loaded codebook:

```text
slot_to_facet = {}
FOR EACH facet IN codebook.facets:
    IF facet.attribute IN slot_to_facet:
        ADD SlotDrift(facet.attribute, slot_to_facet[facet.attribute], facet.name) TO findings
    ELSE:
        slot_to_facet[facet.attribute] = facet.name
```

## Snapshot Schema

A snapshot is a structured capture of tenant state at one moment. Per-principal shape:

```json
{
  "principal_id": "...",
  "principal_type": "user|device|servicePrincipal",
  "attributes": {
    "extensionAttribute1":  "EASTUS",
    "extensionAttribute2":  "IT",
    "extensionAttribute3":  "InfraOps",
    "extensionAttribute4":  "Engineer",
    "extensionAttribute5":  "CC-BAL",
    "extensionAttribute6":  "Employee",
    "extensionAttribute7":  "2024-01-15",
    "extensionAttribute8":  "",
    "extensionAttribute9":  "Secret",
    "extensionAttribute10": "Standard"
  }
}
```

For Arc-managed resources, the equivalent 10 ARM tags appear in the snapshot under `arm_tags` instead of `attributes` (see UIAO_011 / UIAO_012 for the device-plane storage doctrine).

## DriftFinding Shape (Per-Facet)

```json
{
  "phase": "facet-validate",
  "op": "facet-value-validate",
  "target": "user|alice@contoso.com",
  "facet": "department",
  "attribute": "extensionAttribute2",
  "observed_value": "IT-Sec",
  "reason": "extensionAttribute2 'IT-Sec' not in department enumeration. Suggested: 'IT' (Department) + 'CyberOps' (Division at extensionAttribute3).",
  "drift_class": "DRIFT-SEMANTIC",
  "drift_category": "Value",
  "severity": "P2",
  "auto_remediate": false,
  "snapshot_id": "...",
  "timestamp": "2026-05-24T18:00:00Z"
}
```

Drift-class mapping (preserved from v1 for back-compat with downstream consumers):

| `drift_category` | `drift_class` |
|---|---|
| Format | `DRIFT-SCHEMA` |
| Value | `DRIFT-SEMANTIC` |
| Slot | `DRIFT-SCHEMA::slot-occupied` (per ADR-063 sub-class) |
| Orphan | `DRIFT-SEMANTIC::orphan` |
| Phantom | `DRIFT-SEMANTIC::phantom` |

## Comparison Algorithm (Pseudocode)

```text
FUNCTION CompareTenantToBaseline(snapshot, codebook):
    findings = []

    FOR EACH principal IN snapshot.principals:
        FOR EACH facet IN codebook.facets:
            value = principal.attributes[facet.attribute]
            result = ClassifyFacet(facet, value)
            IF result IS NOT OK:
                ADD DriftFinding(principal, facet, result) TO findings

    FOR EACH facet IN codebook.facets WHERE facet.kind == 'enumerated':
        FOR EACH entry IN facet.enumeration WHERE entry.status == 'active':
            matching = snapshot.principals WHERE p.attributes[facet.attribute] == entry.value
            IF matching.count == 0:
                ADD OrphanDriftFinding(facet, entry.value) TO findings

    seen_slots = {}
    FOR EACH facet IN codebook.facets:
        IF facet.attribute IN seen_slots:
            ADD SlotDriftFinding(facet.attribute, seen_slots[facet.attribute], facet.name) TO findings
        seen_slots[facet.attribute] = facet.name

    FOR EACH group IN snapshot.dynamic_groups:
        canonical = library.find_by_name(group.name)
        IF canonical IS NULL:
            ADD PhantomGroupFinding(group) TO findings
        ELIF group.membershipRule != canonical.membershipRule:
            ADD RuleDriftFinding(group, expected=canonical.membershipRule, observed=group.membershipRule) TO findings

    RETURN findings
```

Per-facet validation is **per-clause** for dynamic group rule drift: a rule like `(extensionAttribute2 -eq "IT") and (extensionAttribute3 -eq "OldDivision")` that references a now-deprecated `OldDivision` value surfaces the second clause as a Phantom-facet finding while the first clause continues to validate cleanly. The engine does *not* fail the entire rule on one clause's drift.

## Alert Routing

Per-facet findings route to per-facet stewards. The codebook's `owner` field on each facet declaration specifies the responsible role; findings routing prepends the facet name and slot to the alert payload so triagers can scope investigation immediately.

Severity ladder for alerting (M365 Teams / email):

| Severity | SLA | Channel |
|---|---|---|
| P1 (Format, Slot) | 4 business hours | Teams DM to facet owner + governance steward |
| P2 (Value) | 1 business day | Teams channel post |
| P3 (Orphan, Phantom) | 5 business days | Daily digest email |
| P4 (informational) | — | Weekly summary |

## Boundary Rules

The drift detection engine reads tenant state exclusively through Microsoft Graph API within M365 GCC-Moderate. Per-facet writes (during auto-remediation) use the same Graph surface; for Arc-managed resources, ARM is the secondary transport (per ADR-038 dual-transport doctrine, rebuilt per-facet in ADR-078 Phase 5).

Alert routing uses M365 notification mechanisms (Teams, email) only.

## Drift Considerations

The engine specification itself is a governance artifact subject to Workflow 8. If the engine fails to detect a known per-facet drift condition (e.g., an enumeration miss, a Phantom value with `replaced_by`, a Slot collision), that constitutes an engine defect requiring immediate remediation.

The **cross-surface per-facet equality check** (device with `extensionAttribute*` on Entra and equivalent ARM tags on Arc) is deferred from v2.0; a future ADR (companion to the `DRIFT-SCHEMA::slot-occupied` sub-class deferred in ADR-063) will introduce per-facet cross-surface equality findings. Until then, cross-surface disagreement is detected on the next codebook-driven re-write rather than as a runtime drift event.

## Governance Alignment

This engine is the primary implementation of Principle 4 (Drift Resistance) under Model C. Per-facet validation provides continuous, automated, **independently-scoped** monitoring that makes drift a temporary condition on a single facet rather than a permanent or compounding state across the entire OrgPath surface. Per-facet decomposition also expresses Principle 5 (Composability): a deprecated enumeration value can be replaced facet-by-facet without coordinated rewrites across all consumers.
