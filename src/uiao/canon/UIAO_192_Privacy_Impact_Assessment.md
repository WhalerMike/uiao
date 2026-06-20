---
document_id: UIAO_192
title: "UIAO Privacy Impact Assessment"
version: "1.0"
status: Current
owner: Michael Stratton
created_at: "2026-06-05"
updated_at: "2026-06-19"
publish_to_site: true
publication_style: include
---

# UIAO Privacy Impact Assessment

> **Status: Current — authoritative template.** PIA identified in [`compliance-mapping.qmd §7.1`](../../../docs/customer-documents/compliance/controls-testing/compliance-mapping.qmd) and tracked in [UIAO_184](UIAO_184_Gap_Closure_Register.md) (Workstream A). Addresses the **PT (Personally Identifiable Information Processing and Transparency)** family and the privacy considerations of identity data processed during AD-to-Entra ID modernization. Bracketed `[PLACEHOLDER]` fields are completed per authorizing system.

## Purpose

Assess and document the privacy impact of processing personally identifiable information (PII) within a UIAO Governance OS deployment — principally identity attributes handled during AD-to-Entra ID modernization — so that privacy risk is identified, mitigated, and transparent. Satisfies the PT family of NIST SP 800-53 Rev 5.

## §1 — PII inventory and authority (`PT-1`, `PT-2`)

| Field | Value |
|---|---|
| PII processed | Identity attributes: `[e.g. UPN, employee ID, manager, OrgPath facets, lifecycle state]` |
| Source systems | On-prem Active Directory, Entra ID |
| Authority to process | `[AGENCY AUTHORITY]` |
| Processing purpose | Identity modernization, governance, and drift detection |

The authority and specific purposes for processing PII are documented per `PT-2`/`PT-3`.

## §2 — Data flows

Identity data flows from on-prem AD and Entra ID into UIAO assessment artifacts (UIAOIdentityAssessment, [UIAO_181](UIAO_181_UIAOIdentityAssessment_Module_Specification.md)) and the substrate's evidence pipeline. Each flow is recorded with: source, fields, destination, and retention. PII is processed within the GCC-Moderate boundary; it is not exported outside that boundary.

## §3 — Privacy controls

- **Minimization** — only attributes required for governance and modernization are processed.
- **Access control** — PII-bearing artifacts are subject to the same OrgPath authorization and boundary controls as other governed data; unauthorized access is `DRIFT-AUTHZ`.
- **Integrity & provenance** — PII-bearing evidence carries a provenance envelope; tampering surfaces as `DRIFT-PROVENANCE`.
- **Transparency** — processing purposes and the privacy notice (`[NOTICE REF]`) are published per `PT-5`.

## §4 — Consent and individual participation (`PT-4`, `PT-6`)

Where consent or individual participation applies, the mechanism (`[CONSENT MECHANISM]`) and any system-of-records linkage are documented. For federal employee identity data processed under agency authority, the basis is recorded in §1.

## §5 — Retention and destruction

PII-bearing assessment artifacts are retained for `[RETENTION PERIOD]` consistent with the `AU`/agency records schedule, then securely destroyed. Destruction follows the supply-chain/disposal procedures in the SCRM plan ([UIAO_191](UIAO_191_Supply_Chain_Risk_Management_Plan.md) §7) where applicable.

## §6 — Privacy risk and mitigation

Identified privacy risks (e.g., over-collection during assessment, residual PII in stale artifacts) are recorded with mitigations; residual risk requiring action is tracked as POA&M items ([UIAO_189](UIAO_189_POAM_Template.md)). Evidence-staleness drift helps detect retained PII past its retention window.

## §7 — Gap linkage

This PIA addresses the PT family; until adopted, PT controls remain open POA&M items. On adoption, the SSP ([UIAO_185](UIAO_185_System_Security_Plan_Template.md) §3) PT-adjacent disposition is updated.

## References

- [UIAO_185](UIAO_185_System_Security_Plan_Template.md) — SSP
- [UIAO_181](UIAO_181_UIAOIdentityAssessment_Module_Specification.md) — identity assessment (PII source)
- [UIAO_189](UIAO_189_POAM_Template.md) — POA&M Template
- [UIAO_191](UIAO_191_Supply_Chain_Risk_Management_Plan.md) — SCRM Plan (disposal)
- [UIAO_184](UIAO_184_Gap_Closure_Register.md) — gap-closure register (Workstream A)
- [`compliance-mapping.qmd`](../../../docs/customer-documents/compliance/controls-testing/compliance-mapping.qmd) — PT-family gap analysis
