---
document_id: UIAO_152
title: "Appendix B — Dynamic Group Library (Model C)"
version: "3.0"
status: Current
owner: Michael Stratton
author: Michal Doroszewski
created_at: "2026-04-18"
updated_at: "2026-05-24"
boundary: GCC-Moderate
classification: CANONICAL
promotion:
  prior_version: "2.0 (Model A composite-hyphen, -startsWith / -eq patterns)"
  promoted_by: "Governance Steward"
  promotion_date: "2026-05-24"
  promotion_adr: ADR-078
provenance_flatten:
  prior_id: "MOD_B"
  flattened_at: "2026-05-10"
  flattened_by: "ADR-060"
---

# Appendix B — Dynamic Group Library (Model C)

> **Model C (15-facet multi-attribute) per [ADR-078](adr/adr-078-orgpath-attribute-schema-15-facet.md).** Membership rules compose facet predicates from the 15-slot model rather than `-startsWith` / `-eq` on a composite-hyphen path. The facet/slot definitions are in [UIAO_151](UIAO_151_OrgPath_Codebook.md) v4.0; the executable codebook is [`data/orgpath/codebook.yaml`](data/orgpath/codebook.yaml) `schema_version: 2.0.0`.

## Purpose

This appendix defines all dynamic group definitions that implement the OrgTree structure in Entra ID. Every OrgTree-prefixed group in the tenant must conform to a definition in this library — built from boolean composition of per-facet predicates against the 10 named `onPremisesExtensionAttribute` slots. Groups not listed here are non-canonical and will be flagged as Phantom Drift by the drift detection engine ([UIAO_163](UIAO_163_Drift_Detection_Engine_Specification.md)).

The Dynamic Group Library is the operational bridge between the OrgPath Codebook (UIAO_151) and every downstream governance artifact: Conditional Access policies target these groups, Administrative Units (UIAO_154) scope delegation through them, licensing assignments flow through them, and the drift engine validates them per-clause.

## Scope

Covers all dynamic security groups and Microsoft 365 groups whose membership is derived from facet values across `extensionAttribute1`–`10` (plus tenant-declared reserved slots 11–15 if used). Applies to all group-based access control, delegation, licensing, and policy targeting within the M365 GCC-Moderate boundary.

## Naming Convention

All OrgTree-governed dynamic groups follow a deterministic naming pattern derived from the facet(s) that scope the rule:

```
OrgTree-[FACET]-[VALUE]-[PURPOSE]                        # single-facet
OrgTree-[FACET1]-[VALUE1]-[FACET2]-[VALUE2]-[PURPOSE]    # multi-facet
```

| Component | Rule | Example |
|---|---|---|
| Prefix | Always `OrgTree-` | `OrgTree-` |
| Facet(s) | Facet name(s) in slot order | `Region`, `Department-Division` |
| Value(s) | Enumeration value(s) from the cited facet(s) | `NCR`, `IT-CyberOps` |
| Purpose | Group function suffix | `-Users`, `-Admins`, `-Licensed`, `-CA` |

Examples:
- `OrgTree-Region-NCR-Users` — all NCR-region users (single-facet)
- `OrgTree-Department-IT-Users` — all IT department users (single-facet)
- `OrgTree-IT-CyberOps-Users` — IT/CyberOps division (multi-facet AND)
- `OrgTree-Executive-CA` — Executive Conditional Access target (single-facet, purpose-coded)

## Three Composition Patterns

Under Model C, every dynamic group rule in the library uses one of three patterns built from per-facet predicates against `onPremisesExtensionAttributes`:

### Pattern 1: Single-facet

Captures all principals whose value for one facet matches (single value or set).

```
(user.onPremisesExtensionAttributes.extensionAttribute2 -eq "IT")
(user.onPremisesExtensionAttributes.extensionAttribute9 -in ["Secret","TopSecret","TS_SCI"])
```

**Use cases:** Department-wide policies, region-wide licensing, clearance-band targeting.

### Pattern 2: Multi-facet AND

Combines clauses across multiple facets. Each clause cites one attribute; clauses are joined with `and`.

```
(user.onPremisesExtensionAttributes.extensionAttribute2 -eq "IT") and (user.onPremisesExtensionAttributes.extensionAttribute3 -eq "CyberOps")
```

**Use cases:** Department + Division scoping, Region + Role scoping, Classification + Department scoping.

### Pattern 3: Multi-facet OR / set

Cross-cutting groupings — multiple values or sets across one or more facets.

```
(user.onPremisesExtensionAttributes.extensionAttribute2 -in ["IT","Engineering"])
```

For multi-facet OR, group via parenthesization:

```
((extensionAttribute2 -eq "IT") and (extensionAttribute3 -eq "CyberOps")) or ((extensionAttribute2 -eq "Legal") and (extensionAttribute3 -eq "GRC"))
```

**Use cases:** Joint compliance groups, cross-divisional projects, role-tier sets.

