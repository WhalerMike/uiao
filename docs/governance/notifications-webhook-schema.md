---
id: governance-notifications-webhook-schema
title: "Governance Notifications -- Webhook Payload Schema"
owner: governance-team
status: DRAFT
---

# Governance Notifications -- Webhook Payload Schema

This document defines the JSON payload structure sent to Slack/Teams when governance events occur.
For the machine-readable JSON Schema see `docs/governance/dashboard-api-schema.md`.

---

## 1. Common Envelope

All events share this envelope structure:

```
{
  "event_type": "<type>",
  "timestamp": "<ISO-8601>",
  "environment": "prod | staging",
  "source": "uiao-governance-dashboard",
  "payload": { ... }
}
```

---

## 2. Event: drift_detected

Fired when CI or weekly workflow detects new metadata drift.

Payload fields:
- `document_id` -- canonical document ID
- `title` -- document title
- `owner` -- owner handle
- `severity` -- one of: low, medium, critical
- `issues` -- array of issue objects with: type, field, description, detected_by, report_id
- `links` -- object with: document_url, drift_issue_url, remediation_pr_url

---

## 3. Event: weekly_report_published

Fired when the weekly drift workflow completes and creates a GitHub issue.

Payload fields:
- `report_id` -- weekly report ID (e.g., weekly-2024-12-01)
- `summary` -- object with: total_items, critical, high, resolved_this_week, carried_over
- `links` -- object with: weekly_issue_url, dashboard_url

---

## 4. Event: sla_breach

Fired when acknowledgment SLA (72h) or remediation SLA (14d) is exceeded.

Payload fields:
- `sla_type` -- one of: acknowledgment, remediation
- `threshold_hours` -- SLA threshold (72 or 336)
- `document_id` -- canonical document ID
- `title` -- document title
- `owner` -- owner handle
- `age_hours` -- actual age in hours
- `severity` -- drift severity
- `links` -- object with: document_url, drift_issue_url, owner_view_url
- `escalation` -- object with: to (governance team handle), reason

---

## 5. Delivery Requirements

- Payloads must be delivered within 60 seconds of event occurrence.
- Failed deliveries must be retried with exponential backoff (3 attempts max).
- Webhook secret must be rotated quarterly.
- All event types must be logged to the governance database.
