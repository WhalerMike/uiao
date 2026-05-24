---
document_id: UIAO_151
title: "Appendix A — OrgPath Codebook (Model C, 15-facet multi-attribute)"
version: "4.0"
status: Current
owner: Michael Stratton
author: Michal Doroszewski
created_at: "2026-04-18"
updated_at: "2026-05-24"
boundary: GCC-Moderate
classification: CANONICAL
promotion:
  prior_version: "3.0 (Model A composite-hyphen, ADR-062 8-segment cap)"
  promoted_by: "Governance Steward"
  promotion_date: "2026-05-24"
  promotion_adr: ADR-078
provenance_flatten:
  prior_id: "MOD_A"
  flattened_at: "2026-05-10"
  flattened_by: "ADR-060"
---

# Appendix A — OrgPath Codebook (Model C)

> **Model C (15-facet multi-attribute) is the canonical OrgPath schema for new UIAO adoption.** Per [ADR-078](adr/adr-078-orgpath-attribute-schema-15-facet.md), the prior Model A composite-hyphen path (`extensionAttribute1: ORG-FIN-AP-EAST`) is superseded. The executable canon at [`data/orgpath/codebook.yaml`](data/orgpath/codebook.yaml) is `schema_version: 2.0.0`, validated by [`schemas/orgpath/codebook.schema.json`](../schemas/orgpath/codebook.schema.json), and loaded into a `Codebook` / `Facet` / `FacetValue` Python API at [`uiao.modernization.orgtree.codebook`](../modernization/orgtree/codebook.py).

## Purpose

This appendix defines the canonical 15-facet multi-attribute model for encoding organizational identity in Entra ID `onPremisesExtensionAttributes`. Each of the 15 attribute slots carries one *semantic facet* (Region, Department, Division, Role, CostCenter, Classification, HireDate, TermDate, ClearanceLevel, AccountType — plus five reserved for tenant-specific extension). Together, the facets give every principal a structured identity surface that dynamic groups, Administrative Units, Conditional Access policies, and lifecycle workflows compose against via boolean rules rather than text-parsing a single composite string.

Every other OrgTree artifact depends on this codebook: dynamic groups (UIAO_152) AND facet predicates into membership rules, Administrative Units (UIAO_154) scope by facet tuples, drift detection (UIAO_163) validates each attribute against its facet's enumeration independently, and the delegation matrix maps role assignments to facet-defined scopes.

## Scope

Covers all 15 `onPremisesExtensionAttribute` slots on every user, device, and service-principal object within the M365 GCC-Moderate boundary. Applies to dynamic group membership rules, Administrative Unit scoping, Conditional Access targeting, and lifecycle automation. The codebook is the single source of truth for which facet binds to which slot and which values each facet accepts.

Per ADR-078 and ADR-076, Model C is a **Tier 3+ doctrine for new adoption**. UIAO has no production adopters at this version's ratification; no Model A grandfathering is required. The prior composite-hyphen schema is retired.

## Canonical Attribute Assignments

Per ADR-078 §Canonical attribute assignments, the 10 named facets bind to specific extensionAttribute slots. Slot assignments are canonical and MUST NOT be remapped without a superseding ADR. Slots 11–15 are reserved for tenant-specific extensions and require a governed PR before population.

| Slot | Facet | Kind | Description |
|---|---|---|---|
| `extensionAttribute1` | **Region** | enumerated | Geographic / cloud region (e.g., `NCR`, `WESTUS`, `EMEA`) |
| `extensionAttribute2` | **Department** | enumerated | Top-level department (e.g., `IT`, `HR`, `Finance`, `Legal`) |
| `extensionAttribute3` | **Division** | enumerated | Sub-department division (e.g., `CyberOps`, `InfraOps`, `AppDev`, `GRC`) |
| `extensionAttribute4` | **Role** | enumerated | Functional role (e.g., `Analyst`, `Engineer`, `Manager`, `Director`, `CISO`) |
| `extensionAttribute5` | **CostCenter** | enumerated | Chargeback / license-governance code (e.g., `CC-4100`, `CC-5200`) |
| `extensionAttribute6` | **Classification** | enumerated | Workforce classification (e.g., `Employee`, `Contractor`, `Intern`, `Executive`) |
| `extensionAttribute7` | **HireDate** | typed (ISO date) | Joiner-lifecycle anchor; ISO 8601 `YYYY-MM-DD` |
| `extensionAttribute8` | **TermDate** | typed (ISO date, allow_empty) | Leaver-lifecycle anchor; ISO 8601 or empty for active |
| `extensionAttribute9` | **ClearanceLevel** | enumerated | Personnel security clearance (e.g., `None`, `PublicTrust`, `Secret`, `TopSecret`, `TS_SCI`) |
| `extensionAttribute10` | **AccountType** | enumerated | Account category (e.g., `Standard`, `Privileged`, `Service`, `SharedMailbox`, `Guest`, `Vendor`) |
| `extensionAttribute11`–`15` | **Reserved** | reserved | Tenant-specific extension slots; declare facet semantics via governed PR before populating |