The Model A "Branch" pattern (`-startsWith "ORG-FIN-AP"` to capture an entire subtree) is *not needed* in Model C because the codebook's tree structure is encoded across facets, not in a single string. To capture "all of IT", use single-facet `attr2 -eq "IT"`. To capture "all of IT/CyberOps", use multi-facet `attr2 -eq "IT" and attr3 -eq "CyberOps"`. Each clause validates independently.

## Canonical Group Definitions

### Region groups (`extensionAttribute1`)

| Group Name | Membership Rule | Members |
|---|---|---|
| `OrgTree-Region-NCR-Users` | `(attr1 -eq "NCR")` | National Capital Region |
| `OrgTree-Region-EASTUS-Users` | `(attr1 -eq "EASTUS")` | Eastern United States |
| `OrgTree-Region-EMEA-Users` | `(attr1 -eq "EMEA")` | Europe / Middle East / Africa |
| `OrgTree-Region-US-Users` | `(attr1 -in ["NCR","EASTUS","WESTUS","CENTRAL"])` | All US regions (composite) |

### Department groups (`extensionAttribute2`)

| Group Name | Membership Rule | Members |
|---|---|---|
| `OrgTree-Department-IT-Users` | `(attr2 -eq "IT")` | All IT department |
| `OrgTree-Department-HR-Users` | `(attr2 -eq "HR")` | All HR users |
| `OrgTree-Department-Finance-Users` | `(attr2 -eq "Finance")` | All Finance users |
| `OrgTree-Department-Legal-Users` | `(attr2 -eq "Legal")` | All Legal/Compliance users |
| `OrgTree-Department-Operations-Users` | `(attr2 -eq "Operations")` | All Operations users |
| `OrgTree-Department-Executive-Users` | `(attr2 -eq "Executive")` | Executive/Leadership |

### Division groups (`extensionAttribute2` AND `extensionAttribute3`)

| Group Name | Membership Rule | Members |
|---|---|---|
| `OrgTree-IT-CyberOps-Users` | `(attr2 -eq "IT") and (attr3 -eq "CyberOps")` | IT/CyberOps |
| `OrgTree-IT-InfraOps-Users` | `(attr2 -eq "IT") and (attr3 -eq "InfraOps")` | IT/Infrastructure |
| `OrgTree-IT-AppDev-Users` | `(attr2 -eq "IT") and (attr3 -eq "AppDev")` | IT/Application Development |
| `OrgTree-Legal-GRC-Users` | `(attr2 -eq "Legal") and (attr3 -eq "GRC")` | Legal/GRC |
| `OrgTree-Finance-Cloud-Users` | `(attr2 -eq "Finance") and (attr3 -eq "Cloud")` | Finance cloud-cost team |

### Role-tier groups (`extensionAttribute4`)

| Group Name | Membership Rule | Members |
|---|---|---|
| `OrgTree-Role-Managers-Users` | `(attr4 -in ["Manager","Director","VP"])` | All people-management roles |
| `OrgTree-Role-Engineers-Users` | `(attr4 -in ["Engineer","Architect"])` | All engineering ICs |
| `OrgTree-Role-CISO-Users` | `(attr4 -eq "CISO")` | CISO singletons |

### Clearance-gated groups (`extensionAttribute9`)

| Group Name | Membership Rule | Members |
|---|---|---|
| `OrgTree-Cleared-Secret-Plus-Users` | `(attr9 -in ["Secret","TopSecret","TS_SCI"])` | All cleared personnel |
| `OrgTree-Cleared-TopSecret-Plus-Users` | `(attr9 -in ["TopSecret","TS_SCI"])` | TS / TS-SCI only |

### Account-type groups (`extensionAttribute10`)

| Group Name | Membership Rule | Members |
|---|---|---|
| `OrgTree-AccountType-Privileged-Users` | `(attr10 -eq "Privileged")` | PIM-eligible privileged accounts |
| `OrgTree-AccountType-Service-Users` | `(attr10 -eq "Service")` | Service accounts |
| `OrgTree-AccountType-Guest-Users` | `(attr10 -eq "Guest")` | B2B guests |

### Cross-cutting groups (multi-facet OR / set)

| Group Name | Membership Rule | Purpose |
|---|---|---|
| `OrgTree-SecurityCompliance-Users` | `((attr2 -eq "IT") and (attr3 -eq "CyberOps")) or ((attr2 -eq "Legal") and (attr3 -eq "GRC"))` | Joint Security + Compliance visibility |
| `OrgTree-AllRegional-AP-Users` | `(attr1 -in ["NCR","EASTUS","WESTUS","CENTRAL"]) and (attr2 -eq "Finance")` | All US-region Finance |

### Conditional Access groups

| Group Name | Membership Rule | CA Policy Target |
|---|---|---|
| `OrgTree-Executive-CA` | `(attr6 -eq "Executive")` | Executive MFA enforcement, device compliance |
| `OrgTree-IT-Security-CA` | `(attr2 -eq "IT") and (attr3 -eq "CyberOps") and (attr10 -eq "Privileged")` | Security team — privileged-access policies |
| `OrgTree-AllGovernedUsers-CA` | `(attr2 -ne "")` | Baseline CA — any principal with a populated Department facet |

