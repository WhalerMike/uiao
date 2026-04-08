---
id: runtime-dependency-failure-matrix
title: Governance Runtime Dependency Failure-Mode Matrix
owner: governance-steward
status: DRAFT
---

# UIAO Governance Runtime Dependency Failure-Mode Matrix

## Canonical Failure Analysis Across CI, Workflows, API, DB, and Dashboard

This matrix identifies failure modes across the governance runtime and defines their impact, detection signals, and required governance actions.

---

## 1. Failure-Mode Matrix

| Component | Failure Mode | Impact | Detection Signals | Governance Actions |
|----------|--------------|--------|-------------------|--------------------|
| CI Validator | Misclassification (false positive/negative) | Incorrect drift detection | CI logs, spike in failures | Patch validator, update schema rules |
| CI Validator | Outdated schema | Drift undetected | Drift clusters with missing CI events | Update schema version, redeploy CI |
| Webhook Handler | Event loss | SLA timers not updated | Missing DB entries | Restart handler, replay events |
| Webhook Handler | Mislabeling | Wrong severity/SLA state | Dashboard anomalies | Patch handler logic |
| Weekly Drift Workflow | Workflow failure | Drift not detected | GitHub Actions failure | Rerun workflow, fix YAML |
| Governance API | Latency | Dashboard stale | API latency alerts | Scale API, optimize queries |
| Governance API | Incorrect aggregation | Wrong drift counts | Dashboard inconsistencies | Patch API logic |
| PostgreSQL | Write failure | Drift/SLA not stored | DB error logs | Restore DB, replay events |
| PostgreSQL | Schema mismatch | Incorrect dashboard data | Migration errors | Apply DB migration |
| Dashboard | Stale data | Incorrect governance view | Freshness alerts | Fix API polling |
| Dashboard | Rendering failure | Missing panels | UI logs | Patch UI, redeploy |
| Schema | Version drift | CI mismatch | Schema divergence alerts | Apply schema evolution plan |

---

## 2. Severity Classification

- Critical: SLA timers incorrect, drift undetected, DB corruption
- High: Dashboard stale, CI misclassification
- Medium: Workflow delays, API latency
- Low: UI rendering issues

---

## 3. Governance Controls

- Schema version pinning
- CI validator versioning
- Webhook health checks
- DB integrity checks
- Dashboard freshness monitoring
