---
deliverable_id: Spec2-D3.2
title: "Integration Middleware Specification"
spec: UIAO_136 / Spec 2 — HR-Agnostic Provisioning Architecture
phase: 3
status: Draft
version: 0.1
owner: Identity Architecture
created: 2026-05-01
updated: 2026-05-01
canonical_adrs:
  - ADR-003
  - ADR-035
  - ADR-048
  - ADR-049
  - ADR-050
canonical_docs:
  - UIAO_007
  - UIAO_135
  - UIAO_136
upstream_deliverables:
  - Spec2-D1.1
  - Spec2-D1.5
  - Spec2-D1.6
  - Spec2-D3.1
sibling_deliverables:
  - Spec2-D3.3
  - Spec2-D3.4
  - Spec2-D3.5
  - Spec2-D3.6
  - Spec2-D3.7
  - Spec2-D3.8
boundary: GCC-Moderate
classification: Controlled
---

# Spec 2 — D3.2: Integration Middleware Specification

> **Status (v0.1, 2026-05-01):** Initial draft. The middleware
> reference implementation choice is fixed in
> [`ADR-050`](../adr/adr-050-reference-middleware-implementation-choices.md);
> this document is the canonical contract that any implementation
> MUST satisfy regardless of platform choice. v0.2 verification
> against Microsoft Learn Logic Apps / Functions / Power Automate
> Graph-API documentation is the closure pass.

## 1. Purpose, Scope, and Reference

This deliverable is the canonical Integration Middleware specification
called for in
[`UIAO_136`](../UIAO_136_priority1-transformation-project-plans.md)
§SPEC 2 → Phase 3 → D3.2:

> *Define the middleware layer that normalizes HR data from any
> source into the canonical schema (D1.1). Options: Azure Logic
> Apps, Azure Functions, Power Automate, custom microservice.
> Include: input validation, schema transformation, error
> handling, logging.*

[D3.1 §3.2](./Spec2-D3.1-APIDrivenInboundProvisioningArchitecture.md)
names the middleware as a single component-block and sketches its
responsibilities; D3.2 is the full contract — every input, every
output, every interface that must be present for a deployment to
qualify as a UIAO middleware regardless of the platform it runs on.

### 1.1 Scope

In scope:

- The canonical input contract (HR-source-record schema acceptance).
- The canonical output contract (SCIM 2.0 bulkUpload payload, per
  D3.1 §5).
- The internal sub-component contracts (schema normalizer, OrgPath
  calculator, UPN generator, worker-type classifier, SCIM payload
  builder, token cache, rate limiter, retry/quarantine manager,
  provenance emitter).
- Platform-agnostic posture rules.
- Per-platform implementation guidance (Azure Functions per
  ADR-050 default; Logic Apps and Power Automate as alternatives).
- Configuration surface (substrate-manifest.yaml binding).
- Logging contract.
- Observability hooks.

Out of scope:

- The reference implementation itself — D3.2 specifies the
  contract; ADR-050 names the chosen reference; the code lives in
  the middleware module.
- HR-source data quality (D1.8).
- Provisioning-agent-side concerns (D3.3).
- Attribute-mapping engine internals (D3.4).
- Monitoring rules (D3.7).
- Security posture (D3.8).

## 2. Canonical Input Contract

The middleware accepts records from one or more HR-source adapters.
Each adapter produces records conforming to **the canonical schema
from D1.1**:

```yaml
# Canonical HR record shape (D1.1)
employeeId: string                 # immutable correlation anchor
firstName: string
lastName: string
preferredName: string?
displayName: string?
email: string?
department: string                 # OrgPath codebook input
division: string?
jobTitle: string?
managerEmployeeId: string?
hireDate: date
terminationDate: date?
workerType: enum(D1.6)             # FTE | Contractor | Intern | …
locationCode: string               # OrgPath codebook input
costCenter: string?                # OrgPath codebook input
organizationCode: string?          # OrgPath codebook input
country: string                    # ISO-3166 alpha-2
employmentStatus: enum             # Active | OnLeave | PreHire | Terminated | Rescinded
phoneNumber: string?
addresses: list?
extracted_at: timestamp            # source-system extraction time
```

### 2.1 Acceptance rules

The middleware MUST:

