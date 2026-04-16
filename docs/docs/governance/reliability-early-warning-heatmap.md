---
id: reliability-early-warning-heatmap
title: Governance Reliability Early-Warning Heatmap
owner: governance-steward
status: DRAFT
---

# UIAO Governance Reliability Early-Warning Heatmap

## Visualizing Reliability Risk Across Owners and Drift Indicators

This heatmap highlights owners at risk of reliability degradation based on predictive indicators.

---

## 1. Axes

### X-Axis - Owners

Sorted by: (1) Reliability score ascending, (2) SLA breaches, (3) Drift velocity

### Y-Axis - Early-Warning Indicators

- Drift velocity
- SLA pressure
- CI failure rate
- Metadata quality score
- Automation stability
- Reliability trend slope

---

## 2. Cell Value Formula

CellValue = IndicatorValue * RiskWeight

Where:
- Drift velocity = 4
- SLA pressure = 4
- CI failure rate = 3
- Metadata quality = 2
- Automation stability = 2
- Trend slope = 5

---

## 3. Color Scale

| Score | Color |
|--------|--------|
| 0-3 | #E8F5E9 (light green) |
| 4-7 | #C8E6C9 (green) |
| 8-12 | #FFF9C4 (yellow) |
| 13-18 | #FFE082 (orange) |
| >18 | #FF8A80 (red) |

Override: Any SLA breach -> #D32F2F (deep red).

---

## 4. Data Sources

- owner_reliability_snapshots
- drift_events
- sla_timers
- CI logs
- Webhook logs
- Dashboard API

---

## 5. Update Frequency

- Real-time for SLA
- Hourly for drift velocity
- Daily for reliability trend

---

## 6. Interactions

- Hover: show indicator values
- Click: open owner detail panel
- Filters: appendix, severity, time range

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
