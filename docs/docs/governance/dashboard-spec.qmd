---
id: governance-dashboard-spec
title: "UIAO Governance Dashboard -- Owner Notification Layer Specification"
owner: governance-team
status: DRAFT
---

# Governance Dashboard Specification -- Owner Notification Layer

This specification defines the notification and visibility model for metadata governance operations.

---

## 1. Purpose

Provide maintainers, appendix owners, and governance reviewers with a real-time view of:

- Drift status
- Owner responsibilities
- Aging issues
- Weekly report outcomes
- Required remediation actions

---

## 2. Core Dashboard Components

### A. Corpus Index Table

Columns: Document ID, Title, Owner, Status (current / needs remediation / missing metadata),
Last Updated, Drift Severity (none / low / medium / critical), Actions (open remediation PR, view drift details).

### B. Owner Notification Panel

For each owner: documents assigned, open drift items, aging >72 hours,
remediation PRs awaiting review, escalations pending governance.

### C. Weekly Report Integration

Link to latest weekly drift issue. Summary counts: critical items, high-severity items,
items resolved this week, items carried over.

### D. SLA Tracking

- Time-to-acknowledge (target: 72 hours)
- Time-to-remediate (target: 14 days)
- Escalation triggers: no acknowledgment after 72 hours; no remediation after 14 days

---

## 3. Notification Mechanisms

### A. Inline Dashboard Alerts

- Red badge for critical drift
- Yellow badge for aging items
- Blue badge for new weekly items

### B. Slack / Teams Webhook (optional)

Triggers: new critical drift detected, weekly report published, SLA breach.

Payload includes: document ID, owner, severity, link to remediation PR or drift issue.

### C. GitHub Mentions

- Automatic @owner mention in weekly drift issue
- Automatic assignment of remediation PRs

---

## 4. Data Sources

- `reports/metadata-drift-YYYY-MM-DD.json`
- CI validator output
- GitHub Issues (labels: `metadata-drift`, `weekly-report`, `automated`)
- GitHub PR metadata

---

## 5. Acceptance Criteria

- Dashboard updates within 5 minutes of new drift report.
- Owners can see all assigned items in one view.
- Governance can identify SLA breaches instantly.
- Notification accuracy >= 99%.

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
