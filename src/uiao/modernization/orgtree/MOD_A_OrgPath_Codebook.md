---
document_id: MOD_A
title: "Appendix A — OrgPath Codebook"
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

# Appendix A — OrgPath Codebook

## Purpose

This appendix defines the complete enumeration of OrgPath codes used to encode organizational hierarchy in Entra ID extension attributes. Every valid OrgPath in the system must exist in this codebook. An OrgPath that does not appear here is, by definition, invalid and will be flagged as drift.

The OrgPath is the single most foundational artifact in the OrgTree suite. Every other MOD document depends on it: dynamic groups (MOD_B) key off OrgPath values, Administrative Units (MOD_D) scope to OrgPath segments, drift detection (MOD_M) validates against this codebook, and the delegation matrix maps to OrgPath hierarchy.

## Scope

Covers all hierarchical levels (0 through 4) of the OrgTree. Applies to every user object, every dynamic group membership rule, and every Administrative Unit scope within the M365 GCC-Moderate boundary. The codebook is the single source of truth for organizational structure encoding.

## Canonical OrgPath Format

**Format:** `ORG-[DIV]-[DEPT]-[UNIT]-[TEAM]` (or fewer segments for higher levels)

Design rationale:

- Starts with a fixed root (`ORG`) for easy regex validation and subtree matching
- Uses uppercase alphanumeric segments (2-6 characters) separated by hyphens — machine-friendly, sortable, and human-readable
- Supports both exact node (`-eq`) and branch/subtree (`-startsWith`) queries in dynamic group rules
- Maximum depth: 4 segments after root (Level 4 = Team) — prevents excessive fragmentation while allowing meaningful hierarchy
- Stored in: `extensionAttribute1` (synced from AD or populated by HR provisioning) — this is the single source of truth

**Regex Validation Pattern:** `^ORG(-[A-Z0-9]{2,6}){0,4}$`

### Alternative Format (Readability-First)

If stakeholder communication is a priority over strict machine validation:

`CORP/[REGION]/[DIVISION]/[LOCATION]/[DEPARTMENT]` (e.g., `CORP/US/EAST/BALTIMORE/IT`)

This works equally well with `-startsWith` but is slightly less strict for validation. The canonical recommendation is the `ORG-` format for governance and automation; the `/` format for documentation and executive communication.

## Level Structure

| Level | Segment Count | Example OrgPath | Description | Typical Dynamic Group Rule |
|-------|---------------|-----------------|-------------|---------------------------|
| 0 | 1 | `ORG` | Enterprise Root | All users (rarely used directly) |
| 1 | 2 | `ORG-FIN` | Top-level Division / Agency | `-eq "ORG-FIN"` or `-startsWith "ORG-FIN"` |
| 2 | 3 | `ORG-FIN-AP` | Department within Division | `-startsWith "ORG-FIN-AP"` |
| 3 | 4 | `ORG-FIN-AP-EAST` | Unit / Location / Sub-function | `-startsWith "ORG-FIN-AP-EAST"` |
| 4 | 5 | `ORG-FIN-AP-EAST-T1` | Team / Specific group | `-eq "ORG-FIN-AP-EAST-T1"` |

## Sample Codebook

This is a realistic starter codebook based on common enterprise and government structures. Customize segments to match your actual organization.

### Level 1 — Divisions

| OrgPath | Description |
|---------|-------------|
| `ORG-EXEC` | Executive / Leadership |
| `ORG-FIN` | Finance |
| `ORG-HR` | Human Resources |
| `ORG-IT` | Information Technology |
| `ORG-OPS` | Operations |
| `ORG-LEG` | Legal / Compliance |
| `ORG-SALES` | Sales & Marketing |

### Level 2 — Departments

| OrgPath | Description | Parent |
|---------|-------------|--------|
| `ORG-FIN-AP` | Accounts Payable | ORG-FIN |
| `ORG-FIN-AR` | Accounts Receivable | ORG-FIN |
| `ORG-FIN-BUD` | Budget & Forecasting | ORG-FIN |
| `ORG-IT-SEC` | Security | ORG-IT |
| `ORG-IT-INF` | Infrastructure | ORG-IT |
| `ORG-IT-DEV` | Development / Engineering | ORG-IT |
| `ORG-HR-REC` | Recruitment | ORG-HR |
| `ORG-HR-BEN` | Benefits | ORG-HR |
| `ORG-OPS-LOG` | Logistics | ORG-OPS |
| `ORG-LEG-COM` | Compliance | ORG-LEG |

### Level 3 — Units

