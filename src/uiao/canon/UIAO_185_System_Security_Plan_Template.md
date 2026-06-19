---
document_id: UIAO_185
title: "UIAO System Security Plan (SSP) Template"
version: "1.0"
status: Current
owner: Michael Stratton
created_at: "2026-06-05"
updated_at: "2026-06-19"
publish_to_site: true
publication_style: include
---

# UIAO System Security Plan (SSP) Template

> **Status: Current — authoritative template.** This is the foundational FedRAMP-authorization artifact identified as the single most critical gap in [`compliance-mapping.qmd §7.1`](../../../docs/customer-documents/compliance/controls-testing/compliance-mapping.qmd) and tracked in the gap-closure register [UIAO_184](UIAO_184_Gap_Closure_Register.md) (Workstream A). UIAO-canonical fields are pre-filled for the reference deployment (the **UIAO Governance OS**, v0.7.0, within the GCC-Moderate boundary); bracketed `[…]` fields are **agency-ATO instantiation parameters** completed by the authorizing agency (system owner, authorizing official, agency policy references). It addresses `PL-2` (System Security Plan) and provides the control-implementation framework that maps all 323 FedRAMP Moderate controls to a UIAO implementation, a shared-responsibility statement, or an inheritance declaration.

## Purpose

The SSP is the authoritative description of how an authorizing system implements, shares, or inherits each control in the FedRAMP Moderate baseline (NIST SP 800-53 Rev 5, 323 controls across 20 families). It is the document an assessor reads first and the spine to which the POA&M (`CA-5`), Continuous Monitoring Strategy (`CA-7`), and assessment evidence all attach.

## Scope

This template covers a UIAO Governance OS deployment within the **GCC-Moderate** boundary (Microsoft 365 SaaS). Infrastructure-layer controls are inherited from the underlying Microsoft GCC-Moderate authorization; UIAO-layer controls are implemented by the substrate and its adapters; organizational/procedural controls are the authorizing agency's responsibility.

## How to use this template

1. Complete the remaining agency-ATO `[…]` parameters in §1 (system owner, authorizing official); the UIAO-canonical identity fields are pre-filled.
2. For each control family in §3, record the implementation status using the responsibility model in §2 and cite the UIAO artifact (canon doc id, adapter, or KSI) that satisfies it.
3. Record every control with no full implementation in the POA&M (`CA-5`) and cross-reference it here.
4. Re-validate at each `lifecycle_review`.

## §1 — System identification

| Field | Value |
|---|---|
| System name | UIAO Governance OS |
| System owner | `[OWNER]` *(agency-ATO parameter)* |
| Authorizing official | `[AO]` *(agency-ATO parameter)* |
| Authorization boundary | GCC-Moderate (Microsoft 365 SaaS) |
| Impact level | FedRAMP Moderate |
| Baseline | NIST SP 800-53 Rev 5 (Release 5.2.0) |
| UIAO version | v0.7.0 |

## §2 — Responsibility model

Every control is assigned exactly one disposition:

- **UIAO-implemented** — satisfied by the UIAO substrate, an adapter, or a KSI. Cite the canon doc id / adapter / KSI.
- **Shared** — partially satisfied by UIAO, partially by the agency or Microsoft. State the split explicitly.
- **Inherited** — satisfied by the underlying Microsoft GCC-Moderate authorization (the system neither implements nor can alter it). Cite the inheritance declaration in §5.
- **Agency-responsibility** — an organizational/procedural control the authorizing agency satisfies with its own program documentation (e.g., the AT and PS programs).

## §3 — Control implementation summary by family

Status legend: **I** = UIAO-implemented · **S** = shared · **H** = inherited · **A** = agency-responsibility · **gap** = no full implementation (record in POA&M).

| Family | Controls (Mod) | Primary disposition | UIAO artifact / note |
|---|---|---|---|
| AC — Access Control | 25 | I / S | OrgPath authorization model, Conditional Access library |
| AT — Awareness & Training | 6 | **A** | Agency program — UIAO Security Awareness & Training Program (Workstream A, planned) |
| AU — Audit & Accountability | 16 | I | Evidence pipeline, unified audit log telemetry |
| CA — Assessment, Authorization & Monitoring | 9 | S | This SSP, POA&M template, ConMon strategy |
| CM — Configuration Management | 17 | I | Drift engine, substrate manifest, schema gates |
| CP — Contingency Planning | 13 | S | DR playbook, replication guide |
| IA — Identification & Authentication | 17 | I | Entra adapters, identity assessment, phishing-resistant MFA |
| IR — Incident Response | 8 | S | UIAO Incident Response Plan ([UIAO_186](UIAO_186_Incident_Response_Plan.md)) |
| MA — Maintenance | 6 | S | Operations runbook |
| MP — Media Protection | 7 | **H** | Inherited — see §5 |
| PE — Physical & Environmental | 19 | **H** | Inherited — see §5 |
| PL — Planning | 5 | S | This SSP (`PL-2`) |
| PS — Personnel Security | 10 | **A** | Agency program — UIAO Personnel Security Program (Workstream A, planned) |
| RA — Risk Assessment | 10 | I / S | Drift findings, KSI evaluation, vulnerability mapping |
| SA — System & Services Acquisition | 24 | S | SBOM generation, provenance, SCRM plan (planned) |
| SC — System & Communications Protection | 24 | I / S | Boundary enforcement, TLS, encryption posture |
| SI — System & Information Integrity | 21 | I | Drift detection, integrity verification, freshness |
| SR — Supply Chain Risk Management | 12 | S | SBOM, provenance verification, SCRM plan (planned) |

> The four families Chapter 23 names as uncovered resolve here as **two inheritance declarations** (MP, PE — §5) and **two agency programs** (AT, PS — §4 below). This is the honest disposition: none is a silent gap.

## §4 — Agency-responsibility programs (AT, PS, PL)

AT, PS, and the organizational portions of PL are not implementable by the substrate; they are satisfied by authorizing-agency program documentation. The UIAO corpus provides the program templates (AT and PS templates are planned Workstream A deliverables). Until the agency adopts a program, each affected control is a **gap** recorded in the POA&M.

## §5 — Inheritance declarations (MP, PE)

MP (Media Protection) and PE (Physical & Environmental Protection) controls apply to the physical infrastructure UIAO does not own or operate. They are **inherited in full** from Microsoft's GCC-Moderate authorization. UIAO neither implements nor can alter these controls; the authorizing system asserts inheritance and cites the underlying provider authorization package. No UIAO POA&M entry is required for an inherited control unless the provider authorization lapses.

## §6 — Gaps and POA&M linkage

Every control not marked **I**, **H**, or **A**-satisfied is a gap. Each gap is recorded in the POA&M (`CA-5`) with a remediation milestone and cross-referenced by control id in §3. The residual ~87-control documentation gap from `compliance-mapping.qmd` is closed as the Workstream A documents land and this SSP's dispositions are completed.

## References

- [`compliance-mapping.qmd`](../../../docs/customer-documents/compliance/controls-testing/compliance-mapping.qmd) — gap analysis and §7 remediation roadmap
- [UIAO_184](UIAO_184_Gap_Closure_Register.md) — gap-closure register (Workstream A)
- [UIAO_186](UIAO_186_Incident_Response_Plan.md) — Incident Response Plan (`IR` family)
