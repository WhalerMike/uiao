---
id: governance-bootstrap
title: "UIAO Governance Bootstrap Document -- Canonical Onboarding"
owner: governance-team
status: DRAFT
---

# UIAO Governance Bootstrap Document

## Canonical Onboarding for Maintainers & Governance Stewards

---

## 1. Purpose

This document provides the complete onboarding path for the UIAO Governance Runtime.
It is the single source of truth for governance operations.

Topics covered: what the governance system is, how drift is detected and remediated,
how the runtime components work together, how maintainers interact with CI and dashboards,
and how governance stewards enforce policy.

---

## 2. Governance System Overview

UIAO governance ensures: metadata correctness, drift detection and prevention,
SLA-bound remediation, owner accountability, corpus stability and provenance.

The system is built on a deterministic state machine:

```
Drift Detected -> Owner Acknowledgment -> SLA At Risk -> SLA Breached
-> Governance Review -> Remediation -> CI Validation -> Resolution
```

All transitions are machine-tracked via labels, Projects columns, and automation.

---

## 3. Runtime Architecture

For full details see `runtime-architecture.md`. Summary:

| Component | Role |
|----------|------|
| Webhook Handler | Receives GitHub events, applies labels, enforces SLAs |
| Governance API | Aggregates drift, SLA metrics, reliability scores |
| Dashboard | Visual interface for maintainers and governance |
| PostgreSQL | Stores drift events, SLA timers, owner reliability |

---

## 4. Drift Detection Pipeline

Sources: CI metadata validator, weekly drift workflow, manual detection (rare).

Each drift item creates: a GitHub issue, labels (metadata-drift, <severity>, needs-owner-ack),
a Projects item in New Drift, and a database entry in drift_events.

Owner responsibilities: acknowledge within 72 hours; remediate within 14 days (critical).

---

## 5. SLA Enforcement

| Time | State | Label |
|------|--------|--------|
| 0-48h | Awaiting Acknowledgment | needs-owner-ack |
| 48-72h | SLA At Risk | sla-at-risk |
| >72h | SLA Breached | sla-breached |

Governance is notified via Slack/Teams webhook on every breach.
See `escalation-playbook.md` for the full escalation workflow.

---

## 6. Remediation Workflow

Owner opens a PR using the Remediation PR Template (`.github/PULL_REQUEST_TEMPLATE/remediation-metadata.md`).
CI validator must pass. PR must link to drift issue.
When PR merges: label remediation-complete applied, issue moves to Resolved,
weekly workflow confirms closure.

---

## 7. CI Enforcement

CI blocks merges on: missing required fields, deprecated fields, invalid IDs,
broken references, YAML errors. Emergency bypass requires governance approval.
See `docs/ci/TESTPLAN-metadata-validator.md` for full test matrix.

---

## 8. Dashboard Overview

The dashboard provides: corpus index, SLA heatmap (see `dashboard-heatmap-spec.md`),
weekly reports, owner reliability scores (see `owner-reliability-score.md`).
See `dashboard-spec.md` and `dashboard-wireframe.md` for full specs.

---

## 9. Owner Reliability Score

Score = 100 x (0.30*TTA + 0.30*TTR + 0.20*Breaches + 0.10*CI + 0.10*Weekly).
Scores below 40 trigger governance-review on all open items.
See `owner-reliability-score.md` for full formula.

---

## 10. Onboarding Checklist -- Maintainers

**Week 1:** Read this document. Understand drift -> SLA -> remediation flow.
Run governance runtime locally. Trigger a simulated drift event. Review CI validator output.

**Week 2:** Remediate a real drift item. Open a remediation PR.
Observe CI + dashboard updates. Review SLA heatmap.

**Week 3:** Participate in weekly governance review.
Understand reliability scoring. Review systemic drift patterns.

---

## 11. Onboarding Checklist -- Governance Stewards

**Week 1:** Deploy governance runtime. Validate webhook -> API -> dashboard flow.
Review PostgreSQL schema.

**Week 2:** Configure Slack/Teams notifications. Validate SLA breach escalations.
Review Projects automation.

**Week 3:** Run quarterly reliability scoring. Review systemic drift clusters.
Update governance rules as needed.

---

## 12. Success Criteria

The governance system is considered healthy when:

- Zero new critical metadata errors introduced.
- 90% of drift items acknowledged within 72 hours.
- 80% reduction in legacy drift within 6 weeks.
- Dashboard heatmap shows no persistent hotspots.
- Reliability scores trend upward quarter-over-quarter.

---

## 13. Related Documents

| Document | Purpose |
|---------|---------|
| `escalation-playbook.md` | Full escalation state machine with labels and automation rules |
| `dashboard-spec.md` | Dashboard notification layer specification |
| `dashboard-wireframe.md` | Dashboard UI layout and interaction model |
| `dashboard-heatmap-spec.md` | SLA heatmap color scale and interaction spec |
| `owner-reliability-score.md` | Owner reliability scoring algorithm |
| `notifications-webhook-schema.md` | Slack/Teams webhook payload schema |
| `runtime-architecture.md` | Runtime component architecture |
| `runtime-dataflow.md` | Data flow between runtime components |
| `docs/ci/TESTPLAN-metadata-validator.md` | CI validator test plan |
| `docs/meta/governance-metadata-playbook.md` | Human-readable governance guide |
| `docs/meta/governance-metadata-reviewer-checklist.md` | PR review checklist |

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
