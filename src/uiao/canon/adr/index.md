# Architectural Decision Records (ADRs)

This index lists all UIAO Architectural Decision Records.
ADRs document significant architectural decisions -- the context that drove them, the decision made, and the consequences of that decision.

Per CR-003, accepted ADRs are immutable.

## ADR Status Definitions

| Status | Meaning |
|--------|---------|
| PROPOSED | Under review, not yet accepted |
| ACCEPTED | Approved by Governance Board -- immutable Decision field |
| DEPRECATED | Superseded by a newer ADR but retained for audit trail |
| SUPERSEDED | Replaced by a specific ADR (see `superseded_by` field) |

## ADR-000: Process and Lifecycle

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [ADR-000](adr-000-adr-process.md) | ADR Process and Lifecycle | ACCEPTED | 2026-04-07 |

## ADRs by Theme

### Adapter Model

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [ADR-007](adr-007-multi-cloud-adapter.md) | Multi-Cloud Adapter Model | ACCEPTED | 2026-01-20 |
| [ADR-013](adr-013-adapter-failure-isolation.md) | Adapter Failure Isolation | ACCEPTED | 2026-02-03 |
| [ADR-015](adr-015-adapter-extensibility.md) | Adapter Extensibility | ACCEPTED | 2026-02-08 |
| [ADR-017](adr-017-adapter-sandbox-execution.md) | Adapter Sandbox Execution | ACCEPTED | 2026-02-12 |
| [ADR-021](adr-021-adapter-hot-swap-rollback.md) | Adapter Hot-Swap and Rollback | ACCEPTED | 2026-02-22 |
| [ADR-023](adr-023-adapter-concurrency.md) | Adapter Concurrency | ACCEPTED | 2026-03-01 |
| [ADR-025](adr-025-adapter-health-liveness.md) | Adapter Health and Liveness | ACCEPTED | 2026-03-05 |
| [ADR-027](adr-027-adapter-retirement.md) | Adapter Retirement | ACCEPTED | 2026-03-10 |
| [ADR-059](adr-059-sailpoint-adapter-family.md) | SailPoint NERM Adapter — Boundary-Exception Carve-Out and Slot Allocation | ACCEPTED | 2026-05-07 |

### Identity and Truth Fabric

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [ADR-005](adr-005-canonical-claim-schema.md) | Canonical Claim Schema | ACCEPTED | 2026-01-15 |
| [ADR-008](adr-008-zero-trust-identity.md) | Zero-Trust Identity Anchoring | ACCEPTED | 2026-01-22 |
| [ADR-010](adr-010-vendor-baseline-versioning.md) | Vendor Baseline Versioning | ACCEPTED | 2026-01-25 |
| [ADR-011](adr-011-multi-adapter-correlation.md) | Multi-Adapter Correlation | ACCEPTED | 2026-01-28 |
| [ADR-018](adr-018-mission-channel-enforcement.md) | Mission Channel Enforcement | ACCEPTED | 2026-02-15 |

### Drift Fabric

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [ADR-009](adr-009-drift-ledger-immutability.md) | Drift Ledger Immutability | ACCEPTED | 2026-01-22 |
| [ADR-012](adr-012-canonical-drift-taxonomy.md) | Canonical Drift Taxonomy | ACCEPTED | 2026-02-01 |
| [ADR-019](adr-019-vendor-failure-containment.md) | Vendor Failure Containment | ACCEPTED | 2026-02-18 |

### Evidence Fabric

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [ADR-006](adr-006-evidence-determinism.md) | Evidence Determinism | ACCEPTED | 2026-01-15 |
| [ADR-014](adr-014-evidence-severity-model.md) | Evidence Severity Model | ACCEPTED | 2026-02-05 |
| [ADR-016](adr-016-evidence-bundle-lifecycle.md) | Evidence Bundle Lifecycle | ACCEPTED | 2026-02-10 |
| [ADR-020](adr-020-evidence-correlation-determinism.md) | Evidence Correlation Determinism | ACCEPTED | 2026-02-20 |
| [ADR-022](adr-022-evidence-compression.md) | Evidence Compression | ACCEPTED | 2026-02-25 |
| [ADR-024](adr-024-evidence-diffing.md) | Evidence Diffing | ACCEPTED | 2026-03-03 |
| [ADR-026](adr-026-evidence-lifecycle-guarantees.md) | Evidence Lifecycle Guarantees | ACCEPTED | 2026-03-08 |

