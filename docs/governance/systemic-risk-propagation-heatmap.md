---
id: systemic-risk-propagation-heatmap
title: Governance Systemic-Risk Propagation Heatmap
owner: governance-steward
status: DRAFT
---

# UIAO Governance Systemic-Risk Propagation Heatmap

## Visualizing How Governance Risk Spreads Across Owners, Appendices, and Drift Types

This heatmap models how systemic governance risk propagates across the corpus based on drift clustering, SLA stress, schema divergence, and automation instability.

---

## 1. Axes

### X-Axis - Appendices

Sorted by: (1) Drift density, (2) Schema divergence, (3) Owner reliability

### Y-Axis - Propagation Factors

- Structural coupling
- Referential coupling
- Ownership coupling
- Automation coupling
- Schema divergence
- SLA stress

---

## 2. Cell Value Formula

PropagationRisk = FactorWeight * NormalizedValue

Where:
- Structural coupling = 4
- Referential coupling = 3
- Ownership coupling = 2
- Automation coupling = 3
- Schema divergence = 4
- SLA stress = 5

---

## 3. Color Scale

| Score | Color |
|--------|--------|
| 0-4 | #E8F5E9 (light green) |
| 5-9 | #C8E6C9 (green) |
| 10-14 | #FFF9C4 (yellow) |
| 15-20 | #FFE082 (orange) |
| >20 | #FF8A80 (red) |

Override: Any appendix with >= 2 systemic drift clusters -> #D32F2F (deep red).

---

## 4. Data Sources

- Drift clustering engine
- drift_events
- sla_timers
- owner_reliability_snapshots
- Schema version map
- Automation stability metrics

---

## 5. Update Frequency

- Propagation factors: hourly
- SLA stress: real-time
- Schema divergence: daily

---

## 6. Interactions

- Hover: show propagation factors
- Click: open appendix detail panel
- Filters: drift type, owner, time range