1. Validate every incoming record against the canonical schema
   (JSON Schema or equivalent).
2. Reject records missing required fields with `failure_reason:
   schema-validation` (D2.6 §2.1).
3. Reject records whose `employeeId` is missing or empty.
4. Reject records whose `extracted_at` is older than the tenant-
   configured staleness window (default 24h) with `failure_reason:
   schema-validation` and `failure_detail: stale-record`.
5. Tolerate optional-field absence (passthrough as omitted, not as
   empty string — per D3.1 §5.4).

### 2.2 Per-source adapter contract

Each HR-source adapter (Workday, Oracle HCM, SAP SuccessFactors,
generic CSV/JSON, etc.) MUST emit canonical records. Per-source
field-mapping logic lives **in the adapter**, not in the middleware
core. This is the architectural constraint that makes UIAO HR-
system-agnostic.

Per-source adapters live in `src/uiao/adapters/hr/<source>/` and
expose a uniform `produce_canonical_records()` interface. v0.1 of
D3.2 names the contract; per-source adapter implementations are
out of scope here (each is its own ADR-tracked deliverable).

## 3. Internal Sub-Components

The middleware decomposes into named sub-components. Each MUST be
independently testable; the contracts between them are the
substrate of the implementation.

### 3.1 Schema Normalizer

**Input:** HR-native record from a source adapter.
**Output:** Canonical record per §2.

**Contract:**

- Field-by-field transformation per the per-source adapter's
  declarative mapping.
