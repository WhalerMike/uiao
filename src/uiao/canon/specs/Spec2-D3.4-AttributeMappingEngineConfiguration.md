---
deliverable_id: Spec2-D3.4
title: "Attribute Mapping Engine Configuration"
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
canonical_docs:
  - UIAO_007
  - UIAO_135
  - UIAO_136
upstream_deliverables:
  - Spec2-D1.1
  - Spec2-D1.3
  - Spec2-D1.4
  - Spec2-D1.5
  - Spec2-D1.6
  - Spec2-D3.1
  - Spec2-D3.2
sibling_deliverables:
  - Spec2-D3.5
  - Spec2-D3.6
boundary: GCC-Moderate
classification: Controlled
---

# Spec 2 — D3.4: Attribute Mapping Engine Configuration

> **Status (v0.1, 2026-05-01):** Initial draft. v0.2 verification
> against Microsoft Learn provisioning-attribute-mappings reference
> (function library, expression syntax) is the closure pass.

## 1. Purpose, Scope, and Reference

This deliverable is the canonical Attribute Mapping Engine
specification called for in
[`UIAO_136`](../UIAO_136_priority1-transformation-project-plans.md)
§SPEC 2 → Phase 3 → D3.4:

> *Entra ID provisioning app attribute mapping configuration:
> expression-based mappings, constant values, direct mappings,
> function-based transformations (Switch, Join, Replace, ToUpper).
> Include OrgPath calculation expression.*

D3.4 covers two layers of mapping:

1. **Middleware-side mappings** (D3.2 §3.1 normalizer + §3.5
   payload builder): HR-source-record → canonical record →
   SCIM payload.
2. **Entra-side mappings** (the synchronization job's attribute-
   mappings configuration): SCIM payload → Entra user properties.

Both layers must agree on what gets written where.

### 1.1 Scope

In scope:

- The two-layer mapping architecture.
- The middleware-side attribute mapping rules per D1.3 / D1.4.
- The Entra-side synchronization-job attribute mapping
  configuration (declarative, exported / version-controlled).
- The expression-language surface (functions used by both layers).
- The OrgPath calculation expression (the load-bearing mapping).
- Mapping versioning + drift detection.

Out of scope:

- The OrgPath codebook itself (ADR-035; D1.2 translation rules).
- The UPN generator (D1.5; lives in D3.2 §3.3).
- The worker-type taxonomy (D1.6).
- HR-source per-source mapping logic (lives in source adapters).

## 2. Two-Layer Mapping Architecture

```
HR-source record
   │
   │  (per-source adapter; out of scope)
   ▼
Canonical D1.1 record
   │
   │  Layer 1: Middleware-side mappings (D3.4 §3)
   │           ├ Schema normalization
   │           ├ OrgPath calculation
   │           ├ UPN generation
   │           ├ Worker-type classification
   ▼
SCIM payload (canonical user shape per D3.1 §5.2)
   │
   ▼
Microsoft Graph bulkUpload
   │
   ▼
Entra ID Provisioning Service
   │
   │  Layer 2: Entra-side mappings (D3.4 §4)
   │           ├ SCIM-to-Entra attribute binding
   │           ├ Function-based transformations
   │           ├ Constant-value defaults
   ▼
Entra ID user record
   │
   ▼  (coexistence period)
Provisioning Agent → On-Prem AD writeback
   │
   │  Layer 2 again (downstream): Entra → AD attribute mapping
   ▼
On-prem AD user record
```

Both layers are the canonical contract. Middleware-side
mappings live in code (D3.2 §3); Entra-side mappings live in the
synchronization job's exported configuration (this document).

## 3. Layer 1: Middleware-Side Mappings

The middleware applies transformations from the canonical D1.1
record to the SCIM payload per D1.3 (HR → Entra) and D1.4 (HR →
on-prem AD). The full mapping table is in D1.3 / D1.4 — D3.4
binds the canonical mapping function set.

### 3.1 Direct mappings

Pass-through fields (D1.1 → SCIM):

| D1.1 field | SCIM field |
|---|---|
| `employeeId` | `externalId` |
| `firstName` | `name.givenName` |
| `lastName` | `name.familyName` |
| `displayName` | `displayName` (or computed; see §3.4) |
| `email` | `emails[0].value` (work, primary) |
| `country` | `usageLocation` (ISO-3166 alpha-2) |
| `department` | `enterprise:User.department` |
| `jobTitle` | `enterprise:User.title` (when present) |
| `managerEmployeeId` | `enterprise:User.manager.value` |

