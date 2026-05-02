---
deliverable_id: Spec2-D1.4
title: "HR to On-Prem AD Attribute Mapping Matrix"
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
  - Spec2-D1.3
  - Spec2-D1.6
sibling_deliverables:
  - Spec2-D3.3
  - Spec2-D3.6
boundary: GCC-Moderate
classification: Controlled
---

# Spec 2 — D1.4: HR to On-Prem AD Attribute Mapping Matrix

> **Status (v0.1, 2026-05-01):** Initial draft. The PowerShell
> scaffolder at
> [`tools/discovery/Spec2-D1.4-New-HRToADAttributeMappingMatrix.ps1`](../../../../tools/discovery/Spec2-D1.4-New-HRToADAttributeMappingMatrix.ps1)
> generates a deployment-specific matrix. This document is the
> canonical reference. Coexistence-period only — sunsets per UIAO_007
> on AD decommission.

## 1. Purpose, Scope, and Reference

This deliverable is the canonical HR-to-AD mapping matrix called for
in
[`UIAO_136`](../UIAO_136_priority1-transformation-project-plans.md)
§SPEC 2 → Phase 1 → D1.4:

> *Complete mapping of HR attributes to AD user properties for
> coexistence period: sAMAccountName, distinguishedName (OU
> placement), userPrincipalName, displayName, department, title,
> manager (DN), employeeID, extensionAttributes.*

D1.4 governs Entra-side → on-prem-AD writeback during the AD
decommission coexistence period (UIAO_007). The provisioning agent
(D3.3) consumes this matrix to write back to AD; the Entra-side
fields are the source per the cloud-first asymmetric posture (D3.6
§3).

### 1.1 Scope

In scope:

- The Entra ID (post-D1.3 mapping) → on-prem AD writeback set.
- OU placement rules.
- DN (distinguishedName) construction rules.
- `sAMAccountName` derivation.
- `userAccountControl` flag mapping.
- Coexistence-only scope and sunset path.

Out of scope:

- HR → Entra mapping (see D1.3).
- HR → HR writeback (see D3.6 §4).
- AD-only legacy attributes that don't have a UIAO source-of-truth
  (left untouched by writeback).
- The provisioning agent itself (D3.3).

### 1.2 Direction

D1.4 is **uni-directional**: Entra ID → on-prem AD. AD-side edits
are NOT a UIAO source; per D3.6 §3, AD-side writes during
coexistence are blocked at the AD ACL layer (gMSA + break-glass
only) and any that do occur are overwritten by the next sync cycle.

## 2. The Mapping Table

For each HR attribute landed in Entra ID per D1.3, the Entra → AD
writeback target:

| Entra ID attribute | AD attribute (LDAP name) | Mapping type | Notes |
|---|---|---|---|
| `userPrincipalName` | `userPrincipalName` | direct | UPN preserved across the boundary |
| `mail` | `mail` | direct | |
| `displayName` | `displayName` | direct | |
| `givenName` | `givenName` | direct | |
| `surname` | `sn` | direct | |
| `enterprise:User.department` | `department` | direct | |
| `enterprise:User.title` | `title` | direct | |
| `enterprise:User.manager.value` | `manager` | DN-resolved | See §4 |
| `enterprise:User.employeeNumber` | `employeeID` | direct | |
| `usageLocation` | `c` (country) | direct | ISO-3166 alpha-2 |
| `extensionAttribute1` (OrgPath) | `extensionAttribute1` | direct | Preserved across the boundary |
| `extensionAttribute2` (worker-type tag) | `extensionAttribute2` | direct | |
| `accountEnabled` | `userAccountControl` (bit 2) | bit-mapped | true = bit clear; false = bit set |
| (computed) | `sAMAccountName` | derived | See §3 |
| (computed) | `distinguishedName` | derived | See §5 |

## 3. `sAMAccountName` Derivation

`sAMAccountName` is the legacy NetBIOS-era login name (≤ 20
characters, restricted character set). UIAO derives it from UPN:

```
sAMAccountName = local-part(userPrincipalName) truncated to 20 chars
                 with non-alphanumeric replaced or removed
```

Rules:

