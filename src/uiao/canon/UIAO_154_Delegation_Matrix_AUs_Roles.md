---
document_id: UIAO_154
title: "Appendix D — Delegation Matrix (AUs + Roles) — Model C"
version: "3.0"
status: Current
owner: Michael Stratton
author: Michal Doroszewski
created_at: "2026-04-18"
updated_at: "2026-05-24"
promotion:
  prior_version: "2.0 (Model A composite-hyphen AU rules: -startsWith \"ORG-FIN\")"
  promoted_by: "Governance Steward"
  promotion_date: "2026-05-24"
  promotion_adr: ADR-078
provenance_flatten:
  prior_id: "MOD_D"
  flattened_at: "2026-05-10"
  flattened_by: "ADR-060"
---

# Appendix D — Delegation Matrix (AUs + Roles) — Model C

> **Model C (15-facet multi-attribute) per [ADR-078](adr/adr-078-orgpath-attribute-schema-15-facet.md).** Administrative Unit membership rules compose facet predicates from the 15-slot model rather than `-startsWith` on a composite-hyphen path. The facet/slot definitions are in [UIAO_151](UIAO_151_OrgPath_Codebook.md) v4.1 (Hybrid-C+Path, ADR-127); the dynamic group library that supplies admin groups is in [UIAO_152](UIAO_152_Dynamic_Group_Library.md).

## Purpose

This appendix defines the complete delegation model for the OrgTree using Entra ID Administrative Units (AUs) and scoped role assignments. It specifies who can manage what, within which scope, and with which permissions — under the Model C 15-facet schema. Per ADR-078, AU membership rules cite facet values (e.g., `attr2 -eq "IT"`) rather than text-parsing a composite OrgPath string.

In AD, delegation was implicit: OU placement determined who managed an object. In Entra ID, delegation is explicit: Administrative Units define scope via facet-tuple boolean composition, built-in roles define permissions, and role assignments bind them together. This matrix is the canonical source of truth for all administrative delegation.

## Scope

Covers all Administrative Units, their membership rules (per-facet boolean compositions), and all scoped role assignments within the M365 GCC-Moderate boundary. Applies to every administrative action on identity objects governed by the OrgTree.

## Three-Tier Delegation Model

| Tier | Scope | AU Pattern | Typical Roles |
|---|---|---|---|
| Tier 1 — Enterprise | All governed users (populated Department facet) | `AU-Enterprise` | Global Reader, Security Reader, Reports Reader |
| Tier 2 — Department | Users in one Department facet value | `AU-Department-[VALUE]` | User Administrator, Groups Administrator |
| Tier 3 — Division | Users in one (Department + Division) tuple | `AU-[DEPT]-[DIV]` | Helpdesk Administrator, Password Administrator |
| Cross-cutting | Users matching a cross-facet predicate | `AU-[FACETS]` | Authentication Administrator, Conditional Access Administrator |

## Administrative Unit Registry

### Tier 1 — Enterprise AU

| AU Name | Membership Rule | Scope | Restricted |
|---|---|---|---|
| `AU-Enterprise` | `(user.onPremisesExtensionAttributes.extensionAttribute2 -ne "")` | All principals with a populated Department facet (the canonical "is this principal governed?" predicate) | Yes |

### Tier 2 — Department AUs (`extensionAttribute2`)

| AU Name | Membership Rule | Scope | Restricted |
|---|---|---|---|
| `AU-Department-IT` | `(attr2 -eq "IT")` | All IT users | Yes |
| `AU-Department-HR` | `(attr2 -eq "HR")` | All HR users | Yes |
| `AU-Department-Finance` | `(attr2 -eq "Finance")` | All Finance users | Yes |
| `AU-Department-Legal` | `(attr2 -eq "Legal")` | All Legal users | Yes |
| `AU-Department-Engineering` | `(attr2 -eq "Engineering")` | All Engineering users | Yes |
| `AU-Department-Operations` | `(attr2 -eq "Operations")` | All Operations users | Yes |
| `AU-Department-Sales` | `(attr2 -eq "Sales")` | All Sales/Marketing users | Yes |
| `AU-Department-Executive` | `(attr2 -eq "Executive")` | All Executive/Leadership users | Yes |

