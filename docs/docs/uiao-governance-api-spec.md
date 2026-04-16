---
id: uiao-governance-api-spec
title: "UIAO Governance OS API Specification"
owner: governance-board
status: DRAFT
---

# UIAO Governance OS API Specification

## Machine-to-Machine Governance Integration

This specification defines the machine interfaces for interacting with the UIAO Governance OS.

---

## 1. API Overview

The UIAO Governance API exposes machine-trackable governance primitives for:

- Drift events and clusters
- SLA timers and acknowledgements
- Schema versions and divergence metrics
- Owner reliability scores
- Automation stability metrics
- Systemic-risk scores and propagation vectors
- Normalization violations and enforcement actions

---

## 2. Base URL

    /api/governance/v1/

All endpoints are versioned. Breaking changes increment the version number.

---

## 3. Endpoints

### 3.1 Drift

#### GET /drift/events

Returns all drift events with severity, owner, appendix, and timestamp.

Response fields: id, document_id, owner, appendix, severity, type, detected_at, resolved_at, status

#### GET /drift/clusters

Returns identified drift clusters with propagation vectors and affected document lists.

Response fields: cluster_id, seed_document, affected_documents, propagation_path, cluster_severity, detected_at

---

### 3.2 SLA

#### GET /sla/timers

Returns SLA timers for all owners and documents with current state.

Response fields: timer_id, document_id, owner, drift_event_id, sla_deadline, status, breach_at

#### POST /sla/acknowledge

Acknowledges drift or SLA events, recording the acknowledgement timestamp and actor.

Request fields: timer_id, actor, acknowledgement_note

---

### 3.3 Schema

#### GET /schema/version

Returns current canonical schema version and version history.

Response fields: current_version, previous_version, changed_at, changed_by, changelog_url

#### GET /schema/divergence

Returns schema divergence metrics across the corpus.

Response fields: divergence_rate, diverging_documents, deprecated_fields_present, version_fragmentation_index

---

### 3.4 Metadata Quality

#### GET /quality/score

Returns the current Metadata Quality Score (MQS) at corpus, appendix, and document level.

Response fields: corpus_mqs, appendix_scores, document_scores, computed_at

#### GET /quality/reliability

Returns MG-RI and DG-RI at corpus, appendix, owner, and document level.

Response fields: mg_ri, dg_ri, components, computed_at

---

### 3.5 Systemic-Risk

#### GET /risk/systemic

Returns the current systemic-risk score with contributing factors.

Response fields: systemic_risk_score, drift_pressure, sla_cascade_pressure, schema_divergence, automation_instability, computed_at

#### GET /risk/propagation

Returns propagation probabilities and vectors for current drift set.

Response fields: propagation_probabilities, propagation_vectors, at_risk_documents, cascade_forecast

---

### 3.6 Normalization

#### GET /normalization/violations

Returns all active normalization violations by type and severity.

Response fields: violation_id, document_id, type, severity, detected_at, status, remediation_action

#### POST /normalization/autofix

Triggers automated remediation for Low severity violations.

Request fields: violation_ids (array), actor

Response fields: fixed_count, skipped_count, fix_details

---

### 3.7 Automation

#### GET /automation/stability

Returns CI validator, webhook handler, and workflow stability metrics.

Response fields: ci_stability, webhook_stability, workflow_stability, composite_stability, computed_at

---

## 4. Response Format

All responses follow:

    {
      "status": "ok",
      "timestamp": "ISO-8601",
      "version": "v1",
      "data": {}
    }

Error responses:

    {
      "status": "error",
      "timestamp": "ISO-8601",
      "error_code": "GOV-XXX",
      "message": "Human-readable description"
    }

---

## 5. Authentication

Token-based authentication scoped to governance domains:

- read:drift - read drift events and clusters
- read:sla - read SLA timers
- write:sla - acknowledge SLA events
- read:schema - read schema version and divergence
- read:quality - read MQS and MG-RI
- read:risk - read systemic-risk scores
- read:normalization - read violations
- write:normalization - trigger autofix
- read:automation - read automation stability

---

## 6. Rate Limits

- Read endpoints: 1000 requests per minute per token
- Write endpoints: 100 requests per minute per token
- Bulk endpoints: 10 requests per minute per token

All limits are governance-domain scoped and configurable.

---

## 7. Error Codes

| Code | Meaning |
|------|---------|
| GOV-001 | Invalid schema version |
| GOV-002 | Drift event malformed |
| GOV-003 | SLA timer not found |
| GOV-004 | Automation instability above threshold |
| GOV-005 | Systemic-risk threshold exceeded |
| GOV-006 | Unauthorized scope for operation |
| GOV-007 | Autofix not applicable (severity not Low) |
| GOV-008 | Normalization violation not found |

---

## 8. Governance Guarantees

- Deterministic responses: same input always produces same output
- Provenance-aligned data: all responses include source traceability
- Zero silent failures: all errors return structured GOV error codes
- Audit trail: all write operations are logged with actor and timestamp

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
