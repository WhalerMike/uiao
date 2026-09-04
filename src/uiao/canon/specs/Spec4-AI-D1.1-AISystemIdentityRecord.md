---
document_id: UIAO_196
title: "AI System Identity Record — Machine-Identity Schema and OrgPath Binding for Federal AI Systems"
version: "1.0"
status: Draft
owner: governance-steward
created_at: "2026-06-18"
updated_at: "2026-06-18"
canon_adrs:
  - ADR-112   # Federal AI Use Case Governance — governing ADR
  - ADR-059   # SailPoint adapter family — sailpoint-machine-identity slot
  - ADR-092   # Active Governance — agentic AI as governed data plane
  - ADR-054   # Single-ATO reciprocity — ATO enumeration
  - ADR-012   # Canonical drift taxonomy
publish_to_site: true
---

# UIAO_196 — AI System Identity Record

## Overview

Every deployed or piloted federal AI system inventoried under OMB M-25-21
(EO 13960 §5) is an identity subject in UIAO's machine-identity surface. This
spec defines the canonical record shape, its OrgPath binding rules, the six
drift finding types that detect identity governance gaps, and the L1 scanner
that produces them.

The record is the unit of comparison for the AI identity drift scan
(`uiao.governance.ai_inventory.scanner`). Each field has an expected
governance state; deviations produce `Finding` objects routed through the
ADR-012 drift taxonomy.

The governing ADR is **ADR-112**. This spec provides the operational schema
detail that ADR-112's doctrine section leaves implicit.

---

## 1. Record Fields

| Field | Source | Type | Governance role |
|---|---|---|---|
| `omg_id` | OMB `id` | str | Stable cross-year key; used for dedup across inventory vintages |
| `use_case_name` | OMB `use_case_name` | str | Human label |
| `agency` | OMB `agency` | str | OrgPath prefix (level 1) |
| `agency_name` | OMB `agency_name` | str | Human label |
| `agency_bureau` | OMB `agency_bureau` | str | OrgPath prefix (level 2) |
| `development_stage` | OMB `development_stage` | DevStage | Governs which records enter the live scan population |
| `agent_class` | OMB `classification` | AgentClass | `AGENTIC` triggers P1 path; others P2 |
| `operational_date` | OMB `operational_date` | str \| None | Staleness signal vs. registry |
| `ato_status` | OMB `have_ato` | ATOStatus | `NO` → `DRIFT-COMPLIANCE::ai-ato-gap` |
| `system_name_ato` | OMB `system_name_ato` | str \| None | UIAO registry join key; ATO reciprocity cross-walk |
| `vendor_name` | OMB `vendor_name` | str \| None | → KYC/NERM non-employee surface (ADR-055, ADR-059) |
| `contact_email` | OMB `contact_email` | str \| None | Owner identity anchor; blank → `DRIFT-IDENTITY::ai-unowned` |
| `has_pii` | OMB `has_pii` | bool | Triggers PIA check |
| `pia_url` | OMB `pia_url` | str \| None | `has_pii=True` + blank → `DRIFT-COMPLIANCE::ai-pii-no-pia` |
| `is_high_impact` | OMB `is_high_impact` | bool | Enables `hi_*` checklist evidence ingestion |
| `hi_*` (6 fields) | OMB `hi_*` | str \| None | Evidence targets reporting against M-25-21 §4(b)'s seven minimum risk-management practices; these six cover five of the seven (human training and public feedback have no inventory field) |
| `orgpath` | derived | str \| None | Populated from `agency + agency_bureau`; None → `DRIFT-IDENTITY::ai-no-orgpath` |

---

## 2. OrgPath Binding Rules

OrgPath for an AI system is derived from the OMB inventory's organisational
fields — the same way a device's OrgPath is derived from its managing bureau
in ADR-038.

```
orgpath = agency + ":" + agency_bureau   (when both are non-empty)
orgpath = agency                          (when bureau is blank or equals agency)
orgpath = None                            (when agency is blank → P2 finding)
```

The resulting prefix is a colon-separated namespace path (e.g., `DOD:DISA`)
that matches the first two levels of the OrgPath codebook (ADR-035, ADR-062).
The leaf level is the `system_name_ato` value; when absent, the `omg_id` is
used.

