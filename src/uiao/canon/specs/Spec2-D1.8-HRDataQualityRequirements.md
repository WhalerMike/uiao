---
deliverable_id: Spec2-D1.8
title: "HR Data Quality Requirements"
spec: UIAO_136 / Spec 2 — HR-Agnostic Provisioning Architecture
phase: 1
status: Draft
version: 0.1
owner: Identity Architecture
created: 2026-05-01
updated: 2026-05-01
canonical_adrs:
  - ADR-003
canonical_docs:
  - UIAO_007
  - UIAO_135
  - UIAO_136
upstream_deliverables:
  - Spec2-D1.1
  - Spec2-D1.6
sibling_deliverables:
  - Spec2-D2.6
  - Spec2-D3.2
  - Spec2-D3.7
boundary: GCC-Moderate
classification: Controlled
---

# Spec 2 — D1.8: HR Data Quality Requirements

> **Status (v0.1, 2026-05-01):** Initial draft. Defines the
> minimum-viable HR data quality bar that UIAO middleware enforces
> (§3.1) plus the governance posture for tenants whose HR feed
> falls below the bar (§5).

## 1. Purpose, Scope, and Reference

This deliverable is the canonical HR Data Quality specification
called for in
[`UIAO_136`](../UIAO_136_priority1-transformation-project-plans.md)
§SPEC 2 → Phase 1 → D1.8:

> *Define minimum data quality standards for HR feed: required
> fields, validation rules, allowed values, referential integrity
> (manager must exist before direct report), data freshness SLA.*

D1.8 names the contract HR-source-of-truth systems MUST honor for
UIAO provisioning to function. Failures route to D2.6 quarantine.
D3.7 alerts on quarantine-rate elevation; D3.2 enforces the rules at
the middleware boundary.

### 1.1 Scope

In scope:

- The minimum-viable required-field set (§2).
- Validation rules per field class (§3).
- Referential integrity rules (manager link, codebook membership)
  (§4).
- Data freshness SLA (§3.5).
- Tenant-side data quality governance (§5).
- D2.6 failure-reason mapping.

Out of scope:

- HR-side data-cleansing tooling (vendor-specific; not UIAO's
  concern).
- Specific HR vendor's quality controls (per-vendor quality is
  documented in D1.7).
- Per-tenant data extension fields (UIAO canonical only).

## 2. Required Field Set

Per D1.1 §4.1, the canonical required fields:

| Field | Required | Failure mode if absent |
|---|---|---|
| `employeeId` | YES | `schema-validation` (no correlation possible) |
| `firstName` | YES | `schema-validation` |
| `lastName` | YES | `schema-validation` |
| `department` | YES | `schema-validation` (OrgPath input) |
| `hireDate` | YES | `schema-validation` |
| `workerType` | YES | `worker-type-unknown` (per D1.6) |
| `locationCode` | YES | `schema-validation` (OrgPath input) |
| `country` | YES | `usage-location-missing` (license region) |
| `employmentStatus` | YES | `schema-validation` |
| `extracted_at` | YES | `schema-validation` |

A record missing any of these is **non-provisionable** and routes
to D2.6 quarantine.

### 2.1 Strongly-recommended fields

Not strictly required, but absence increases operational friction:

| Field | Reason recommended |
|---|---|
| `email` | When absent, UIAO derives email from UPN; HR's record-of-truth posture is weaker |
| `managerEmployeeId` | Without it, dynamic groups and access-review trees are incomplete |
| `division` / `costCenter` | Improves OrgPath codebook resolution (per ADR-035) |
| `terminationDate` (when applicable) | Without it, leaver flow blocks |
| `addresses[work]` | Required for badging / equipment-shipping integrations downstream |

## 3. Validation Rules per Field Class

### 3.1 Identifier integrity

| Field | Rule |
|---|---|
| `employeeId` | 1–64 chars; printable ASCII recommended; **immutable** (never changes for a given worker) |
| `managerEmployeeId` | If non-null: must be a valid `employeeId` format AND should reference an existing record (see §4.1) |

### 3.2 Name integrity

| Field | Rule |
|---|---|
| `firstName`, `lastName` | Non-empty; ≤100 chars; UTF-8 (diacritics permitted); MUST NOT be obvious placeholders (`UNKNOWN`, `TBD`, `XXX`) |
| `displayName` | When provided: ≤200 chars; ideally aligns with `lastName, firstName` or `firstName lastName` per tenant policy |

The placeholder check is implemented as a tenant-policy lint —
records with placeholder values pass schema validation but are
flagged for HR data-quality review.

### 3.3 Date integrity

| Field | Rule |
|---|---|
| `hireDate` | ISO-8601 calendar date; ≥ 1900-01-01; ≤ today + 5 years (sanity bound on far-future hires) |
| `terminationDate` | ISO-8601 calendar date; ≥ `hireDate`; ≤ today + 5 years |
| `extracted_at` | ISO-8601 UTC timestamp; ≤ now; not older than tenant staleness window |

### 3.4 Enum + format integrity

| Field | Rule |
|---|---|
| `workerType` | Must be in D1.6 canonical enum |
| `employmentStatus` | Must be in D1.1 §2 enum |
| `country` | Must match `^[A-Z]{2}$` (ISO-3166 alpha-2) |
| `email` | When present: RFC 5322 well-formed |

### 3.5 Freshness SLA

The middleware enforces a freshness SLA on `extracted_at`:

| Tenant tier | Default staleness window | Action on violation |
|---|---|---|
| Federal civilian (default) | 24 hours | Quarantine (`schema-validation` / `failure_detail: stale-record`) |
| Real-time-required tenants | 1 hour | Quarantine + alert |
| Daily-batch tenants | 36 hours | Quarantine |

