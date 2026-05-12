---
document_id: UIAO_144
title: "UIAO HRIT Productization Operational Spec"
version: "0.1"
status: Draft
classification: CANONICAL
owner: "Michael Stratton"
created_at: "2026-05-06"
updated_at: "2026-05-11"
boundary: "GCC-Moderate"
---

# UIAO HRIT Productization Operational Spec

> **Status:** Draft v0.1 — Phase 0 stub. Sections 4–9 are filled by the
> Batch A workstreams in `inbox/v0.6.0-hrit-productization/03-batch-plan.md`.
> Promoted to v1.0 when Batch A merges into the v0.6.0 RC1 integration
> branch. ADR-065 (renumbered from the original ADR-058 to resolve a
> slot collision with Microsoft Purview ADR-058) ratifies this spec as
> `accepted` per maintainer governance review.

## 1. Overview

This spec is the **operational counterpart** to UIAO_140 (Single-ATO
Reciprocity Model) and Spec2-D6.1 (Federal HRIT Integration Runbook).
It defines:

- **What runtime artifacts** UIAO produces to operationalize the
  Single-ATO reciprocity model (reciprocity records, per-agency
  bundles, ATO-cadence telemetry, configuration-latitude drift
  findings).
- **Which CLI commands** an agency operator invokes for each step
  of the reciprocity lifecycle.
- **Which evidence-graph nodes and edges** anchor reciprocity records
  to the controlling ATO decision.
- **Which KSIs** continuously evaluate reciprocity-program health.

Established under ADR-065 (originally drafted as ADR-058; see ADR for
renumber history). Authoritative for any UIAO deployment operating
under a single-tenant-of-record / multi-tenant-of-consumption
authorization model. Reference instance is the OPM Federal HRIT
Modernization platform (Solicitation 24322626R0007).

This spec is consumed by `uiao.oscal.reciprocity_record`,
`uiao.oscal.reciprocity_bundle`, `uiao.cli.reciprocity`,
`uiao.monitoring.ato_cadence`, `uiao.governance.config_latitude`, and
the KSI evaluation pipeline (`uiao.ksi`).

## 2. Scope

In scope (v0.6.0):
- Reciprocity-record artifact emission and signing
- Per-consuming-agency bundle aggregation
- Evidence-graph integration (`ato-decision` → `reciprocity-record`)
- ConMon SLA enforcement (30/45-day SSP cadence, 30-day reauth window)
- Configuration-latitude drift detection
- CLI surface: `uiao reciprocity {onboard-agency, list-records, verify}`
- KSI-RECIP-* rule family

Out of scope (v0.6.0; pursued in adjacent themes):
- Login.gov adapter implementation (ADR-056 Stage 3)
- KYC adapter implementation (ADR-055)
- Per-HRIT-system adapter coverage (Spec2-D6.1 §2 enumerates 12 systems;
  reference subset only in v0.6.0)
- Microsoft Tier-1 adapter completion (#299 follow-on)
- Transport plane (ADR-057 candidate, pending renumber)

## 3. Roles

Same role taxonomy as UIAO_140 §2 (System Operator, Authorizing
Official, Consuming Agency, Continuous Monitor). This spec adds:

| Role | Definition |
|---|---|
| **Reciprocity Operator** | Person or process invoking `uiao reciprocity onboard-agency` to emit a record for a consuming agency |
| **Bundle Verifier** | Person or process consuming a per-agency bundle outside the UIAO platform — typically a consuming-agency AO or auditor |

## 4. Reciprocity-Record Artifact

> **Filled by Batch A WS-A1 (schema) + WS-A2 (emitter).**

Defines:
- Required and optional fields
- Signing algorithm and signature scope
- Provenance-block contract
- Schema location: `src/uiao/schemas/reciprocity-record/reciprocity-record.schema.json`

## 5. Per-Agency Bundle Aggregation

> **Filled by Batch A WS-A6.**

Defines:
- Bundle composition (record + scoped component-definition + scoped
  assessment-results + provenance manifest)
- Self-verification contract (no UIAO platform access required)
- File-system layout under `<out-dir>/<consuming-agency-code>/`

## 6. Evidence Graph v1.2 Integration

> **Filled by Batch A WS-A3.**

Defines:
- New node types: `ato-decision`, `reciprocity-record`
- New edge types: `ato-decision → reciprocity-record`,
  `reciprocity-record → consuming-agency`
- Backward-compatibility statement (UIAO_113 v1.1 → v1.2)

## 7. ConMon SLA Enforcement

> **Filled by Batch A WS-A5.**

Defines:
- 30-day SSP draft deadline (UIAO_140 §4 line 63)
- 45-day SSP final deadline (UIAO_140 §4 line 65)
- 30-day reauthorization window (UIAO_140 §4 line 75 / ADR-054 line 131)
- CLI: `uiao conmon ato-cadence-check` semantics

## 8. Configuration-Latitude Drift Detection

> **Filled by Batch A WS-A7.**

Defines:
- SSP-side latitude table format
- Tenant-side configuration ingestion
- Drift class binding (DRIFT-SCHEMA, P2 default)
- CQL query for filtering latitude-class findings

## 9. CLI Surface

> **Filled by Batch A WS-A4.**

Sub-app: `uiao reciprocity`
- `onboard-agency` — emit a reciprocity record for a consuming agency
- `list-records` — enumerate registered reciprocity records
- `verify` — verify a record's signature

Cadence enforcement: `uiao conmon ato-cadence-check`

## 10. KSI Family

> **Filled by Batch A WS-A10.**

KSI-RECIP-001 through KSI-RECIP-008+. Each KSI maps to a NIST SP 800-53
control and emits a deterministic PASS/WARN/FAIL verdict.

## 11. Provenance

- Established by ADR-065 (originally ADR-058; renumbered to resolve slot collision)
- Operational counterpart to UIAO_140 (model) and Spec2-D6.1 (runbook)
- Amends UIAO_113 to v1.2 in §6
- HRIT traceability inherited from UIAO_140 / ADR-054

## 12. References

- ADR-054 (Single-ATO Reciprocity Model)
- ADR-065 (this spec's ratifying ADR; renumbered from ADR-058)
- UIAO_112 (Multi-Tenant Isolation v1.1)
- UIAO_113 (Evidence Graph — v1.2 in scope)
- UIAO_140 (Single-ATO Reciprocity Model)
- Spec2-D6.1 (Federal HRIT Integration Runbook v0.1)
- OPM Solicitation 24322626R0007 Amd 4