## Facet Kinds

Every facet declares one of three kinds:

| Kind | Validation | Use cases |
|---|---|---|
| **enumerated** | Value must appear in the facet's closed `enumeration` list | Region, Department, Division, Role, CostCenter, Classification, ClearanceLevel, AccountType |
| **typed** | Value must match `value_type` and optional `value_pattern` regex; `allow_empty: true` permits empty string | HireDate, TermDate (dates are not enumerable) |
| **reserved** | No value accepted until promoted to enumerated or typed via governed PR | Slots 11–15 until declared |

The Python loader rejects any value that is neither active nor explicitly deprecated. The drift engine emits `DRIFT-SEMANTIC` per-facet for unknown values and per-facet for deprecated values — the second class additionally carries the `replaced_by` successor for remediation.

## Slot Uniqueness Invariant

Each `extensionAttribute` slot is claimed by exactly one facet. The Python loader's `_validate_integrity` step rejects any codebook that declares two facets binding the same slot:

```
Facets 'region' and 'second_facet' both bind to 'extensionAttribute1'.
Each extensionAttribute slot must be claimed by at most one facet.
```

This invariant cannot be expressed in JSON Schema (which checks per-property shape, not cross-property uniqueness), so the loader enforces it after schema validation.

## Per-Facet Enumeration (Starter Set)

The shipped codebook starter values target federal-IT defaults. Tenants extend each enumeration via governed PRs. The full enumeration lives in [`data/orgpath/codebook.yaml`](data/orgpath/codebook.yaml); excerpts shown here.

### Region (`extensionAttribute1`)

| Value | Description |
|---|---|
| `NCR` | National Capital Region |
| `EASTUS` | Eastern United States |
| `WESTUS` | Western United States |
| `CENTRAL` | Central United States |
| `EMEA` | Europe / Middle East / Africa |
| `APAC` | Asia-Pacific |
| `LATAM` | Latin America |

### Department (`extensionAttribute2`)

| Value | Description |
|---|---|
| `IT` | Information Technology |
| `HR` | Human Resources |
| `Finance` | Finance |
| `Legal` | Legal / Compliance |
| `Engineering` | Engineering |
| `Operations` | Operations |
| `Sales` | Sales / Marketing |
| `Executive` | Executive / Leadership |

### Classification (`extensionAttribute6`)

| Value | Description |
|---|---|
| `Employee` | Full-time employee |
| `PartTime` | Part-time employee |
| `Contractor` | Contractor / vendor |
| `Intern` | Intern |
| `Executive` | Executive |
| `Volunteer` | Volunteer |

### ClearanceLevel (`extensionAttribute9`)

| Value | Description |
|---|---|
| `None` | No clearance required / not applicable |
| `PublicTrust` | Public Trust |
| `Secret` | Secret |
| `TopSecret` | Top Secret |
| `TS_SCI` | Top Secret / Sensitive Compartmented Information |

*(Division, Role, CostCenter, AccountType enumerations are similar in shape and shipped in the YAML; the four examples above are representative.)*

### HireDate / TermDate (`extensionAttribute7` / `extensionAttribute8`)

Typed facets with `value_type: date` and `value_pattern: "^\d{4}-\d{2}-\d{2}$"`. TermDate additionally declares `allow_empty: true` so active employees carry an empty string rather than a sentinel future date.

## Dynamic Group Rules — Boolean Composition

Model C's central operational advantage: dynamic group rules compose facets via standard boolean operators, not regex matching against a single composite string. The Entra dynamic membership language fully supports this:

```
(user.onPremisesExtensionAttributes.extensionAttribute2 -eq "IT") and
(user.onPremisesExtensionAttributes.extensionAttribute3 -eq "CyberOps")
```

### Single-facet groups

| Group | Rule | Captures |
|---|---|---|
| `OrgTree-Department-IT` | `(attr2 -eq "IT")` | All IT users across every region, division, role |
| `OrgTree-Region-NCR` | `(attr1 -eq "NCR")` | All National Capital Region users |
| `OrgTree-Classification-Executive` | `(attr6 -eq "Executive")` | All Executive-classified principals |

### Multi-facet compositions

