---
id: metadata-drift-heatmap-spec
title: Metadata Drift Heatmap Specification
owner: governance-steward
status: DRAFT
---

# UIAO Metadata Drift Heatmap Specification

## Canonical Visualization of Drift Severity, Frequency, and Owner Distribution

This specification defines the structure, color scale, and data sources for the metadata drift heatmap.

---

## 1. Purpose

To provide a high-resolution view of drift distribution across owners and severity levels.

---

## 2. Axes

### X-Axis - Owners

Sorted by: (1) Critical drift count, (2) SLA breaches, (3) Reliability score ascending

### Y-Axis - Severity Levels

- critical
- high
- medium
- low

---

## 3. Cell Value Formula

CellValue = DriftCount * SeverityWeight

Where: critical = 4, high = 3, medium = 2, low = 1

---

## 4. Color Scale

| Value | Color |
|--------|--------|
| 0 | #E8F5E9 (light green) |
| 1-5 | #C8E6C9 (green) |
| 6-10 | #FFF9C4 (yellow) |
| 11-20 | #FFE082 (orange) |
| >20 | #FF8A80 (red) |

Override: Any SLA breach -> #D32F2F (deep red) regardless of score.

---

## 5. Data Sources

- drift_events table
- sla_timers table
- owner_reliability_snapshots
- Dashboard API (/api/dashboard)

---

## 6. Update Frequency

- Drift events: real-time
- SLA overrides: real-time
- Heatmap recompute: every 5 minutes

---

## 7. Interactions

- Hover: show drift items + SLA timers
- Click: open owner detail panel
- Filters: severity, appendix, time range

---

## 8. Acceptance Criteria

- Deterministic color mapping
- SLA overrides always applied
- Owner sorting reproducible

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
