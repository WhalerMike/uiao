---
id: governance-handbook
title: "UIAO Governance Handbook -- Canonical Operating Manual"
owner: governance-team
status: DRAFT
---

# UIAO Governance Handbook

## Canonical Operating Manual for Maintainers & Governance Stewards

---

## 1. Purpose

This handbook provides a complete, printable reference for the UIAO Governance Runtime.
It defines the governance model, roles, workflows, SLAs, runtime architecture, and operational procedures.

---

## 2. Governance Principles

- Metadata must be correct, complete, and schema-aligned.
- Drift must be detected early and remediated quickly.
- Owners are accountable for their documents.
- Governance enforces SLAs and prevents systemic drift.
- All actions must be deterministic, auditable, and provenance-preserving.

---

## 3. Roles

**Maintainers:** Remediate drift, open remediation PRs, ensure CI passes.

**Appendix Owners:** Acknowledge drift within 72 hours, remediate critical items within 14 days.

**Governance Stewards:** Enforce SLAs, review systemic drift, maintain governance rules and schema.

---

## 4. Drift Lifecycle

1. Drift detected (CI or weekly workflow)
2. Issue created with severity labels
3. Owner acknowledgment (<=72h)
4. Remediation PR opened
5. CI validation
6. Merge + resolution
7. Weekly workflow confirms closure

---

## 5. SLAs

- Acknowledgment SLA: 72 hours
- Remediation SLA (critical): 14 days
- Escalation: sla-at-risk -> sla-breached -> governance review

---

## 6. CI Enforcement

CI blocks merges on: missing required fields, deprecated fields, invalid IDs, broken references, YAML errors.
Emergency bypass requires governance approval.

---

## 7. Governance Runtime Architecture

```
GitHub -> Webhook Handler -> Governance API -> Dashboard UI
                          -> PostgreSQL (state)
```

---

## 8. Dashboard

Corpus Index, SLA Heatmap, Weekly Reports, Owner Reliability Scores.

---

## 9. Reliability Score

Weighted formula combining: Time-to-Acknowledge, Time-to-Remediate, SLA breaches, CI failures, weekly unacknowledged items.
See `owner-reliability-score.md` for full formula.

---

## 10. Quarterly Governance Review

Drift trends, SLA performance, reliability scores, systemic drift clusters, schema updates, governance interventions.
See `quarterly-review-template.md` for the template.

---

## 11. Deployment

- Local: docker compose up -d
- Production: Helm chart
- Reverse proxy: NGINX

See `runtime-deploy.md` for full deployment guide.

---

## 12. Related Documents

| Document | Purpose |
|---------|---------|
| `bootstrap.md` | Full onboarding guide |
| `escalation-playbook.md` | SLA and escalation state machine |
| `governance-charter.md` | Formal governance policy |
| `steward-playbook.md` | Steward responsibilities |
| `day1-owner-quickstart.md` | New owner quick start |
| `runtime-architecture.md` | Runtime component overview |
| `quarterly-review-template.md` | Quarterly review format |

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
