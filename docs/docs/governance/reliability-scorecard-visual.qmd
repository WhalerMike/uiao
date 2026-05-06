---
id: reliability-scorecard-visual
title: Governance Reliability Scorecard (Visual)
owner: governance-steward
status: DRAFT
---

# UIAO Governance Reliability Scorecard (Visual)

## Visual Representation of Owner Reliability Score Components

---

## Mermaid Diagram

```mermaid
flowchart TD
    A[Owner Reliability Score] --> B[TTA Time-to-Acknowledge]
    A --> C[TTR Time-to-Remediate]
    A --> D[SLA Breaches]
    A --> E[CI Failure Rate]
    A --> F[Weekly Unacknowledged Items]
    B --> B1[72h SLA Compliance]
    C --> C1[14d SLA Compliance]
    D --> D1[At-Risk Count]
    D --> D2[Breached Count]
    E --> E1[Validator Accuracy]
    F --> F1[Backlog Size]

    style A fill:#0d47a1,stroke:#fff,color:#fff
    style B fill:#1976d2,stroke:#fff,color:#fff
    style C fill:#1976d2,stroke:#fff,color:#fff
    style D fill:#1976d2,stroke:#fff,color:#fff
    style E fill:#1976d2,stroke:#fff,color:#fff
    style F fill:#1976d2,stroke:#fff,color:#fff
```

---

## ASCII Scorecard

```
+---------------------------+
| OWNER RELIABILITY SCORE   |
+------+------+-------+-----+------+
|  TTA |  TTR |  SLA  |  CI | Unack|
|      |      |Breach | Fail|Items |
+------+------+-------+-----+------+
| 72h  | 14d  |At-Risk|Accur|Backlog
| SLA  | SLA  |Breach |     |      |
+------+------+-------+-----+------+
```

---

## Scoring Rules

| Component | Weight | Green | Yellow | Red |
|-----------|--------|-------|--------|-----|
| TTA (72h) | 25% | >95% | 80-95% | <80% |
| TTR (14d) | 25% | >90% | 75-90% | <75% |
| SLA At-Risk | 20% | 0 | 1-2 | >2 |
| SLA Breached | 20% | 0 | 1 | >1 |
| CI Failures | 5% | <1% | 1-3% | >3% |
| Unacked Items | 5% | 0 | 1-3 | >3 |

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
