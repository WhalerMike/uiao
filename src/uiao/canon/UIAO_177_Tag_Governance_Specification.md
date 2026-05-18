---
document_id: UIAO_177
title: "UIAO Tag Governance Specification"
version: "1.0"
status: Draft
classification: CANONICAL
owner: Michael Stratton
created_at: "2026-05-18"
updated_at: "2026-05-18"
boundary: GCC-Moderate
---

# UIAO Tag Governance Specification

## Goal

Provide a consistent metadata layer across Entra and Azure.

## Canonical tag rules

- Tags must follow a fixed schema defined by UIAO.
- Tags outside the schema are allowed but marked **non-canonical**.
- Tags that conflict with canonical tags are removed.
- Canonical tags are always overwritten by UIAO.

## Required canonical tags

| Tag | Type | Meaning |
|---|---|---|
| `uiao.org.path` | string | OrgTree lineage (canonical OrgPath value — see [UIAO_151_OrgPath_Codebook](UIAO_151_OrgPath_Codebook.md)). |
| `uiao.lifecycle` | string | One of `active`, `leave`, `disabled`. |
| `uiao.owner` | string | Identity ID of the owning principal. |
| `uiao.boundary` | string | Zone or boundary classification (see [UIAO_171_Multi-Cloud_Boundary_Model](UIAO_171_Multi-Cloud_Boundary_Model.md)). |

All four tags are required on every governed object in Entra and Azure.
Absence of a canonical tag is itself a drift event.

## Enforcement

- UIAO reads all tags.
- UIAO compares tags to schema.
- UIAO removes forbidden tags (tags that conflict with canonical tags).
- UIAO overwrites canonical tags (canonical values always win over tenant-side edits).
- UIAO logs drift events.

## Drift mapping

| Trigger | Drift class |
|---|---|
| A canonical tag is missing on a governed object. | `DRIFT-SCHEMA` |
| A canonical tag's value diverges from the UIAO-declared value. | `DRIFT-SEMANTIC` |
| A non-canonical tag conflicts with a canonical tag (same key, different namespace shape). | `DRIFT-SCHEMA` (resolved by removal). |
| A canonical tag is edited tenant-side after UIAO writeback. | `DRIFT-AUTHZ` (re-overwritten by UIAO; logged). |

Drift classes are defined in [`docs/docs/16_DriftDetectionStandard.qmd`](../../../docs/docs/16_DriftDetectionStandard.qmd).

## Related canon

- [UIAO_010_OrgPath_in_Azure_Policy](UIAO_010_OrgPath_in_Azure_Policy.md) — Arc-side `OrgPath` tag consumption by Azure Policy targeting.
- [UIAO_151_OrgPath_Codebook](UIAO_151_OrgPath_Codebook.md) — canonical vocabulary for `uiao.org.path` values.
- [UIAO_153_Attribute_Mapping_Table](UIAO_153_Attribute_Mapping_Table.md) — device-plane writeback origin for OrgPath tags.
- [UIAO_171_Multi-Cloud_Boundary_Model](UIAO_171_Multi-Cloud_Boundary_Model.md) — canonical vocabulary for `uiao.boundary` values.
- [UIAO_174_Governance_Telemetry_Model](UIAO_174_Governance_Telemetry_Model.md) — drift event emission surface.
