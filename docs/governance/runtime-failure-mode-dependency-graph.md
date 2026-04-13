---
id: runtime-failure-mode-dependency-graph
title: Governance Runtime Failure-Mode Dependency Graph
owner: governance-steward
status: DRAFT
---

# UIAO Governance Runtime Failure-Mode Dependency Graph

## How Failures Propagate Across the Governance Runtime

---

## Mermaid Diagram

```mermaid
flowchart TD
    subgraph GitHub
        GH1[Issues]
        GH2[Pull Requests]
        GH3[CI Events]
        GH4[Workflow Triggers]
    end

    GH1 --> WH[Webhook Handler]
    GH2 --> WH
    GH3 --> CI[CI Validator]
    GH4 --> WF[Weekly Drift Workflow]

    WH --> API[Governance API]
    CI --> API
    WF --> API

    API --> DB[(PostgreSQL)]
    DB --> API
    API --> UI[Governance Dashboard]
```

---

## Failure Mode Annotations

### Webhook Handler Failure

- Event Loss: Missing SLA Updates
- Mislabeling: Wrong severity/SLA state applied

### CI Validator Failure

- Misclassification: Incorrect Drift Detection
- Outdated schema: Drift undetected

### Workflow Crash

- Undetected Drift: Weekly report missing

### DB Write Error

- SLA/Drift State Corruption

### Dashboard Stale Data

- Incorrect Governance Decisions

---

## ASCII Diagram

```
GitHub --> Webhook --> API --> DB --> Dashboard
     |--> CI --------^
     |--> Workflow --^

Failure Modes:
- Webhook loss       --> SLA timers wrong
- CI misclassify     --> Drift undetected or false drift
- Workflow crash     --> Weekly drift missing
- DB write failure   --> Corrupted SLA/drift state
- Dashboard stale    --> Incorrect governance decisions
```

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