### Tier 3 — Division AUs (`extensionAttribute2` AND `extensionAttribute3`)

| AU Name | Membership Rule | Scope | Restricted |
|---|---|---|---|
| `AU-IT-CyberOps` | `(attr2 -eq "IT") and (attr3 -eq "CyberOps")` | IT/CyberOps | Yes |
| `AU-IT-InfraOps` | `(attr2 -eq "IT") and (attr3 -eq "InfraOps")` | IT/Infrastructure | Yes |
| `AU-IT-AppDev` | `(attr2 -eq "IT") and (attr3 -eq "AppDev")` | IT/AppDev | Yes |
| `AU-Legal-GRC` | `(attr2 -eq "Legal") and (attr3 -eq "GRC")` | Legal/GRC | Yes |
| `AU-HR-Recruitment` | `(attr2 -eq "HR") and (attr3 -eq "Service")` | HR/Recruitment (Division=Service per starter codebook) | Yes |

### Cross-cutting AUs (multi-facet compositions)

| AU Name | Membership Rule | Scope | Restricted |
|---|---|---|---|
| `AU-Region-NCR-Privileged` | `(attr1 -eq "NCR") and (attr10 -eq "Privileged")` | NCR-region privileged-access accounts | Yes |
| `AU-Cleared-TopSecret-Plus` | `(attr9 -in ["TopSecret","TS_SCI"])` | Top-secret cleared personnel | Yes |
| `AU-Contractor-Active` | `(attr6 -eq "Contractor") and (attr8 -eq "")` | Active contractors (empty TermDate) | Yes |

## Role Assignment Matrix

### Tier 1 — Enterprise-scoped roles

| Role | Assigned To | Scoped To | Purpose |
|---|---|---|---|
| Global Reader | `OrgTree-IT-CyberOps-Users` | `AU-Enterprise` | Security team read-all for monitoring |
| Security Reader | `OrgTree-Legal-GRC-Users` | `AU-Enterprise` | Compliance team audit visibility |
| Reports Reader | `OrgTree-Department-Executive-Users` | `AU-Enterprise` | Executive dashboard access |

### Tier 2 — Department-scoped roles

| Role | Assigned To | Scoped To | Purpose |
|---|---|---|---|
| User Administrator | `OrgTree-Finance-Admins` | `AU-Department-Finance` | Finance user lifecycle |
| Groups Administrator | `OrgTree-Finance-Admins` | `AU-Department-Finance` | Finance group management |
| User Administrator | `OrgTree-HR-Admins` | `AU-Department-HR` | HR user lifecycle |
| Groups Administrator | `OrgTree-HR-Admins` | `AU-Department-HR` | HR group management |
| User Administrator | `OrgTree-IT-Admins` | `AU-Department-IT` | IT user lifecycle |
| Groups Administrator | `OrgTree-IT-Admins` | `AU-Department-IT` | IT group management |
| User Administrator | `OrgTree-Operations-Admins` | `AU-Department-Operations` | Operations user lifecycle |
| User Administrator | `OrgTree-Legal-Admins` | `AU-Department-Legal` | Legal user lifecycle |

### Tier 3 — Division-scoped roles

| Role | Assigned To | Scoped To | Purpose |
|---|---|---|---|
| Helpdesk Administrator | `OrgTree-IT-CyberOps-Admins` | `AU-IT-CyberOps` | CyberOps password resets, basic user support |
| Helpdesk Administrator | `OrgTree-IT-InfraOps-Admins` | `AU-IT-InfraOps` | InfraOps user support |
| Password Administrator | `OrgTree-HR-Recruitment-Admins` | `AU-HR-Recruitment` | Recruitment password resets |
| Helpdesk Administrator | `OrgTree-Legal-GRC-Admins` | `AU-Legal-GRC` | GRC team user support |