| OrgPath | Description | Parent |
|---------|-------------|--------|
| `ORG-IT-SEC-SOC` | Security Operations Center | ORG-IT-SEC |
| `ORG-IT-SEC-IAM` | Identity & Access Management | ORG-IT-SEC |
| `ORG-IT-INF-NET` | Networking | ORG-IT-INF |
| `ORG-FIN-AP-EAST` | Accounts Payable East Region | ORG-FIN-AP |
| `ORG-FIN-AP-WEST` | Accounts Payable West Region | ORG-FIN-AP |

### Level 4 — Teams

| OrgPath | Description | Parent |
|---------|-------------|--------|
| `ORG-IT-SEC-SOC-T1` | SOC Tier 1 Analysts | ORG-IT-SEC-SOC |
| `ORG-IT-SEC-SOC-T2` | SOC Tier 2 Engineers | ORG-IT-SEC-SOC |
| `ORG-IT-DEV-APP1` | Application Team 1 | ORG-IT-DEV |

## Dynamic Group Rules

Every OrgPath level supports Entra ID dynamic membership rules. The key design decision: use `-startsWith` for branch/subtree groups and `-eq` for leaf-node groups.

### Branch Groups (Subtree Membership)

| Group Name | Rule | Captures |
|------------|------|----------|
| `SG-FIN-All` | `(user.extensionAttribute1 -startsWith "ORG-FIN")` | All Finance users across all departments, units, and teams |
| `SG-IT-SEC-All` | `(user.extensionAttribute1 -startsWith "ORG-IT-SEC")` | All Security users including SOC, IAM, and all sub-teams |
| `SG-FIN-AP-All` | `(user.extensionAttribute1 -startsWith "ORG-FIN-AP")` | All Accounts Payable users across all regions |

### Node Groups (Exact Membership)

| Group Name | Rule | Captures |
|------------|------|----------|
| `SG-IT-SEC-SOC-T1` | `(user.extensionAttribute1 -eq "ORG-IT-SEC-SOC-T1")` | Only SOC Tier 1 Analysts |
| `SG-EXEC` | `(user.extensionAttribute1 -eq "ORG-EXEC")` | Only Executive / Leadership |

### Compound Rules

| Group Name | Rule | Use Case |
|------------|------|----------|
| `SG-IT-Privileged` | `(user.extensionAttribute1 -startsWith "ORG-IT-SEC") -or (user.extensionAttribute1 -startsWith "ORG-IT-INF")` | Security + Infrastructure (elevated access) |
| `SG-FIN-Regional` | `(user.extensionAttribute1 -startsWith "ORG-FIN-AP-EAST") -or (user.extensionAttribute1 -startsWith "ORG-FIN-AP-WEST")` | All regional AP staff |

## Administrative Unit Mapping

Administrative Units mirror the OrgPath hierarchy for scoped delegation. Each AU uses dynamic membership rules keyed to the same OrgPath segments.

| Administrative Unit | Membership Rule | Scoped Role | Delegate |
|--------------------|-----------------|-------------|----------|
| `AU-IT` | `extensionAttribute1 -startsWith "ORG-IT"` | User Administrator | IT Division Lead |
| `AU-IT-SEC` | `extensionAttribute1 -startsWith "ORG-IT-SEC"` | User Administrator | CISO / Security Lead |
| `AU-FIN` | `extensionAttribute1 -startsWith "ORG-FIN"` | User Administrator | CFO / Finance Lead |
| `AU-HR` | `extensionAttribute1 -startsWith "ORG-HR"` | User Administrator | CHRO / HR Lead |

## Boundary Rules

1. All OrgPath codes must match the regex `^ORG(-[A-Z0-9]{2,6}){0,4}$`
2. Maximum hierarchy depth is 4 segments below root (Level 4)
3. Each segment must be between 2 and 6 uppercase ASCII letters or digits
4. OrgPath values are stored in `extensionAttribute1` within Entra ID, which is within the M365 GCC-Moderate boundary
5. No OrgPath may reference external systems or identifiers outside the M365 SaaS perimeter
6. HR system is the authoritative source — IT never manually edits OrgPath values

## Drift Detection Rules

The drift detection engine (MOD_M) validates every user's OrgPath against this codebook. Five drift categories apply:

| Category | Definition | Severity | Auto-Remediate | Example |
|----------|-----------|----------|----------------|---------|
| Value Drift | User's `extensionAttribute1` contains a value not in this codebook | High | No — requires investigation | User has `ORG-FIN-TAX` but no such code exists |
| Format Drift | User's OrgPath does not match the regex | Critical | No — requires manual correction | User has `org-fin-ap` (lowercase) |
| Hierarchy Drift | An OrgPath code exists but its parent path does not | Critical | No — codebook integrity issue | `ORG-FIN-AP-EAST` exists but `ORG-FIN-AP` was removed |
| Orphan Drift | An OrgPath code exists in the codebook but has zero matching users | Medium | Flag for review | `ORG-SALES` defined but no users assigned |
| Phantom Drift | A user has an OrgPath that was deprecated in the codebook | Medium | Yes — flag for reassignment | User has `ORG-MKT` which was renamed to `ORG-SALES` |

