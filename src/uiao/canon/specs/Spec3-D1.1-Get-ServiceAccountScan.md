document_id: UIAO_139
title: "Spec3-D1.1 - Service Account Discovery Scan"
version: "1.0"
status: Draft
classification: CANONICAL
owner: "Michael Stratton"
created_at: "2026-04-29"
updated_at: "2026-04-29"
boundary: "GCC-Moderate"
---

# Spec3-D1.1 - Service Account Discovery Scan

## Overview
This discovery specification identifies all service accounts, classifies them by workload type, evaluates risk posture, and recommends modernization targets per ADR-004. It performs a 7-pass scan across SPNs, password policies, delegation, AdminCount, and naming patterns.

## Inputs
- Read access to:
  - All user and service accounts in Active Directory
- PowerShell modules:
  - ActiveDirectory

## Outputs
- Structured JSON file containing:
  - SPN inventory
  - Password-never-expires flags
  - gMSA and sMSA detection
  - Delegation configuration
  - AdminCount status
  - Naming pattern classification
  - Workload classification:
    - SQL
    - Web
    - Exchange
    - Named application
  - Risk score:
    - Critical
    - High
    - Medium
    - Low
  - Recommended modernization target:
    - Managed Identity
    - Workload Identity Federation
    - gMSA
    - App Registration

## Script Logic Summary
1. Query all accounts with `Get-ADUser -Properties *`.
2. Extract SPNs and classify workloads.
3. Detect:
   - gMSAs
   - sMSAs
   - Password-never-expires
   - Delegation
   - AdminCount
4. Apply naming pattern heuristics.
5. Assign risk score based on:
   - Delegation
   - SPN exposure
   - Password policy
   - Privilege level
6. Recommend modernization target per ADR-004.
7. Emit structured JSON to disk.

## Evidence Produced
- `service-accounts.json` containing:
  - Full service account dataset
  - Risk scoring
  - Modernization recommendations

## Operational Notes
- This discovery feeds:
  - Workload identity migration planning
  - Privileged access cleanup
  - SPN rationalization
- High-risk accounts should be remediated before enabling Conditional Access enforcement.

## Appendix A - Copy Section
This appendix intentionally retained per UIAO global rule.