### Cross-cutting scoped roles

| Role | Assigned To | Scoped To | Purpose |
|---|---|---|---|
| Authentication Administrator | `OrgTree-IT-InfraOps-Admins` | `AU-Region-NCR-Privileged` | NCR PAM steward — privileged account MFA |
| Conditional Access Administrator | `OrgTree-IT-CyberOps-Admins` | `AU-Cleared-TopSecret-Plus` | Personnel Security Office — cleared CA rules |

## Administrator Groups

Each AU requires a corresponding administrator group. These are NOT dynamic — they are *assigned* groups with governed membership per UIAO_155 Workflow 5.

| Admin Group | Type | Members | Governance |
|---|---|---|---|
| `OrgTree-Finance-Admins` | Assigned | Finance department administrators | UIAO_155 Workflow 5 |
| `OrgTree-HR-Admins` | Assigned | HR department administrators | UIAO_155 Workflow 5 |
| `OrgTree-IT-Admins` | Assigned | IT department administrators | UIAO_155 Workflow 5 |
| `OrgTree-Operations-Admins` | Assigned | Operations department administrators | UIAO_155 Workflow 5 |
| `OrgTree-Legal-Admins` | Assigned | Legal department administrators | UIAO_155 Workflow 5 |
| `OrgTree-IT-CyberOps-Admins` | Assigned | IT/CyberOps division administrators | UIAO_155 Workflow 5 |
| `OrgTree-IT-InfraOps-Admins` | Assigned | IT/InfraOps division administrators | UIAO_155 Workflow 5 |
| `OrgTree-HR-Recruitment-Admins` | Assigned | HR/Recruitment division administrators | UIAO_155 Workflow 5 |
| `OrgTree-Legal-GRC-Admins` | Assigned | Legal/GRC division administrators | UIAO_155 Workflow 5 |

## Restricted Management AUs

All AUs in this matrix are configured as **Restricted Management Administrative Units**. This means:

1. **Global Administrators cannot manage AU members** without an explicit AU-scoped role assignment
2. **Only users with roles scoped to the specific AU** can manage objects within it
3. **This prevents privilege escalation** — a Global Admin cannot bypass facet-scoped delegation without governance approval

## Delegation Decision Tree

```
[Administrative Action Required]
        |
        v
Is the target principal governed by OrgTree?
  (Does attr2 [Department] have a populated value?)
        |                    |
       YES                   NO
        |                    |
        v                    v
  Read the principal's     DENY: Object is
  facet values (attr1..10)  outside governance
        |                    scope
        v
  Determine the AU(s) the principal belongs to
  by evaluating each AU's membership rule against
  the principal's facet values
        |
        v
  Does the actor hold the required role
  in any of those AUs?
        |           |
       YES          NO
        |           |
        v           v
  EXECUTE        Is there a higher-tier
  within scope   AU (e.g., AU-Enterprise)
                 with the role?
                    |         |
                   YES        NO
                    |         |
                    v         v
               EXECUTE    DENY: No valid
               at higher  delegation path
               scope
```

## Drift Detection Rules

Per-clause classification: a multi-facet rule like `(attr2 -eq "IT") and (attr3 -eq "OldDivision")` reports drift on the second clause if `OldDivision` is deprecated in the codebook, while the first clause continues to validate cleanly.

| Drift Type | Detection | Severity | Auto-Remediate |
|---|---|---|---|
| AU Membership Drift | AU membership rule in tenant differs from canonical rule | HIGH | Yes — overwrite rule |
| Clause Drift | A single facet clause in a multi-facet AU rule references a deprecated or unknown facet value | HIGH | No — fix codebook or rule, depending on root cause |
| Role Assignment Drift | A role assignment exists in tenant not in this matrix | CRITICAL | No — investigate (potential privilege escalation) |
| Orphaned AU | AU exists with no role assignments | LOW | No — flag for review |
| Missing AU | Entry in this matrix but no corresponding AU in tenant | HIGH | Yes — create AU |
| Unrestricted AU | AU exists without Restricted Management flag | CRITICAL | Yes — enable restriction |
| Admin Group Drift | Admin group has members not approved through Workflow 5 | HIGH | No — flag for governance review |

