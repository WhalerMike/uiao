---
document_id: MOD_D
title: "Appendix D — Delegation Matrix (AUs + Roles)"
version: "2.0"
status: CANONICAL
owner: Michael Stratton
author: Michal Doroszewski
created_at: 2026-04-18
updated_at: 2026-04-19
boundary: GCC-Moderate
namespace: MOD
parent_canon: UIAO_008
provenance:
  prior_version: "1.0 (DRAFT scaffold)"
  promoted_by: "Copilot Tasks"
  promotion_date: "2026-04-19"
---

# Appendix D — Delegation Matrix (AUs + Roles)

## Purpose

This appendix defines the complete delegation model for the OrgTree using Entra ID Administrative Units (AUs) and scoped role assignments. It specifies who can manage what, within which scope, and with which permissions. This is the governance replacement for Active Directory's OU-level delegation.

In AD, delegation was implicit: OU placement determined who managed an object. In Entra ID, delegation is explicit: Administrative Units define scope, built-in roles define permissions, and role assignments bind them together. This matrix is the canonical source of truth for all administrative delegation.

## Scope

Covers all Administrative Units, their membership rules, and all scoped role assignments within the M365 GCC-Moderate boundary. Applies to every administrative action on identity objects governed by the OrgTree.

## Three-Tier Delegation Model

| Tier | Scope | AU Pattern | Typical Roles |
|------|-------|-----------|---------------|
| Tier 1 — Enterprise | All governed users | `AU-ORG-Enterprise` | Global Reader, Security Reader |
| Tier 2 — Division | All users in one division | `AU-ORG-[DIV]` | User Administrator, Groups Administrator |
| Tier 3 — Department | Users in one department | `AU-ORG-[DIV]-[DEPT]` | Helpdesk Administrator, Password Administrator |

## Administrative Unit Registry

### Tier 1 — Enterprise AUs

| AU Name | Membership Rule | Scope | Restricted |
|---------|----------------|-------|-----------|
| `AU-ORG-Enterprise` | `(user.extensionAttribute1 -startsWith "ORG")` | All governed users | Yes |

### Tier 2 — Division AUs

| AU Name | Membership Rule | Scope | Restricted |
|---------|----------------|-------|-----------|
| `AU-ORG-FIN` | `(user.extensionAttribute1 -startsWith "ORG-FIN")` | All Finance users | Yes |
| `AU-ORG-HR` | `(user.extensionAttribute1 -startsWith "ORG-HR")` | All Human Resources users | Yes |
| `AU-ORG-IT` | `(user.extensionAttribute1 -startsWith "ORG-IT")` | All IT users | Yes |
| `AU-ORG-OPS` | `(user.extensionAttribute1 -startsWith "ORG-OPS")` | All Operations users | Yes |
| `AU-ORG-LEG` | `(user.extensionAttribute1 -startsWith "ORG-LEG")` | All Legal users | Yes |
| `AU-ORG-EXEC` | `(user.extensionAttribute1 -startsWith "ORG-EXEC")` | All Executive users | Yes |

### Tier 3 — Department AUs (Examples)

| AU Name | Membership Rule | Scope | Restricted |
|---------|----------------|-------|-----------|
| `AU-ORG-IT-SEC` | `(user.extensionAttribute1 -startsWith "ORG-IT-SEC")` | IT Security | Yes |
| `AU-ORG-IT-INF` | `(user.extensionAttribute1 -startsWith "ORG-IT-INF")` | IT Infrastructure | Yes |
| `AU-ORG-IT-DEV` | `(user.extensionAttribute1 -startsWith "ORG-IT-DEV")` | IT Development | Yes |
| `AU-ORG-FIN-AP` | `(user.extensionAttribute1 -startsWith "ORG-FIN-AP")` | Accounts Payable | Yes |
| `AU-ORG-FIN-BUD` | `(user.extensionAttribute1 -startsWith "ORG-FIN-BUD")` | Budget | Yes |
| `AU-ORG-HR-REC` | `(user.extensionAttribute1 -startsWith "ORG-HR-REC")` | Recruitment | Yes |
| `AU-ORG-HR-BEN` | `(user.extensionAttribute1 -startsWith "ORG-HR-BEN")` | Benefits | Yes |

## Role Assignment Matrix

### Tier 1 — Enterprise-Scoped Roles

| Role | Assigned To | Scoped To | Purpose |
|------|-----------|----------|---------|
| Global Reader | `OrgTree-IT-SEC-Users` | `AU-ORG-Enterprise` | Security team read-all for monitoring |
| Security Reader | `OrgTree-LEG-COM-Users` | `AU-ORG-Enterprise` | Compliance team audit visibility |
| Reports Reader | `OrgTree-EXEC-Users` | `AU-ORG-Enterprise` | Executive dashboard access |

### Tier 2 — Division-Scoped Roles

| Role | Assigned To | Scoped To | Purpose |
|------|-----------|----------|---------|
| User Administrator | `OrgTree-FIN-Admins` | `AU-ORG-FIN` | Finance division user lifecycle |
| Groups Administrator | `OrgTree-FIN-Admins` | `AU-ORG-FIN` | Finance division group management |
| User Administrator | `OrgTree-HR-Admins` | `AU-ORG-HR` | HR division user lifecycle |
| Groups Administrator | `OrgTree-HR-Admins` | `AU-ORG-HR` | HR division group management |
| User Administrator | `OrgTree-IT-Admins` | `AU-ORG-IT` | IT division user lifecycle |
| Groups Administrator | `OrgTree-IT-Admins` | `AU-ORG-IT` | IT division group management |
| User Administrator | `OrgTree-OPS-Admins` | `AU-ORG-OPS` | Operations user lifecycle |
| User Administrator | `OrgTree-LEG-Admins` | `AU-ORG-LEG` | Legal user lifecycle |

