---
document_id: UIAO_100
title: "UIAO Compliance Orchestrator"
version: "1.0"
status: Current
classification: CANONICAL
owner: "Michael Stratton"
created_at: "2026-04-14"
updated_at: "2026-04-14"
boundary: "GCC-Moderate"
---

# UIAO Compliance Orchestrator

## Responsibilities
- Schedule SCuBA runs (e.g., nightly)
- Trigger:
  - Normalization
  - KSI evaluation
  - Drift engine
  - OSCAL emitters
  - POA&M generator
- Notify:
  - Operators
  - Auditors (read-only)

## Scheduling Model
- Cron-like schedules per tenant:
  - `0 2 * * *` — nightly SCuBA
  - `0 3 * * *` — drift + POA&M update

## Failure Handling
- Per-job retries
- Dead-letter queue
- Alerting hooks (email/webhook)
