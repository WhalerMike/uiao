document_id: UIAO_137
title: "Spec1-D1.1 - AD Computer Inventory Discovery"
version: "1.0"
status: Draft
classification: CANONICAL
owner: "Michael Stratton"
created_at: "2026-04-29"
updated_at: "2026-04-29"
boundary: "GCC-Moderate"
---

# Spec1-D1.1 - AD Computer Inventory Discovery

## Overview
This discovery specification defines the data collection required to establish a complete, authoritative inventory of all Active Directory computer objects. The output provides the baseline for device lifecycle classification (Active / Stale / Abandoned), OS distribution analysis, infrastructure role detection, and OrgPath readiness.

This discovery is the first input into the D1.x identity modernization sequence.

## Inputs
- Active Directory domain connectivity
- Read access to:
  - `CN=Computers`
  - All delegated OUs containing computer objects
- PowerShell modules:
  - ActiveDirectory

## Outputs
- Structured JSON file containing:
  - Distinguished Name
  - Operating System + version
  - LastLogonTimestamp (converted to UTC)
  - OU path
  - SPN list
  - BitLocker key presence flag
  - LAPS password age (Windows LAPS or legacy AD LAPS)
  - Delegation flags
  - Infrastructure classification:
    - Domain Controller
    - ADFS
    - PKI / Certificate Services
    - Standard workstation/server
  - State classification:
    - Active (<= 30 days)
    - Stale (31-180 days)
    - Abandoned (> 180 days)
  - OS distribution summary

## Script Logic Summary
1. Query all computer objects using `Get-ADComputer -Properties *`.
2. Normalize timestamps and convert to UTC.
3. Extract:
   - OS fields
   - SPNs
   - Delegation flags
   - LAPS attributes
4. Detect infrastructure roles using:
   - SPN patterns
   - OU placement
   - Service flags
5. Classify lifecycle state using last logon thresholds.
6. Generate summary statistics:
   - OS distribution
   - State distribution
   - Infrastructure counts
7. Emit structured JSON to disk.

## Evidence Produced
- `computers.json` containing the full dataset
- Summary block embedded in the JSON:
  - OS distribution
  - Active/Stale/Abandoned counts
  - Infrastructure role counts

## Operational Notes
- This discovery must run before any device OrgPath planning.
- Domain Controllers may require elevated permissions to read BitLocker and LAPS attributes.
- The output is consumed by:
  - OrgPath readiness analysis
  - Device lifecycle cleanup planning
  - Conditional Access device filter design

## Appendix A - Copy Section
This appendix intentionally retained per UIAO global rule.