Full path example: `DOD:DISA::ACAS`

---

## 3. Live Population

Only `development_stage ∈ {deployed, pilot}` records enter the drift scan.
Pre-deployment, retired, and unknown-stage records are parsed and retained
in `ScanResult.records` for reference but do not generate findings.

This mirrors the OMB inventory's own "deployed and piloted" active population
of ~1,818 systems (2025 vintage).

---

## 4. Drift Finding Types

Six finding types, extending the ADR-012 taxonomy:

| Drift class | Severity | Posture | Trigger |
|---|---|---|---|
| `DRIFT-COMPLIANCE::ai-ato-gap` | P2 | NEVER_AUTOFIX | `ato_status = NO` for any live system |
| `DRIFT-IDENTITY::ai-no-orgpath` | P2 | PER_POLICY | `orgpath = None` (agency field blank) |
| `DRIFT-IDENTITY::ai-unowned` | P2 | NEVER_AUTOFIX | `contact_email = None` |
| `DRIFT-COMPLIANCE::ai-pii-no-pia` | P2 | NEVER_AUTOFIX | `has_pii = True` and `pia_url = None` |
| `DRIFT-IDENTITY::ai-shadow` | P1 | NEVER_AUTOFIX | UIAO registry entry absent from OMB inventory |
| `DRIFT-COMPLIANCE::ai-agentic-ungoverned` | P1 | NEVER_AUTOFIX | `agent_class = AGENTIC` and `ato_status ≠ YES` |

P1 findings trigger `halt_on_critical` in the drift gate (ADR-040): shadow AI
and ungoverned agentic systems block the live remediation pass. P2 findings
surface for operator disposition per the three-way promote/force/quarantine
model (ADR-074, ADR-092 §5).

---

## 5. Scanner Interface

```python
from uiao.governance.ai_inventory import scan_inventory

result = scan_inventory(
    "data/2025_individually_reported_AI_use_cases.csv",
    known_registry_ids={"ACAS", "ADVANA"},   # optional; enables shadow detection
)

print(result.summary())          # human-readable summary
print(result.to_json())          # ODR-compatible JSON for downstream evidence
for f in result.p1_findings:
    print(f.finding_id, f.drift_class, f.name)
```

The scanner is read-only (L1, observe). No writes. Promotion to L2 (advise)
or L3 (gated actuation) requires a governance-board decision per ADR-112 §3
and ADR-092.

---

## 6. Inventory Staleness

The OMB inventory is published annually. Between vintages the scanner is run
against the last-downloaded CSV. The `inventory_vintage` field in `ScanResult`
records the year; callers should log a staleness warning when the vintage is
more than 13 months old (OMB typically publishes Q1).

---

## 7. Shadow AI Detection

Shadow AI detection requires a `known_registry_ids` set — the collection of
`system_name_ato` values already in UIAO's machine-identity registry. When
supplied:

- Every registry ID absent from the OMB inventory → P1 `DRIFT-IDENTITY::ai-shadow`
- These are the most critical findings: systems acting inside the identity
  substrate that have evaded the M-25-21 reporting obligation

When `known_registry_ids=None`, shadow detection is skipped and the scanner
operates as a pure OMB inventory analyzer.

---

## 8. Evidence Produced

Each finding carries an `evidence_ref` tag for downstream OSCAL correlation:

| Evidence ref | NIST controls | Findings it traces |
|---|---|---|
| `omg-inventory` | IA-2, IA-4, AC-2, CA-7, CM-8 | ATO gap, no OrgPath, unowned, PII/PIA, agentic ungoverned |
| `uiao-registry` | CM-8, IA-2 | Shadow AI |

The `to_json()` method on `ScanResult` produces an ODR-compatible JSON payload
ready for ingestion by the evidence fabric (ADR-006, ADR-016).

---

## Appendix A — Spec copy retained per UIAO global rule

This spec is `UIAO_196` at version 1.0. Normative authority rests with
ADR-112. The Python implementation lives at:

```
src/uiao/governance/ai_inventory/
    __init__.py
    schema.py     — AISystemRecord, AgentClass, DevStage, ATOStatus
    drift.py      — drift class constants and Finding constructors
    scanner.py    — scan_inventory(), ScanResult
```
