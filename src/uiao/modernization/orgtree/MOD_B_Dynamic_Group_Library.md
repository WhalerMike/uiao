---
document_id: MOD_B
title: "Appendix B — Dynamic Group Library"
version: "2.0"
status: CANONICAL
classification: Controlled
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

# Appendix B — Dynamic Group Library

## Purpose

This appendix defines all dynamic group definitions that implement the OrgTree structure in Entra ID. Every OrgPath-scoped group in the tenant must conform to a definition in this library. Groups not listed here are non-canonical and will be flagged as Phantom Drift by the drift detection engine (MOD_M).

The Dynamic Group Library is the operational bridge between the OrgPath Codebook (MOD_A) and every downstream governance artifact: Conditional Access policies target these groups, Administrative Units (MOD_D) scope delegation through them, licensing assignments flow through them, and the drift engine validates them.

## Scope

Covers all dynamic security groups and Microsoft 365 groups whose membership is derived from OrgPath values stored in `extensionAttribute1`. Applies to all group-based access control, delegation, licensing, and policy targeting within the M365 GCC-Moderate boundary.

## Naming Convention

All OrgTree-governed dynamic groups follow a deterministic naming pattern:

```
OrgTree-[SCOPE]-[PURPOSE]
```

| Component | Rule | Example |
|-----------|------|---------|
| Prefix | Always `OrgTree-` | `OrgTree-` |
| Scope | OrgPath segment (without `ORG-` prefix) | `FIN`, `FIN-AP`, `IT-SEC-SOC` |
| Purpose | Group function suffix | `-Users`, `-Admins`, `-Licensed`, `-CA` |

Examples:
- `OrgTree-FIN-Users` — All users in the Finance division
- `OrgTree-IT-SEC-SOC-Users` — All SOC analysts
- `OrgTree-HR-Licensed` — HR users targeted for specific license SKUs
- `OrgTree-EXEC-CA` — Executive users targeted by Conditional Access policies

## Three Query Patterns

Dynamic group membership rules use three patterns against `extensionAttribute1`:

### Pattern 1: Branch Query (Subtree)

Captures all users at and below a hierarchy level. Use `-startsWith` operator.

```
(user.extensionAttribute1 -startsWith "ORG-FIN")
```

This matches: `ORG-FIN`, `ORG-FIN-AP`, `ORG-FIN-AP-EAST`, `ORG-FIN-AP-EAST-T1`

**Use cases:** Division-wide policies, broad licensing, Conditional Access targeting

### Pattern 2: Node Query (Exact)

Captures only users at a specific hierarchy level. Use `-eq` operator.

```
(user.extensionAttribute1 -eq "ORG-IT-SEC-SOC-T1")
```

This matches only: `ORG-IT-SEC-SOC-T1`

**Use cases:** Team-specific access, granular delegation, application assignment

### Pattern 3: Compound Query (Multi-Branch)

Combines multiple OrgPath conditions. Use `-or` operator.

```
(user.extensionAttribute1 -startsWith "ORG-IT-SEC") -or (user.extensionAttribute1 -startsWith "ORG-LEG-COM")
```

**Use cases:** Cross-divisional projects, shared compliance groups, joint access policies

## Canonical Group Definitions

### Level 1 — Division Groups (Branch Queries)

| Group Name | Membership Rule | Members |
|-----------|----------------|---------|
| `OrgTree-FIN-Users` | `(user.extensionAttribute1 -startsWith "ORG-FIN")` | All Finance division users |
| `OrgTree-HR-Users` | `(user.extensionAttribute1 -startsWith "ORG-HR")` | All Human Resources users |
| `OrgTree-IT-Users` | `(user.extensionAttribute1 -startsWith "ORG-IT")` | All IT users |
| `OrgTree-OPS-Users` | `(user.extensionAttribute1 -startsWith "ORG-OPS")` | All Operations users |
| `OrgTree-LEG-Users` | `(user.extensionAttribute1 -startsWith "ORG-LEG")` | All Legal/Compliance users |
| `OrgTree-EXEC-Users` | `(user.extensionAttribute1 -startsWith "ORG-EXEC")` | All Executive/Leadership users |