- Diacritic preservation (transliteration is the UPN generator's
  job, not the normalizer's).
- Date normalization to ISO-8601.
- Country code normalization to ISO-3166 alpha-2.
- Per-source-specific quirks isolated in the adapter; the
  normalizer's output is platform-agnostic.

### 3.2 OrgPath Calculator

**Input:** Canonical record + ADR-035 codebook + ADR-048 attribute-
selection rules.
**Output:** OrgPath string.

**Contract:**

- Pure function: same inputs always produce the same OrgPath.
- Codebook miss → returns a sentinel value; caller routes to D2.6
  quarantine (`orgpath-codebook-miss`).
- Versioned: each calculator output carries the calculator's
  semver. Drift-engine attestation depends on this version stamp
  (ADR-040).

### 3.3 UPN Generator

**Input:** Canonical record + tenant UPN policy (D1.5).
**Output:** UPN string + collision-suffix metadata.

**Contract:**

- Pure function for the deterministic part.
- Collision resolution requires a tenant-side query (existing UPN
  table); the generator MUST be supplied a `collision_check(upn) ->
  bool` callback rather than embedding the lookup.
- Diacritic transliteration per RFC 5198 / D1.5 rules.
- Versioned.

### 3.4 Worker-Type Classifier

**Input:** Canonical record + D1.6 taxonomy.
**Output:** Classified worker type + license-affinity attribute
value.

**Contract:**

- Maps HR-side worker type strings to D1.6 canonical values.
- Unknown HR-side values route to D2.6 quarantine
  (`worker-type-unknown`).
- Versioned (D1.6 taxonomy version).

### 3.5 SCIM Payload Builder

**Input:** Canonical record + outputs of §3.2–§3.4.
**Output:** SCIM 2.0 user-payload object per D3.1 §5.2.

**Contract:**

- Strict adherence to the SCIM schema (canonical user shape).
- Operation method derived from event type (POST for new pre-hire
  / day-of-hire-no-prehire, PATCH for everything else; per D2.x
  per-workflow rules).
- Bulk envelope assembly per D3.1 §5.3, with up to 50 operations
  per envelope.
- Canonical-payload SHA-256 hash computed AFTER assembly is
  complete.

### 3.6 Token Cache + Refresh

**Input:** Service-principal credentials (per ADR-004 workload-
identity-federation default; certificate fallback per ADR-039).
**Output:** Valid Microsoft Graph access token.

**Contract:**

- Acquires tokens via the configured authentication mode
  (preferred: managed identity / WIF; fallback: certificate).
- Caches tokens until expiry minus a tenant-configured safety
  margin (default 5 minutes).
- Resolves Graph endpoint per the cloud-aware host map
  (commercial / GCC-High / DoD per the convention documented in
  AGENTS.md "Operating rules").
- Token-acquisition failure routes to D2.6 quarantine with
  `failure_reason: graph-auth-failure`.

### 3.7 Rate Limiter

**Input:** SCIM bulkUpload requests from the payload builder.
**Output:** Throttled request stream to the Graph client.

**Contract:**

- Token-bucket algorithm sized per D3.1 §7.1 throttling envelope
  (40 calls per 5-second window plus tenant daily cap, per
  current canonical D3.1 verification).
- Per-tenant isolated buckets (a noisy tenant does not starve
  others).
- Backpressure surfaces upward to the payload builder so it can
  pause batch construction.

### 3.8 Retry / Quarantine Manager

**Input:** Failed bulkUpload responses from the Graph client.
**Output:** Re-injected requests OR quarantine queue records.

**Contract:**

- Implements the failure taxonomy from D3.1 §6.1.
- Retry policy: exponential backoff per D3.1 §6.2 for transient
  classes (429, 5xx).
- Permanent classes (4xx-non-429) route directly to quarantine
  per D3.1 §6.3 + D2.6 §2.
- Per-record state machine (open → in-progress → resolved /
  wont-fix per D2.6 §3.2).

### 3.9 Provenance Emitter

**Input:** SCIM payload + Graph response + outcome.
**Output:** Provenance record per D3.1 §8.2.

**Contract:**

- One record per provisioning event (no batching) per D3.1 §8.3.
- Synchronous emission: the bulkUpload call does NOT return to
  the caller until the provenance record is persisted.
- Emission-failure escalates to security-incident class per D2.6
  (`provenance-emission-failed`).

## 4. Platform-Agnostic Posture

D3.2 specifies the contract; it does NOT prescribe the platform.
A UIAO-conformant middleware can run on:

| Platform | Posture | Notes |
|---|---|---|
| Azure Functions (Python) | **Default per ADR-050** | Reference implementation; consumption or premium plan |
| Azure Container Apps | Acceptable | For tenants needing always-on or longer-running operations |
| Custom microservice (Kubernetes / on-prem) | Acceptable | When deployment must run on tenant infrastructure |
| Azure Logic Apps | Acceptable for low-volume tenants | Visual designer; cleaner ops surface but harder to test |
| Power Automate | **Discouraged** | Limited error-handling; harder to enforce contracts |

The contract surface is what makes a deployment conformant. The
canonical-payload-hash + provenance record together prove that
the middleware honored the spec, regardless of platform.

## 5. Per-Platform Implementation Guidance

### 5.1 Azure Functions (default)

Per ADR-050:

- Python 3.11+ runtime.
- HTTP-triggered + Timer-triggered functions.
- Managed-identity auth to Microsoft Graph (no stored secrets).
- Application Insights for observability; OpenTelemetry for
  cross-component tracing.
- Per-deployment configuration via `substrate-manifest.yaml` +
  environment variable overrides for sensitive values.

### 5.2 Logic Apps

When chosen:

- Use Logic Apps Standard (not Consumption) for enterprise SLA.
- Custom connector for the bulkUpload endpoint (not built-in).
- Visual error-handling MUST achieve parity with §3.8 contract.

### 5.3 Custom microservice

When chosen:

- Implement all sub-components per §3 contracts.
- Container image MUST be signed and scanned (per UIAO supply-
  chain posture; ADR-022 / D3.8 §6).
- Deployment manifest landed in `substrate-manifest.yaml`.

## 6. Configuration Surface

The middleware reads configuration from a layered config store:

```yaml
middleware:
  platform: "azure-functions"           # default per ADR-050
  graph:
    cloud: "commercial"                 # commercial | gcc-high | dod
    api_version: "v1.0"                 # v1.0 | beta
    auth_mode: "managed-identity"       # managed-identity | wif | cert
    token_cache_ttl_seconds: 3300       # 55 min, leaves 5-min margin
    safety_margin_seconds: 300
  rate_limit:
    bucket_size: 40
    bucket_window_seconds: 5
    daily_call_limit: 2000              # P1/P2; 6000 for Governance
  bulk:
    operations_per_call: 50
  hr_sources:
    - id: "primary"
      adapter: "uiao.adapters.hr.workday"
      cron: "0 */15 * * * *"            # every 15 minutes
      staleness_window_hours: 24
  retry:
    max_attempts: 5
    base_backoff_seconds: 30
    max_backoff_seconds: 600
  quarantine:
    sink: "azure-cosmos"                # cosmos | table-storage | postgres
    sla_overrides: {}
  provenance:
    sink: "uiao-governance-os"
    sync: true                          # synchronous emission per §3.9
  feature_flags:
    cae_aware: true
    upn_collision_lookup: "graph-query"
```

Configuration MUST be validated at startup; invalid configuration
MUST block the middleware from accepting HR records (rather than
silently default).

## 7. Logging Contract

The middleware emits structured logs with the following minimum
fields:

| Field | Source |
|---|---|
| `timestamp` | UTC ISO-8601 |
| `level` | DEBUG/INFO/WARN/ERROR |
| `request_id` | per-batch correlation id |
| `external_id` | per-record correlation id (HR `employeeId`) |
| `component` | sub-component name (§3.x) |
| `event` | event-type string |
| `outcome` | success / partial / failure |
| `latency_ms` | per-operation latency |
| `graph_request_id` | Microsoft Graph response request-id |

Logs do NOT contain HR PII beyond `external_id` + `upn`. PII
appears only in the canonical payload, which is logged to a
separate tenant-scoped audit store with retention and access
controls per D3.8.

## 8. Observability Hooks

The middleware exposes:

- **Metrics** (per-tenant, per-time-window): `records_processed`,
  `records_quarantined`, `graph_calls`, `graph_429`, `graph_5xx`,
  `provenance_emissions`, `provenance_failures`, `latency_p50/p95/p99`.
- **Traces** (OpenTelemetry): per-record span tree from HR
  ingestion → SCIM emission → provenance write.
- **Health endpoint** (HTTP GET `/health`): returns 200 when all
  sub-components are operational, 503 with details otherwise.
- **Readiness endpoint** (HTTP GET `/ready`): returns 200 when
  the middleware is ready to accept HR records (token cache
  warm; configuration valid; provenance store reachable).

D3.7 binds the metrics + traces to alerting rules.

## 9. References

### 9.1 Primary canon

- [ADR-003](../adr/adr-003-api-driven-inbound-provisioning.md)
- [ADR-035](../adr/adr-035-orgpath-codebook-binding.md)
- [ADR-048](../adr/adr-048-orgpath-attribute-storage-decision.md)
- [ADR-049](../adr/adr-049-microsoft-adapter-coverage-expansion.md)
- [ADR-050](../adr/adr-050-reference-middleware-implementation-choices.md)

### 9.2 UIAO docs

- [UIAO_007](../UIAO_007_OrgTree_Modernization_AD_to_EntraID_v1.0.md)
- [UIAO_136](../UIAO_136_priority1-transformation-project-plans.md) — §SPEC 2 → Phase 3 → D3.2.

### 9.3 Spec 2 sister deliverables

- [Spec2-D3.1](./Spec2-D3.1-APIDrivenInboundProvisioningArchitecture.md) — substrate; §3.2 names this component-block.
- [Spec2-D3.3](./Spec2-D3.3-ProvisioningAgentDeploymentArchitecture.md) — coexistence path consumes this middleware's output.
- [Spec2-D3.4](./Spec2-D3.4-AttributeMappingEngineConfiguration.md) — attribute-mapping engine sub-component contract.
- [Spec2-D3.5](./Spec2-D3.5-OrgPathPopulationPipeline.md) — end-to-end OrgPath flow.
- [Spec2-D3.6](./Spec2-D3.6-WritebackSpecification.md) — writeback paths exit through this middleware.
- [Spec2-D3.7](./Spec2-D3.7-MonitoringAlertingConfiguration.md) — observability rules consume §8 hooks.
- [Spec2-D3.8](./Spec2-D3.8-DataFlowSecurityAssessment.md) — security posture this middleware MUST satisfy.

### 9.4 Microsoft documentation (verification pending in v0.2)

- Microsoft Learn — Azure Functions Python developer guide.
- Microsoft Learn — Logic Apps Standard.
- Microsoft Learn — Managed identities for Microsoft Graph.

### 9.5 Compliance

- NIST SP 800-53 Rev 5: AC-2, AU-2, SC-8 (data in transit), SC-13 (cryptographic protection).
