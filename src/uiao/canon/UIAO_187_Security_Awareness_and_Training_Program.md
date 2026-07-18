---
document_id: UIAO_187
title: "UIAO Security Awareness and Training Program"
version: "1.0"
status: Current
owner: Michael Stratton
created_at: "2026-06-05"
updated_at: "2026-06-19"
publish_to_site: true
publication_style: include
---

# UIAO Security Awareness and Training Program

> **Status: Current — authoritative template.** Agency-responsibility program template that closes the **AT (Awareness & Training)** family — one of the four families Chapter 23 names as uncovered. The SSP ([UIAO_185](UIAO_185_System_Security_Plan_Template.md) §4) declares AT as an agency-responsibility program; this document is that program template. Covers `AT-1` through `AT-4`. Bracketed `[PLACEHOLDER]` fields are completed per authorizing agency. Tracked in [UIAO_184](UIAO_184_Gap_Closure_Register.md) (Workstream A).

## Purpose

Establish the security awareness and role-based training program for personnel who operate, administer, develop for, or use a UIAO Governance OS deployment, satisfying the policy (`AT-1`), literacy/awareness (`AT-2`), role-based (`AT-3`), and records (`AT-4`) requirements of NIST SP 800-53 Rev 5.

## §1 — Policy and procedures (`AT-1`)

The authorizing agency maintains a security awareness and training policy reviewed at least annually and after any significant change. `[AGENCY POLICY REF]` is the governing instrument; this program is its UIAO-specific implementation.

## §2 — Awareness training (`AT-2`)

All users complete security awareness training:

- **At onboarding**, before being granted access.
- **Annually** thereafter as a refresher.
- **On significant change** to threat landscape or system.

Awareness content includes phishing recognition, social engineering, credential hygiene (phishing-resistant MFA), insider-threat indicators (`AT-2(2)`), and acceptable use.

### Phishing simulation

The agency runs a phishing-simulation program at `[FREQUENCY]`. Click/report rates are tracked per §4; repeat clickers receive targeted follow-up training.

## §3 — Role-based training (`AT-3`)

Personnel in security-significant roles complete role-specific training before assuming the role and annually:

| Role | Training focus |
|---|---|
| Administrators | Privileged-access governance, OrgPath authorization model, Conditional Access, drift remediation, halt-on-critical procedures |
| Developers | Secure development, canon-change process (AGENTS.md I5), provenance/evidence requirements, SBOM |
| Operators | Incident response roles ([UIAO_186](UIAO_186_Incident_Response_Plan.md)), evidence chain of custody, runbook procedures |
| End users | Awareness baseline (§2) plus data-handling for their access level |

## §4 — Training records (`AT-4`)

Completion is recorded per individual with: training type, completion date, and next-due date. Records are retained for `[RETENTION PERIOD]` consistent with `AU` audit-retention policy and are available as assessment evidence. Outstanding/overdue training is reported to the system owner.

## §5 — Gap linkage

Until the agency formally adopts this program, AT-family controls remain a **gap** recorded in the POA&M (`CA-5`). On adoption, the AT family moves from agency-responsibility-planned to satisfied in the SSP §3 disposition.

## References

- [UIAO_185](UIAO_185_System_Security_Plan_Template.md) — SSP (`AT` disposition, §4)
- [UIAO_188](UIAO_188_Personnel_Security_Program.md) — Personnel Security Program (paired PS family)
- [UIAO_184](UIAO_184_Gap_Closure_Register.md) — gap-closure register (Workstream A)
- [`compliance-mapping.qmd`](../../../docs/customer-documents/uiao-aan-integration/09-compliance-mapping.qmd) — `AT-1`…`AT-4` gap analysis