1. Take the UPN local-part (everything before `@`).
2. Strip any character not in `[A-Za-z0-9._-]`.
3. If length > 20, truncate to 20 (worst-case loses the collision
   suffix; document in adapter metadata for audit).
4. Lowercase.

Example:

| UPN | sAMAccountName |
|---|---|
| `jane.doe@agency.gov` | `jane.doe` |
| `jane.doe.contractor@agency.gov` | `jane.doe.contractor` |
| `jane.doe.contractor2@agency.gov` | `jane.doe.contracto2` (truncated) |

When truncation produces a sAMAccountName collision (separate from
the UPN-side collision resolved per D1.5), the agent appends a
numeric suffix at the cost of further truncation. Tenants whose
naming scheme regularly produces > 20-char local parts SHOULD adopt
a shorter UPN convention (e.g., `firstinitial.lastname`).

## 4. Manager DN Resolution

`enterprise:User.manager.value` in SCIM is an `externalId`
reference. AD's `manager` attribute is a **DN** reference (path to
the manager's user object).

The provisioning agent resolves the DN at writeback time:

1. Look up the manager's `externalId` in the writeback OU subtree
   via `employeeID` attribute.
2. Construct the manager's DN.
3. Write to the user's `manager` attribute.

Failure modes:

| Condition | Behavior |
|---|---|
| Manager not yet present in AD (newer-than-user records) | Defer manager link to next sync cycle (deferred resolution) |
| Manager `externalId` not found anywhere (HR data quality) | Quarantine record per D2.6 with `failure_reason: manager-stale` |
| Manager exists in cloud but AD writeback is excluded | Leave AD `manager` empty; cloud-side `manager` remains source-of-truth |

## 5. OU Placement (`distinguishedName`)

Per D2.1 §8, OU placement is computed at the middleware layer (not
the agent). The middleware emits a `dn` hint in the SCIM payload's
agent-private extension; the agent honors it.

OU structure (canonical UIAO):

```
OU=Cloud-Provisioned, DC=<domain>
├── OU=Employees
│   ├── OU=US-DC
│   │   ├── OU=HRIT
│   │   ├── OU=Finance
│   │   └── ...
│   ├── OU=US-VA
│   └── ...
├── OU=Contractors
├── OU=Interns
├── OU=Vendors
└── OU=Volunteers
```

The mapping rules:

| HR attribute | OU level |
|---|---|
| `workerType` | Top-level (`OU=Employees`, `OU=Contractors`, …) |
| `locationCode` | Second level (`OU=US-DC`, `OU=US-VA`, …) |
| `department` | Third level (`OU=HRIT`, `OU=Finance`, …) |

D3.3 §5 names the canonical OU subtree (`OU=Cloud-Provisioned`).
Tenants whose AD topology requires different placement may override,
documented in `substrate-manifest.yaml`.

## 6. `userAccountControl` Bit Mapping

AD's `userAccountControl` is a bitmask. UIAO's writeback affects
specifically:

| UAC bit | Decimal | UIAO source |
|---|---|---|
| ACCOUNTDISABLE (bit 1, value 2) | 2 | `accountEnabled = false` → bit set; true → bit clear |
| PASSWD_NOTREQD (bit 5, value 32) | 32 | NOT set by UIAO (cloud-only auth posture) |
| DONT_EXPIRE_PASSWORD (bit 16, value 65536) | 65536 | Tenant policy |
| WORKSTATION_TRUST_ACCOUNT (bit 12) | 4096 | NOT user accounts |

UIAO's writeback only manages ACCOUNTDISABLE. Other UAC bits are
preserved unchanged (or set per tenant policy out of band).

## 7. Excluded Attributes

UIAO does NOT write back to:

| AD attribute | Reason |
|---|---|
| `pwdLastSet` | UIAO uses cloud-only auth (no AD password rotation by middleware) |
| `unicodePwd` / `userPassword` | UIAO never sets AD passwords |
| `objectSid` | AD-side identifier; AD-managed |
| `objectGUID` | AD-side identifier; AD-managed |
| `memberOf` | Computed from group memberships; not directly set |
| `lastLogon` / `lastLogonTimestamp` | AD-side activity record |
| `proxyAddresses` | Exchange / cloud-managed |

