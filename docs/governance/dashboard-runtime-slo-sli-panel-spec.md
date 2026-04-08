---
id: dashboard-runtime-slo-sli-panel-spec
title: Governance Runtime SLO/SLI Dashboard Panel Specification
owner: governance-steward
status: DRAFT
---

# UIAO Governance Runtime SLO/SLI Dashboard Panel

## Specification for Monitoring Drift Detection, SLA Accuracy, and Automation Health

This panel visualizes runtime performance against governance SLOs and SLIs, enabling stewards to detect automation drift and runtime instability early.

---

## 1. Purpose

To provide a real-time, authoritative view of governance runtime health across drift detection latency, SLA timer accuracy, dashboard freshness, CI validator reliability, workflow success rate, and webhook uptime.

---

## 2. Panel Components

### A. Drift Detection Latency Gauge

- SLO: 95% < 5 minutes
- SLI: median + p95 latency
- Color coding: green/yellow/red

### B. SLA Timer Accuracy Meter

- SLO: 99% accuracy
- SLI: timestamp deviation
- Alerts: >1% deviation

### C. Dashboard Freshness Indicator

- SLO: <5 minutes stale
- SLI: last refresh timestamp
- Overrides: stale >10 minutes -> red

### D. CI Validator Reliability

- SLO: 99% accuracy
- SLI: false positive/negative rate
- Trendline: 30-day

### E. Workflow Success Rate

- SLO: 98%
- SLI: workflow run status
- Alerts: failure -> immediate red

### F. Webhook Uptime

- SLO: 99.5%
- SLI: health check availability
- Alerts: downtime >5 minutes

---

## 3. Update Frequency

- Drift latency: real-time
- SLA accuracy: real-time
- Dashboard freshness: every 60 seconds
- CI reliability: hourly
- Workflow success: per run
- Webhook uptime: every 30 seconds

---

## 4. Interactions

- Hover: show raw metrics
- Click: open component detail panel
- Filters: time range, appendix, owner

---

## 5. Acceptance Criteria

- No stale data >5 minutes
- Deterministic color mapping
- All values traceable to DB or API