The window is configured in `substrate-manifest.yaml`. Records older
than the window represent HR-feed freshness gaps that need
investigation.

## 4. Referential Integrity

### 4.1 Manager link

`managerEmployeeId` is a foreign-key reference to another worker's
`employeeId`. The middleware's posture:

| Manager state at observation | Behavior |
|---|---|
| Manager is in current batch | OK; Entra reconciles asynchronously after both records process |
| Manager exists in Entra from prior cycle | OK; link resolves immediately |
| Manager not yet in Entra (newer hire) | OK; deferred resolution per D2.1 §6 |
| Manager `active: false` for ≤90 days | OK; potentially stale but not blocking |
| Manager `active: false` for >90 days | Quarantine: `manager-stale` |
| Manager `employeeId` not findable anywhere | Quarantine: `manager-stale` |
| Manager link forms a cycle (rare; A→B→A) | Quarantine; HR data integrity error |

The 90-day stale-manager threshold is configurable per tenant.

### 4.2 OrgPath codebook membership

Per ADR-035, `department` / `division` / `locationCode` /
`costCenter` values must be in the OrgPath codebook. Codebook miss
→ quarantine `orgpath-codebook-miss`. The codebook is a separate
canonical artifact (per ADR-035); its update cadence is governed
there.

### 4.3 Worker type validity

`workerType` must be in D1.6 taxonomy. Invalid → `worker-type-unknown`.
Tenants who introduce a new worker type SHOULD update D1.6 first
(per D1.6 §7); records arriving with the new type before the
taxonomy update are quarantined.

### 4.4 Cross-field consistency

| Constraint | Action on violation |
|---|---|
| `terminationDate < hireDate` | `schema-validation` |
| `employmentStatus = Terminated` AND `terminationDate` absent | `schema-validation` |
| `employmentStatus = PreHire` AND `hireDate < today` (per tenant TZ) | `schema-validation` (HR should have re-classified to Active by now) |
| Manager cycle | `schema-validation` |

## 5. Tenant-Side Governance

UIAO's posture: HR is source-of-truth. Data quality issues at the
HR layer are NOT UIAO's responsibility to fix. UIAO's role:

1. **Detect** — quarantine records that violate D1.8 rules.
2. **Surface** — D3.7 alerts on quarantine-rate elevation per
   `failure_reason` class.
3. **Audit** — every quarantined record produces a provenance event
   (D2.6 §7), forming the record of HR data quality over time.
4. **Inform** — operators have a CLI / dashboard surface for
   filtering quarantine records by source HR system.

UIAO does NOT:

- Auto-correct HR-side data.
- Default missing required fields to substitute values.
- Silently drop records that fail validation.

### 5.1 Quality-rate SLAs (operational)

Tenant-policy expectations (typical):

| Quality dimension | Target |
|---|---|
| Records passing schema validation | ≥ 99% per cycle |
| Records with stale `extracted_at` | ≤ 1% per cycle |
| Records with `manager-stale` failures | ≤ 0.5% per cycle |
| Records with `orgpath-codebook-miss` failures | ≤ 0.5% per cycle |

Sustained breach of these targets triggers tier-1 alerts (D3.7 §5.1)
and creates an HR-side action item.

## 6. The HR Data Quality Dashboard

D3.7 §6 names a "Quarantine queue depth (open, in-progress, by
failure_reason)" panel. D1.8's contribution to that panel:

- Per-`failure_reason` breakdown.
- Per-source HR system breakdown (when multiple sources are wired).
- Trend over time (4-week rolling).
- Top-10 offending HR records by recurrence.
- Mean time to triage / resolve / re-inject (per D2.6 §6).

## 7. Schema-Drift Considerations

When the HR system adds, removes, or renames fields:

1. The per-source adapter is updated to map the new schema to
   D1.1 canonical.
2. If the HR-side change reduces information UIAO depends on
   (e.g., HR drops `division`), the deployment's substrate
   manifest is updated to reflect the reduced inputs.
3. UIAO's middleware is unaffected; the canonical schema is stable
   per D1.1's versioning rules.

The drift posture: **adapter changes absorb HR-side schema changes**.
UIAO canonical is invariant.

## 8. References

### 8.1 Primary canon

- [ADR-003](../adr/adr-003-api-driven-inbound-provisioning.md)

### 8.2 UIAO docs

- [UIAO_007](../UIAO_007_OrgTree_Modernization_AD_to_EntraID_v1.0.md)
- [UIAO_135](../UIAO_135_identity-directory-transformation-inventory.md)
- [UIAO_136](../UIAO_136_priority1-transformation-project-plans.md) — §SPEC 2 → Phase 1 → D1.8.

### 8.3 Spec 2 sister deliverables

- [Spec2-D1.1 — Canonical HR Attribute Schema](./Spec2-D1.1-CanonicalHRAttributeSchema.md) — schema definition; D1.8 enforces against it.
- [Spec2-D1.6 — Worker Type Classification Taxonomy](./Spec2-D1.6-WorkerTypeClassificationTaxonomy.md) — `workerType` validity.
- [Spec2-D2.6 — Error Handling & Quarantine Specification](./Spec2-D2.6-ErrorHandlingQuarantineSpecification.md) — failure-reason taxonomy + quarantine queue.
- [Spec2-D3.2 — Integration Middleware Specification](./Spec2-D3.2-IntegrationMiddlewareSpecification.md) §2 — input acceptance contract.
- [Spec2-D3.7 — Monitoring & Alerting Configuration](./Spec2-D3.7-MonitoringAlertingConfiguration.md) — quality alerting rules.

### 8.4 Compliance

- NIST SP 800-53 Rev 5: AC-2 (account management — quality of provisioning data), AU-6 (audit review), CA-7 (continuous monitoring — the freshness + quality SLAs are continuous-monitoring controls).
