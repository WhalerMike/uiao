---
id: metadata-governance-reliability-index
title: Metadata Governance Reliability Index (MG-RI)
owner: governance-steward
status: DRAFT
---

# UIAO Metadata Governance Reliability Index (MG-RI)

## Composite Score for Metadata Stability, Drift Resistance, and Governance Health

MG-RI measures the reliability of metadata governance across the corpus.

---

## 1. Inputs

### A. Metadata Quality Score (MQS)

0-100 scale.

### B. Drift Frequency (DF)

Drift events per 30 days.

### C. Drift Severity Index (DSI)

Weighted severity: DSI = 4C + 3H + 2M + 1L

### D. SLA Compliance (SLA)

1 = no breaches, 0.5 = at-risk, 0 = breached

### E. Automation Stability (AS)

CI + webhook + workflow uptime.

---

## 2. Normalization

DF_n = max(0, 1 - DF/10)
DSI_n = max(0, 1 - DSI/20)
AS_n = AS
MQS_n = MQS/100

---

## 3. Weighted Formula

MG-RI = 100 * (
  0.30 * MQS_n +
  0.25 * DF_n +
  0.20 * DSI_n +
  0.15 * SLA +
  0.10 * AS_n
)

---

## 4. Interpretation

| Score | Meaning |
|-------|---------|
| 90-100 | Excellent governance reliability |
| 75-89 | Strong, stable governance |
| 60-74 | Moderate, needs improvement |
| 40-59 | At risk |
| <40 | Critical governance concern |

---

## 5. Use Cases

- Quarterly governance review
- Systemic drift forecasting
- Owner coaching
- Schema evolution planning
- Automation tuning
