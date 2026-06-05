---
document_id: UIAO_189
title: "UIAO Plan of Action and Milestones (POA&M) Template"
version: "0.1"
status: Draft
classification: CANONICAL
owner: Michael Stratton
created_at: "2026-06-05"
updated_at: "2026-06-05"
boundary: GCC-Moderate
publish_to_site: true
publication_style: include
---

# UIAO Plan of Action and Milestones (POA&M) Template

> **Status: Draft / template.** FedRAMP-compliant POA&M format identified in [`compliance-mapping.qmd §7.1`](../../../docs/customer-documents/compliance/controls-testing/compliance-mapping.qmd) and tracked in [UIAO_184](UIAO_184_Gap_Closure_Register.md) (Workstream A). Addresses `CA-5`. It is the structured ledger of open control gaps and their remediation, and the document the SSP ([UIAO_185](UIAO_185_System_Security_Plan_Template.md) §6) and Incident Response Plan ([UIAO_186](UIAO_186_Incident_Response_Plan.md) §5) both feed into.

## Purpose

The POA&M tracks every known control weakness — its risk, owner, remediation milestones, and completion date — so that residual risk is visible and closure is scheduled rather than implied. It is the authoritative gap ledger an assessor reviews alongside the SSP.

## §1 — POA&M item schema (`CA-5`)

Each open item records:

| Field | Description |
|---|---|
| POA&M ID | Unique identifier `[POAM-NNNN]` |
| Control(s) | NIST 800-53 control id(s) the weakness affects |
| Weakness | Description of the gap or deficiency |
| Source | Detection origin — assessment, drift finding, audit, incident |
| Risk rating | High / Moderate / Low (per the agency risk methodology) |
| Responsible party | `[OWNER]` accountable for remediation |
| Scheduled completion | Target date |
| Milestones | Dated interim steps |
| Status | Open / In progress / Completed / Risk-accepted |
| Evidence | Pointer to closure evidence (canon-anchored) |

## §2 — Risk rating

Risk is rated from the likelihood and impact of the weakness. High-risk items carry the nearest scheduled completion and are reported per the Continuous Monitoring Strategy ([UIAO_190](UIAO_190_Continuous_Monitoring_Strategy.md)). A weakness may be **risk-accepted** only with documented authorizing-official approval recorded in the item.

## §3 — Automated generation

POA&M items are generated, not only hand-entered:

- **From assessment output** — UIAOPlanGenerators ([UIAO_183](UIAO_183_UIAOPlanGenerators_Module_Specification.md)) emits FedRAMP-compliant POA&M items with required fields and risk ratings from assessment data (`compliance-mapping.qmd §7.3`).
- **From drift findings** — an `unauthorized`-classification drift finding (`DRIFT-AUTHZ`, broken-seal `DRIFT-PROVENANCE`, lifecycle `DRIFT-IDENTITY`) opens a POA&M item automatically, carrying its severity into the risk rating.
- **From incidents** — corrective actions from the IR lessons-learned step ([UIAO_186](UIAO_186_Incident_Response_Plan.md) §5) become POA&M items.

## §4 — Lifecycle and reporting

Items are reviewed at the cadence defined in the Continuous Monitoring Strategy. On closure, the evidence pointer is populated and the affected SSP §3 disposition is updated. Open High-risk items are escalated per `CA-5` and the ConMon escalation path.

## §5 — Gap linkage

This template addresses `CA-5`; until adopted and populated, `CA-5` remains an open item. The residual ~87-control documentation gap (Gap 2) is worked down as POA&M items are created for each and closed as the corresponding Workstream A documents land.

## References

- [UIAO_185](UIAO_185_System_Security_Plan_Template.md) — SSP (§6 gap/POA&M linkage)
- [UIAO_190](UIAO_190_Continuous_Monitoring_Strategy.md) — Continuous Monitoring Strategy (review cadence, escalation)
- [UIAO_186](UIAO_186_Incident_Response_Plan.md) — Incident Response Plan (corrective-action feed)
- [UIAO_184](UIAO_184_Gap_Closure_Register.md) — gap-closure register (Workstream A)
- [`compliance-mapping.qmd`](../../../docs/customer-documents/compliance/controls-testing/compliance-mapping.qmd) — `CA-5` gap analysis
