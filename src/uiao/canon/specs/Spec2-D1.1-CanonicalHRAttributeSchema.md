---
deliverable_id: Spec2-D1.1
title: "Canonical HR Attribute Schema"
spec: UIAO_136 / Spec 2 — HR-Agnostic Provisioning Architecture
phase: 1
status: Draft
version: 0.1
owner: Identity Architecture
created: 2026-05-01
updated: 2026-05-01
canonical_adrs:
  - ADR-003
  - ADR-035
canonical_docs:
  - UIAO_007
  - UIAO_135
  - UIAO_136
sibling_deliverables:
  - Spec2-D1.2
  - Spec2-D1.3
  - Spec2-D1.4
  - Spec2-D1.5
  - Spec2-D1.6
  - Spec2-D1.7
  - Spec2-D1.8
boundary: GCC-Moderate
classification: Controlled
---

# Spec 2 — D1.1: Canonical HR Attribute Schema

> **Status (v0.1, 2026-05-01):** Initial canonical draft. The PowerShell
> discovery generator at
> [`tools/discovery/Spec2-D1.1-Get-HRAttributeSchema.ps1`](../../../../tools/discovery/Spec2-D1.1-Get-HRAttributeSchema.ps1)
> probes the deployment's HR source for attribute presence and emits a
> deployment-specific report. This document is the **canonical schema
> contract** that every UIAO deployment's HR-source adapter MUST satisfy
> before records flow into the middleware (D3.2).

## 1. Purpose, Scope, and Reference

This deliverable is the canonical HR Attribute Schema called for in
[`UIAO_136`](../UIAO_136_priority1-transformation-project-plans.md)
§SPEC 2 → Phase 1 → D1.1:

> *Define the minimum set of HR attributes required for identity
> provisioning: Employee ID, First Name, Last Name, Display Name,
> Email, Department, Division, Job Title, Manager Employee ID, Hire
> Date, Termination Date, Worker Type (employee/contractor/intern),
> Location Code, Cost Center, Organization Code (for OrgPath
> derivation).*

D1.1 is referenced as the input contract by D3.2 §2 (middleware
input), the upstream of D2.1–D2.5 + D2.7 + D2.8 (each spec's
pre-conditions cite D1.1 schema validation), and the basis for D2.6's
`schema-validation` failure_reason.

### 1.1 Scope

In scope:

- The minimum required attribute set for UIAO provisioning.
- Per-attribute type, format, validation rules, optionality.
- The relationship between `employeeId` (canonical correlation
  anchor) and per-source identifiers.
- Source-system-agnostic design — the schema MUST be satisfiable
  by any HR system with reasonable adapter mapping.
- The schema's relationship to the SCIM 2.0 wire format (D3.1 §5).
- Versioning rules.

Out of scope:

- HR-source-specific quirks (handled by per-source adapters; see
  Spec2-D1.7 connector comparison for vendor-specific surfaces).
- Optional HR attributes used by some agencies but not load-
  bearing for identity provisioning (e.g., security clearance
  level, union membership; agencies model these via per-tenant
  schema extensions, NOT canonical-schema additions).
- HR-to-OrgPath translation logic (see D1.2).
- HR-to-Entra / HR-to-AD mapping (see D1.3 / D1.4).

### 1.2 Audience

- HR-source adapter authors (the contract their `produce_canonical_records()`
  output MUST conform to).
- Middleware engineers (the contract their input validation enforces).
- Auditors (the canonical record-of-truth for what HR data UIAO
  ingests).

## 2. The Schema

### 2.1 Top-level shape

```yaml
# Canonical HR record (single worker)
employeeId: string                 # required; immutable correlation anchor
firstName: string                  # required
lastName: string                   # required
preferredName: string?             # optional; used for displayName fallback
displayName: string?               # optional; HR-side preferred display
email: string?                     # optional; HR-side primary email
department: string                 # required; OrgPath codebook input
division: string?                  # optional; OrgPath codebook input
jobTitle: string?                  # optional
managerEmployeeId: string?         # optional; null = no manager (e.g., agency head)
hireDate: date                     # required (ISO-8601)
terminationDate: date?             # optional; populated for leaver events
workerType: enum                   # required; per D1.6 taxonomy
locationCode: string               # required; OrgPath codebook input
costCenter: string?                # optional; OrgPath codebook input (per agency)
organizationCode: string?          # optional; top-level org tag
country: string                    # required; ISO-3166 alpha-2
employmentStatus: enum             # required; Active|OnLeave|PreHire|Terminated|Rescinded
phoneNumber: string?               # optional
addresses: list?                   # optional; list of {type, street, city, region, postalCode, country}
extracted_at: timestamp            # required; source-system extraction time (ISO-8601 UTC)
adapter_metadata: object?          # optional; per-source provenance (versions, notes)
```

