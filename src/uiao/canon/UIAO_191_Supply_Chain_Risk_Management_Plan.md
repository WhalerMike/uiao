---
document_id: UIAO_191
title: "UIAO Supply Chain Risk Management Plan"
version: "1.0"
status: Current
owner: Michael Stratton
created_at: "2026-06-05"
updated_at: "2026-06-19"
publish_to_site: true
publication_style: include
---

# UIAO Supply Chain Risk Management Plan

> **Status: Current — authoritative template.** SCRM plan identified in [`compliance-mapping.qmd §7.1`](../../../docs/customer-documents/uiao-aan-integration/09-compliance-mapping.qmd) and tracked in [UIAO_184](UIAO_184_Gap_Closure_Register.md) (Workstream A). Addresses `SR-1` through `SR-12`. Bracketed `[PLACEHOLDER]` fields are completed per authorizing agency.

## Purpose

Establish how supply-chain risk is identified, assessed, and mitigated across the third-party components a UIAO Governance OS deployment depends on — so that a compromised or untrustworthy upstream component is detected and bounded rather than silently trusted. Satisfies `SR-1` through `SR-12` of NIST SP 800-53 Rev 5, and aligns with `SA-12`-adjacent acquisition controls in the SSP.

## §1 — Policy and procedures (`SR-1`)

The authorizing agency maintains a supply-chain risk-management policy reviewed at least annually. `[AGENCY POLICY REF]` governs; this plan is its UIAO-specific implementation.

## §2 — SCRM plan and roles (`SR-2`, `SR-3`)

A documented SCRM plan and process apply to all components in the dependency footprint. Responsible roles: `[SCRM LEAD]`, `[SYSTEM OWNER]`. Controls and processes protecting the supply chain (`SR-3`) are enumerated per component class in §4.

## §3 — Provenance and traceability (`SR-4`)

Every component carries recorded provenance — origin, version, and integrity hash. The UIAO substrate's provenance posture extends here: a component whose provenance cannot be established is treated as untrusted. Broken or missing provenance surfaces as a `DRIFT-PROVENANCE` finding (per `src/uiao/governance/drift.py`).

## §4 — Component classes and vetting (`SR-5`, `SR-6`)

| Component class | Examples | Vetting |
|---|---|---|
| Source-control & CI | Gitea, GitHub Actions | Pinned versions, integrity verification, supplier review |
| PowerShell modules | UIAO toolchain modules ([ADR-094](adr/adr-094-assessment-to-plan-toolchain.md)) | Authenticode signing (`SI-7`/`SA-10`), signed SHA-256 manifest |
| Doc/build toolchain | Quarto, Node.js dependencies | SBOM enumeration, dependency review |
| Python runtime deps | `pyproject.toml` / lockfile | SBOM, pinned versions, vulnerability scan |

Suppliers/components are assessed (`SR-6`) before adoption and on significant change.

## §5 — SBOM generation and maintenance (`SR-4`, `SA-15`)

A software bill of materials is generated and maintained for the deployment (`uiao generate-sbom`), enumerating components and versions. The SBOM is regenerated on dependency change and retained as canon-anchored evidence.

## §6 — Supplier risk assessment methodology (`SR-6`, `SR-8`)

Suppliers are rated on criticality and trustworthiness; notification agreements (`SR-8`) are recorded where applicable. High-criticality components carry tighter monitoring and a documented contingency if the supplier or component is compromised or discontinued.

## §7 — Tamper, disposal, and component authenticity (`SR-9`…`SR-12`)

Tamper protection (`SR-9`/`SR-10`), component-authenticity verification (`SR-11`), and secure disposal (`SR-12`) procedures apply to the deployment's components and the artifacts it produces. Integrity-hash verification and signed manifests are the primary authenticity mechanisms.

## §8 — Gap linkage

This plan addresses the `SR` family; until adopted, `SR` controls remain open POA&M items ([UIAO_189](UIAO_189_POAM_Template.md)). On adoption, the SR disposition in the SSP ([UIAO_185](UIAO_185_System_Security_Plan_Template.md) §3) is updated.

## References

- [UIAO_185](UIAO_185_System_Security_Plan_Template.md) — SSP (`SR`/`SA` disposition)
- [UIAO_189](UIAO_189_POAM_Template.md) — POA&M Template
- [ADR-094](adr/adr-094-assessment-to-plan-toolchain.md) — module signing/OSCAL contract
- [UIAO_184](UIAO_184_Gap_Closure_Register.md) — gap-closure register (Workstream A)
- [`compliance-mapping.qmd`](../../../docs/customer-documents/uiao-aan-integration/09-compliance-mapping.qmd) — `SR` gap analysis
