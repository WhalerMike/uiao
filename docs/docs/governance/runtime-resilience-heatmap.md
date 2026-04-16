---
id: runtime-resilience-heatmap
title: "Governance Runtime Resilience Heatmap"
owner: governance-board
status: DRAFT
---

# UIAO Governance Runtime Resilience Heatmap

## Heatmap of Resilience Across Runtime Components and Resilience Factors

This heatmap visualizes how resilient each runtime component is across key resilience dimensions.

---

## 1. Purpose

To give governance operators a structured, color-coded view of resilience gaps across the runtime stack, enabling targeted hardening investments.

---

## 2. Axes

### X-Axis: Runtime Components

| Component | Description |
|-----------|-------------|
| CI validator | GitHub Actions CI lint and schema validation |
| Webhook handler | GitHub webhook event ingestion service |
| Weekly drift workflow | Scheduled drift detection and reporting workflow |
| Governance API | REST API serving governance data |
| PostgreSQL | Governance data store |
| Dashboard | MkDocs-based governance documentation site |

### Y-Axis: Resilience Factors

| Factor | Symbol | Description |
|--------|--------|-------------|
| Redundancy | R | Number of redundant instances or replicas |
| Fault isolation | FI | Degree to which failures are contained |
| Recovery time | RT | Mean time to recover from failure (inverted: lower is better) |
| Failure impact | FI2 | Blast radius of component failure (inverted: lower is better) |
| Observability coverage | OC | Percentage of failure modes covered by monitoring |
| Chaos-resilience | CR | Pass rate on chaos engineering test suite |

---

## 3. Cell Value Formula

Each cell is a normalized score in [0, 1]:

    ResilienceFactorScore = NormalizedFactorValue

For RT (recovery time) and FI2 (failure impact), the score is inverted:

    Score = 1 - NormalizedValue

So that higher scores always mean better resilience across all factors.

---

## 4. Color Scale

| Score Range | Color | Meaning |
|-------------|-------|---------|
| 0.0-0.2 | #FF8A80 (red) | Critical resilience gap |
| 0.2-0.4 | #FFE082 (orange) | Significant gap |
| 0.4-0.6 | #FFF9C4 (yellow) | Moderate gap |
| 0.6-0.8 | #C8E6C9 (green) | Acceptable |
| 0.8-1.0 | #A5D6A7 (dark green) | Strong resilience |

---

## 5. Data Sources

- Chaos-engineering test results from runtime chaos test plan
- Incident and recovery logs from governance API and CI systems
- Observability coverage inventory (monitoring, alerting, tracing)
- Runtime configuration documentation (redundancy, fault isolation design)

---

## 6. Update Frequency

| Data Source | Refresh Rate |
|-------------|--------------|
| Chaos test results | After each test run |
| Incident logs | Real-time |
| Observability coverage | On infrastructure change |
| Runtime configuration | On deployment |

---

## 7. Interactions

| Interaction | Result |
|-------------|--------|
| Hover cell | Show factor details and last chaos test result |
| Click component | Open component resilience report |
| Filter environment | Toggle dev, stage, prod views |
| Filter time range | Show resilience trend over selected period |

---

## 8. Governance Actions

| Heatmap Signal | Action |
|----------------|--------|
| CI validator row red | Harden CI validator redundancy and fault isolation |
| Webhook handler RT red | Improve webhook handler recovery procedures |
| PostgreSQL FI2 red | Add read replicas and failover configuration |
| Any component CR < 0.6 | Schedule targeted chaos engineering sprint |
| Full column red | Escalate to governance board for infrastructure review |

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