## 8. JML Behavior on AD

| Event | AD effect |
|---|---|
| Joiner — pre-hire | User created (disabled) in target OU per §5; `userAccountControl` ACCOUNTDISABLE set |
| Joiner — day-of-hire | ACCOUNTDISABLE cleared; rest of attributes already set during pre-hire |
| Mover | Single attribute-update writeback for changed fields. **OU move occurs** if `workerType`/`location`/`department` change crosses an OU boundary |
| Leaver | ACCOUNTDISABLE set; account remains in original OU during retention; OrgPath frozen |
| Rehire (Path A reactivation) | ACCOUNTDISABLE cleared; full attribute refresh |
| Rehire (Path B new) | New AD account creation per Joiner pattern |
| Conversion | Single PATCH; **OU move likely** since worker-type change crosses top-level OU |

OU moves are LDAP move operations. They require gMSA Move-from-source
+ Move-to-destination permissions, both typically granted within the
single `OU=Cloud-Provisioned` subtree.

## 9. AD Group Membership

Per D3.6 §2.2: group writeback is enabled when there are AD-side
legacy applications consuming group membership from on-prem. UIAO's
posture: enable group writeback case-by-case.

When enabled:

- Cloud → AD group writeback is configured at the synchronization-job
  level (out of D1.4 scope).
- The user's `memberOf` attribute is computed from the AD-side
  groups they're members of (after writeback).
- D1.4 does NOT directly map to `memberOf`; it's a derived attribute
  on the AD side.

## 10. Sunset Path

Per D3.3 §9 + D3.6 §5: when AD decommissions per UIAO_007:

1. Verify zero AD-side identity dependencies remain.
2. Disable the synchronization job's AD-writeback flag.
3. Continue observability for 30 days.
4. Decommission the agent (D3.3 §9 8-step runbook).
5. **D1.4 becomes a historical document** — no further writeback.
6. Consider removing the writeback OUs and gMSA at the agency's
   chosen retention boundary.

## 11. Drift Detection

Per ADR-040: the drift engine checks that AD-side state matches
Entra-side state per the §2 mapping. Mismatches are
DRIFT-IDENTITY findings. The drift engine ignores excluded
attributes (§7).

## 12. References

### 12.1 Primary canon

- [ADR-003](../adr/adr-003-api-driven-inbound-provisioning.md)
- [ADR-035](../adr/adr-035-orgpath-codebook-binding.md)
- [ADR-048](../adr/adr-048-orgpath-attribute-storage-decision.md)

### 12.2 UIAO docs

- [UIAO_007](../UIAO_007_OrgTree_Modernization_AD_to_EntraID_v1.0.md) — coexistence + decommission sequencing.
- [UIAO_136](../UIAO_136_priority1-transformation-project-plans.md) — §SPEC 2 → Phase 1 → D1.4.

### 12.3 Spec 2 sister deliverables

- [Spec2-D1.1 — Canonical HR Attribute Schema](./Spec2-D1.1-CanonicalHRAttributeSchema.md) — root input.
- [Spec2-D1.3 — HR → Entra ID Attribute Mapping Matrix](./Spec2-D1.3-HRToEntraAttributeMappingMatrix.md) — upstream layer.
- [Spec2-D1.6 — Worker Type Classification Taxonomy](./Spec2-D1.6-WorkerTypeClassificationTaxonomy.md) — §5 OU level driver.
- [Spec2-D3.3 — Provisioning Agent Deployment Architecture](./Spec2-D3.3-ProvisioningAgentDeploymentArchitecture.md) — agent deploys writeback.
- [Spec2-D3.6 — Writeback Specification](./Spec2-D3.6-WritebackSpecification.md) — operational boundary.

### 12.4 Discovery generator

- [`tools/discovery/Spec2-D1.4-New-HRToADAttributeMappingMatrix.ps1`](../../../../tools/discovery/Spec2-D1.4-New-HRToADAttributeMappingMatrix.ps1)

### 12.5 Compliance

- NIST SP 800-53 Rev 5: AC-2, IA-4, AU-2, CM-3.