### Level 2 — Department Groups (Branch Queries)

| Group Name | Membership Rule | Members |
|-----------|----------------|---------|
| `OrgTree-FIN-AP-Users` | `(user.extensionAttribute1 -startsWith "ORG-FIN-AP")` | Accounts Payable |
| `OrgTree-FIN-AR-Users` | `(user.extensionAttribute1 -startsWith "ORG-FIN-AR")` | Accounts Receivable |
| `OrgTree-FIN-BUD-Users` | `(user.extensionAttribute1 -startsWith "ORG-FIN-BUD")` | Budget & Forecasting |
| `OrgTree-IT-SEC-Users` | `(user.extensionAttribute1 -startsWith "ORG-IT-SEC")` | Security |
| `OrgTree-IT-INF-Users` | `(user.extensionAttribute1 -startsWith "ORG-IT-INF")` | Infrastructure |
| `OrgTree-IT-DEV-Users` | `(user.extensionAttribute1 -startsWith "ORG-IT-DEV")` | Development/Engineering |
| `OrgTree-HR-REC-Users` | `(user.extensionAttribute1 -startsWith "ORG-HR-REC")` | Recruitment |
| `OrgTree-HR-BEN-Users` | `(user.extensionAttribute1 -startsWith "ORG-HR-BEN")` | Benefits |
| `OrgTree-OPS-LOG-Users` | `(user.extensionAttribute1 -startsWith "ORG-OPS-LOG")` | Logistics |
| `OrgTree-LEG-COM-Users` | `(user.extensionAttribute1 -startsWith "ORG-LEG-COM")` | Compliance |

### Level 3 — Unit Groups (Branch or Node Queries)

| Group Name | Membership Rule | Members |
|-----------|----------------|---------|
| `OrgTree-IT-SEC-SOC-Users` | `(user.extensionAttribute1 -startsWith "ORG-IT-SEC-SOC")` | SOC (all tiers) |
| `OrgTree-IT-SEC-IAM-Users` | `(user.extensionAttribute1 -startsWith "ORG-IT-SEC-IAM")` | Identity & Access Management |
| `OrgTree-IT-INF-NET-Users` | `(user.extensionAttribute1 -startsWith "ORG-IT-INF-NET")` | Networking |
| `OrgTree-FIN-AP-EAST-Users` | `(user.extensionAttribute1 -eq "ORG-FIN-AP-EAST")` | AP East Region |
| `OrgTree-FIN-AP-WEST-Users` | `(user.extensionAttribute1 -eq "ORG-FIN-AP-WEST")` | AP West Region |

### Level 4 — Team Groups (Node Queries)

| Group Name | Membership Rule | Members |
|-----------|----------------|---------|
| `OrgTree-IT-SEC-SOC-T1-Users` | `(user.extensionAttribute1 -eq "ORG-IT-SEC-SOC-T1")` | SOC Tier 1 Analysts |
| `OrgTree-IT-SEC-SOC-T2-Users` | `(user.extensionAttribute1 -eq "ORG-IT-SEC-SOC-T2")` | SOC Tier 2 Engineers |
| `OrgTree-IT-DEV-APP1-Users` | `(user.extensionAttribute1 -eq "ORG-IT-DEV-APP1")` | Application Team 1 |

### Cross-Functional Groups (Compound Queries)

| Group Name | Membership Rule | Purpose |
|-----------|----------------|---------|
| `OrgTree-SecurityCompliance-Users` | `(user.extensionAttribute1 -startsWith "ORG-IT-SEC") -or (user.extensionAttribute1 -startsWith "ORG-LEG-COM")` | Joint Security + Compliance visibility |
| `OrgTree-AllRegionalAP-Users` | `(user.extensionAttribute1 -startsWith "ORG-FIN-AP-EAST") -or (user.extensionAttribute1 -startsWith "ORG-FIN-AP-WEST")` | All regional AP teams |

