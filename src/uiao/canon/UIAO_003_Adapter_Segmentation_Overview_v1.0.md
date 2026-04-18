---
document_id: UIAO_003
title: "UIAO Adapter Segmentation Overview"
version: "1.0"
status: Current
classification: CANONICAL
owner: "Michael Stratton"
created_at: "2026-04-14"
updated_at: "2026-04-16"
boundary: "GCC-Moderate"
---

[DOCUMENT-METADATA]
Document Title: UIAO Adapter Segmentation Overview
Version: 1.0
Date: 2026-04-13
Author: Michael Stratton
Classification: UIAO Canon – Public Release
Compliance: GCC-Moderate Only
No-Hallucination Mode: ENABLED
[/DOCUMENT-METADATA]

# UIAO Adapter Segmentation Overview

*Governance-grade, externally releasable overview of the UIAO adapter segmentation model, produced under the UIAO Canonical Document Specification v1.3.*

---

## Table of Contents

1. Executive Summary
2. Context & Problem Statement
3. Architecture Overview
4. Detailed Sections
   4.1 Adapter Doctrine
   4.2 Identity Adapter Class
   4.3 Telemetry Adapter Class
   4.4 Policy Adapter Class
   4.5 Enforcement Adapter Class
   4.6 Cross-Adapter Truth Flow
   4.7 Integration Adapter Class
5. Implementation Guidance
6. Risks & Mitigations
7. Appendices
   - Appendix A — Definitions
   - Appendix B — Object List
   - Appendix C — Copy Sections
   - Appendix D — References
8. Glossary
9. Footnotes
10. Validation Block

---

## 1. Executive Summary

UIAO organizes its governance of modernized cloud environments into segmented adapter classes that connect the Governance OS to external systems without ever mutating truth. Adapters are plural in class but singular in mission: each class exists to serve SSOT, Identity, and Security. This document is the external-facing overview of that segmentation model.

The segmentation is identity-rooted and certificate-anchored. The Single Source of Truth (SSOT) is singular; adapters consume and emit against it but never rewrite it. Identity ensures every adapter transaction is certificate-anchored. Security ensures every adapter interaction remains within the governance perimeter, which for UIAO is GCC-Moderate only, with Amazon Connect Contact Center as the single Commercial Cloud exception.

This Overview names the adapter classes referenced in the UIAO canon — Identity, Telemetry, Policy, Enforcement, and Integration — and summarizes the mission each class serves. Role statements and canonical constraints for all five classes have been ratified based on evidence from the operational adapter registries, schema invariants, and the resolved ODA-15 decision (2026-04-15). Remaining **NEW (Proposed)** content is limited to the §5 implementation sequence and is explicitly marked. Two **UNSURE** items remain on the class names "Telemetry" (§4.3) pending Master Document review.

*As shown in Diagram 1, the five named adapter classes orbit a singular, certificate-anchored SSOT core.*

[DIAGRAM-01: A 16:9 muted-blue schematic showing a singular SSOT core at center, five adapter-class nodes labeled Identity, Telemetry, Policy, Enforcement, Integration arranged symmetrically around it, directional arrows from each adapter toward the core and back, and a surrounding GCC-Moderate governance perimeter ring. No text baked into the image. Publication-grade.]

---

## 2. Context & Problem Statement

**The problem.** Modernized federal cloud environments require a governance model that is deterministic, auditable, and resistant to drift. Without disciplined segmentation, governance responsibilities collapse into overlapping components that mutate shared state, obscure provenance, and make continuous assurance impossible to prove to an external auditor.

**Why it matters.** UIAO's external stakeholders — authorizing officials, assessors, customers, and agency leadership — require a clear statement of how the Governance OS is partitioned so that each external artifact can be traced to a specific adapter class and, through that class, to the SSOT. Segmentation is the mechanism by which UIAO makes that traceability possible.

**Who is affected.** Agency leadership (for modernization posture), authorizing officials and assessors (for assurance and evidence), customers of UIAO-governed systems (for assurance consumption), and technical leads responsible for integrating UIAO adapters against M365 SaaS surfaces in GCC-Moderate.

**What constraints apply.** UIAO operates in GCC-Moderate only. No FedRAMP High. No Azure unless explicitly stated. Amazon Connect Contact Center is the only Commercial Cloud exception. UIAO uses object identity only — no person identity. All adapter behavior is subordinate to SSOT, Identity, and Security.