### 2.2 JSON Schema

The canonical machine-readable representation is JSON Schema draft
2020-12. The full schema lives in the deployment repository; the
reference shape:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://uiao.gov/schemas/hr-canonical-record.schema.json",
  "title": "UIAO Canonical HR Record",
  "type": "object",
  "required": [
    "employeeId", "firstName", "lastName", "department",
    "hireDate", "workerType", "locationCode", "country",
    "employmentStatus", "extracted_at"
  ],
  "properties": {
    "employeeId":          { "type": "string", "minLength": 1, "maxLength": 64 },
    "firstName":           { "type": "string", "minLength": 1, "maxLength": 100 },
    "lastName":            { "type": "string", "minLength": 1, "maxLength": 100 },
    "preferredName":       { "type": "string", "maxLength": 100 },
    "displayName":         { "type": "string", "maxLength": 200 },
    "email":               { "type": "string", "format": "email" },
    "department":          { "type": "string", "minLength": 1, "maxLength": 200 },
    "division":            { "type": "string", "maxLength": 200 },
    "jobTitle":            { "type": "string", "maxLength": 200 },
    "managerEmployeeId":   { "type": ["string", "null"], "maxLength": 64 },
    "hireDate":            { "type": "string", "format": "date" },
    "terminationDate":     { "type": ["string", "null"], "format": "date" },
    "workerType":          {
      "type": "string",
      "enum": ["FullTimeEmployee", "PartTimeEmployee", "Contractor",
                "Intern", "Vendor", "Volunteer", "ExternalCollaborator"]
    },
    "locationCode":        { "type": "string", "minLength": 1, "maxLength": 32 },
    "costCenter":          { "type": "string", "maxLength": 32 },
    "organizationCode":    { "type": "string", "maxLength": 32 },
    "country":             { "type": "string", "pattern": "^[A-Z]{2}$" },
    "employmentStatus":    {
      "type": "string",
      "enum": ["Active", "OnLeave", "PreHire", "Terminated", "Rescinded"]
    },
    "phoneNumber":         { "type": "string", "maxLength": 32 },
    "addresses":           { "type": "array", "items": { "$ref": "#/$defs/address" } },
    "extracted_at":        { "type": "string", "format": "date-time" },
    "adapter_metadata":    { "type": "object", "additionalProperties": true }
  },
  "additionalProperties": false,
  "$defs": {
    "address": {
      "type": "object",
      "required": ["type"],
      "properties": {
        "type":          { "type": "string", "enum": ["work", "home", "mailing"] },
        "streetAddress": { "type": "string" },
        "locality":      { "type": "string" },
        "region":        { "type": "string" },
        "postalCode":    { "type": "string" },
        "country":       { "type": "string", "pattern": "^[A-Z]{2}$" }
      },
      "additionalProperties": false
    }
  }
}
```

The schema is **closed**: `additionalProperties: false`. Per-tenant
extensions land in a separate `tenant_extensions` object (out of
scope for v0.1; tenant-extension contract to be specified in v0.2).

## 3. Field-by-Field Contract

### 3.1 `employeeId` — the correlation anchor

| Property | Value |
|---|---|
| Required | Yes |
| Type | string (1–64 chars; printable ASCII recommended) |
| Mutability | **Immutable** for the lifetime of the worker's identity in UIAO |
| Source | HR system's stable worker identifier |
| Used as | SCIM `externalId` (D3.1 §5.4); `enterprise:User.employeeNumber`; AD `employeeID`; provenance correlation key |

The `employeeId` is the load-bearing UIAO correlation anchor. It MUST
persist across:
- Mover events (department change, manager change, etc.).
- Conversion events (worker-type change).
- Leaver/Rehire (D2.4 Path A reactivation).

If HR's primary worker identifier is mutable (e.g., changes on rehire
or conversion), the per-source adapter is responsible for projecting
to a stable surrogate. The middleware MUST treat `employeeId` as
immutable.

### 3.2 Name fields

| Field | Required | Notes |
|---|---|---|
| `firstName` | Yes | Diacritics preserved; transliteration is the UPN generator's job (D1.5) |
| `lastName` | Yes | Same |
| `preferredName` | No | Used as displayName component when tenant policy prefers it |
| `displayName` | No | HR-side preferred display; if absent, middleware composes from first+last per tenant policy |

### 3.3 Lifecycle dates

| Field | Required | Notes |
|---|---|---|
| `hireDate` | Yes | ISO-8601 date; drives D2.7 pre-hire window calculation |
| `terminationDate` | No | ISO-8601 date; populated for in-flight leavers; null/absent for active workers |

The middleware compares these against tenant time zone (D2.7 §5),
NOT UTC.

### 3.4 Organizational fields

| Field | Required | Used by |
|---|---|---|
| `department` | Yes | OrgPath codebook (ADR-035); SCIM `enterprise:User.department` |
| `division` | No | OrgPath codebook (when applicable) |
| `jobTitle` | No | SCIM `enterprise:User.title`; access-review trigger criteria (D2.2 §8) |
| `managerEmployeeId` | No | SCIM `enterprise:User.manager.value` |
| `locationCode` | Yes | OrgPath codebook; tenant-policy named-location bindings |
| `costCenter` | No | OrgPath codebook (per agency) |
| `organizationCode` | No | OrgPath codebook top-level tag |

The four codebook-input fields (department, division, locationCode,
costCenter) are the inputs to OrgPath calculation per ADR-035. The
codebook's contract with this schema is the canonical input shape.

### 3.5 Worker classification

| Field | Required | Notes |
|---|---|---|
| `workerType` | Yes | Per D1.6 canonical taxonomy |
| `employmentStatus` | Yes | Active/OnLeave/PreHire/Terminated/Rescinded |
| `country` | Yes | ISO-3166 alpha-2; drives `usageLocation` for license region (D2.2 §9) |

### 3.6 Optional contact + provenance

| Field | Required | Notes |
|---|---|---|
| `email` | No | If provided, used as primary email; if absent, derived from UPN |
| `phoneNumber` | No | Pass-through to SCIM phoneNumbers[work] |
| `addresses` | No | Pass-through to SCIM addresses |
| `extracted_at` | Yes | Source-system extraction time; D3.2 §2.1 staleness check input |
| `adapter_metadata` | No | Per-source provenance (adapter version, source system, source record id) |

## 4. Validation Rules

The middleware MUST validate every incoming record. Failure routes to
D2.6 quarantine with `failure_reason: schema-validation` and a
`failure_detail` string naming the violated rule.

### 4.1 Required-field absence

A record missing any of the §2 required fields fails validation.

### 4.2 Type/format violations

- `employeeId`, `firstName`, `lastName`, `department`, `locationCode`:
  empty string is a violation.
- `hireDate`, `terminationDate`: must parse as ISO-8601 calendar
  date.
- `country`: must match `^[A-Z]{2}$`.
- `email`: when present, must satisfy basic RFC 5322 well-formedness.
- `extracted_at`: must parse as ISO-8601 UTC timestamp.

### 4.3 Enum violations

- `workerType` not in D1.6 taxonomy → `failure_reason:
  worker-type-unknown` (NOT `schema-validation`).
- `employmentStatus` not in the §2 enum → `schema-validation`.

### 4.4 Cross-field constraints

- `terminationDate < hireDate` → schema-validation violation.
- `employmentStatus = "Terminated"` AND `terminationDate` absent →
  schema-validation violation.
- `employmentStatus = "PreHire"` AND `hireDate < today` (per tenant
  TZ) → schema-validation violation (a pre-hire whose start date
  has already passed should be reclassified Active by HR).

### 4.5 Staleness

`extracted_at` older than the tenant-configured staleness window
(default 24h, per D3.2 §6 configuration) → `schema-validation` with
`failure_detail: stale-record`.

## 5. Worker-Type Enum (Bridge to D1.6)

D1.1's `workerType` enum aligns with D1.6's canonical taxonomy:

| D1.1 enum value | D1.6 canonical type |
|---|---|
| `FullTimeEmployee` | Full-Time Employee |
| `PartTimeEmployee` | Part-Time Employee |
| `Contractor` | Contractor |
| `Intern` | Intern |
| `Vendor` | Vendor |
| `Volunteer` | Volunteer |
| `ExternalCollaborator` | External Collaborator |

D1.6 is the authoritative source; D1.1 mirrors it for schema-
validation purposes. Adding a new worker type to D1.6 requires a
parallel addition to D1.1's enum.

## 6. Source-System Mapping Pattern

UIAO is HR-system-agnostic. Per-source adapters in
`src/uiao/adapters/hr/<source>/` map vendor schemas to the canonical
shape:

| Vendor field name (typical) | Canonical D1.1 field |
|---|---|
| Workday `Employee_ID` / `Worker_ID` | `employeeId` |
| Oracle HCM `PersonNumber` | `employeeId` |
| SAP SuccessFactors `userId` / `personIdExternal` | `employeeId` |
| Workday `First_Name` | `firstName` |
| Oracle HCM `FirstName` | `firstName` |
| ... | ... |

The full mapping per vendor is the per-source-adapter's
documentation, NOT this canonical spec. D1.7 (HR Connector
Comparison Matrix) documents per-vendor field availability and
gaps.

## 7. Versioning

The schema carries a semver. v0.1 (this version) is the initial
canonical baseline. Backward-incompatible changes require:

1. A new ADR documenting the change rationale.
2. A version bump (e.g., 0.1 → 0.2 for additive changes; 0.1 → 1.0
   for the closure verification; 1.0 → 2.0 for breaking changes).
3. An update to the canonical schema file in the deployment
   repository.
4. A migration plan for in-flight records (when applicable).

The middleware reads the schema version at startup and stamps it on
every provenance record (via `middleware.schema_validator_version`
field).

## 8. Tenant Extensions (out of scope for v0.1)

Some agencies require fields beyond the canonical set (e.g., security
clearance, union membership, agency-specific codes). The v0.1
posture: extensions are NOT in scope. The schema is closed
(`additionalProperties: false`).

A future `tenant_extensions: object` field MAY be added in v0.2 to
allow per-tenant extension blocks while preserving the closed
canonical core. Specification of that surface is deferred.

## 9. References

### 9.1 Primary canon

- [ADR-003](../adr/adr-003-api-driven-inbound-provisioning.md) — API-driven inbound provisioning (the schema is the contract upstream of bulkUpload).
- [ADR-035](../adr/adr-035-orgpath-codebook-binding.md) — OrgPath codebook (the schema's organizational fields are codebook inputs).

### 9.2 UIAO docs

- [UIAO_007](../UIAO_007_OrgTree_Modernization_AD_to_EntraID_v1.0.md)
- [UIAO_135](../UIAO_135_identity-directory-transformation-inventory.md)
- [UIAO_136](../UIAO_136_priority1-transformation-project-plans.md) — §SPEC 2 → Phase 1 → D1.1.

### 9.3 Spec 2 sister deliverables

- Spec2-D1.2 — HR-to-OrgPath Translation Rules — consumes department / division / locationCode / costCenter (canonical .md forthcoming; PowerShell scaffolder at [`tools/discovery/Spec2-D1.2-ConvertTo-OrgPathTranslationRules.ps1`](../../../../tools/discovery/Spec2-D1.2-ConvertTo-OrgPathTranslationRules.ps1)).
- [Spec2-D1.3 — HR → Entra ID Attribute Mapping Matrix](./Spec2-D1.3-HRToEntraAttributeMappingMatrix.md) — consumes the full schema.
- [Spec2-D1.4 — HR → On-Prem AD Attribute Mapping Matrix](./Spec2-D1.4-HRToADAttributeMappingMatrix.md) — same.
- Spec2-D1.5 — UPN Generation Rules — consumes name + email + country (canonical .md forthcoming; PowerShell scaffolder at [`tools/discovery/Spec2-D1.5-New-UPNGenerationRules.ps1`](../../../../tools/discovery/Spec2-D1.5-New-UPNGenerationRules.ps1)).
- [Spec2-D1.6 — Worker Type Classification Taxonomy](./Spec2-D1.6-WorkerTypeClassificationTaxonomy.md) — defines `workerType` enum.
- [Spec2-D1.7 — HR Source System Connector Comparison Matrix](../../../../tools/discovery/Spec2-D1.7-HRConnectorComparisonMatrix.md) — per-vendor field availability.
- [Spec2-D1.8 — HR Data Quality Requirements](./Spec2-D1.8-HRDataQualityRequirements.md) — derived-from validation rules.
- [Spec2-D3.2 — Integration Middleware Specification](./Spec2-D3.2-IntegrationMiddlewareSpecification.md) §2 — middleware-side input contract.

### 9.4 Discovery generator

- [`tools/discovery/Spec2-D1.1-Get-HRAttributeSchema.ps1`](../../../../tools/discovery/Spec2-D1.1-Get-HRAttributeSchema.ps1) — probes deployment HR source for schema-conformance.

### 9.5 Compliance

- NIST SP 800-53 Rev 5: AC-2, AU-2, IA-4 (the schema is the input boundary for identity-data flow).
