---
id: systemic-risk-forecasting-model
title: Governance Systemic-Risk Forecasting Model
owner: governance-steward
status: DRAFT
---

# UIAO Governance Systemic-Risk Forecasting Model

## Predictive Model for Anticipating Structural Governance Failures

This model forecasts the likelihood of systemic governance risk across the corpus by combining drift clustering, SLA pressure, automation stability, and metadata quality signals.

---

## 1. Purpose

To predict systemic governance failures before they occur, enabling proactive intervention.

---

## 2. Inputs

### A. Drift Cluster Density (DCD)

Number and size of drift clusters detected in the last 30 days.

### B. Cross-Appendix Correlation (CAC)

Percentage of drift patterns shared across 2 or more appendices.

### C. SLA Stress Index (SSI)

Weighted measure of sla-at-risk and sla-breached items.

### D. Automation Stability Score (ASS)

CI accuracy, webhook uptime, workflow success rate.

### E. Schema Divergence Ratio (SDR)

Percentage of documents not aligned with current schema version.

### F. Metadata Quality Score (MQS)

Average metadata quality across affected appendices.

---

## 3. Normalization

DCD_n = min(1, DCD / 10)
CAC_n = CAC
SSI_n = SSI
ASS_n = 1 - ASS
SDR_n = SDR
MQS_n = 1 - (MQS / 100)

---

## 4. Weighted Formula

SystemicRisk = 100 * (
  0.25 * DCD_n +
  0.20 * CAC_n +
  0.20 * SSI_n +
  0.15 * ASS_n +
  0.10 * SDR_n +
  0.10 * MQS_n
)

---

## 5. Interpretation

| Score | Meaning |
|-------|---------|
| 0-29 | Low systemic risk |
| 30-59 | Moderate systemic risk |
| 60-79 | High systemic risk |
| 80-100 | Critical systemic risk |

---

## 6. Governance Actions

### Moderate (30-59)

- Increase monitoring
- Review schema alignment

### High (60-79)

- Governance steward review
- CI + workflow evaluation

### Critical (80-100)

- Immediate governance intervention
- Systemic drift RCA
- Schema/CI/workflow updates

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
