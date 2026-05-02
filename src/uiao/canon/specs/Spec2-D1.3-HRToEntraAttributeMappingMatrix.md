---
deliverable_id: Spec2-D1.3
title: "HR to Entra ID Attribute Mapping Matrix"
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
  - ADR-048
canonical_docs:
  - UIAO_007
  - UIAO_135
  - UIAO_136
upstream_deliverables:
  - Spec2-D1.1
sibling_deliverables:
  - Spec2-D1.4
  - Spec2-D1.5
  - Spec2-D1.6
  - Spec2-D3.2
  - Spec2-D3.4
boundary: GCC-Moderate
classification: Controlled
---

# Spec 2 — D1.3: HR to Entra ID Attribute Mapping Matrix

> **Status (v0.1, 2026-05-01):** Initial draft. The PowerShell
> scaffolder at
> [`tools/discovery/Spec2-D1.3-New-AttributeMappingMatrix.ps1`](../../../../tools/discovery/Spec2-D1.3-New-AttributeMappingMatrix.ps1)
> generates a deployment-specific matrix from the deployment's actual
> HR source feeds. This document is the **canonical reference matrix**
> — the mapping every UIAO deployment honors before the per-source
> overrides apply.

## 1. Purpose, Scope, and Reference

This deliverable is the canonical HR-to-Entra mapping matrix called
for in
[`UIAO_136`](../UIAO_136_priority1-transformation-project-plans.md)
§SPEC 2 → Phase 1 → D1.3:

> *Complete mapping of HR attributes to Entra ID user properties:
> userPrincipalName, mail, displayName, department, jobTitle,
> manager, employeeId, extensionAttributes (OrgPath), employeeType,
> accountEnabled, usageLocation.*

D1.3 is the bridge between the canonical HR record (D1.1) and the
SCIM 2.0 wire format (D3.1 §5.2 / §5.4). It is consumed by the
middleware's payload builder (D3.2 §3.5) and by the Entra-side
synchronization-job mapping configuration (D3.4 §4).

### 1.1 Scope

In scope:

- The canonical 1:1 / 1:N mapping from D1.1 fields to SCIM payload
  fields and Entra ID user properties.
- The transformation rules for computed fields (UPN, OrgPath,
  display name composition).
- The pass-through rules for optional fields.
- The omit-empty-don't-emit-empty-string contract.
- Mapping behavior under JML events (Joiner / Mover / Leaver /
  Rehire / Conversion).
- The `extensionAttribute` allocation map.

Out of scope:

- HR-source-specific field mapping (per-source adapters; D1.7
  matrix).
- The OrgPath codebook itself (ADR-035 + D1.2).
- The UPN generator's collision resolution (D1.5).
- Tenant-specific extension attribute usage (per-tenant policy).
- AD writeback mapping (see D1.4).

## 2. The Canonical Mapping Table

The full mapping from D1.1 canonical record → SCIM payload (per
D3.1 §5.2):

| D1.1 field | SCIM payload field | Mapping type | Notes |
|---|---|---|---|
| `employeeId` | `externalId` | direct | Correlation anchor; immutable |
| `employeeId` | `enterprise:User.employeeNumber` | direct | Microsoft requires both |
| (computed) | `userName` | UPN generator (D1.5) | Source: firstName + lastName + tenant domain + collision resolution |
| `firstName` | `name.givenName` | direct | Diacritics preserved |
| `lastName` | `name.familyName` | direct | Diacritics preserved |
| (composed) | `displayName` | composition | Default: `lastName, firstName`; tenant-policy override |
| `email` (or computed) | `emails[0].value` (work, primary) | direct OR derived from UPN | If HR `email` absent, derive from UPN |
| `phoneNumber` | `phoneNumbers[0].value` (work) | direct (when present) | Omit array element if absent |
| `addresses` | `addresses` | direct | Pass-through; type→type mapping |
| (derived) | `active` | derived from `employmentStatus` | Active/OnLeave→true; PreHire→false; Terminated→false |
| `country` | `usageLocation` | direct | ISO-3166 alpha-2 |
| `department` | `enterprise:User.department` | direct | |
| `jobTitle` | `enterprise:User.title` | direct (when present) | Omit if absent |
| `managerEmployeeId` | `enterprise:User.manager.value` | direct | Omit if null |
| (computed) | `extensionAttribute1` | OrgPath calculator (ADR-035) | OrgPath via codebook lookup |
| (computed) | `extensionAttribute2` | worker-type-derived license-affinity tag | Per D1.6 + tenant policy |
| (default) | `preferredLanguage` | constant | Default `en-US`; tenant override |

## 3. Field-by-Field Specification

### 3.1 Identity correlation: `externalId` + `employeeNumber`

Both SCIM `externalId` and `enterprise:User.employeeNumber` MUST be
populated with the canonical `employeeId` value. This is a Microsoft
constraint — bulkUpload requires both fields, and Entra reconciles on
both during async processing.

