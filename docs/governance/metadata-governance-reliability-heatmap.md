---
id: metadata-governance-reliability-heatmap
title: "Metadata Governance Reliability Heatmap"
owner: governance-board
status: DRAFT
---

# UIAO Metadata Governance Reliability Heatmap

## Visualizing Reliability Across Owners, Appendices, and Drift Indicators

This heatmap highlights reliability strengths and weaknesses across the metadata governance ecosystem.

---

## 1. Purpose

To provide a visual, data-driven view of where metadata reliability risks are concentrated by owner and indicator, enabling targeted governance intervention.

---

## 2. Axes

### X-Axis: Owners

Sorted by:

1. Reliability score (ascending — lowest reliability leftmost)
2. SLA breaches (descending — most breaches left)
3. Drift velocity (descending — fastest drift left)

### Y-Axis: Reliability Indicators

- Metadata quality score
- Drift frequency
- Drift severity index
- Schema divergence
- Automation stability
- Owner reliability trend

---

## 3. Cell Value Formula

Each cell is scored as:

    CellValue = IndicatorValue x RiskWeight

Indicator weights:

| Indicator | Weight |
|-----------|--------|
| Drift frequency | 4 |
| Drift severity index | 4 |
| Schema divergence | 3 |
| Metadata quality score | 2 |
| Automation stability | 2 |
| Owner reliability trend | 5 |

---

## 4. Color Scale

| Cell Score | Color | Meaning |
|------------|-------|---------|
| 0-4 | #E8F5E9 (light green) | Healthy |
| 5-9 | #C8E6C9 (green) | Acceptable |
| 10-14 | #FFF9C4 (yellow) | Caution |
| 15-20 | #FFE082 (orange) | At risk |
| >20 | #FF8A80 (red) | Critical |

Override rule: Any cell where the owner has an active SLA breach is rendered #D32F2F (deep red) regardless of computed score.

---

## 5. Data Sources

- owner_reliability_snapshots: 30-day rolling owner reliability scores
- drift_events: All drift events with severity classification
- sla_timers: Active and resolved SLA timers per owner
- Schema version map: Current and expected schema versions per document
- Automation stability metrics: CI, webhook, and workflow uptime

---

## 6. Update Frequency

- Drift events: real-time
- SLA timers: real-time
- Owner reliability snapshots: daily
- Schema version map: on schema change
- Automation stability: every 5 minutes

---

## 7. Governance Actions

| Heatmap Signal | Action |
|----------------|--------|
| Owner column all red | Escalate to governance board for owner review |
| Drift frequency row all red | Trigger corpus-wide drift investigation |
| Schema divergence row elevated | Force schema normalization sprint |
| SLA breach override active | Open SLA remediation ticket immediately |
| Automation stability row red | Patch CI validator and workflows |