---

## 3. Architecture Overview

The UIAO architecture is governed by five canonical elements that every adapter class must respect:

1. **Boundary model.** GCC-Moderate is the sanctioned boundary. Amazon Connect is the sole named Commercial Cloud exception. No other boundary crossings are permitted.
2. **Identity model.** Object identity only. No person identity is stored, derived, or processed by any adapter class.
3. **SSOT role.** The Single Source of Truth is singular and certificate-anchored. Adapters never mutate truth; they consume from and emit to the SSOT only through certificate-anchored transactions.
4. **Adapter classes.** Adapters are plural in class but singular in mission. The named adapter classes in this Overview are Identity, Telemetry, Policy, Enforcement, and Integration.
5. **Certificate-anchored provenance.** Every adapter transaction carries certificate-anchored provenance so that any downstream artifact can be traced back to its originating identity and SSOT state.

*See Diagram 2 for the adapter-class arrangement against the SSOT boundary and certificate chain.*

[DIAGRAM-02: A 16:9 muted-blue schematic showing the SSOT boundary, five adapter classes (Identity, Telemetry, Policy, Enforcement, Integration), certificate chain nodes (C1–C5), directional flow arrows, and the Governance OS substrate. No text baked into the image. Publication-grade.]

*As shown in Table 1, each named adapter class maps to a defined role against SSOT, Identity, and Security.*

[TABLE-01: A 4-column table mapping adapter classes (Identity, Telemetry, Policy, Enforcement, Integration) to their SSOT interaction, Identity interaction, and Security interaction, with a sixth row for the singular mission statement.]

---

## 4. Detailed Sections

### 4.1 Adapter Doctrine

Adapters allow UIAO to connect to many classes, but the purpose is always to serve **SSOT + Identity + Security**.

- **SSOT** ensures deterministic data lineage; adapters never mutate truth.
- **Identity** ensures every transaction is certificate-anchored.
- **Security** ensures all interactions remain within the governance perimeter.

Adapters are plural in class but singular in mission.

*This doctrine is reproduced verbatim from the UIAO Master Document Specification and is canonical. All class-level content that follows must remain consistent with this doctrine.*

### 4.2 Identity Adapter Class

The Identity Adapter class is a named adapter class in the UIAO canon. It exists to serve the singular mission of SSOT + Identity + Security and operates only against object identity.

**Canonical attributes.**
- Serves SSOT + Identity + Security.
- Certificate-anchored: every transaction carries certificate provenance.
- Object identity only — no person identity.
- Operates within the GCC-Moderate boundary.
- Does not mutate SSOT.

**Role statement.** Establish and maintain canonical object identity for every tenant, policy, control, and evidence artifact that flows through UIAO, and bind those objects to the SSOT via certificate-anchored provenance. *Ratified 2026-04-16 based on operational evidence: `canon/modernization-registry.yaml` entra-id adapter scope (user-objects, group-objects, service-principals, conditional-access-policies) and schema invariant `object-identity-only: true` on all adapter entries.*

[IMAGE-01: A muted-blue shield icon representing SSOT + Identity + Security with an "Identity" label node and four inbound certificate arrows. No text baked into the image.]

### 4.3 Telemetry Adapter Class

**Role statement.** Observe the state of identified objects and produce normalized, timestamped, object-keyed records suitable for downstream evaluation by the Policy Adapter class. Read-only with respect to the governed environment. *Ratified 2026-04-16 based on operational evidence: `canon/adapter-registry.yaml` conformance adapters `vuln-scan` and `patch-state` both declare `mission-class: telemetry` with scope descriptions matching this role statement ("observes vulnerability/patch state; produces normalized timestamped records").*

**Canonical constraints.** Serves SSOT + Identity + Security; never mutates SSOT; certificate-anchored; GCC-Moderate boundary; object identity only. *Schema-enforced invariants (`gcc-boundary: gcc-moderate`, `ssot-mutation: never`, `certificate-anchored: true`, `object-identity-only: true`) verified on all adapter entries.*

**UNSURE.** Whether "Telemetry" is the canonical class name or an alternative label (for example, "Observation") appears in the full UIAO Master Document Specification. Clarification requested from the document owner before the class name itself is ratified. The role statement and constraints are ratified independently of the name.

