---
id: reliability-score-decomposition-diagram
title: Governance Reliability Score Decomposition Diagram
owner: governance-steward
status: DRAFT
---

# UIAO Governance Reliability Score Decomposition Diagram

## Visual Breakdown of Owner Reliability Score Components

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
```

---

## ASCII Diagram

```
          Owner Reliability Score
      /        |         |         |         |
   TTA        TTR    SLA Breaches  CI Fail  Weekly Unacked
    |           |      /      |      |           |
 72h SLA    14d SLA  At-Risk Breach Accuracy  Backlog
```

---

## Component Definitions

### TTA - Time to Acknowledge

Measures how quickly owners acknowledge drift issues. Target: within 72 hours.

### TTR - Time to Remediate

Measures how quickly owners remediate acknowledged drift. Target: within 14 days for critical issues.

### SLA Breaches

Counts of at-risk and breached SLA items attributed to this owner.

### CI Failure Rate

Percentage of CI validator failures linked to documents owned by this owner.

### Weekly Unacknowledged Items

Backlog of unacknowledged drift items accumulated week-over-week.