### Substrate & Packaging

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [ADR-028](adr-028-monorepo-consolidation-gos-integration.md) | Monorepo Consolidation and GOS Integration | ACCEPTED | 2026-04-15 |
| [ADR-029](adr-029-substrate-v1-ready-for-release.md) | Substrate v1 Ready for Release | ACCEPTED | 2026-04-16 |
| [ADR-030](adr-030-pre-uiao-terminology-reconciliation.md) | Pre-UIAO Terminology Reconciliation | ACCEPTED | 2026-04-17 |
| [ADR-031](adr-031-namespace-package-rename.md) | Python Package uiao_impl → uiao.impl (PEP 420 Namespace) | ACCEPTED | 2026-04-17 |
| [ADR-032](adr-032-single-package-consolidation.md) | Single-Package Consolidation — flatten src/uiao/ | ACCEPTED | 2026-04-20 |
| [ADR-044](adr-044-substrate-governance-realignment.md) | Substrate Governance Realignment to Post-ADR-032 Single Package | ACCEPTED | 2026-04-23 |
| [ADR-046](adr-046-cli-surface-convention.md) | CLI Surface Convention: Sub-App-per-Domain | ACCEPTED | 2026-04-23 |

### Boundary & Compliance

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [ADR-033](adr-033-gcc-boundary-drift-class.md) | GCC Boundary Drift Class and Compensating Controls Architecture | PROPOSED | 2026-04-19 |
| [ADR-043](adr-043-fedramp-rfc-0026-ca7-integration.md) | FedRAMP RFC-0026 (CA-7 Continuous Monitoring Expectations) — UIAO Integration | PROPOSED | 2026-04-21 |
| [ADR-045](adr-045-scan-redaction-policy.md) | Scan Artifact Redaction Policy for Multi-Agency Distribution | PROPOSED | 2026-04-23 |

### Device & Identity Modernization

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [ADR-034](adr-034-three-plane-device-model.md) | Three-Plane Device Model and OrgPath Plane-Aware Architecture | PROPOSED | 2026-04-20 |
| [ADR-035](adr-035-orgpath-codebook-binding.md) | OrgPath Codebook — Executable Canon Binding | ACCEPTED | 2026-04-20 |
| [ADR-036](adr-036-dynamic-group-provisioning.md) | Dynamic Group Library — Executable Canon + Entra Provisioning Adapter | ACCEPTED | 2026-04-20 |
| [ADR-037](adr-037-admin-unit-provisioning.md) | Delegation Matrix — Executable Canon + Entra AU/Role Provisioning Adapter | ACCEPTED | 2026-04-20 |
| [ADR-038](adr-038-device-plane-orgpath.md) | Device-Plane OrgPath Provisioning — Graph + ARM Dual-Transport Adapter | ACCEPTED | 2026-04-20 |
| [ADR-039](adr-039-policy-targeting.md) | OrgTree Policy Targeting — Intune + Azure Policy Dual Transport | ACCEPTED | 2026-04-20 |
| [ADR-040](adr-040-drift-engine.md) | OrgTree Drift Detection Engine — Six-Phase Orchestrator | ACCEPTED | 2026-04-20 |
| [ADR-041](adr-041-uiao-git-infrastructure.md) | UIAO Git Infrastructure — Self-Hosted Git on Windows Server 2025 + IIS | ACCEPTED | 2026-05-12 |
| [ADR-042](adr-042-ad-computer-conversion-guide-integration.md) | AD Computer Conversion Guide — Canonical Input to Phase 4 Device Planes | DRAFT | 2026-04-20 |

### Microsoft Coverage

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [ADR-048](adr-048-orgpath-attribute-selection.md) | OrgPath Attribute Selection — extensionAttributes over Custom Security Attributes | ACCEPTED | 2026-04-28 |
| [ADR-049](adr-049-microsoft-adapter-coverage-expansion.md) | Microsoft Modernization Adapter Coverage Expansion — Defender Suite, Azure Migrate, Azure Policy for Arc, Entra Governance, Entra Workload ID, Intune-Modernization | ACCEPTED | 2026-04-30 |
| [ADR-050](adr-050-reference-middleware-implementation-choices.md) | D3.1 Reference Middleware — Runtime, Language, Packaging, and Test Choices | ACCEPTED | 2026-04-30 |