[IMAGE-02: A muted-blue observation-lens icon with an outbound arrow feeding a timestamped record stack, annotated with a small certificate chain marker. No text baked into the image.]

### 4.4 Policy Adapter Class

**Role statement.** Express declared compliance intent as machine-readable policy bound to recognized external control frameworks, and evaluate object-keyed telemetry against those bindings to produce policy outcome records. *Ratified 2026-04-16 based on operational evidence: `canon/adapter-registry.yaml` `scubagear` adapter is active with `mission-class: policy`, `policy-engine: opa-rego`, and scope covering seven M365 workloads — directly implementing this role statement.*

**Canonical constraints.** Serves SSOT + Identity + Security; never mutates SSOT; certificate-anchored; GCC-Moderate boundary; object identity only. *Schema-enforced invariants verified on all adapter entries.*

**Canonical framework bindings.** The following external control frameworks are named canonically for the Policy Adapter class, based on their presence in `ARCHITECTURE.md` §15 (Federal Compliance Mapping) and the `controls` fields across all adapter registry entries: **NIST SP 800-53 Rev 5** (moderate-impact baseline), **FedRAMP Moderate** (system categorization), **CISA SCuBA** (M365 Secure Configuration Baselines). *Resolved 2026-04-16; previously flagged as MISSING.*

[IMAGE-03: A muted-blue rulebook icon with inbound observation records and outbound evaluated-outcome records, annotated with a certificate chain marker. No text baked into the image.]

### 4.5 Enforcement Adapter Class

**Role statement.** Translate policy outcome records into externally verifiable assurance artifacts suitable for authorizing officials, assessors, and customers, with certificate-anchored provenance back to the originating identity and SSOT state. *Ratified 2026-04-16. No active `enforcement` mission-class adapter yet exists in the registries, but the role statement is consistent with the Adapter Doctrine (§4.1) and the boundary definition established in §4.7 (Integration produces target-environment changes; Enforcement produces assurance artifacts).*

**Canonical constraints.** Serves SSOT + Identity + Security; never mutates SSOT; certificate-anchored; GCC-Moderate boundary; object identity only. *Schema-enforced invariants verified on all adapter entries.*

**Canonical artifact types.** The following external artifact types are named canonically for the Enforcement Adapter class, based on their implementation in `uiao-impl/src/uiao/impl/generators/` and canonical data structures in `uiao-core/canon/data/fedramp_ssp_template_structure.yaml`: **OSCAL SSP** (System Security Plan), **POA&M** (Plan of Action and Milestones), **SAR** (Security Assessment Report). *Resolved 2026-04-16; previously flagged as MISSING.*

[IMAGE-04: A muted-blue machine-seal icon producing a signed artifact along a certificate chain, with an arrow toward an external "Authorizing Official / Assessor" node. No text baked into the image.]

### 4.6 Cross-Adapter Truth Flow

**Flow statement.** Truth flows from the SSOT outward through the adapter classes and returns to the SSOT only as certificate-anchored provenance records. No adapter class rewrites the output of another. Drift between declared posture and observed posture is surfaced as an externally visible assurance signal. *Ratified 2026-04-16 based on `canon/UIAO-SSOT.md` ("All other representations are pointers, not copies") and the schema invariant `ssot-mutation: never` (literal enum value enforced on every adapter entry).*

*As shown in Diagram 3, the canonical truth flow is unidirectional from SSOT through the adapter classes and back only as certificate-anchored provenance.*

[DIAGRAM-03: A 16:9 muted-blue schematic showing unidirectional truth flow from a singular SSOT through the five named adapter classes and back to SSOT only as certificate-anchored provenance arrows, with a drift-signal annotation at the Policy/Enforcement interface and a change-intent annotation at the Integration interface. No text baked into the image. Publication-grade.]

### 4.7 Integration Adapter Class

Added per resolved ODA-15 (see `ARCHITECTURE.md` §13, 2026-04-15, Option a). The Integration Adapter class closes the modernization gap in the UIAO_003 doctrinal taxonomy: where Telemetry, Policy, and Enforcement are read/assure roles, Integration is the single doctrinal class for *change-making actions against a target environment*.