### Conditional Access Groups

| Group Name | Membership Rule | CA Policy Target |
|-----------|----------------|-----------------|
| `OrgTree-EXEC-CA` | `(user.extensionAttribute1 -startsWith "ORG-EXEC")` | Executive MFA enforcement, device compliance |
| `OrgTree-IT-SEC-CA` | `(user.extensionAttribute1 -startsWith "ORG-IT-SEC")` | Security team — privileged access policies |
| `OrgTree-AllUsers-CA` | `(user.extensionAttribute1 -startsWith "ORG")` | Baseline CA policies for all governed users |

### Licensing Groups

| Group Name | Membership Rule | License SKU |
|-----------|----------------|-------------|
| `OrgTree-EXEC-Licensed` | `(user.extensionAttribute1 -startsWith "ORG-EXEC")` | E5 + Copilot |
| `OrgTree-IT-Licensed` | `(user.extensionAttribute1 -startsWith "ORG-IT")` | E5 |
| `OrgTree-Standard-Licensed` | `(user.extensionAttribute1 -startsWith "ORG") -and (user.extensionAttribute1 -notMatch "ORG-EXEC.*|ORG-IT.*")` | E3 |

## Drift Detection Rules

| Drift Type | Detection | Severity | Auto-Remediate |
|-----------|-----------|----------|----------------|
| Rule Drift | Tenant group rule differs from canonical rule in this library | HIGH | Yes — overwrite from canonical source |
| Phantom Group | Group with `OrgTree-` prefix exists in tenant but has no entry in this library | MEDIUM | No — investigate, then delete or canonize |
| Missing Group | Entry exists in this library but no corresponding group in tenant | HIGH | Yes — create group from canonical definition |
| Name Drift | Group exists with correct rule but wrong name | LOW | Yes — rename to canonical name |
| Membership Drift | Group membership does not match expected user count | MEDIUM | Root cause is OrgPath values (MOD_A), not group rules |

## Governance Rules

1. **No manual members.** If a group appears in this library, it is dynamic-only. Manually assigned members are drift by definition.
2. **One canonical rule per group.** Each group has exactly one membership rule. Multiple rules for the same scope require separate groups.
3. **Naming is deterministic.** The group name is derived from the OrgPath scope and purpose. Renaming a group without updating this library is drift.
4. **Changes require governed workflow.** Adding, modifying, or removing a group definition follows Workflow 3 (Dynamic Group Creation/Modification) in Appendix E and requires validation per Appendix J Group Tests.
5. **OrgPath dependency.** Every membership rule references `extensionAttribute1` values defined in MOD_A. If an OrgPath value is removed from the codebook, all groups referencing it must be updated or retired.

## PowerShell Validation

```powershell
# Validate all OrgTree dynamic groups match canonical definitions
$canonicalGroups = @{
    "OrgTree-FIN-Users" = '(user.extensionAttribute1 -startsWith "ORG-FIN")'
    "OrgTree-HR-Users"  = '(user.extensionAttribute1 -startsWith "ORG-HR")'
    "OrgTree-IT-Users"  = '(user.extensionAttribute1 -startsWith "ORG-IT")'
    # ... extend with full library
}

$tenantGroups = Get-MgGroup -Filter "startsWith(displayName,'OrgTree-')" -All
foreach ($g in $tenantGroups) {
    $canonical = $canonicalGroups[$g.DisplayName]
    if (-not $canonical) {
        Write-Warning "PHANTOM: $($g.DisplayName) — not in canonical library"
    } elseif ($g.MembershipRule -ne $canonical) {
        Write-Warning "RULE DRIFT: $($g.DisplayName)"
        Write-Warning "  Tenant:    $($g.MembershipRule)"
        Write-Warning "  Canonical: $canonical"
    } else {
        Write-Host "OK: $($g.DisplayName)" -ForegroundColor Green
    }
}
```