---
document_id: UIAO_179
title: "Canonical Drift Output Schema — Unified DriftRecord and Facet Mapping"
version: "1.0"
status: Draft
owner: Michael Stratton
created_at: "2026-05-18"
updated_at: "2026-06-17"
# Draft canon, pending reconciliation review (see PR #556). Will flip
# to true and gain a docs/.qmd entry once status moves to Current.
publish_to_site: false
---

# UIAO_179 — Canonical Drift Output Schema

## Purpose

Specifies the canonical record shape that every UIAO adapter, classifier, and orchestrator emits when it observes a drift event. Unifies the per-adapter `DriftReport` shapes in `src/uiao/adapters/database_base.py` with the system-level taxonomy from ADR-012 and the object-level facet labels introduced by UIAO_177 and UIAO_178.

## Scope

Applies to every drift-emitting surface in the substrate: tag governance (UIAO_177), provisioning (UIAO_178), tenancy and authz supplements, OrgTree validators, conformance adapters, and the addressing-plane drift collector (UIAO_195). Does not replace ADR-012's drift class definitions; it consolidates how those classes are reported.

## Shared primitive — `drift_core`

As of ADR-108, the substrate uses a shared plane-agnostic primitive at
`src/uiao/governance/drift_core.py`. Every plane's collector imports
`Finding`, `Severity`, `Posture`, `gate`, and `events_json` from this module
rather than duplicating them. The `Finding.to_event()` method emits an ODR
telemetry event that aligns with the `DriftRecord` shape below.

Callers that need the full `DriftRecord` (including `object_id`, `object_facet`,
`recommended_action`, and `correlation_id`) wrap `Finding` at the
orchestration layer; `drift_core` stays minimal and plane-agnostic.

`drift_core` severity (P1/P2/P3) maps to `DriftRecord` severity as follows:

| `drift_core.Severity` | `DriftRecord.severity` |
|---|---|
| P1 | `critical` |
| P2 | `high` |
| P3 | `medium` |

## Record shape

`DriftRecord` is the canonical output. Every emitter SHOULD produce records that satisfy this schema; CLI and Evidence Graph consumers MAY assume the schema.

| Field                | Type     | Required | Notes                                                                             |
|----------------------|----------|----------|-----------------------------------------------------------------------------------|
| `object_id`          | string   | yes      | Canonical principal, resource, or artifact identifier.                            |
| `drift_class`        | enum     | yes      | One of the six ADR-012 classes (`DRIFT-SCHEMA` … `DRIFT-BOUNDARY`).               |
| `object_facet`       | enum     | yes      | `identity` \| `access` \| `resource` \| `tag` \| `device` \| `boundary` \| `semantic`. |
| `expected_value`     | any      | yes      | Canonical desired state. `null` when the canonical answer is "must not exist".    |
| `actual_value`       | any      | yes      | Observed state. `null` when the object does not exist.                            |
| `severity`           | enum     | yes      | `low` \| `medium` \| `high` \| `critical`. Aligned with UIAO_110.                 |
| `recommended_action` | string   | yes      | Short imperative (e.g. `overwrite-canonical-tag`, `remove-forbidden-key`).        |
| `first_observed`     | ISO 8601 | yes      | UTC timestamp of the first observation of this drift.                             |
| `last_observed`      | ISO 8601 | yes      | UTC timestamp of the most recent observation. Equal to `first_observed` on first emit. |
| `source_adapter`     | string   | yes      | Adapter or module identifier (e.g. `entra-adapter`, `provisioner`).               |
| `correlation_id`     | string   | no       | Caller-supplied correlation key, propagated end-to-end.                           |

Implementations expose `to_dict()` returning the field set above with timestamps serialised to ISO 8601.

## Facet → class mapping

`object_facet` does not replace `drift_class`; the two are independent axes. The expected mapping in normal operation is:

| `object_facet` | Typical `drift_class`              |
|----------------|------------------------------------|
| `identity`     | `DRIFT-IDENTITY`                   |
| `access`       | `DRIFT-AUTHZ`                      |
| `resource`     | `DRIFT-SCHEMA` or `DRIFT-IDENTITY` |
| `tag`          | `DRIFT-SCHEMA` or `DRIFT-SEMANTIC` |
| `device`       | `DRIFT-IDENTITY`                   |
| `boundary`     | `DRIFT-BOUNDARY`                   |
| `semantic`     | `DRIFT-SEMANTIC`                   |

Any combination outside the typical mapping is permitted but MUST be justifiable in the emitter's docstring.

## Severity policy

- `low` — informational; observed-state difference does not violate canon.
- `medium` — canon violated, no immediate impact on authorisation or boundary.
- `high` — canon violated and reaches an authorisation surface (RBAC, group, conditional access).
- `critical` — boundary violation (`DRIFT-BOUNDARY`) or identity-state corruption (`DRIFT-IDENTITY` where the principal is unrecoverable from canonical state).

The orchestrator escalation thresholds in UIAO_167 reference these levels by name.

## Implementation surface

- `src/uiao/governance/drift_output.py` — `DriftRecord` dataclass, `ObjectFacet` literal, factory helpers.
- `src/uiao/adapters/database_base.py` — `DriftReport` retained for back-compat; new code SHOULD emit `DriftRecord` directly.
- `src/uiao/evidence/graph.py` — Evidence Graph consumers index records by `(object_id, drift_class, object_facet)`.

## Backward compatibility

Existing `DriftReport` instances continue to validate. A converter (`drift_record_from_report()`) yields the canonical shape from legacy reports; classifiers under `src/uiao/governance/drift.py` adopt `DriftRecord` directly.

## Out of scope

- Drift remediation policy (UIAO_111 enforcement runtime).
- Drift severity scoring at the Risk layer (UIAO_170).