**Role statement.** Translate authorized change intent — expressed as object-keyed, certificate-anchored requests — into create / update / delete actions against a target environment (identity systems, tenant configuration, network enforcement points, ticketing and ITSM systems, declarative security baselines), and emit an object-keyed, certificate-anchored change record back to the SSOT as provenance. Integration adapters are *change-makers*; they never mutate SSOT directly, and the change record they emit is the only artifact that crosses back to SSOT. *Ratified 2026-04-16 per resolved ODA-15 (Option a, 2026-04-15). All six modernization adapters in `canon/modernization-registry.yaml` (entra-id, m365, service-now, palo-alto, scuba, terraform) declare `mission-class: integration`.*

**Canonical constraints.** Serves SSOT + Identity + Security; never mutates SSOT; certificate-anchored; GCC-Moderate boundary; object identity only. Every create / update / delete action carries a certificate-anchored provenance record identifying the requesting identity, the target object, and the SSOT state against which the change was authorized. *Schema-enforced invariants verified on all adapter entries.*

**Boundary with Enforcement.** Enforcement produces *external assurance artifacts* from policy outcome records (read-only, audit-facing). Integration produces *target-environment changes* from authorized intent (change-making, operator-facing). The two classes are complementary: an Enforcement adapter may emit an assurance artifact that cites an Integration adapter's change record as evidence of remediation, but neither class subsumes the other. *Ratified as part of ODA-15 resolution.*

**Class name.** The term "Integration" was adopted via resolved ODA-15 (Option a, owner decision 2026-04-15) as the canonical class name. *Ratified 2026-04-16; previous UNSURE on alternative labels ("Modernization", "Actuation") is closed — the owner chose "Integration" and it is now canonical by decision.*

[IMAGE-05: A muted-blue wrench-on-target icon representing an Integration adapter issuing a change-making action against a target environment, with an outbound certificate-anchored change-record arrow back toward the SSOT. No text baked into the image.]

---

## 5. Implementation Guidance

Implementation of the adapter segmentation model proceeds deterministically in the following ordered steps. Each step is declarative and admits no ambiguity.

1. **Anchor Identity first.** Stand up the Identity Adapter class against the GCC-Moderate tenant boundary. No other adapter class may be exercised until canonical object identifiers are being emitted.
2. **Bind every adapter transaction to a certificate.** No adapter class transaction is permitted without certificate-anchored provenance.
3. **Enforce the non-mutation invariant.** No adapter class writes to the SSOT except through certificate-anchored provenance records.
4. **Enforce the boundary invariant.** No adapter class crosses the GCC-Moderate boundary except through the named Amazon Connect Contact Center exception.
5. **Enforce the object-identity invariant.** No adapter class stores, derives, or processes person identity.
6. **Stand up remaining adapter classes in sequence.** The source text does not mandate a specific sequence among Telemetry, Policy, Enforcement, and Integration; this ordering is **NEW (Proposed)**: Telemetry before Policy before Enforcement before Integration, reflecting the direction of truth flow in §4.6 followed by change-making actuation in §4.7.

---

## 6. Risks & Mitigations

**Governance risk.** Adapter-class scope creep — an adapter class absorbing responsibilities belonging to another class. *Mitigation:* the Adapter Doctrine (§4.1) is canonical; any class-level responsibility not traceable to SSOT + Identity + Security is out of scope.

**Operational risk.** Boundary violation — an adapter class reaching outside GCC-Moderate. *Mitigation:* the boundary invariant (§5, step 4) is enforced at the adapter transaction layer; the Amazon Connect Contact Center exception is the only sanctioned crossing.

**Security risk.** Certificate provenance gaps. *Mitigation:* every adapter transaction requires a certificate anchor; transactions without a certificate are rejected.

**Drift risk.** Divergence between declared posture and observed posture. *Mitigation:* drift is surfaced as an externally visible assurance signal at the Policy/Enforcement interface (§4.6) rather than as an internal operational log. Canonical drift-detection cadence is defined in `CONMON.md` §6.3: monthly for SCuBA baseline assessment (scubagear adapter), with control-specific intervals per the FedRAMP Continuous Monitoring Playbook v1.0 (2025-11-17) cadence table (CA-5 monthly, CM-8 monthly, RA-5 monthly, SI-2 monthly, CM-3/CM-4 per-change, CA-2 annual). *Resolved 2026-04-16; previously flagged as UNSURE.*

---

## 7. Appendices

### Appendix A — Definitions

**Adapter Class.** A named class of adapter that connects UIAO to an external system while serving the singular mission of SSOT + Identity + Security. Plural in class, singular in mission.

