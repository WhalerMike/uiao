---
id: governance-owner-reliability-score
title: "UIAO Governance -- Owner Reliability Scoring Algorithm"
owner: governance-team
status: DRAFT
---

# UIAO Governance -- Owner Reliability Scoring Algorithm

This algorithm produces a single numeric score (0-100) representing an owner's governance reliability.
It is the authoritative formula for the dashboard heatmap and quarterly governance reviews.

---

## 1. Input Variables

| Variable | Definition |
|---------|-----------|
| TTA | Average Time-to-Acknowledge (hours) |
| TTR | Average Time-to-Remediate (days) |
| B | Number of SLA breaches in last 90 days |
| R | Number of repeated CI failures |
| W | Number of weekly reports with unacknowledged items |

---

## 2. Normalization

Each variable is normalized to a 0.0-1.0 range (1.0 = perfect, 0.0 = worst):

- TTA_n = max(0, 1 - TTA / 72)
- TTR_n = max(0, 1 - TTR / 14)
- B_n   = max(0, 1 - B / 5)
- R_n   = max(0, 1 - R / 10)
- W_n   = max(0, 1 - W / 6)

---

## 3. Weighted Score Formula

Score = 100 x (0.30 x TTA_n + 0.30 x TTR_n + 0.20 x B_n + 0.10 x R_n + 0.10 x W_n)

---

## 4. Score Interpretation

| Score | Meaning |
|-------|---------|
| 90-100 | Exemplary governance reliability |
| 75-89 | Strong, consistent performance |
| 60-74 | Acceptable but needs improvement |
| 40-59 | At-risk owner |
| < 40 | Governance intervention required |

---

## 5. Usage

- Dashboard heatmap sorts owners by score (ascending = most at-risk first).
- Quarterly governance reviews use score trends to identify systemic issues.
- Scores below 40 trigger governance-review label on all open items.
- Scores are snapshots -- recalculated weekly from the drift database.

---

## 6. Governance Reporting Metrics (Auto-Derived)

- **TTA (Time to Acknowledge):** Derived from needs-owner-ack -> acknowledgment timestamp.
- **TTR (Time to Remediate):** Derived from issue creation -> PR merge timestamp.
- **SLA Breach Rate:** Count of issues with sla-breached label per milestone.
- **Owner Reliability Score:** Computed weekly; stored in `owner_reliability_snapshots` table.
- **Systemic Drift Index:** Number of items entering governance-review per quarter.

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
