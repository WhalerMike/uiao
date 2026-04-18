---
id: metadata-drift-propagation-heatmap
title: Metadata Drift Propagation Heatmap
owner: governance-steward
status: DRAFT
---

# UIAO Metadata Drift Propagation Heatmap

## Visualizing How Drift Spreads Across the Corpus

This heatmap models how metadata drift propagates across appendices, owners, and drift types based on structural, referential, and automation coupling.

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

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
