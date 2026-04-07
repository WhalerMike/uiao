---
id: governance-escalation-playbook
title: "UIAO Governance Escalation Playbook -- Metadata Drift"
owner: governance-team
status: DRAFT
---

# UIAO Governance Escalation Playbook -- Metadata Drift (Machine-Trackable Edition)

## 1. Purpose

This playbook defines the canonical, automatable escalation workflow for metadata drift.
Every step maps to labels, milestones, and GitHub Projects columns so governance can
track and enforce SLAs with zero ambiguity.

---

## 2. GitHub Labels (Canonical)

| Label | Purpose |
|-------|---------|
| `metadata-drift` | Item contains drift detected by CI or weekly workflow |
| `drift-critical` | Severity = critical |
| `drift-high` | Severity = high |
| `drift-medium` | Severity = medium |
| `drift-low` | Severity = low |
| `needs-owner-ack` | Awaiting owner acknowledgment (0-72h) |
| `sla-at-risk` | Approaching SLA breach (48-72h) |
| `sla-breached` | SLA exceeded (>=72h or >=14d) |
| `governance-review` | Governance intervention required |
| `remediation-in-progress` | Owner has begun remediation |
| `remediation-complete` | PR merged and validated |
| `ci-metadata-failure` | CI validator failed on PR |
| `emergency-bypass` | Governance-approved CI bypass |

---

## 3. Milestones (Time-Bound Governance Cycles)

| Milestone | Definition |
|----------|------------|
| Weekly Drift -- YYYY-MM-DD | Auto-created by weekly workflow; all drift items for that week |
| Critical Remediation -- Q# | All critical items requiring remediation within the quarter |
| Governance Review -- Q# | Items escalated to governance for systemic or repeated issues |

---

## 4. GitHub Projects Columns (State Machine)

| Column | Meaning | Entry Condition | Exit Condition |
|--------|---------|----------------|----------------|
| 1. New Drift | Newly detected drift | Weekly workflow or CI creates issue | Owner assigned |
| 2. Awaiting Owner Acknowledgment | Owner must acknowledge within 72h | needs-owner-ack label applied | Owner comments or assigns self |
| 3. SLA At Risk | 48-72h without acknowledgment | Automation adds sla-at-risk | Owner acknowledges OR SLA breach |
| 4. SLA Breached | >72h no acknowledgment OR >14d no remediation | Automation adds sla-breached | Governance triage |
| 5. Remediation In Progress | Owner working on fix | PR opened + remediation-in-progress | CI passes + PR approved |
| 6. Governance Review | Systemic issues or repeated breaches | Governance applies governance-review | Governance resolution |
| 7. Ready for Merge | CI passing, approvals complete | CI validator passes | PR merged |
| 8. Resolved | Drift eliminated | PR merged + weekly workflow confirms | None |

---

## 5. Automation Rules (Deterministic)

**Rule 1 -- New Drift:** When weekly workflow or CI detects drift, create issue with labels
`metadata-drift`, `<severity>`, `needs-owner-ack`. Add to New Drift column. Assign owner.

**Rule 2 -- 48-Hour Warning:** If no acknowledgment after 48 hours, add label `sla-at-risk`.
Move to SLA At Risk column. Send Slack/Teams webhook.

**Rule 3 -- 72-Hour SLA Breach:** If still no acknowledgment, add label `sla-breached`.
Move to SLA Breached column. Trigger webhook. Tag governance team.

**Rule 4 -- Remediation PR Opened:** When owner opens PR, add label `remediation-in-progress`.
Move issue to Remediation In Progress. Link PR to issue.

**Rule 5 -- CI Failure:** If validator fails, add label `ci-metadata-failure`. Block merge.

**Rule 6 -- Governance Review:** If repeated SLA breaches or systemic schema violations,
add label `governance-review`. Move to Governance Review.

**Rule 7 -- Resolution:** When PR merges and CI passes, add label `remediation-complete`.
Move to Resolved. Weekly workflow confirms resolution and closes issue.

---

## 6. State Transition Diagram

```
New Drift
   -> (auto-assign)
Awaiting Owner Acknowledgment
   -> (48h)
SLA At Risk
   -> (72h)
SLA Breached
   -> (governance)
Governance Review
   -> (owner remediation)
Remediation In Progress
   -> (CI passing + approvals)
Ready for Merge
   -> (merge)
Resolved
```

---

## 7. SLAs

- **Acknowledgment SLA:** Owner acknowledges within 72 hours.
- **Remediation SLA:** Remediation PR opened and passing CI within 14 days for critical items.

---

## 8. Roles

- **Owner:** Primary responsible party for a document.
- **Docs Maintainer:** Reviews remediation PRs and ensures schema alignment.
- **Governance Team:** Final authority on policy, exceptions, and SLA breaches.

---

## 9. Acceptance Criteria (Machine-Trackable)

- Every drift item must have exactly one severity label.
- Every item must be in exactly one project column.
- SLA transitions must occur automatically.
- Governance must be notified on every breach.
- Weekly workflow must close resolved items automatically.
- Dashboard must reflect state changes within 5 minutes.
