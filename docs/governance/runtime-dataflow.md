---
id: governance-runtime-dataflow
title: "UIAO Governance Runtime -- Data Flow Reference"
owner: governance-team
status: DRAFT
---

# UIAO Governance Runtime -- Data Flow Reference

This document defines how governance data moves between components.
For component architecture see `runtime-architecture.md`.

---

## 1. Drift Detected

1. Weekly workflow or CI detects metadata drift.
2. Webhook handler receives GitHub issue event.
3. Handler writes drift event to `drift_events` table with severity + timestamp.
4. Handler applies labels (`metadata-drift`, `<severity>`, `needs-owner-ack`).
5. Handler creates SLA timer entry in `sla_timers` table.
6. API aggregates updated corpus index.
7. Dashboard displays updated state within 5 minutes.

---

## 2. SLA Timer Expiry

1. Webhook cron job (runs hourly) queries `sla_timers` table.
2. For items with acknowledgment_due_at exceeded: adds `sla-at-risk` (48h) or `sla-breached` (72h) label.
3. Updates `sla_ack_breached` flag in database.
4. Fires `sla_breach` webhook event to Slack/Teams.
5. Tags governance team on GitHub issue.
6. API exposes updated SLA metrics.
7. Dashboard heatmap highlights breached cells in deep red.

---

## 3. Remediation PR Opened

1. Owner opens PR linked to drift issue.
2. Webhook detects `pull_request.opened` event.
3. Handler adds `remediation-in-progress` label to issue.
4. PR linked to issue in GitHub Projects.
5. API moves item to Remediation In Progress state.
6. Dashboard updates item status.

---

## 4. Remediation Complete

1. PR is merged.
2. Webhook detects `pull_request.closed` with `merged: true`.
3. Handler adds `remediation-complete` label.
4. Updates `remediated_at` timestamp in `sla_timers` table.
5. Weekly workflow confirms closure in next run.
6. Dashboard marks item resolved.
7. Owner reliability snapshot updated.

---

## 5. Weekly Report Published

1. Weekly workflow runs (Monday 09:00 UTC or `workflow_dispatch`).
2. Drift scan script queries all markdown files for metadata issues.
3. Report written to `reports/metadata-drift-YYYY-MM-DD.json`.
4. GitHub issue created with weekly summary.
5. Webhook fires `weekly_report_published` event.
6. API updates weekly reports list.
7. Dashboard weekly reports view refreshes.