### 3.2 Computed mappings

| Output field | Computation |
|---|---|
| `userName` (UPN) | UPN generator (D1.5; D3.2 §3.3) |
| `extensionAttribute1` | OrgPath calculator (D3.2 §3.2; ADR-035 codebook + ADR-048 attribute selection) |
| `enterprise:User.employeeNumber` | = `externalId` (Microsoft requires both) |
| `active` | derived from D1.1 `employmentStatus` per D2.x rules |
| `accountEnabled` (AD) | = `active` |

### 3.3 Constant defaults (per-deployment)

| Output field | Value |
|---|---|
| `preferredLanguage` | `en-US` (override per deployment) |
| `usageLocation` | falls back to deployment default if D1.1 `country` is null |

### 3.4 Tenant-policy mappings

Tenants choose:

- `displayName` format: `firstName lastName` vs. `lastName, firstName` vs. preserve-from-HR.
- Email visibility (proxyAddresses entries beyond primary).
- Phone-number formatting.

Tenant policy lives in `substrate-manifest.yaml` and the
middleware's mapping table reads it at startup.

## 4. Layer 2: Entra-Side Synchronization Job Mapping

The Entra ID provisioning service consumes the SCIM payload and
writes Entra user properties via its **attribute-mappings**
configuration. This configuration is authored in the Microsoft
Entra portal OR via Microsoft Graph synchronization API.

### 4.1 Default mappings

For each SCIM attribute the bulkUpload payload carries, the Entra
provisioning job has a default mapping to the corresponding
Entra ID user property. The defaults are appropriate for most
fields (`externalId` → `employeeId`; `userName` → `userPrincipalName`;
etc.).

UIAO MUST NOT silently rely on defaults — every load-bearing
attribute mapping is **explicitly listed** in the deployment's
exported attribute-mapping configuration.

### 4.2 Function-based transformations

Microsoft documents an expression-language surface for attribute
mappings. The functions UIAO MUST be familiar with:

| Function | Usage |
|---|---|
| `Switch(source, default, "case1", "value1", …)` | Conditional value selection |
| `Join(separator, list…)` | Concatenation |
| `Replace(source, oldValue, oldValueRegex, replacementValueGroup, replacementValue, escaped)` | Text replacement |
| `ToUpper(source)` / `ToLower(source)` | Case normalization |
| `IIF(condition, ifTrue, ifFalse)` | Inline conditional |
| `Mid(source, start, length)` | Substring |
| `IsPresent(source)` | Existence check |
| `Trim(source)` | Whitespace trimming |
| `Item(source, index)` | List indexing |

The full function surface MUST be re-verified against Microsoft
Learn at v0.2 (these names are the ones documented as of D3.1's
verification date; minor surface changes are typical year-over-
year).

### 4.3 OrgPath calculation expression

UIAO's OrgPath could in principle be computed Entra-side via the
expression language. **UIAO does NOT do this.** OrgPath is
computed middleware-side per ADR-050 (the middleware owns the
ADR-035 codebook; the Entra expression language is too constrained
to evaluate codebook lookups reliably at scale).

The Entra-side mapping for `extensionAttribute1` is a **direct
mapping** from the SCIM payload's `extensionAttribute1`:

```
Source: scim:User:urn:scim:schemas:extension:Microsoft:2.0:User:extensionAttribute1
Target: extensionAttribute1
Type: direct
```

This is the canonical UIAO posture and the reason why D3.4 is a
small spec relative to a generic Entra deployment guide: most of
the transformation happens in the middleware.

### 4.4 AD writeback mapping (coexistence)

The provisioning agent (D3.3) honors a separate set of mappings
from Entra → on-prem AD. UIAO's writeback set per D1.4:

| Entra attribute | AD attribute |
|---|---|
| `userPrincipalName` | `userPrincipalName` |
| `mail` | `mail` |
| `displayName` | `displayName` |
| `givenName` | `givenName` |
| `surname` | `sn` |
| `department` | `department` |
| `title` | `title` |
| `manager` | `manager` (DN-resolved) |
| `extensionAttribute1` | `extensionAttribute1` (preserved) |
| `employeeId` | `employeeID` |
| `usageLocation` | `c` (country) |
| `accountEnabled` | `userAccountControl` (with appropriate flag bits) |

