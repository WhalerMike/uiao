---
document_id: UIAO_105
title: "UIAO Auditor API"
version: "1.0"
status: Current
classification: CANONICAL
owner: "Michael Stratton"
created_at: "2026-04-14"
updated_at: "2026-04-14"
boundary: "GCC-Moderate"
---

# UIAO Auditor API

The Auditor API provides read-only access to UIAO compliance evidence, findings, POA&M entries, and OSCAL outputs for auditors and oversight personnel.

---

## Purpose

- Read-only evidence retrieval
- Provenance verification
- OSCAL document download (SSP, SAP, SAR, POA&M)
- Finding and POA&M visibility
- No write access — auditors cannot modify data

---

## Authentication

- OAuth2 / OIDC (Entra ID)
- Required role: `UIAO.Viewer` or `UIAO.Auditor`
- All requests require `Authorization: Bearer <JWT>`

---

## Endpoints

### GET /api/auditor/evidence/{id}
Returns a single evidence object by ID.

**Response:**
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

### GET /api/auditor/evidence
Returns all evidence objects, with optional filters.

**Query Parameters:**
- `control_id` — filter by control (e.g., `IA-2`)
- `collector` — filter by source (e.g., `SCuBA`)
- `from` / `to` — date range filter

---

### GET /api/auditor/findings
Returns all compliance findings.

**Response:**
```json
[
  {
    "finding_id": "FIND-0001",
    "control_id": "AC-21",
    "severity": "Medium",
    "status": "Open",
    "detected_at": "2026-04-10T00:00:00Z",
    "evidence_ids": ["EV-0006"]
  }
]
```

---

### GET /api/auditor/poam
Returns all POA&M entries.

**Response:**
```json
[
  {
    "poam_id": "POAM-0001",
    "control_id": "AC-21",
    "severity": "Medium",
    "status": "Open",
    "milestones": [...],
    "finding_id": "FIND-0001"
  }
]
```

---

### GET /api/auditor/oscal/ssp
Returns the current OSCAL SSP JSON.

---

### GET /api/auditor/oscal/sap
Returns the current OSCAL SAP JSON.

---

### GET /api/auditor/oscal/sar
Returns the current OSCAL SAR JSON.

---

### GET /api/auditor/oscal/poam
Returns the current OSCAL POA&M JSON.

---

## File Location

```
uiao/api/
  └── auditor-api.md     (this file)
```