### Tier 3 — Department-Scoped Roles

| Role | Assigned To | Scoped To | Purpose |
|------|-----------|----------|---------|
| Helpdesk Administrator | `OrgTree-IT-SEC-Admins` | `AU-ORG-IT-SEC` | Security dept password resets, basic user support |
| Helpdesk Administrator | `OrgTree-FIN-AP-Admins` | `AU-ORG-FIN-AP` | AP department user support |
| Password Administrator | `OrgTree-HR-REC-Admins` | `AU-ORG-HR-REC` | Recruitment password resets |
| Authentication Administrator | `OrgTree-IT-SEC-IAM-Users` | `AU-ORG-Enterprise` | IAM team MFA management (enterprise-wide) |

## Administrator Groups

Each AU requires a corresponding administrator group. These are NOT dynamic — they are assigned groups with governed membership.

| Admin Group | Type | Members | Governance |
|------------|------|---------|-----------|
| `OrgTree-FIN-Admins` | Assigned | Finance division administrators | MOD_E Workflow 5 |
| `OrgTree-HR-Admins` | Assigned | HR division administrators | MOD_E Workflow 5 |
| `OrgTree-IT-Admins` | Assigned | IT division administrators | MOD_E Workflow 5 |
| `OrgTree-OPS-Admins` | Assigned | Operations division administrators | MOD_E Workflow 5 |
| `OrgTree-LEG-Admins` | Assigned | Legal division administrators | MOD_E Workflow 5 |
| `OrgTree-IT-SEC-Admins` | Assigned | IT Security department administrators | MOD_E Workflow 5 |
| `OrgTree-FIN-AP-Admins` | Assigned | AP department administrators | MOD_E Workflow 5 |
| `OrgTree-HR-REC-Admins` | Assigned | Recruitment department administrators | MOD_E Workflow 5 |

## Restricted Management AUs

All AUs in this matrix are configured as **Restricted Management Administrative Units**. This means:

1. **Global Administrators cannot manage AU members** without an explicit AU-scoped role assignment
2. **Only users with roles scoped to the specific AU** can manage objects within it
3. **This prevents privilege escalation** — a Global Admin cannot bypass division-level delegation without governance approval

## Delegation Decision Tree

```
[Administrative Action Required]
        |
        v
Is the target user governed by OrgTree?
        |                    |
       YES                   NO
        |                    |
        v                    v
  Read target user's     DENY: Object is
  extensionAttribute1    outside governance
        |                scope
        v
  Map OrgPath to AU
  (Level 1 = Division AU,
   Level 2 = Department AU)
        |
        v
  Does the actor hold the
  required role in that AU?
        |           |
       YES          NO
        |           |
        v           v
  EXECUTE        Is there a higher-tier
  within scope   AU with the role?
                    |         |
                   YES        NO
                    |         |
                    v         v
               EXECUTE    DENY: No valid
               at higher  delegation path
               scope
```

## Drift Detection Rules

| Drift Type | Detection | Severity | Auto-Remediate |
|-----------|-----------|----------|----------------|
| AU Membership Drift | AU membership rule in tenant differs from canonical rule | HIGH | Yes — overwrite rule |
| Role Assignment Drift | A role assignment exists in tenant not in this matrix | CRITICAL | No — investigate (potential privilege escalation) |
| Orphaned AU | AU exists with no role assignments | LOW | No — flag for review |
| Missing AU | Entry in this matrix but no corresponding AU in tenant | HIGH | Yes — create AU |
| Unrestricted AU | AU exists without Restricted Management flag | CRITICAL | Yes — enable restriction |
| Admin Group Drift | Admin group has members not approved through Workflow 5 | HIGH | No — flag for governance review |

## Governance Rules

1. **All AUs are Restricted Management.** Non-restricted AUs are drift. No exceptions.
2. **Role assignments use built-in roles only.** Custom role definitions require governance approval through MOD_E Workflow 5.
3. **Admin groups are assigned, not dynamic.** Administrator group membership is a governed decision, not an attribute-driven automation.
4. **No unscoped role assignments.** Every role assignment must be scoped to an AU. Tenant-wide role assignments are governance violations except for designated Governance Stewards.
5. **Division before department.** Tier 3 (department) AUs are only created when a division has more than 50 users AND the division administrator requests sub-delegation.

## PowerShell Validation

```powershell
# Validate all AUs match canonical definitions
$canonicalAUs = @{
    "AU-ORG-Enterprise" = '(user.extensionAttribute1 -startsWith "ORG")'
    "AU-ORG-FIN"        = '(user.extensionAttribute1 -startsWith "ORG-FIN")'
    "AU-ORG-HR"         = '(user.extensionAttribute1 -startsWith "ORG-HR")'
    "AU-ORG-IT"         = '(user.extensionAttribute1 -startsWith "ORG-IT")'
    # ... extend with full registry
}

$tenantAUs = Get-MgDirectoryAdministrativeUnit -All
foreach ($au in $tenantAUs) {
    if ($au.DisplayName -like "AU-ORG-*") {
        $canonical = $canonicalAUs[$au.DisplayName]
        if (-not $canonical) {
            Write-Warning "PHANTOM AU: $($au.DisplayName)"
        } elseif (-not $au.IsMemberManagementRestricted) {
            Write-Warning "UNRESTRICTED: $($au.DisplayName) — must be Restricted Management"
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