```yaml
externalId:                                EMP-12345
enterprise:User.employeeNumber:            EMP-12345
```

### 3.2 UPN: `userName`

`userName` is the load-bearing identity attribute. The UPN generator
(D1.5) produces it from canonical record + tenant policy.

The middleware MUST emit a UPN for every record. UPN absence → record
quarantined with `failure_reason: schema-validation` and
`failure_detail: upn-empty`.

UPN format (typical):

```
firstname.lastname@tenant-domain.gov                   # default
firstname.lastname.contractor@tenant-domain.gov         # contractor variant (per D1.6)
firstname.lastname2@tenant-domain.gov                   # collision-suffix
```

### 3.3 Names: `givenName` / `familyName` / `displayName`

| SCIM field | Canonical source | Notes |
|---|---|---|
| `name.givenName` | `firstName` | Diacritics preserved |
| `name.familyName` | `lastName` | Diacritics preserved |
| `name.middleName` | (out of scope v0.1) | |
| `displayName` | composed | Tenant policy: `lastName, firstName` (default) OR `firstName lastName` OR HR-provided `displayName` |

The `displayName` composition is per-tenant policy. The default UIAO
posture: `lastName, firstName` (e.g., "Doe, Jane") which sorts well in
M365 directory-list views. Tenants may override.

If HR provides a non-empty `displayName`, the middleware MUST honor
it (HR is source-of-truth for display preference). Composed display
names apply only when HR's `displayName` is empty/absent.

### 3.4 Communication: `emails` + `phoneNumbers` + `addresses`

| SCIM field | Canonical source | Behavior |
|---|---|---|
| `emails[0].value` (work, primary) | HR `email` OR computed UPN | If HR provides, use; else derive from UPN |
| `phoneNumbers[0].value` (work) | HR `phoneNumber` | Omit array entry if absent |
| `addresses` | HR `addresses` (list) | Pass-through; type→type |

The omit-empty-don't-emit-empty-string contract from D3.1 §5.4:
empty optional fields are OMITTED entirely from the SCIM payload.
The middleware MUST NOT emit empty strings for missing values.

### 3.5 Lifecycle: `active`

`active` is derived from `employmentStatus`:

| HR `employmentStatus` | SCIM `active` |
|---|---|
| Active | true |
| OnLeave | true (account stays active; CA policies may restrict) |
| PreHire | false |
| Terminated | false |
| Rescinded | false (and routes to D2.7 §6.1 cleanup) |

### 3.6 Region: `usageLocation`

`usageLocation` MUST be populated from `country` (ISO-3166 alpha-2).
This drives M365 license assignment region behavior.

If `country` is absent in HR feed, the record is quarantined per
D2.6 with `failure_reason: usage-location-missing`. There is no
"safe default" — license region is a tenant-policy + legal concern.

### 3.7 Organization: `department` / `title` / `manager`

| SCIM field | Canonical source | Notes |
|---|---|---|
| `enterprise:User.department` | `department` | Direct; OrgPath calculator ALSO consumes this |
| `enterprise:User.title` | `jobTitle` | Direct (when present); omit if absent |
| `enterprise:User.manager.value` | `managerEmployeeId` | Direct; omit `manager` block entirely if null |

`manager.value` is an `externalId` reference. Entra ID reconciles
manager links asynchronously; dangling references resolve on later
sync cycles (per D2.1 §6).

### 3.8 OrgPath: `extensionAttribute1`

`extensionAttribute1` is the load-bearing OrgPath attribute per
ADR-048 (attribute selection) + ADR-035 (codebook binding).

```yaml
urn:scim:schemas:extension:Microsoft:2.0:User:
  extensionAttribute1:    GOV/EXEC/OPM/HRIT
```

Computation path: HR record's `department` + `division` +
`locationCode` + `costCenter` + `organizationCode` →
OrgPath calculator (D3.2 §3.2) → string.

### 3.9 Worker-type / license-affinity: `extensionAttribute2`

`extensionAttribute2` (or the tenant-named equivalent) holds a
worker-type-derived license-affinity tag that drives group-based
licensing. Per D1.6 taxonomy and tenant policy.

Examples:

| `workerType` | `extensionAttribute2` (illustrative) |
|---|---|
| FullTimeEmployee | `FTE-E5` |
| PartTimeEmployee | `PTE-E3` |
| Contractor | `CONTRACTOR-A1` |
| Intern | `INTERN-A1` |

Tenants choose the actual tag taxonomy. UIAO's contract: ONE
license-affinity tag per record, derived from worker type.

### 3.10 Constants

| SCIM field | Default value | Override |
|---|---|---|
| `preferredLanguage` | `en-US` | Tenant policy |

The middleware emits the default unless tenant configuration
overrides.

## 4. ExtensionAttribute Allocation Map