## PowerShell Validation

Basic validation script using Microsoft Graph PowerShell:

```powershell
# Prerequisites: Connect-MgGraph -Scopes "User.Read.All", "Group.Read.All"

$users = Get-MgUser -All -Property Id, OnPremisesExtensionAttributes, DisplayName
$regex = '^ORG(-[A-Z0-9]{2,6}){0,4}$'

# Format drift — OrgPath does not match regex
$formatDrift = $users | Where-Object {
    $path = $_.OnPremisesExtensionAttributes.ExtensionAttribute1
    $path -and $path -notmatch $regex
}

# Value drift — OrgPath not in codebook (load codebook from YAML or hardcoded list)
$codebook = @(
    'ORG', 'ORG-EXEC', 'ORG-FIN', 'ORG-HR', 'ORG-IT', 'ORG-OPS', 'ORG-LEG', 'ORG-SALES',
    'ORG-FIN-AP', 'ORG-FIN-AR', 'ORG-FIN-BUD', 'ORG-IT-SEC', 'ORG-IT-INF', 'ORG-IT-DEV',
    'ORG-HR-REC', 'ORG-HR-BEN', 'ORG-OPS-LOG', 'ORG-LEG-COM',
    'ORG-IT-SEC-SOC', 'ORG-IT-SEC-IAM', 'ORG-IT-INF-NET', 'ORG-FIN-AP-EAST', 'ORG-FIN-AP-WEST',
    'ORG-IT-SEC-SOC-T1', 'ORG-IT-SEC-SOC-T2', 'ORG-IT-DEV-APP1'
)

$valueDrift = $users | Where-Object {
    $path = $_.OnPremisesExtensionAttributes.ExtensionAttribute1
    $path -and $path -match $regex -and $path -notin $codebook
}

# Report
Write-Host "=== FORMAT DRIFT ===" -ForegroundColor Red
$formatDrift | Select DisplayName, @{N='OrgPath'; E={$_.OnPremisesExtensionAttributes.ExtensionAttribute1}}

Write-Host "=== VALUE DRIFT ===" -ForegroundColor Yellow
$valueDrift | Select DisplayName, @{N='OrgPath'; E={$_.OnPremisesExtensionAttributes.ExtensionAttribute1}}

Write-Host "Format Drift: $($formatDrift.Count) users" -ForegroundColor Red
Write-Host "Value Drift: $($valueDrift.Count) users" -ForegroundColor Yellow
```

## Implementation Steps

1. **Finalize the codebook** — Export your current AD OU structure, normalize it into the `ORG-` format, and get HR/stakeholder sign-off on codes. Every code in the codebook must have an owner.

2. **Populate the attribute** — Use Entra provisioning or a sync job (Entra Connect, or direct HR-to-Entra provisioning) to write OrgPath to `extensionAttribute1`. HR is the authoritative source — IT never manually edits this value.

3. **Create dynamic groups** — Start with Level 1-2 branch groups (all of Finance, all of IT). Add node-level groups as Conditional Access and delegation requirements emerge.

4. **Create Administrative Units** — Mirror the dynamic group structure. Start with division-level AUs, add department-level AUs for teams with dedicated delegation needs.

5. **Validate** — Run the PowerShell validation script above to detect format drift and value drift. Resolve all critical issues before enabling governance automation.

6. **Enable drift detection** — Connect this codebook to the drift detection engine (MOD_M) for continuous monitoring.

## Governance Alignment

This codebook implements Principle 2 (Schema Fixity): the codebook structure is fixed; only values (specific OrgPath entries) change through the OrgPath Registration workflow (Appendix E, Workflow 1). Every addition, deprecation, or modification to this codebook requires a governed PR through the contributor workflow (Appendix V), passing all validation gates (Appendix J, Schema Tests), and receiving approval from the Governance Board.

## Change Log

| Version | Date | Change | Author |
|---------|------|--------|--------|
| 1.0 | 2026-04-18 | Initial scaffold — structure, regex, drift rules | Copilot Tasks |
| 2.0 | 2026-04-19 | Promoted to CANONICAL — added sample entries, dynamic group rules, AU mapping, PowerShell validation, implementation steps | Copilot Tasks |
