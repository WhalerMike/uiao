---
document_id: UIAO_186
title: "UIAO Incident Response Plan"
version: "1.0"
status: Current
owner: Michael Stratton
created_at: "2026-06-05"
updated_at: "2026-06-19"
publish_to_site: true
publication_style: include
---

# UIAO Incident Response Plan

> **Status: Current — authoritative template.** Standalone incident-response plan identified in [`compliance-mapping.qmd §7.1`](../../../docs/customer-documents/uiao-aan-integration/09-compliance-mapping.qmd) and tracked in [UIAO_184](UIAO_184_Gap_Closure_Register.md) (Workstream A). Covers `IR-1` through `IR-8`. Bracketed `[PLACEHOLDER]` fields are completed per authorizing agency.

## Purpose and scope

This plan establishes how security incidents affecting a UIAO Governance OS deployment within the GCC-Moderate boundary are detected, classified, contained, reported, and closed out. It satisfies the policy-and-procedure (`IR-1`), training (`IR-2`), testing (`IR-3`), handling (`IR-4`), monitoring (`IR-5`), reporting (`IR-6`), assistance (`IR-7`), and planning (`IR-8`) requirements of NIST SP 800-53 Rev 5.

## Roles (`IR-7`)

| Role | Responsibility |
|---|---|
| Incident Response Lead | `[NAME]` — owns the response, declares severity, authorizes containment |
| System Owner | `[NAME]` — accountable system authority |
| Agency SOC / CISA liaison | `[CONTACT]` — external reporting |
| Evidence custodian | `[NAME]` — chain of custody |

## §1 — Incident classification matrix (`IR-4`)

| Severity | Definition | Examples | Target response |
|---|---|---|---|
| **1 — Critical** | Confirmed compromise of identity plane, canon integrity, or boundary | Privilege escalation (`DRIFT-AUTHZ` unauthorized), canon tamper, data exfiltration | Immediate; declare within 15 min |
| **2 — High** | Significant control failure or suspected compromise | MFA disabled tenant-wide, broken provenance seal (`DRIFT-PROVENANCE`), repeated failed-auth surge | Within 1 hour |
| **3 — Medium** | Localized control deviation, no confirmed compromise | Single-principal drift, stale evidence beyond SLA | Within 1 business day |
| **4 — Low** | Policy deviation with no security impact | Informational drift, advisory findings | Next review cycle |

Drift findings from the UIAO drift engine feed this matrix directly: an `unauthorized`-classification finding (`DRIFT-AUTHZ`, broken-seal `DRIFT-PROVENANCE`) opens at minimum Severity 2.

## §2 — Response lifecycle (`IR-4`)

1. **Detect** — drift engine alert, telemetry, audit log, or human report.
2. **Triage & classify** — assign severity per §1; open an incident record with a unique id and timestamp.
3. **Contain** — isolate the affected principal/resource; halt automated remediation on Severity 1–2 (the drift engine's halt-on-critical behavior); preserve state before any change.
4. **Eradicate & recover** — remove the cause, restore canonical state from baseline, verify via a governance pass.
5. **Report** — per §3 timelines.
6. **Close & learn** — per §5.

## §3 — Reporting timelines (`IR-6`)

| Trigger | Recipient | Timeline |
|---|---|---|
| Any confirmed incident affecting federal information | Agency SOC / CISA | Per agency policy and US-CERT/CISA federal incident notification requirements (`[AGENCY SLA]`, typically within 1 hour of declaration for major incidents) |
| Severity 1 (Critical) | Authorizing Official + CISA liaison | Immediately on declaration |
| Severity 2 (High) | System Owner + Agency SOC | Within `[N]` hours |
| Suspected criminal activity | Law enforcement coordination (§6) | Per agency legal counsel |

Report content includes: incident id, severity, detection source, affected systems/principals, current status, and preliminary impact. Reporting timelines are completed by the authorizing agency to match its US-CERT/CISA obligations.

## §4 — Evidence preservation and chain of custody (`IR-4`)

- Capture the pre-containment state (drift snapshot, audit log extract, telemetry) **before** any remediation alters it.
- Record each evidence item with: collector, collection timestamp, source, and a content hash. Each handoff is logged with custodian and timestamp.
- Evidence is retained for `[RETENTION PERIOD]` consistent with `AU` audit-retention policy.
- A broken or unattributed evidence envelope is itself a `DRIFT-PROVENANCE` finding and must be noted in the incident record.

## §5 — Lessons learned (`IR-4`)

Within `[N]` business days of closing a Severity 1–2 incident, the IR Lead convenes a review covering: timeline, root cause, response effectiveness, and corrective actions. Corrective actions that require control or documentation changes are recorded in the POA&M (`CA-5`); systemic findings feed back into canon (an ADR where doctrine changes).

## §6 — Law-enforcement coordination (`IR-7`)

Suspected criminal activity is escalated to `[AGENCY LEGAL COUNSEL]` before external law-enforcement contact. No evidence is released externally without counsel approval. Chain of custody (§4) is mandatory once law-enforcement coordination is anticipated.

## §7 — Testing and training (`IR-2`, `IR-3`)

- **Training (`IR-2`):** all response-role holders complete IR training at onboarding and annually.
- **Testing (`IR-3`):** the plan is exercised at least annually via a tabletop or simulated incident; results and corrective actions are recorded.

## References

- [UIAO_185](UIAO_185_System_Security_Plan_Template.md) — SSP (`IR` family disposition)
- [UIAO_184](UIAO_184_Gap_Closure_Register.md) — gap-closure register (Workstream A)
- [`compliance-mapping.qmd`](../../../docs/customer-documents/uiao-aan-integration/09-compliance-mapping.qmd) — `IR-1`…`IR-8` gap analysis
