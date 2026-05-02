---
deliverable_id: Spec2-D5.4
title: "HR System Onboarding Playbook"
spec: UIAO_136 / Spec 2 — HR-Agnostic Provisioning Architecture
phase: 5
status: Draft
version: 0.1
owner: Identity Architecture
created: 2026-05-02
updated: 2026-05-02
canonical_adrs:
  - ADR-003
canonical_docs:
  - UIAO_007
  - UIAO_136
upstream_deliverables:
  - Spec2-D1.1
  - Spec2-D1.7
  - Spec2-D3.2
  - Spec2-D5.1
sibling_deliverables: []
boundary: GCC-Moderate
classification: Controlled
---

# Spec 2 — D5.4: HR System Onboarding Playbook

> **Status (v0.1, 2026-05-02):** Initial canonical playbook. Used
> when the agency adds a new HR source system to an existing
> Spec 2 deployment (e.g., post-OPM-procurement when Workday or
> Oracle is selected; or when an agency adds a secondary HR source
> for a sub-org).

## 1. Purpose, Scope, and Reference

This deliverable is the canonical HR System Onboarding Playbook
called for in
[`UIAO_136`](../UIAO_136_priority1-transformation-project-plans.md)
§SPEC 2 → Phase 5 → D5.4:

> *Playbook for connecting a new HR system (when OPM selects
> Workday or Oracle): steps to configure native connector or
> middleware adapter, attribute mapping validation, test cycle,
> parallel run, cutover.*

D5.4 specifies the steps to add a new HR source. UIAO's design is
HR-system-agnostic (per ADR-003) — the playbook makes that
agnosticism actionable.

### 1.1 Scope

In scope:

- Per-vendor adapter implementation pattern.
- Per-vendor validation steps.
- Test cycle (mirroring D4.x at smaller scale).
- Parallel-run pattern.
- Cutover into production.

Out of scope:

- Vendor-specific connector / API details (those live in the
  per-vendor ADR + adapter code).
- HR-side procurement decisions (this playbook starts after the
  HR system is selected).
- Cross-source consolidation (when ingesting from N HR systems
  simultaneously) — covered in D4.2 §4.

## 2. Onboarding Phases

### 2.1 Phase A — Connector evaluation

| Step | Activity |
|---|---|
| A.1 | Cross-reference vendor against D1.7 connector matrix; confirm support category (native Microsoft connector / custom adapter / SCIM-conformant) |
| A.2 | If native Microsoft connector available: assess feature parity vs. D1.1 schema (per D1.7) |
| A.3 | If custom adapter required: scope adapter implementation effort |
| A.4 | Decision: native vs. custom. UIAO posture: prefer native when feature-parity is sufficient; custom adapter when D1.1 fields are missing from native |

### 2.2 Phase B — Adapter implementation (custom path)

When custom adapter required:

| Step | Activity |
|---|---|
| B.1 | Author per-vendor ADR documenting field mappings (vendor field → D1.1 canonical field) |
| B.2 | Implement adapter in `src/uiao/adapters/hr/<vendor>/` per the contract (D3.2 §2.2) |
| B.3 | Implement `produce_canonical_records()` exposing the canonical schema |
| B.4 | Add per-vendor unit tests |
| B.5 | Add per-vendor entry to D4.1 fixture (synthetic records) |
| B.6 | Run D4.2 integration tests against the new adapter (test tenant) |

### 2.3 Phase B' — Native connector configuration (if chosen)

| Step | Activity |
|---|---|
| B'.1 | Configure the native connector in Entra portal |
| B'.2 | Map the native connector's output to canonical UIAO fields via Layer-2 mapping (D3.4 §4) |
| B'.3 | Document the gap if any D1.1 field is unfillable from native; fall back to custom adapter for that field |
| B'.4 | Test cycle |

### 2.4 Phase C — Test cycle

| Step | Activity |
|---|---|
| C.1 | Test tenant: ingest a sample HR feed (real but anonymized; or synthetic from D4.1 fixture extended) |
| C.2 | Verify canonical records emitted match expected D1.1 shape |
| C.3 | Verify SCIM payloads emitted match expected D3.1 §5.2 shape |
| C.4 | Verify provenance records carry correct `source.hr_system` value |
| C.5 | Run targeted D4.2 integration tests against this source |
| C.6 | Run D4.3 performance test against this source's expected volume |

### 2.5 Phase D — Parallel run

| Step | Activity |
|---|---|
| D.1 | In production, enable the new source's adapter in **dry-run** mode |
| D.2 | Run for N days (typical: 7) — middleware computes what it WOULD emit; logs predicted records |
| D.3 | Reconcile predictions against existing reality (records from this HR source already provisioned by other means? what was the existing manual process?) |
| D.4 | Investigate any divergences |

### 2.6 Phase E — Cutover

