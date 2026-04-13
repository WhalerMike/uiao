---
id: metadata-drift-resilience-index
title: Metadata Governance Drift-Resilience Index (DG-RI)
owner: governance-steward
status: DRAFT
---

# UIAO Metadata Governance Drift-Resilience Index (DG-RI)

## Composite Score for Metadata Stability, Drift Resistance, and Governance Robustness

DG-RI measures how resilient metadata is to drift, schema changes, and automation instability.

---

## 1. Inputs

### A. Metadata Quality Score (MQS)

0-100 scale.

### B. Drift Frequency (DF)

Drift events per 30 days.

### C. Drift Severity Index (DSI)

Weighted severity: DSI = 4C + 3H + 2M + 1L

### D. Schema Divergence (SDR)

Percentage of documents not aligned with current schema.

### E. Automation Stability (AS)

CI + webhook + workflow uptime.

### F. Owner Reliability (OR)

30-day reliability trend.

---

## 2. Normalization

DF_n = max(0, 1 - DF/10)
DSI_n = max(0, 1 - DSI/20)
SDR_n = 1 - SDR
AS_n = AS
OR_n = OR/100

---

## 3. Weighted Formula

DG-RI = 100 * (
  0.25 * MQS_n +
  0.20 * DF_n +
  0.20 * DSI_n +
  0.15 * SDR_n +
  0.10 * AS_n +
  0.10 * OR_n
)

---

## 4. Interpretation

| Score | Meaning |
|-------|---------|
| 90-100 | Highly drift-resilient |
| 75-89 | Strong resilience |
| 60-74 | Moderate resilience |
| 40-59 | At risk |
| <40 | Drift-prone |

---

## 5. Use Cases

- Drift forecasting
- Owner coaching
- Schema evolution planning
- Automation tuning
- Quarterly governance review

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