Microsoft Entra ID reserves `extensionAttribute1` through
`extensionAttribute15` for tenant-defined string attributes. UIAO's
canonical allocation:

| Attribute | UIAO usage |
|---|---|
| `extensionAttribute1` | **OrgPath** (ADR-048; load-bearing) |
| `extensionAttribute2` | Worker-type / license-affinity tag |
| `extensionAttribute3` | LOA / sabbatical flag (per D2.8 §4.1) |
| `extensionAttribute4` | Tenant-policy reserved |
| `extensionAttribute5` | Tenant-policy reserved |
| `extensionAttribute6`–`15` | Tenant-defined |

Tenants MUST NOT redefine `extensionAttribute1` for non-OrgPath use.
This is a UIAO canonical constraint (per ADR-048).

## 5. JML Behavior

How the mapping behaves across JML events:

### 5.1 Joiner (D2.1)

All §2 mappings emit on first POST (or PATCH if pre-hire record
exists). `active` flag follows D2.7 windows: false during pre-hire,
true at day-of-hire.

### 5.2 Mover (D2.2)

Single PATCH with delta fields only. Unchanged fields are NOT
re-emitted (per D2.2 §5: single atomic PATCH per cycle).

### 5.3 Leaver (D2.3)

Step 1 of D2.3 §4 emits a PATCH setting `active: false`. All other
mapped attributes are PRESERVED (D2.3 §6 OrgPath freeze rule).

### 5.4 Rehire (D2.4)

Path A (reactivation): full attribute refresh PATCH per §2.
Path B (new): full POST per §2.

### 5.5 Conversion (D2.5)

Atomic PATCH carrying `workerType` (→ `extensionAttribute2` re-stamp),
OrgPath recompute (→ `extensionAttribute1` re-stamp), and any other
delta fields. UPN preserved by default (D2.5 §4.1).

## 6. Drift Detection Anchor

Each record's emitted `extensionAttribute1` value MUST match what
the current OrgPath calculator produces from the current HR record.
The drift engine (ADR-040) reads provenance records and reconciles:

| Drift class | Trigger |
|---|---|
| `DRIFT-IDENTITY` | Stored `extensionAttribute1` ≠ current calculator output |
| `DRIFT-PROVENANCE` | Emitted-calculator-version differs from current-deployed-version AND outputs differ |

D1.3's contract with the drift engine: the mapping table in §2 is the
source of truth. Drift on any §2 field is a finding.

## 7. References

### 7.1 Primary canon

- [ADR-003](../adr/adr-003-api-driven-inbound-provisioning.md)
- [ADR-035](../adr/adr-035-orgpath-codebook-binding.md)
- [ADR-048](../adr/adr-048-orgpath-attribute-storage-decision.md) — extensionAttribute1 selection.

### 7.2 UIAO docs

- [UIAO_007](../UIAO_007_OrgTree_Modernization_AD_to_EntraID_v1.0.md)
- [UIAO_136](../UIAO_136_priority1-transformation-project-plans.md) — §SPEC 2 → Phase 1 → D1.3.

### 7.3 Spec 2 sister deliverables

- [Spec2-D1.1 — Canonical HR Attribute Schema](./Spec2-D1.1-CanonicalHRAttributeSchema.md) — input contract.
- [Spec2-D1.4 — HR to On-Prem AD Attribute Mapping Matrix](./Spec2-D1.4-HRToADAttributeMappingMatrix.md) — coexistence-time AD writeback.
- Spec2-D1.5 — UPN Generation Rules — §3.2 source (canonical .md forthcoming; PowerShell scaffolder at [`tools/discovery/Spec2-D1.5-New-UPNGenerationRules.ps1`](../../../../tools/discovery/Spec2-D1.5-New-UPNGenerationRules.ps1)).
- [Spec2-D1.6 — Worker Type Classification Taxonomy](./Spec2-D1.6-WorkerTypeClassificationTaxonomy.md) — §3.9 source.
- [Spec2-D3.1](./Spec2-D3.1-APIDrivenInboundProvisioningArchitecture.md) §5 — SCIM payload contract this matrix conforms to.
- [Spec2-D3.2](./Spec2-D3.2-IntegrationMiddlewareSpecification.md) §3.5 — payload builder consumes this matrix.
- [Spec2-D3.4](./Spec2-D3.4-AttributeMappingEngineConfiguration.md) §4 — Entra-side synchronization-job mapping configuration is layer 2 of this matrix.

### 7.4 Discovery generator

- [`tools/discovery/Spec2-D1.3-New-AttributeMappingMatrix.ps1`](../../../../tools/discovery/Spec2-D1.3-New-AttributeMappingMatrix.ps1) — generates deployment-specific matrix from actual HR feeds.

### 7.5 Compliance

- NIST SP 800-53 Rev 5: AC-2, IA-4, AU-2, CM-3 (mapping is configuration; changes require change control).