> **ADR-048 numbering note:** Two files share the ADR-048 slot on disk:
> `adr-048-orgpath-attribute-selection.md` (canonical OrgPath attribute selection decision, ACCEPTED 2026-04-28)
> and `adr-048-orgpath-attribute-storage-decision.md` (status: "Current", appears to be a UIAO-V0 Canonical Architecture Volume document mislabeled with an ADR filename).
> Maintainer action required: assign a distinct ADR number or retire the second file.

### Federal Federation Block

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [ADR-051](adr-051-saml-trust-anchor.md) | SAML as a Third Trust-Anchor Type for Application Identity | ACCEPTED | 2026-05-04 |
| [ADR-052](adr-052-piv-usaccess-adapter.md) | PIV / USAccess Conformance Adapter — Federal Personnel Trust-Anchor Authority | ACCEPTED | 2026-05-04 |
| [ADR-053](adr-053-opm-azure-apim-adapter.md) | OPM Azure APIM Integration Adapter — Centralized Federal API Gateway Authority | ACCEPTED | 2026-05-04 |
| [ADR-054](adr-054-single-ato-reciprocity.md) | Single-ATO Reciprocity Model — Multi-Tenant Authorization Boundary | ACCEPTED | 2026-05-04 |
| [ADR-055](adr-055-customer-identity-canon-block.md) | Customer Identity Canon Block — KYC Protocol & Reciprocal Attribute Exchange | ACCEPTED | 2026-05-05 |
| [ADR-056](adr-056-login-gov-activation-contract.md) | Login.gov Federation Service — Activation Contract (Stage 2) | ACCEPTED | 2026-05-05 |

### Mission Themes

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [ADR-065](adr-065-hrit-productization-mission.md) | HRIT Single-ATO Productization as v0.6.0 Mission Theme | ACCEPTED | 2026-05-11 |

> **Renumber note:** ADR-065 was originally drafted as ADR-058 (proposed
> 2026-05-06). Renumbered to ADR-065 to resolve slot collision with
> `adr-058-microsoft-purview-conformance-adapter-coverage.md` (accepted
> 2026-05-07). Backfilled-accepted on 2026-05-11; runtime work shipped
> via PR #422.

### Speculative / Queued

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [ADR-057](adr-057-thousandeyes-networks-pillar-scope.md) | ThousandEyes — Networks-Pillar Conditional Adoption Under GCC-Moderate — Proposed | PROPOSED | 2026-04-27 |
| [ADR-066](adr-066-application-aware-networking-and-token-bound-transport.md) | Application-Aware Networking and Token-Bound Transport Plane | PROPOSED | 2026-05-05 |

### ADR-047 Numbering Collision

Two files share the ADR-047 slot on disk. Maintainer action required to establish the canonical mapping:

| File | Title | Status | Date |
|------|-------|--------|------|
| [adr-047-continuous-monitoring-program.md](adr-047-continuous-monitoring-program.md) | Continuous Monitoring Program and Customer Documentation Platform Architecture | PROPOSED | 2026-04-14 |
| [adr-047-fedramp-20x-integration.md](adr-047-fedramp-20x-integration.md) | FedRAMP 20x Integration — KSI emission and Minimum Assessment Scope adoption | PROPOSED | 2026-04-27 |

> One of these files must be renumbered before the ADR-047 slot can be treated as canonically resolved.

### ADR-057 Numbering Collision (resolved 2026-05-12)

The collision is resolved: `adr-057-application-aware-networking-and-token-bound-transport.md`
has been renumbered to **ADR-066** (`adr-066-application-aware-networking-and-token-bound-transport.md`).
ADR-057 now belongs solely to `adr-057-thousandeyes-networks-pillar-scope.md`.

## Recent ADRs (032–064, post-consolidation)

