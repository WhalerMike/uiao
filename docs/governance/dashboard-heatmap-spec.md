---
id: governance-dashboard-heatmap-spec
title: "UIAO Governance Dashboard -- SLA Heatmap Specification"
owner: governance-team
status: DRAFT
---

# UIAO Governance Dashboard -- SLA Heatmap Specification

This heatmap visualizes SLA performance across owners, appendices, and severity levels.

---

## 1. Purpose

Provide a single-glance view of SLA health across the corpus, enabling governance to identify:
- At-risk owners
- Systemic drift patterns
- Severity clusters
- SLA breach hotspots

---

## 2. Heatmap Axes

**X-Axis -- Owners:** Sorted by (1) number of critical items, (2) SLA breach count,
(3) owner reliability score (ascending = most at-risk first).

**Y-Axis -- Severity Levels:** critical, high, medium, low.

---

## 3. Cell Values

Each cell represents the count of drift items for an owner at a given severity level.

Cell also displays: % acknowledged within SLA, % remediated within SLA, average TTA, average TTR.

---

## 4. Color Scale

| Value | Color |
|-------|--------|
| 0 | Green-light (#E8F5E9) |
| 1-3 | Green (#C8E6C9) |
| 4-6 | Yellow (#FFF9C4) |
| 7-10 | Orange (#FFE082) |
| >10 | Red (#FF8A80) |

SLA breach cells override color to deep red (#D32F2F) regardless of count.

---

## 5. Interactions

**Hover:** Shows document list, drift types, SLA timers, links to remediation PRs.

**Click:** Opens owner detail panel with severity-filtered document list and SLA history chart.

---

## 6. Data Sources

- `reports/metadata-drift-*.json`
- CI validator logs
- Issue labels: `sla-at-risk`, `sla-breached`, etc.
- Owner reliability score (see `owner-reliability-score.md`)

---

## 7. Acceptance Criteria

- Heatmap updates within 5 minutes of new drift detection.
- SLA breach cells always override severity color.
- Owner sorting deterministic and reproducible.
- All interactions resolve to canonical dashboard views.