Manager DN resolution: the provisioning agent looks up the
manager's DN in the writeback OU subtree based on `employeeID`.
If the manager doesn't exist in AD yet, the writeback uses a
deferred-resolution pattern (write user without manager link;
re-attempt on next sync cycle).

### 4.5 Configuration export

The Entra-side mapping configuration MUST be exported and
version-controlled. UIAO uses Microsoft Graph's synchronization
API to fetch the current job configuration as JSON, store it in
the deployment repository at `config/synchronization-job/<job-id>.json`,
and validate on every CI run that the deployed configuration
matches the committed configuration.

Drift between deployed and committed → tier-2 alert per D3.7.

## 5. Expression-Language Examples

Illustrative examples of the kinds of mappings UIAO is likely to
have:

```
# Direct mapping
displayName = displayName

# Function-based
mailNickname = Replace(mailNickname, ,
                  "([A-Za-z0-9])\.([A-Za-z0-9])",
                  "$1$2", "")

# Conditional
employeeType = Switch(workerType, "Other",
                  "Full-Time Employee", "Employee",
                  "Part-Time Employee", "Employee",
                  "Contractor", "Contractor",
                  "Intern", "Intern")

# IIF
companyName = IIF(IsPresent(division), division, "Default Org")
```

These are not load-bearing UIAO mappings; they're examples of the
expression surface. The deployment's actual mappings live in the
exported configuration.

## 6. Versioning + Drift Detection

Each mapping (middleware-side and Entra-side) carries a version:

- **Middleware-side:** the OrgPath calculator / UPN generator / worker-
  type classifier each carry a semver tracked in D3.2 §3.
- **Entra-side:** the synchronization-job configuration JSON carries
  the Microsoft-assigned `templateId` plus a UIAO-stamped
  `uiao_version` field in the deployment repository.

The drift engine (ADR-040) reads provenance records (D3.1 §8.2)
which include the calculator version stamps. Mismatches between
emitted-version and current-deployed-version are
DRIFT-PROVENANCE / DRIFT-IDENTITY findings.

## 7. Failure Modes

D3.4-specific failure modes (delegated to D2.6):

| Failure | `failure_reason` |
|---|---|
| Codebook miss (OrgPath) | `orgpath-codebook-miss` |
| Worker-type classifier miss | `worker-type-unknown` |
| UPN-generator collision unresolvable | `upn-collision` |
| Required mapping absent in Entra-side config | new class: `entra-mapping-missing` (alert; not record-specific) |
| Drift between deployed Entra config and committed config | `entra-mapping-drift` (alert; not record-specific) |

The two new alert classes route to operations, not the per-record
quarantine queue, since they are configuration concerns.

## 8. References

### 8.1 Primary canon

- [ADR-003](../adr/adr-003-api-driven-inbound-provisioning.md)
- [ADR-035](../adr/adr-035-orgpath-codebook-binding.md)
- [ADR-048](../adr/adr-048-orgpath-attribute-storage-decision.md)
- [ADR-049](../adr/adr-049-microsoft-adapter-coverage-expansion.md)

### 8.2 UIAO docs

- [UIAO_136](../UIAO_136_priority1-transformation-project-plans.md) — §SPEC 2 → Phase 3 → D3.4.

### 8.3 Spec 2 sister deliverables

- [Spec2-D3.1](./Spec2-D3.1-APIDrivenInboundProvisioningArchitecture.md) — §5 SCIM payload contract.
- [Spec2-D3.2](./Spec2-D3.2-IntegrationMiddlewareSpecification.md) — middleware-side mapping engine.
- [Spec2-D3.5](./Spec2-D3.5-OrgPathPopulationPipeline.md) — end-to-end OrgPath flow.
- [Spec2-D3.6](./Spec2-D3.6-WritebackSpecification.md) — Entra → AD writeback mappings.
- Spec2-D1.1 — canonical schema (forthcoming).
- Spec2-D1.3 — HR → Entra attribute mapping matrix.
- Spec2-D1.4 — HR → on-prem AD attribute mapping matrix.
- Spec2-D1.5 — UPN generation rules.
- Spec2-D1.6 — worker-type taxonomy.

### 8.4 Microsoft documentation (verification pending in v0.2)

- Microsoft Learn — Reference for writing expressions for attribute mappings in Microsoft Entra.
- Microsoft Learn — How attribute mappings work for app provisioning.

### 8.5 Compliance

- NIST SP 800-53 Rev 5: CM-2 (baseline configuration), CM-3 (configuration change control), AU-2.
