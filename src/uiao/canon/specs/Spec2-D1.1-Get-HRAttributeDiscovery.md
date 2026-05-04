document_id: UIAO_138
title: "Spec2-D1.1 - HR Attribute Schema Discovery"
version: "1.0"
status: Draft
classification: CANONICAL
owner: "Michael Stratton"
created_at: "2026-04-29"
updated_at: "2026-04-29"
boundary: "GCC-Moderate"
---

# Spec2-D1.1 - HR Attribute Schema Discovery

## Overview
This discovery specification evaluates the readiness of the HR -> Entra ID provisioning pipeline. It inspects HR attribute population rates, extensionAttribute usage, UPN domain consistency, department/division taxonomy, and OU structure alignment. It also determines whether `extensionAttribute1` is available for OrgPath per ADR-048.

## Inputs
- Read access to:
  - All user objects in Active Directory
- PowerShell modules:
  - ActiveDirectory

## Outputs
- Structured JSON file containing:
  - Population rates for:
    - givenName
    - sn
    - displayName
    - employeeID
    - employeeType
    - department
    - division
  - Usage audit for all 15 extensionAttributes
  - UPN domain inventory with:
    - counts
    - conflicts
    - non-authoritative domains
  - Department/division taxonomy summary
  - OU structure analysis
  - Provisioning Readiness Assessment:
    - 6 checks, each PASS/WARN/FAIL
  - OrgPath attribute availability flag for `extensionAttribute1`

## Script Logic Summary
1. Query all user objects with `Get-ADUser -Properties *`.
2. Compute population rates for core HR attributes.
3. Inspect all 15 extensionAttributes for:
   - usage
   - collisions
   - non-standard values
4. Build UPN domain inventory and detect:
   - unauthorized domains
   - mixed-case UPNs
   - duplicates
5. Analyze department/division taxonomy:
   - cardinality
   - normalization
   - outliers
6. Evaluate OU structure alignment with HR data.
7. Run the 6-check Provisioning Readiness Assessment:
   - HR completeness
   - UPN consistency
   - ExtensionAttribute availability
   - Department/division normalization
   - OU alignment
   - Provisioning blockers
8. Emit structured JSON to disk.

## Evidence Produced
- `hr-attributes.json` containing:
  - Population metrics
  - ExtensionAttribute usage map
  - UPN domain inventory
  - Taxonomy summary
  - Readiness Assessment

## Operational Notes
- This discovery must run before OrgPath allocation.
- `extensionAttribute1` availability is a gating factor per ADR-048.
- The taxonomy output is consumed by:
  - OrgPath calculator
  - Dynamic group design
  - Administrative Unit scoping

## Appendix A - Copy Section
This appendix intentionally retained per UIAO global rule.