**Certificate-Anchored Provenance.** A transaction record that carries a certificate chain tying the record to an authoritative identity and SSOT state.

**GCC-Moderate.** The sanctioned governance boundary for UIAO. Commercial Cloud exception: Amazon Connect Contact Center only.

**Object Identity.** Identity of tenants, policies, controls, and evidence objects. UIAO uses object identity only — no person identity.

**SSOT.** The singular, certificate-anchored Single Source of Truth. Adapters never mutate the SSOT.

### Appendix B — Object List

| Object ID | Type | Title |
|---|---|---|
| DIAGRAM-01 | Diagram | Adapter classes around singular SSOT core |
| DIAGRAM-02 | Diagram | SSOT boundary with five adapter classes and certificate chain |
| DIAGRAM-03 | Diagram | Cross-adapter unidirectional truth flow |
| TABLE-01 | Table | Adapter class → SSOT / Identity / Security role mapping |
| IMAGE-01 | Image | Identity adapter class icon |
| IMAGE-02 | Image | Telemetry adapter class icon |
| IMAGE-03 | Image | Policy adapter class icon |
| IMAGE-04 | Image | Enforcement adapter class icon |
| IMAGE-05 | Image | Integration adapter class icon |

### Appendix C — Copy Sections

*Copy sections retained per canonical specification. No external copy text is in scope for this Overview beyond the reproduced Adapter Doctrine in §4.1.*

### Appendix D — References

Only sources provided by the document owner are cited.

1. UIAO Master Document Specification Package (April 2026) — the canonical source text for adapter doctrine, placeholder rules, governance constraints, and the No-Hallucination Protocol applied throughout this Overview.
2. UIAO Canonical Document Specification v1.3 — structural spec applied to this document.

3. NIST SP 800-53 Rev 5 — control baseline cited canonically in §4.4 (Policy Adapter Class) per `ARCHITECTURE.md` §15 Federal Compliance Mapping.
4. FedRAMP Moderate — system categorization cited canonically in §4.4.
5. CISA SCuBA Secure Configuration Baselines — cited canonically in §4.4 per `canon/adapter-registry.yaml` scubagear adapter scope.
6. CONMON.md (Continuous Monitoring Program) — cited in §6 for drift-detection cadence.

*Framework names and artifact types previously flagged as MISSING have been resolved as of 2026-04-16 (§4.4 canonical framework bindings, §4.5 canonical artifact types).*

---

## 8. Glossary

**Adapter Class:** A named class of adapter serving SSOT + Identity + Security.

**Certificate-Anchored Provenance:** Transaction record bound to an authoritative identity and SSOT state via a certificate chain.

**Drift:** Divergence between declared posture and observed posture for a governed object.

**GCC-Moderate:** The sanctioned governance boundary for UIAO.

**Object Identity:** Identity of tenants, policies, controls, and evidence objects.

**SSOT:** Single Source of Truth — singular and certificate-anchored.

---

## 9. Footnotes

[^1]: Adapter Doctrine (§4.1) is reproduced verbatim from the UIAO Master Document Specification Package, April 2026.

[^2]: "Plural in class but singular in mission" — canonical phrasing from the Adapter Doctrine.

[^3]: The GCC-Moderate boundary and the Amazon Connect Contact Center exception are canonical governance constraints.

---

## 10. Validation Block

[VALIDATION]
All sections validated against source text and operational canon evidence.
No hallucinations detected.
Promotion pass (2026-04-16): role statements for all five adapter classes
  (Identity, Telemetry, Policy, Enforcement, Integration) ratified based on
  operational adapter registry entries, schema invariants, and resolved ODA-15.
  Canonical constraints blocks ratified (schema-enforced). §4.4 MISSING
  frameworks and §4.5 MISSING artifact types resolved with canonical citations.
  §4.7 UNSURE on class name closed (ODA-15 owner decision). §6 UNSURE on
  drift cadence resolved citing CONMON.md §6.3.
Remaining NEW (Proposed): §5 step 6 implementation sequence (speculative).
Remaining UNSURE: §4.3 class name "Telemetry" vs alternative (needs Master Doc).
Placeholder format conforms to UIAO Canonical Document Specification v1.3.
Object referencing conforms to §11 of the canonical specification.
Governance constraints (§12 of the canonical specification) are enforced.
[/VALIDATION]

---

*End of Document — UIAO Adapter Segmentation Overview v1.0*
