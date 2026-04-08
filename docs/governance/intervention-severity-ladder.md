---
id: intervention-severity-ladder
title: Governance Intervention Severity Ladder
owner: governance-steward
status: DRAFT
---

# UIAO Governance Intervention Severity Ladder

## Canonical Escalation Levels for Drift, SLA Breaches, and Systemic Risk

This ladder defines the five levels of governance intervention, from minor drift correction to full systemic governance action.

---

## Level 1 - Advisory

Trigger:
- Low/medium drift
- No SLA risk

Actions:
- Owner notification
- Standard remediation PR
- No escalation

---

## Level 2 - Corrective

Trigger:
- Repeated drift
- SLA-at-risk
- CI validator failures

Actions:
- Owner coaching
- Required remediation plan
- Reliability score adjustment

---

## Level 3 - Escalation

Trigger:
- SLA-breached
- Critical drift unacknowledged
- Owner unresponsive

Actions:
- Governance steward intervention
- Ownership reassignment
- Mandatory training

---

## Level 4 - Systemic

Trigger:
- Drift clusters across appendices
- Schema divergence
- Automation drift

Actions:
- Schema update
- CI validator update
- Workflow update
- Systemic drift RCA

---

## Level 5 - Governance Emergency

Trigger:
- Widespread automation failure
- SLA system collapse
- Corpus-wide metadata corruption

Actions:
- Freeze merges
- Activate manual SLA enforcement
- Full runtime audit
- Executive notification
