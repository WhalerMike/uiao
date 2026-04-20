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
