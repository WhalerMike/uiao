---
title: "19 Reconciliation Model"
author: "UIAO Modernization Program"
date: today
date-format: "MMMM D, YYYY"
format:
  html: default
  docx: default
  pdf: default
  gfm: default
---

# UIAO Federated Reconciliation & Conflict Resolution Model

**Document:** 19
**Phase:** 5 — Data Governance Substrate
**Version:** 1.0
**Status:** Draft
**Classification:** CUI/FOUO
**Date:** 2026-04-01

---

## 1. Purpose

The UIAO Reconciliation Model defines what happens when two or more Truth Sources disagree on the value of the same canonical claim. It transforms UIAO from a data pipeline into a **federated truth authority** — the first machine-readable conflict resolution framework for U.S. federal canonical data.

---

## 2. Conflict Classification

| Class | Code | Definition |
|---|---|---|
| Value Conflict | `CONFLICT-VALUE` | Two authoritative sources assert different values for the same claim |
| Temporal Conflict | `CONFLICT-TEMPORAL` | Two sources agree on value but disagree on timestamp (staleness) |
| Provenance Conflict | `CONFLICT-PROVENANCE` | Two sources assert the same value but lineage chains are incompatible |
| Jurisdiction Conflict | `CONFLICT-JURISDICTION` | Two agencies assert authority over the same claim domain |
| Consent Conflict | `CONFLICT-CONSENT` | A claim is transmitted with conflicting consent envelopes |

---

## 3. Confidence Scoring Model

Every claim in a conflict state receives a confidence score:

```
confidence_score = (source_authority_weight × 0.40)
                 + (recency_score × 0.30)
                 + (provenance_integrity_score × 0.20)
                 + (cross_validation_score × 0.10)
```

| Factor | Definition |
|---|---|
| `source_authority_weight` | Statutory or regulatory primacy of the Truth Source (0.0–1.0) |
| `recency_score` | Age of the claim relative to expected refresh cycle (0.0–1.0) |
| `provenance_integrity_score` | Lineage chain completeness and hash validity (0.0–1.0) |
| `cross_validation_score` | Agreement with independent third-party sources (0.0–1.0) |

A claim with `confidence_score >= 0.85` is auto-resolved to the higher-scoring source. Scores below 0.85 require human adjudication.

---

## 4. Conflict Resolution Workflow

1. **DETECT** — Conflict identified at adapter boundary or telemetry plane
2. **CLASSIFY** — Conflict class assigned (`CONFLICT-*`)
3. **SCORE** — Confidence scores computed for all conflicting claims
4. **ROUTE** — Score >= 0.85: auto-resolve | Score < 0.85: escalate
5. **ADJUDICATE** — Canon Steward or designated agency officer reviews
6. **RESOLVE** — Winning claim stamped with `RESOLVED` status and reconciliation metadata
7. **SUPERSEDE** — Losing claim marked `SUPERSEDED` with pointer to winning claim
8. **AUDIT** — Full conflict record written to telemetry plane and audit log

---

## 5. Reconciliation Record Schema

```yaml
reconciliation_record:
  conflict_id: "urn:uiao:conflict:{uuid}"
  conflict_class: "{CONFLICT-*}"
  claims_in_conflict:
    - claim_id: "{urn:uiao:claim:...}"
      source: "{agency_id}"
      confidence_score: 0.00–1.00
      resolution_status: "winner | loser | inconclusive"
  auto_resolved: true | false
  resolution_method: "auto | human_adjudication"
  adjudicator_identity: "{identity or null}"
  resolution_timestamp: "{ISO8601}"
  winning_claim_id: "{urn:uiao:claim:...}"
  superseded_claim_ids:
    - "{urn:uiao:claim:...}"
  reconciliation_rationale: "{free text}"
  audit_record_id: "{telemetry_event_id}"
```

---

## 6. Human Adjudication Triggers

Human adjudication is mandatory when:

- `confidence_score < 0.85` for any conflicting claim
- Conflict class is `CONFLICT-JURISDICTION`
- Conflict involves a claim used in an active legal, enforcement, or benefits determination
- Any conflicting source asserts `source_classification: authoritative`

---

## 7. Compliance Mapping

| NIST Control | Reconciliation Requirement |
|---|---|
| AU-3 (Audit Record Content) | `reconciliation_record` written to audit log |
| IR-4 (Incident Handling) | Conflict escalation and adjudication workflow |
| SA-9 (External System Services) | Source authority weights for external agency Truth Sources |
| PM-16 (Threat Awareness) | `CONFLICT-JURISDICTION` triggers as governance risk signals |

---

## 8. Cross-References

- `docs/15_ProvenanceProfile.md` — Provenance integrity scoring for conflicts
- `docs/16_DriftDetectionStandard.md` — Drift events that trigger reconciliation
- `docs/17_ConsentEnvelope.md` — Consent conflicts (CONFLICT-CONSENT)
- `docs/18_ClaimCatalog.md` — Claim versioning and supersession rules
- `docs/09_CrosswalkIndex.md` — Master crosswalk index

---

## 9. Revision History

| Version | Date | Author | Summary |
|---|---|---|---|
| 1.0 | 2026-04-01 | UIAO Canon Engine | Initial canonical release — Phase 5 Data Governance Substrate |