> Theme classification for these ADRs is deferred — the themes above were
> defined pre-consolidation and re-categorizing the post-consolidation
> body of ADRs is its own cleanup task. Listed chronologically by ADR
> number.

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [ADR-032](adr-032-single-package-consolidation.md) | Single-Package Consolidation — flatten src/uiao/ | ACCEPTED | 2026-04-20 |
| [ADR-033](adr-033-gcc-boundary-drift-class.md) | GCC Boundary Drift Class and Compensating Controls Architecture | PROPOSED | 2026-04-19 |
| [ADR-034](adr-034-three-plane-device-model.md) | Three-Plane Device Model and OrgPath Plane-Aware Architecture | PROPOSED | 2026-04-20 |
| [ADR-035](adr-035-orgpath-codebook-binding.md) | OrgPath Codebook — Executable Canon Binding | ACCEPTED | 2026-04-20 |
| [ADR-036](adr-036-dynamic-group-provisioning.md) | Dynamic Group Library — Executable Canon + Entra Provisioning Adapter | ACCEPTED | 2026-04-20 |
| [ADR-037](adr-037-admin-unit-provisioning.md) | Delegation Matrix — Executable Canon + Entra AU/Role Provisioning Adapter | ACCEPTED | 2026-04-20 |
| [ADR-038](adr-038-device-plane-orgpath.md) | Device-Plane OrgPath Provisioning — Graph + ARM Dual-Transport Adapter | ACCEPTED | 2026-04-20 |
| [ADR-039](adr-039-policy-targeting.md) | OrgTree Policy Targeting — Intune + Azure Policy Dual Transport | ACCEPTED | 2026-04-20 |
| [ADR-040](adr-040-drift-engine.md) | OrgTree Drift Detection Engine — Six-Phase Orchestrator | ACCEPTED | 2026-04-20 |
| [ADR-041](adr-041-uiao-git-infrastructure.md) | UIAO Git Infrastructure — Self-Hosted Git on Windows Server 2025 + IIS | ACCEPTED | 2026-05-12 |
| [ADR-042](adr-042-ad-computer-conversion-guide-integration.md) | AD Computer Conversion Guide — Canonical Input to Phase 4 Device Planes | DRAFT | 2026-04-20 |
| [ADR-043](adr-043-fedramp-rfc-0026-ca7-integration.md) | FedRAMP RFC-0026 (CA-7 Continuous Monitoring Expectations) — UIAO Integration | ACCEPTED | 2026-04-21 |
| [ADR-044](adr-044-substrate-governance-realignment.md) | Substrate Governance Realignment to Post-ADR-032 Single Package | ACCEPTED | 2026-04-23 |
| [ADR-045](adr-045-scan-redaction-policy.md) | Scan Artifact Redaction Policy for Multi-Agency Distribution | PROPOSED | 2026-04-23 |
| [ADR-046](adr-046-cli-surface-convention.md) | CLI Surface Convention: Sub-App-per-Domain | ACCEPTED | 2026-04-23 |
| [ADR-047a](adr-047-continuous-monitoring-program.md) | Continuous Monitoring Program and Customer Documentation Platform Architecture | PROPOSED | 2026-04-14 |
| [ADR-047b](adr-047-fedramp-20x-integration.md) | FedRAMP 20x Integration — KSI emission and Minimum Assessment Scope adoption | PROPOSED | 2026-04-27 |
| [ADR-048](adr-048-orgpath-attribute-selection.md) | OrgPath Attribute Selection — extensionAttributes over Custom Security Attributes | ACCEPTED | 2026-04-28 |
| [ADR-049](adr-049-microsoft-adapter-coverage-expansion.md) | Microsoft Modernization Adapter Coverage Expansion | ACCEPTED | 2026-04-30 |
| [ADR-050](adr-050-reference-middleware-implementation-choices.md) | D3.1 Reference Middleware — Runtime, Language, Packaging, and Test Choices | ACCEPTED | 2026-04-30 |
| [ADR-051](adr-051-saml-trust-anchor.md) | SAML as a Third Trust-Anchor Type for Application Identity | ACCEPTED | 2026-05-04 |
| [ADR-052](adr-052-piv-usaccess-adapter.md) | PIV / USAccess Conformance Adapter — Federal Personnel Trust-Anchor Authority | ACCEPTED | 2026-05-04 |
| [ADR-053](adr-053-opm-azure-apim-adapter.md) | OPM Azure APIM Integration Adapter — Centralized Federal API Gateway Authority | ACCEPTED | 2026-05-04 |
| [ADR-054](adr-054-single-ato-reciprocity.md) | Single-ATO Reciprocity Model — Multi-Tenant Authorization Boundary | ACCEPTED | 2026-05-04 |
| [ADR-055](adr-055-customer-identity-canon-block.md) | Customer Identity Canon Block — KYC Protocol & Reciprocal Attribute Exchange | ACCEPTED | 2026-05-05 |
| [ADR-056](adr-056-login-gov-activation-contract.md) | Login.gov Federation Service — Activation Contract (Stage 2) | ACCEPTED | 2026-05-05 |
| [ADR-057](adr-057-thousandeyes-networks-pillar-scope.md) | ThousandEyes — Networks-Pillar Conditional Adoption Under GCC-Moderate | PROPOSED | 2026-04-27 |
| [ADR-058](adr-058-microsoft-purview-conformance-adapter-coverage.md) | Microsoft Purview Conformance Adapter Coverage — Audit, DLP, Information Protection, Insider Risk | ACCEPTED | 2026-05-07 |
| [ADR-059](adr-059-sailpoint-adapter-family.md) | SailPoint NERM Adapter — Boundary-Exception Carve-Out and Slot Allocation | ACCEPTED | 2026-05-07 |
| [ADR-060](adr-060-mod-namespace-flatten-into-uiao-canon.md) | Flatten MOD_xxx Namespace into UIAO_NNN Canon — Single-Registry Consolidation | PROPOSED | 2026-05-10 |
| [ADR-061](adr-061-fedramp-cr26-catalog-vendoring.md) | FedRAMP CR26 Catalog Vendoring — Authority Posture, Pin Discipline, and Optional `oscal-cli` Round-Trip | PROPOSED | 2026-05-10 |
| [ADR-062](adr-062-orgpath-depth-extension.md) | OrgPath Hierarchy Depth Extension — 4 Levels to 8 Levels | ACCEPTED | 2026-04-26 |
| [ADR-063](adr-063-orgpath-storage-slot-binding.md) | OrgPath Storage Slot — extensionAttribute1 Binding | ACCEPTED | 2026-05-11 |
| [ADR-064](adr-064-drift-schema-slot-occupied-subclass.md) | DRIFT-SCHEMA::slot-occupied — Sub-class for Pre-existing Non-OrgPath Values | ACCEPTED | 2026-05-11 |
| [ADR-065](adr-065-hrit-productization-mission.md) | HRIT Single-ATO Productization as v0.6.0 Mission Theme (renumbered from ADR-058) | ACCEPTED | 2026-05-11 |
| [ADR-066](adr-066-application-aware-networking-and-token-bound-transport.md) | Application-Aware Networking and Token-Bound Transport Plane (renumbered from ADR-057) | PROPOSED | 2026-05-05 |
| [ADR-070](adr-070-foundational-primacy-charter-tier.md) | Foundational Primacy — Charter Tier and Amendment Process | ACCEPTED | 2026-05-15 |
| [ADR-074](adr-074-drift-ssot-contention.md) | DRIFT-SSOT-CONTENTION — New Drift Class for Data-Plane Stewardship Authority | PROPOSED | 2026-05-18 |
| [ADR-075](adr-075-surface-hub-reconciliation.md) | Surface Hub Reconciliation with ADR-001 — Meeting-Room Class as Migration-Only Carve-Out | ACCEPTED | 2026-05-18 |

### Known frontmatter inconsistencies (deferred for separate cleanup)

- `adr-033-gcc-boundary-drift-class.md` declares `id: ADR-030` in frontmatter; filename is the source of truth.
- `adr-034-three-plane-device-model.md` declares `id: ADR-031` in frontmatter; filename is the source of truth.
- ADR-047 has two files (`continuous-monitoring-program` and `fedramp-20x-integration`) — duplicate ADR number, listed as 047a / 047b.

## ADR Governance Rules

Per CR-003 (ADR Immutability), once an ADR is ACCEPTED:

- The Context, Decision, and Date fields are immutable
- Amendments require a new superseding ADR
- The superseded ADR must include `superseded_by: ADR-MMM`

All ADR changes require Governance Plane approval. See [ADR-000](adr-000-adr-process.md) for the full process.

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
