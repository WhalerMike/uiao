# UIAO Evidence Collector Interface

The Evidence Collector Framework provides standardized, pluggable evidence ingestion for the UIAO compliance engine.

---

## Purpose

- Standardized evidence ingestion across all sources
- Pluggable collector architecture
- Hashing and provenance generation
- IR object binding

---

## Collector Types

### A. SCuBA Collector
- Raw SCuBA JSON output
- Normalized UIAO fields
- KSI evaluation results
- Source: ScubaGear / adapter-run-scuba.ps1

### B. Azure AD Collector
- Conditional Access policies
- MFA registration status
- Sign-in logs and risk events
- Source: Microsoft Graph API

### C. M365 Collector
- Exchange Online settings
- SharePoint sharing configuration
- DLP policy status
- Source: Microsoft Graph / Exchange PowerShell

### D. Defender Collector
- Threat protection settings
- Safe Links / Safe Attachments status
- Defender for Office 365 policies
- Source: Security & Compliance API

---

## Required Interface Methods

### collect()
Collects raw evidence from the source system.
- Returns: raw evidence object
- Must be idempotent

### normalize()
Converts raw evidence into UIAO IR normalized fields.
- Input: raw evidence object
- Returns: normalized IR fields

### hash()
Computes SHA-256 hash of the normalized evidence.
- Input: normalized evidence
- Returns: hash string (sha256:...)

### provenance()
Generates a provenance manifest for the collected evidence.
- Input: normalized evidence + hash
- Returns: provenance manifest object

### bind()
Binds evidence to an IR object and control.
- Input: normalized evidence, IR object ID, control ID
- Returns: evidence binding record

---

## Evidence Object Schema

```json
{
  "evidence_id": "EV-0001",
  "collector": "SCuBA",
  "field": "MFAEnabled",
  "value": true,
  "collected_at": "2026-04-10T00:00:00Z",
  "hash": "sha256:...",
  "provenance_manifest": "prov-scuba-20260410-01.json",
  "ir_object": "IR-ACCT-MFA-001",
  "control_id": "IA-2"
}
```

---

## File Locations

```
uiao-core/evidence/
  ├── collector-interface.md     (this file)
  ├── graph-schema.md            (evidence graph model)
  ├── collectors/
  │   ├── scuba-collector.ps1
  │   ├── azuread-collector.ps1
  │   ├── m365-collector.ps1
  │   └── defender-collector.ps1
  └── schemas/
      └── evidence-object.schema.json
```