| Group | Rule | Use case |
|---|---|---|
| `OrgTree-IT-CyberOps` | `(attr2 -eq "IT") and (attr3 -eq "CyberOps")` | IT/CyberOps division — narrow team scope |
| `OrgTree-Privileged-Cleared` | `(attr10 -eq "Privileged") and (attr9 -in ["Secret","TopSecret","TS_SCI"])` | Privileged accounts with clearance — high-blast-radius gate |
| `OrgTree-NCR-IT-Managers` | `(attr1 -eq "NCR") and (attr2 -eq "IT") and (attr4 -in ["Manager","Director"])` | NCR-region IT leadership — meeting/announcement targeting |

### Lifecycle-driven groups

| Group | Rule | Use case |
|---|---|---|
| `OrgTree-Active-Employees` | `(attr8 -eq "")` | Empty TermDate ⇒ active employee |
| `OrgTree-Leavers-Next-30d` | `(attr8 -gt "<today>") and (attr8 -lt "<today+30d>")` | Pre-departure offboarding queue (templated date) |
| `OrgTree-Contractors-In-IT` | `(attr2 -eq "IT") and (attr6 -eq "Contractor")` | Department-scoped contractor view for license audits |

The boolean composition is auditable per-clause (each clause cites a single attribute) and refactorable per-facet (changing a facet enumeration does not require re-parsing rule strings).

## Administrative Unit Mapping

Administrative Units scope role assignments by facet tuples mirroring the dynamic-group pattern. The membership rule is a boolean composition; the AU itself can be Restricted Management per UIAO_154.

| Administrative Unit | Membership Rule | Scoped Role | Delegate |
|---|---|---|---|
| `AU-Department-IT` | `attr2 -eq "IT"` | User Administrator | IT Division Lead |
| `AU-IT-CyberOps` | `(attr2 -eq "IT") and (attr3 -eq "CyberOps")` | Helpdesk Administrator | CyberOps Manager |
| `AU-Region-NCR-Privileged` | `(attr1 -eq "NCR") and (attr10 -eq "Privileged")` | Authentication Administrator | NCR PAM Steward |
| `AU-Cleared-TopSecret-Plus` | `attr9 -in ["TopSecret","TS_SCI"]` | Conditional Access Administrator | Personnel Security Office |

## Boundary Rules

1. Each `extensionAttribute` slot 1–15 may be claimed by at most one facet (loader-enforced).
2. Slots 11–15 default to `kind: reserved` and reject all values until declared via governed PR.
3. Enumerated facet values must match the facet's `enumeration` list (case-sensitive); non-matching values are `DRIFT-SEMANTIC`.
4. Typed facet values must match `value_type` and optional `value_pattern`; non-matching values are `DRIFT-SEMANTIC`.
5. OrgPath data lives in Entra ID `onPremisesExtensionAttributes` within the M365 GCC-Moderate boundary; no facet references external systems outside the SaaS perimeter.
6. HR is the authoritative source for facet values; IT never manually edits Entra-side `extensionAttribute*` slots.
7. Deprecated values must declare `replaced_by` resolving to an active value in the same facet's enumeration.

## Drift Detection — Per Facet

The drift detection engine validates each principal's 10 named facet values independently against the codebook. Five drift categories apply per-facet, not per composite path:

| Category | Definition | Severity | Auto-Remediate | Example |
|---|---|---|---|---|
| **Value Drift** | `attr[N]` value not in facet enumeration (or not matching typed pattern) | High | No — flag for investigation | `attr1 = "ATLANTIS"` when Region enumeration has no such value |
| **Format Drift** | `attr[N]` value violates typed `value_pattern` | Critical | No — manual correction | `attr7 = "Jan 15 2024"` (HireDate must be ISO `2024-01-15`) |
| **Slot Drift** | A facet's declared `attribute:` was remapped to a different slot without ADR | Critical | No — codebook integrity issue | Codebook PR moves Region from `attr1` to `attr3` without superseding ADR |
| **Orphan Drift** | A facet enumeration value has zero matching principals | Medium | Flag for review | `Region = "LATAM"` declared but no users assigned |
| **Phantom Drift** | A principal carries a value that was deprecated in the codebook | Medium | Flag + suggest `replaced_by` | `Department = "ITSecurity"` after deprecation in favor of `IT` |

Per-facet classification means a principal with a valid Region but an unknown Department gets one `DRIFT-SEMANTIC` finding for the Department slot only — the Region facet is independently passing.

## PowerShell Validation

The PowerShell module `Test-OrgPathFormat` validates Model C facet values per slot. Sample validation flow:

