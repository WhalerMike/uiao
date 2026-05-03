---
deliverable_id: Spec2-D5.3
title: "Provisioning Governance Specification"
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
  - Spec2-D3.1
  - Spec2-D3.2
  - Spec2-D3.7
  - Spec2-D3.8
sibling_deliverables:
  - Spec2-D5.5
boundary: GCC-Moderate
classification: Controlled
---

# Spec 2 — D5.3: Provisioning Governance Specification

> **Status (v0.1, 2026-05-02):** Initial canonical steady-state
> governance specification. Names the recurring reviews,
> ownership boundaries, and policy-change cadences once Spec 2 is
> in production.

## 1. Purpose, Scope, and Reference

This deliverable is the canonical Provisioning Governance
Specification called for in
[`UIAO_136`](../UIAO_136_priority1-transformation-project-plans.md)
§SPEC 2 → Phase 5 → D5.3:

> *Ongoing governance: provisioning log retention (7 years for
> compliance), quarterly access review of provisioning service
> principal permissions, annual attribute mapping review, OrgPath
> hierarchy change management.*

D5.3 names the steady-state governance posture. After D5.1 cutover
+ D5.2 legacy decommission, the substrate enters operational
maintenance — D5.3 specifies what that maintenance looks like.

### 1.1 Scope

In scope:

- Recurring governance reviews (cadence + ownership + scope).
- Retention policies (provenance store, quarantine store, logs).
- Change management for canonical artifacts (codebooks, mappings,
  taxonomy, schema).
- Operational ownership (Identity Engineering vs. Identity
  Governance vs. HR Operations).
- Audit-evidence flow.

Out of scope:

- Per-deployment ops escalation runbooks (operational, not canon).
- Per-tenant policy decisions (each agency decides its own).
- Specific monitoring rule values (D3.7 covers).

## 2. Recurring Reviews

### 2.1 Quarterly: Provisioning Service Principal Access Review

| Property | Value |
|---|---|
| Cadence | Quarterly |
| Owner | Identity Governance lead |
| Scope | Microsoft Graph permissions held by the middleware service principal |
| Acceptance criteria | All permissions per D3.8 §4; no scope creep; principal not used outside automated middleware |
| Output | Sign-off record archived with quarter timestamp |

### 2.2 Annual: Attribute Mapping Review

| Property | Value |
|---|---|
| Cadence | Annual |
| Owner | Identity Architecture lead |
| Scope | Both layers of D3.4 (middleware-side D1.3/D1.4 + Entra-side synchronization-job mapping) |
| Acceptance criteria | Mapping in production matches what D3.4 specifies; no drift; codebook references resolve |
| Output | Annual attribute-mapping certification archived |

### 2.3 Annual: Schema Review

| Property | Value |
|---|---|
| Cadence | Annual |
| Owner | Identity Architecture lead |
| Scope | D1.1 canonical schema; per-source adapter mappings |
| Acceptance criteria | Schema sufficient for current HR-source set; no required field absent; D1.6 worker-type taxonomy reflects current org |
| Output | Schema-version recommendation (advance, hold, deprecate) |

### 2.4 Annual: D2.6 Failure-Reason Taxonomy Review

| Property | Value |
|---|---|
| Cadence | Annual |
| Owner | Identity Engineering lead |
| Scope | D2.6 §2 enumeration |
| Acceptance criteria | Coverage matches actual production failures observed in past year; no orphan classes; no production failures un-classified |
| Output | Taxonomy update recommendation |

### 2.5 Continuous: Quarantine Triage SLA Review

| Property | Value |
|---|---|
| Cadence | Weekly (operational); rolled into monthly governance review |
| Owner | HR Operations + Identity Engineering jointly |
| Scope | Quarantine queue per D2.6 §4 SLA |
| Acceptance criteria | ≥95% of records resolved within SLA; no queue growth; per-`failure_reason` rates within tolerances |
| Output | Weekly dashboard; monthly summary |

### 2.6 Continuous: Drift Engine Findings Review

| Property | Value |
|---|---|
| Cadence | Weekly |
| Owner | Identity Engineering lead |
| Scope | All drift-engine findings per ADR-040 + D5.5 |
| Acceptance criteria | All findings either remediated, accepted-as-known, or escalated |
| Output | Per-finding disposition log |

## 3. Retention Policies

| Artifact | Retention | Rationale |
|---|---|---|
| Provenance records | 7 years | Federal civilian audit; agency-specific NARA may extend |
| Quarantine records | 7 years | Same |
| Operational logs (D3.7) | 1–3 years | Operational debugging window; not audit-class |
| Microsoft Graph provisioning logs | Per Microsoft retention; mirror to Log Analytics for ≥1 year | Cross-side reconciliation |
| Sign-off records (validation, cutover, decommission, governance reviews) | 7 years | Audit |
| Validation Report instances | 7 years | Same |
| Canonical artifacts (D1.1 schema, D1.6 taxonomy, D2.6 failure_reason taxonomy, mappings) | Forever (source-control history) | The canon |