### Licensing groups

| Group Name | Membership Rule | License SKU |
|---|---|---|
| `OrgTree-Executive-Licensed` | `(attr6 -eq "Executive")` | E5 + Copilot |
| `OrgTree-IT-Licensed` | `(attr2 -eq "IT")` | E5 |
| `OrgTree-Standard-Licensed` | `(attr2 -ne "") and (attr2 -notIn ["Executive","IT"])` | E3 (everyone else with a populated Department) |

### Lifecycle-driven groups (`extensionAttribute7` / `extensionAttribute8`)

| Group Name | Membership Rule | Members |
|---|---|---|
| `OrgTree-Active-Employees` | `(attr8 -eq "")` | Empty TermDate ⇒ active |
| `OrgTree-Contractors-In-IT` | `(attr2 -eq "IT") and (attr6 -eq "Contractor")` | IT contractors |
| `OrgTree-Leavers-Next-30d` | `(attr8 -gt "<today>") and (attr8 -lt "<today+30d>")` | Pre-departure offboarding queue (date template) |

## Drift Detection Rules

Per-clause classification means a rule like `(attr2 -eq "IT") and (attr3 -eq "OldDivision")` reports drift on the second clause if `OldDivision` was deprecated, while the first clause continues to validate cleanly against the Department facet's enumeration.

| Drift Type | Detection | Severity | Auto-Remediate |
|---|---|---|---|
| Rule Drift | Tenant group rule differs from canonical rule in this library | HIGH | Yes — overwrite from canonical source |
| Clause Drift | A single clause in a multi-facet rule references a deprecated or unknown facet value | HIGH | No — fix codebook or rule, depending on root cause |
| Phantom Group | Group with `OrgTree-` prefix exists in tenant but has no entry in this library | MEDIUM | No — investigate, then delete or canonize |
| Missing Group | Entry exists in this library but no corresponding group in tenant | HIGH | Yes — create group from canonical definition |
| Name Drift | Group exists with correct rule but wrong name | LOW | Yes — rename to canonical name |
| Membership Drift | Group membership does not match expected user count | MEDIUM | Root cause is facet values in UIAO_151, not group rules |

## Governance Rules

1. **No manual members.** If a group appears in this library, it is dynamic-only. Manually assigned members are drift by definition.
2. **One canonical rule per group.** Each group has exactly one membership rule. Multiple rules for the same scope require separate groups.
3. **Naming is deterministic.** The group name is derived from the cited facet(s) + value(s) + purpose. Renaming without updating this library is drift.
4. **Single-facet preferred.** Multi-facet compositions only when the cross-facet selection is operationally distinct.
5. **Changes require governed workflow.** Adding, modifying, or removing a group definition follows Workflow 3 (Dynamic Group Creation/Modification) in Appendix E and requires validation per Appendix J Group Tests.
6. **Facet dependency.** Every membership rule cites facet values defined in UIAO_151. If a facet value is deprecated, all groups referencing it must update or retire.

## PowerShell Validation

```powershell
# Validate OrgTree dynamic groups against the canonical Model C library
$canonicalGroups = @{
    "OrgTree-Region-NCR-Users"          = '(user.onPremisesExtensionAttributes.extensionAttribute1 -eq "NCR")'
    "OrgTree-Department-IT-Users"       = '(user.onPremisesExtensionAttributes.extensionAttribute2 -eq "IT")'
    "OrgTree-IT-CyberOps-Users"         = '(user.onPremisesExtensionAttributes.extensionAttribute2 -eq "IT") and (user.onPremisesExtensionAttributes.extensionAttribute3 -eq "CyberOps")'
    "OrgTree-Cleared-Secret-Plus-Users" = '(user.onPremisesExtensionAttributes.extensionAttribute9 -in ["Secret","TopSecret","TS_SCI"])'
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

A complete validation flow loads the canonical library from a structured YAML (per the Phase 5 consumer rebuild per ADR-078) and reconciles per-clause facet citations against the codebook's current enumerations.

## Change Log

| Version | Date | Change | Author |
|---|---|---|---|
| 1.0 | 2026-04-18 | Initial DRAFT scaffold — Model A composite-hyphen, Branch/Node/Compound patterns | Copilot Tasks |
| 2.0 | 2026-04-19 | Promoted to CANONICAL — full Model A group inventory, drift rules, validation script | Copilot Tasks |
| **3.0** | **2026-05-24** | **Full Model C rewrite per [ADR-078](adr/adr-078-orgpath-attribute-schema-15-facet.md).** Replaced Branch/Node patterns with three boolean-composition patterns over facet predicates; rewrote group inventory by facet (Region/Department/Division/Role/Clearance/AccountType/Cross-cutting/CA/Licensing/Lifecycle); added Clause Drift to the drift category set; updated PowerShell validation for `onPremisesExtensionAttributes.extensionAttribute*` references. | Governance Steward |