```powershell
# Prerequisites: Connect-MgGraph -Scopes "User.Read.All"
# Load the Model C codebook from canon
$codebookPath = "src/uiao/canon/data/orgpath/codebook.yaml"
$codebook = ConvertFrom-Yaml (Get-Content $codebookPath -Raw)

$users = Get-MgUser -All -Property Id, OnPremisesExtensionAttributes, DisplayName

# Per-facet validation — Region (extensionAttribute1)
$regionFacet = $codebook.facets.region
$validRegions = $regionFacet.enumeration | ForEach-Object { $_.value }

$regionDrift = $users | Where-Object {
    $value = $_.OnPremisesExtensionAttributes.ExtensionAttribute1
    $value -and ($value -notin $validRegions)
}

Write-Host "=== REGION DRIFT (extensionAttribute1) ===" -ForegroundColor Yellow
$regionDrift | Select DisplayName, @{N='Region'; E={$_.OnPremisesExtensionAttributes.ExtensionAttribute1}}

# Per-facet validation — HireDate (typed, ISO date)
$hireDatePattern = $codebook.facets.hire_date.value_pattern
$hireDateDrift = $users | Where-Object {
    $value = $_.OnPremisesExtensionAttributes.ExtensionAttribute7
    $value -and ($value -notmatch $hireDatePattern)
}

Write-Host "=== HIRE-DATE FORMAT DRIFT (extensionAttribute7) ===" -ForegroundColor Red
$hireDateDrift | Select DisplayName, @{N='HireDate'; E={$_.OnPremisesExtensionAttributes.ExtensionAttribute7}}
```

A complete per-facet validation script iterates every facet declared in the codebook and emits findings per slot. The shipped Python implementation at `uiao.modernization.orgtree.codebook` exposes `Facet.is_active(value)` and `Facet.is_valid_value(value)` helpers that the PowerShell module delegates to via the `uiao` CLI under Tier 3+ adoption.

## Implementation Steps

1. **Finalize the codebook** — Review and customize each of the 10 named facet enumerations against your tenant's actual organizational structure. The shipped starter values are federal-IT defaults; every tenant tunes Department, Division, Role, CostCenter, and ClearanceLevel to match local taxonomy.
2. **Plan reserved-slot use** — If your tenant needs additional facets beyond the 10 named ones, draft a governed PR declaring semantics for one or more of slots 11–15. Per ADR-078, this MUST verify the slot's current `extensionAttribute[N]` value is null tenant-wide before promoting the facet.
3. **Populate the attributes** — Use HR-driven inbound provisioning (HR system → Entra Connect → 10-slot population) to write each facet to its slot. Per ADR-001/ADR-002, this happens at the identity-provisioning layer; IT never manually edits these values in Entra.
4. **Author dynamic groups** — Start with single-facet groups (`Department`, `Region`) and grow to multi-facet compositions (`Department + Division + Role`) as Conditional Access targeting matures.
5. **Create Administrative Units** — Mirror the dynamic group pattern with AU scoping. Mark each AU as Restricted Management per UIAO_154.
6. **Validate** — Run per-facet validation (PowerShell module or `uiao orgtree validate codebook`) to surface any pre-existing Value or Format Drift before enabling governance automation.
7. **Enable drift detection** — Wire the codebook into the drift engine (UIAO_163; rebuilt per-facet in ADR-078 Phase 5+) for continuous per-slot monitoring.

## Governance Alignment

This codebook implements the **SSOT** universal principle (per [ADR-079](adr/adr-079-governance-principle-reconciliation.md)): the per-facet enumerations are the canonical definition of which values are legal for each `extensionAttribute` slot, defined exactly once and consumed by every downstream rule, AU, drift check, and lifecycle workflow. Changes follow the canonical contributor workflow (UIAO_172): governed PR, schema validation gate, drift-engine impact review, integration tests, Governance Board approval. Adding a value to an enumeration is additive (safe); deprecating a value requires `replaced_by` pointing at the successor.

## Change Log

| Version | Date | Change | Author |
|---|---|---|---|
| 1.0 | 2026-04-18 | Initial scaffold — Model A composite-hyphen structure, regex, drift rules | Copilot Tasks |
| 2.0 | 2026-04-19 | Promoted to CANONICAL — Model A sample entries, dynamic group rules, AU mapping, PowerShell validation, implementation steps | Copilot Tasks |
| 3.0 | 2026-04-26 | Model A extended hierarchy depth from 4 to 8 segments (ADR-062) — regex `{0,8}`, level table extended through Squad | Governance Steward |
| **4.0** | **2026-05-24** | **Full Model C rewrite per [ADR-078](adr/adr-078-orgpath-attribute-schema-15-facet.md)** — Model A composite-hyphen retired; canonical OrgPath schema is now 15-facet multi-attribute (10 named + 5 reserved). Per-facet enumerations; boolean composition for dynamic group rules; per-facet drift; slot uniqueness invariant; updated PowerShell validation to per-facet flow. Schema version `2.0.0`. No Model A grandfathering (no production adopters at ratification per ADR-078). | Governance Steward |