## Governance Rules

1. **All AUs are Restricted Management.** Non-restricted AUs are drift. No exceptions.
2. **Role assignments use built-in roles only.** Custom role definitions require governance approval through UIAO_155 Workflow 5.
3. **Admin groups are assigned, not dynamic.** Administrator group membership is a governed decision, not an attribute-driven automation.
4. **No unscoped role assignments.** Every role assignment must be scoped to an AU. Tenant-wide role assignments are governance violations except for designated Governance Stewards.
5. **Department before Division.** Tier 3 (Division) AUs are only created when a Department has more than 50 users AND the Department administrator requests sub-delegation.
6. **Cross-cutting AUs require justification.** AUs whose rule spans facets other than Department + Division (e.g., Clearance × Region) require a documented operational need and governance approval.

## PowerShell Validation

```powershell
# Validate Model C AUs against canonical definitions
$canonicalAUs = @{
    "AU-Enterprise"               = '(user.onPremisesExtensionAttributes.extensionAttribute2 -ne "")'
    "AU-Department-IT"            = '(user.onPremisesExtensionAttributes.extensionAttribute2 -eq "IT")'
    "AU-IT-CyberOps"              = '(user.onPremisesExtensionAttributes.extensionAttribute2 -eq "IT") and (user.onPremisesExtensionAttributes.extensionAttribute3 -eq "CyberOps")'
    "AU-Cleared-TopSecret-Plus"   = '(user.onPremisesExtensionAttributes.extensionAttribute9 -in ["TopSecret","TS_SCI"])'
    # ... extend with full registry
}

$tenantAUs = Get-MgDirectoryAdministrativeUnit -All
foreach ($au in $tenantAUs) {
    if ($au.DisplayName -like "AU-*") {
        $canonical = $canonicalAUs[$au.DisplayName]
        if (-not $canonical) {
            Write-Warning "PHANTOM AU: $($au.DisplayName)"
        } elseif (-not $au.IsMemberManagementRestricted) {
            Write-Warning "UNRESTRICTED: $($au.DisplayName) — must be Restricted Management"
        } elseif ($au.MembershipRule -ne $canonical) {
            Write-Warning "RULE DRIFT: $($au.DisplayName)"
        } else {
            Write-Host "OK: $($au.DisplayName)" -ForegroundColor Green
        }
    }
}

# Check for unscoped role assignments (governance violation)
$unscopedRoles = Get-MgRoleManagementDirectoryRoleAssignment -All |
    Where-Object { -not $_.DirectoryScopeId -or $_.DirectoryScopeId -eq "/" }
if ($unscopedRoles) {
    Write-Warning "GOVERNANCE VIOLATION: $($unscopedRoles.Count) unscoped role assignments found"
}
```

## Change Log

| Version | Date | Change | Author |
|---|---|---|---|
| 1.0 | 2026-04-18 | Initial DRAFT scaffold | Copilot Tasks |
| 2.0 | 2026-04-19 | Promoted to CANONICAL — Model A AU rules using `-startsWith "ORG-FIN"`, division/department tiers | Copilot Tasks |
| **3.0** | **2026-05-24** | **Full Model C rewrite per [ADR-078](adr/adr-078-orgpath-attribute-schema-15-facet.md).** AU registry rewritten with facet-tuple boolean compositions; Tier 2/3 renamed to Department/Division to align with facet semantics; cross-cutting AU category added (multi-facet predicates beyond Department + Division); role-assignment matrix updated; Clause Drift added to drift category set; PowerShell validation updated for `onPremisesExtensionAttributes.extensionAttribute*` references. | Governance Steward |
