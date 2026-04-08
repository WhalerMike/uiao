---
id: runtime-slo-sli-spec
title: Governance Runtime SLO/SLI Specification
owner: governance-steward
status: DRAFT
---

# UIAO Governance Runtime SLO/SLI Specification

## Service Levels for Drift Detection, SLA Enforcement, and Dashboard Accuracy

This specification defines the service level objectives (SLOs) and service level indicators (SLIs) for the governance runtime.

---

## 1. Purpose

To ensure the governance runtime operates predictably, reliably, and with minimal drift or downtime.

---

## 2. Core SLOs

### SLO 1 - Drift Detection Latency

Objective: 95% of drift events detected within 5 minutes
SLI: Time from GitHub event to DB entry

### SLO 2 - SLA Timer Accuracy

Objective: 99% accuracy in SLA timestamps
SLI: Difference between expected and actual SLA deadlines

### SLO 3 - Dashboard Freshness

Objective: Dashboard data < 5 minutes old
SLI: Timestamp of last API refresh

### SLO 4 - CI Validator Reliability

Objective: 99% accuracy (no false positives/negatives)
SLI: Validator error classification accuracy

### SLO 5 - Workflow Success Rate

Objective: 98% success rate for weekly drift workflow
SLI: Workflow run status

### SLO 6 - Webhook Handler Uptime

Objective: 99.5% uptime
SLI: Health check availability

---

## 3. Supporting SLIs

### Drift Volume SLI

Tracks weekly drift count.

### SLA Breach SLI

Tracks number of SLA breaches per week.

### Automation Drift SLI

Tracks automation failures (CI, webhook, dashboard).

---

## 4. Error Budgets

| SLO | Error Budget |
|------|--------------|
| Drift detection | 5% of events may exceed 5 minutes |
| SLA accuracy | 1% timestamp deviation allowed |
| Dashboard freshness | 5 minutes stale allowed |
| CI validator | 1% misclassification allowed |
| Workflow success | 2% failures allowed |
| Webhook uptime | 0.5% downtime allowed |

---

## 5. Governance Actions When Error Budgets Are Exceeded

- Trigger automation audit
- Freeze schema changes
- Increase monitoring
- Patch CI/webhook/dashboard
- Governance steward review