| Step | Activity |
|---|---|
| E.1 | Disable any pre-existing manual / one-off provisioning for this HR source |
| E.2 | Enable the new source's adapter in **live** mode |
| E.3 | Monitor first incremental sync cycle |
| E.4 | Verify provenance count matches HR record delta |
| E.5 | Run for 7 days; reconcile divergences daily |
| E.6 | Sign-off after clean 7-day window |

## 3. Per-Vendor Implementation Notes

### 3.1 Workday

- Native connector exists (Entra ID Workday inbound provisioning).
- Per D1.7 verification: feature-rich; covers ~95% of D1.1 fields.
- Custom-adapter overlay needed for: agency-specific extension
  fields; certain federal-civilian-specific worker-class
  classifications.

### 3.2 Oracle HCM Cloud

- Native connector exists.
- Per D1.7 verification: feature parity similar to Workday.
- Same overlay pattern for agency-specific extensions.

### 3.3 SAP SuccessFactors

- Native connector exists.
- Per D1.7 verification: feature parity similar.
- Agency-specific overlay typically needed for federal civilian
  employment-class fields.

### 3.4 Generic HR / custom HR systems

- Custom adapter required.
- Adapter ingests via vendor's API (typically REST/JSON or SOAP).
- Schedule: typically every 15 min poll (matches middleware
  default cycle).
- Authentication: per vendor's API (OAuth2 typical; certificate
  in some cases).

## 4. Per-Source Configuration

When the new source is wired, the deployment's
`substrate-manifest.yaml` gains an entry:

```yaml
middleware:
  hr_sources:
    - id: "primary-workday"
      adapter: "uiao.adapters.hr.workday"
      cron: "0 */15 * * * *"
      staleness_window_hours: 24
      auth:
        method: "oauth2-client-credentials"
        # ... (per-vendor)
    - id: "secondary-custom"      # the new source
      adapter: "uiao.adapters.hr.<custom>"
      cron: "0 0 */6 * * *"        # every 6h for the secondary
      staleness_window_hours: 8
      auth:
        # ...
```

The per-source `id` becomes part of the provenance record
(`source.hr_system`).

## 5. Cross-Source Considerations

When multiple sources are wired:

| Concern | Posture |
|---|---|
| `employeeId` collision across sources | UIAO requires globally-unique employeeIds within the tenant. Sources MUST namespace (e.g., `WD-EMP-12345` vs. `OR-EMP-67890`). Adapter responsibility. |
| Record-of-truth conflicts | Tenant policy: which source wins on conflict. Declare in `substrate-manifest.yaml`. |
| Per-source quarantine routing | D2.6 quarantine records carry `source` field so per-source quality can be tracked separately. |
| Per-source SLA | D5.3 §2.5 review tracks quarantine triage SLA per source. |

## 6. Rollback

If the new source's onboarding fails at any phase:

| Phase | Rollback |
|---|---|
| A — Connector evaluation | Trivial; no production change |
| B — Adapter implementation | Trivial; adapter not yet in production |
| C — Test cycle | Trivial; test tenant only |
| D — Parallel run (dry-run mode) | Trivial; disable dry-run flag |
| E.1 — Disable existing manual provisioning | Re-enable manual provisioning |
| E.2 — Enable live | Disable adapter; re-enable manual; investigate |
| E.5 — 7-day window | Disable adapter; investigate; re-onboard later |

## 7. Sign-off

After successful onboarding (Phase E.6):

| Role | Sign-off |
|---|---|
| Identity Engineering lead | Adapter operational |
| Identity Architecture lead | Mapping conforms to D1.3 / D1.4 |
| HR Operations lead (for the new source) | HR side operational fit |
| Compliance | Provenance + auditability for the new source |

## 8. References

### 8.1 Primary canon

- [ADR-003](../adr/adr-003-api-driven-inbound-provisioning.md)

### 8.2 UIAO docs

- [UIAO_007](../UIAO_007_OrgTree_Modernization_AD_to_EntraID_v1.0.md)
- [UIAO_136](../UIAO_136_priority1-transformation-project-plans.md) — §SPEC 2 → Phase 5 → D5.4.

### 8.3 Spec 2 sister deliverables

- [Spec2-D1.1 — Canonical HR Attribute Schema](./Spec2-D1.1-CanonicalHRAttributeSchema.md) — what the new adapter MUST produce.
- [Spec2-D1.7 — HR Source System Connector Comparison Matrix](../../../../tools/discovery/Spec2-D1.7-HRConnectorComparisonMatrix.md) — per-vendor evaluation reference.
- [Spec2-D3.2 — Integration Middleware Specification](./Spec2-D3.2-IntegrationMiddlewareSpecification.md) §2.2 — per-source adapter contract.
- [Spec2-D5.1 — Production Cutover Runbook](./Spec2-D5.1-ProductionCutoverRunbook.md) — analogous sequence at full-deployment scale.

### 8.4 Compliance

- NIST SP 800-53 Rev 5: CM-2, CM-3, AC-2.
