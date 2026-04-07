---
id: governance-runtime-architecture
title: "UIAO Governance Runtime -- Architecture Reference"
owner: governance-team
status: DRAFT
---

# UIAO Governance Runtime -- Architecture Reference

## 1. Overview

The governance runtime is a three-tier system:

```
GitHub --> Webhook Handler --> Governance API --> Dashboard UI
                           --> PostgreSQL (state)
```

Each component has a deterministic role:

### A. Webhook Handler

- Receives GitHub events (issues, PRs, workflow runs)
- Applies labels, SLA logic, and state transitions
- Writes events + SLA timestamps to PostgreSQL
- Triggers downstream notifications (Slack/Teams)

### B. Governance API

Aggregates: drift reports, issue labels, PR metadata, SLA metrics, owner reliability scores.
Serves the Dashboard JSON API contract.
Provides a stable contract for the frontend.

### C. Dashboard

Renders: corpus index, SLA heatmap, drift items, weekly reports, reliability scores.
Calls API every 30-60 seconds.

### D. PostgreSQL

Stores: drift events, SLA timestamps, owner reliability snapshots, weekly report summaries, governance interventions.

---

## 2. Directory Structure

```
governance-runtime/
|
|-- docker-compose.yml
|
|-- webhook/
|   |-- Dockerfile
|   '-- uiao-governance-webhook.js
|
|-- api/
|   |-- Dockerfile
|   '-- uiao-governance-api.js
|
'-- dashboard/
    |-- Dockerfile
    '-- src/
        '-- components/
            '-- GovernanceDashboard.tsx
```

---

## 3. Data Flow

### Drift Detected

Webhook receives event -> Writes event to DB -> API exposes updated corpus index ->
Dashboard updates within 5 minutes.

### SLA Timer

Webhook cron job checks DB -> Adds sla-at-risk or sla-breached -> API exposes updated SLA metrics ->
Dashboard heatmap updates.

### Remediation PR

Webhook detects PR merge -> Marks issue as remediation-complete -> API updates corpus ->
Dashboard marks item resolved.

---

## 4. Health Checks

| Component | Endpoint | Expected Response |
|-----------|---------|-------------------|
| Webhook | GET /health | { "status": "ok" } |
| API | GET /api/health | { "status": "ok" } |
| Dashboard | GET / | Static HTML (200) |
| Database | pg_isready | Responds on port 5432 |

---

## 5. Acceptance Criteria

- Webhook receives GitHub events and writes to DB.
- API returns valid JSON matching the dashboard schema.
- Dashboard renders corpus index and SLA heatmap.
- Drift -> SLA -> Remediation -> Resolution flows visible end-to-end.
- All components pass health checks.
