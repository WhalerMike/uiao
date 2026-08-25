---
document_id: UIAO_190
title: "UIAO Continuous Monitoring Strategy"
version: "1.0"
status: Current
owner: Michael Stratton
created_at: "2026-06-05"
updated_at: "2026-06-19"
publish_to_site: true
publication_style: include
---

# UIAO Continuous Monitoring Strategy

> **Status: Current — authoritative template.** Formal ConMon strategy identified in [`compliance-mapping.qmd §7.1`](../../../docs/customer-documents/uiao-orgcomp-integration/09-compliance-mapping.qmd) and tracked in [UIAO_184](UIAO_184_Gap_Closure_Register.md) (Workstream A). Addresses `CA-7` and links to the FedRAMP 20x KSI framework. It defines what is monitored, how often, how it is reported, and when it escalates — the operational counterpart to the point-in-time SSP assessment.

## Purpose

Continuous monitoring sustains the authorization between assessments by detecting control drift, evidence staleness, and risk changes continuously rather than at a yearly snapshot. UIAO's governance-as-code posture makes this native: drift detection, KSI evaluation, and the evidence pipeline are already continuous; this strategy formalizes their scope, cadence, and reporting per `CA-7`.

## §1 — Monitoring scope

| Surface | Mechanism | Drift / signal |
|---|---|---|
| Identity & authorization | Drift engine (`src/uiao/governance/drift.py`) | `DRIFT-AUTHZ`, `DRIFT-IDENTITY` |
| Configuration & policy | Drift engine + substrate walker | `DRIFT-SCHEMA`, `DRIFT-SEMANTIC` |
| Evidence integrity & provenance | Provenance classifier + freshness | `DRIFT-PROVENANCE`, staleness |
| Control posture (KSIs) | KSI evaluation (`uiao ksi evaluate`) | KSI pass/fail trend |
| Canon integrity | Substrate drift gate (CI) | Registry/citation resolution |

## §2 — Frequency

- **Continuous / event-driven:** drift detection on each governance pass; CI substrate-drift on every canon change.
- **Scheduled:** KSI evaluation and freshness sweeps at `[FREQUENCY]`; evidence-staleness review against per-adapter SLAs.
- **Periodic:** monthly posture report; annual strategy review.

## §3 — Metrics and KSIs

The strategy tracks a defined metric set (open POA&M items by risk, drift findings by class/severity, KSI pass rate, evidence freshness). These map to the **FedRAMP 20x Key Security Indicators** framework: machine-readable, continuously evaluated evidence rather than periodic attestations. Thresholds are recorded in `[KSI THRESHOLD CONFIG]`.

## §4 — Reporting

- A continuously updated posture view (the governance dashboard) presents drift, KSI, and POA&M state.
- A periodic ConMon report `[FREQUENCY]` is delivered to the system owner and authorizing official, summarizing posture changes, new POA&M items, and remediation progress.

## §5 — Escalation

- An `unauthorized`-classification drift finding raises an incident per the Incident Response Plan ([UIAO_186](UIAO_186_Incident_Response_Plan.md) §1) and opens a POA&M item ([UIAO_189](UIAO_189_POAM_Template.md) §3).
- A High-risk POA&M item past its scheduled completion escalates to the authorizing official.
- KSI threshold breaches escalate per `[AGENCY SLA]`.

## §6 — Gap linkage

This strategy addresses `CA-7`; until adopted it remains an open item. Once adopted, the CA family disposition in the SSP ([UIAO_185](UIAO_185_System_Security_Plan_Template.md) §3) is updated to reflect implemented continuous monitoring.

## References

- [UIAO_189](UIAO_189_POAM_Template.md) — POA&M Template (item generation, review cadence)
- [UIAO_185](UIAO_185_System_Security_Plan_Template.md) — SSP (`CA` disposition)
- [UIAO_186](UIAO_186_Incident_Response_Plan.md) — Incident Response Plan (escalation)
- [UIAO_184](UIAO_184_Gap_Closure_Register.md) — gap-closure register (Workstream A)
- [`compliance-mapping.qmd`](../../../docs/customer-documents/uiao-orgcomp-integration/09-compliance-mapping.qmd) — `CA-7` gap analysis