Retention enforcement is per-store. The middleware does NOT delete
records; tenant-side retention policies on Cosmos / Postgres /
Log Analytics handle expiration.

## 4. Change Management for Canonical Artifacts

### 4.1 OrgPath codebook (ADR-035)

| Change type | Process |
|---|---|
| Add new department / division / location to codebook | Canon governance change; reviewed by Identity Architecture lead; ADR or registry entry |
| Rename / restructure | Same + impact analysis on existing deployed records |
| Deprecate | Phased — flag as deprecated for 1 quarter; remove after no records use it |

### 4.2 Worker-type taxonomy (D1.6)

| Change type | Process |
|---|---|
| Add new worker type | New ADR; D1.1 enum update; D1.6 §3 profile add; downstream cross-spec coordination (D2.5 conversion matrix; D2.7 windows; D2.8 scope filter) |
| Modify existing profile | Targeted change; affected deployments re-run D4.2 |
| Deprecate | Same phased approach as codebook |

### 4.3 D1.3 / D1.4 mapping matrices

| Change type | Process |
|---|---|
| Map a previously-unmapped HR field | Spec update + middleware code change + test addition |
| Change a mapping target | Higher review bar; impact on existing deployed records |
| Remove a mapping | Highest bar; phased deprecation |

### 4.4 D2.6 failure_reason taxonomy

Per D2.6 §10: stable taxonomy. New `failure_reason` values
require:

1. D2.6 update.
2. Canon registry update.
3. Search-and-update across D2.x + D3.1 references.
4. Note in next version's `verification_history`.

## 5. Operational Ownership

| Domain | Owner |
|---|---|
| Middleware code + deployment | Identity Engineering |
| Provisioning agents | Identity Engineering + Infrastructure |
| Provisioning service principal credentials | Identity Engineering (operations); Identity Governance (audit) |
| OrgPath codebook | Identity Architecture |
| Worker-type taxonomy | Identity Architecture |
| HR-source adapter code | Identity Engineering |
| HR data quality (records, freshness) | HR Operations |
| Quarantine triage | HR Operations + Identity Engineering jointly |
| Access reviews | Identity Governance |
| Compliance evidence | Compliance / Audit lead |
| Incident response (security-incident class per D2.6 §5.1) | Identity Engineering on-call + Agency CISO |

## 6. Audit Evidence Flow

How audit evidence flows from substrate operation to auditor:

```
Per-record provisioning event
   ↓ (D3.1 §8 provenance emission)
Provenance record (UIAO Governance OS)
   ↓ (queryable; linked to Microsoft Graph request_id)
Aggregate evidence query (per-control)
   ↓
Compliance Orchestrator / OSCAL evidence pack
   ↓
Auditor consumption (FedRAMP Moderate, agency audit)
```

Spec 2 substrate is the upstream of:

- AC-2 (Account Management) — every joiner / leaver event has a
  provenance record.
- AU-2 (Audit Events) — same.
- IA-4 (Identifier Management) — UPN + employeeId binding.

UIAO Governance OS is the consumer; D5.3 names the boundary.

## 7. Continuous Improvement

| Channel | Cadence | Output |
|---|---|---|
| Quarterly retro | Per quarter | Spec 2 substrate quarterly review; what's working / what isn't |
| Annual canon review | Annual | Roll up of all annual reviews above; agency-level posture statement |
| Post-incident review | Per security-incident-class event (D2.6 §5.1) | Lessons learned; canon updates if warranted |

## 8. References

### 8.1 Primary canon

- [ADR-003](../adr/adr-003-api-driven-inbound-provisioning.md)

### 8.2 UIAO docs

- [UIAO_007](../UIAO_007_OrgTree_Modernization_AD_to_EntraID_v1.0.md)
- [UIAO_136](../UIAO_136_priority1-transformation-project-plans.md) — §SPEC 2 → Phase 5 → D5.3.

### 8.3 Spec 2 sister deliverables

- [Spec2-D3.1](./Spec2-D3.1-APIDrivenInboundProvisioningArchitecture.md) §8 — provenance record contract.
- [Spec2-D3.2](./Spec2-D3.2-IntegrationMiddlewareSpecification.md) §6 — configuration surface (governance-managed).
- [Spec2-D3.7](./Spec2-D3.7-MonitoringAlertingConfiguration.md) — operational health observability.
- [Spec2-D3.8](./Spec2-D3.8-DataFlowSecurityAssessment.md) — security posture (governance-attested annually).
- [Spec2-D5.5 — Provisioning Drift Detection Rules](./Spec2-D5.5-ProvisioningDriftDetectionRules.md) — drift findings into §2.6 review.

### 8.4 Compliance

- NIST SP 800-53 Rev 5: AC-2, AU-2, AU-6 (audit review), AU-11 (audit retention), CA-7 (continuous monitoring), CM-3 (change control), IR-4 (incident response), PL-2 (system security plan).
