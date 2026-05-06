---
id: risk-early-warning-model
title: Governance Risk Early-Warning Scoring Model
owner: governance-steward
status: DRAFT
---

# UIAO Governance Risk Early-Warning Scoring Model

## Predictive Risk Scoring for Drift, SLA Breaches, and Systemic Failures

This model provides a quantitative early-warning signal for governance risk across owners, appendices, and the entire corpus.

---

## 1. Purpose

To detect governance risk before SLA breaches, systemic drift, or automation failures occur.

---

## 2. Inputs

### A. Drift Velocity (DV)

Rate of new drift items per week.

### B. Drift Severity Index (DSI)

Weighted severity score:

DSI = 4C + 3H + 2M + 1L

### C. SLA Pressure (SLAP)

Percentage of items currently in sla-at-risk.

### D. Owner Reliability Trend (ORT)

30-day slope of reliability score.

### E. Automation Stability (AS)

Workflow success rate, CI accuracy, webhook uptime.

---

## 3. Normalization

DV_n = min(1, DV / 10)

DSI_n = min(1, DSI / 20)

SLAP_n = SLAP

ORT_n = max(0, 1 - ORT/20)

AS_n = 1 - AS

---

## 4. Weighted Formula

RiskScore = 100 * (
  0.30 * DV_n +
  0.25 * DSI_n +
  0.20 * SLAP_n +
  0.15 * ORT_n +
  0.10 * AS_n
)

---

## 5. Interpretation

| Score | Meaning |
|-------|---------|
| 0-29 | Low risk |
| 30-59 | Moderate risk |
| 60-79 | High risk |
| 80-100 | Critical governance risk |

---

## 6. Governance Actions by Tier

### Moderate (30-59)

- Increase monitoring
- Notify owners

### High (60-79)

- Governance steward review
- Schema/CI evaluation

### Critical (80-100)

- Immediate governance intervention
- Systemic drift investigation
- Automation audit

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
