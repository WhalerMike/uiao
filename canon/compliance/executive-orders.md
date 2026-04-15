---
document_id: UIAO_004
title: "UIAO Compliance with Presidential Executive Orders"
version: "1.0"
status: Current
classification: CANONICAL
owner: "Michael Stratton"
created_at: "2026-04-15"
updated_at: "2026-04-15"
boundary: "GCC-Moderate"
---

# UIAO Compliance with Presidential Executive Orders

> **Purpose.** This document is the canonical mapping between UIAO
> (Unified Identity-Addressing-Overlay Architecture) and the Presidential
> Executive Orders whose provisions UIAO is architected to help Federal
> agencies implement.
>
> **Scope.** Narrowly focused on the three Executive Orders — plus the
> March 2026 *President Trump's Cyber Strategy for America* — whose
> provisions directly drive UIAO's design themes: Zero Trust
> architecture, federal cybersecurity modernization, FedRAMP / cloud
> transition, post-quantum cryptography, and continuous compliance. Other
> IT-adjacent EOs (workforce, ICTS supply-chain, bulk-power, AI
> leadership, DOGE) are **out of scope** for this document.
>
> **Provenance.** EO numbers, titles, and dates below are sourced from
> the Federal Register / GovInfo, White House presidential-actions
> archive, and Congressional Research Service analyses. Where an EO has
> been amended, the amending instrument is cited.
>
> **No-hallucination protocol.** UIAO artifacts that cite these EOs must
> cite them by the canonical number-and-date shown here. If a cited EO
> does not appear in this table, add it here first (with source) before
> referencing it from a downstream canon artifact.

## Scope themes and UIAO capabilities

UIAO's federal-cybersecurity value proposition rests on four capability
pillars. Each of the three EOs below maps to one or more of these
pillars.

| Pillar | UIAO artifact(s) |
|---|---|
| **Claims-based evidence fabric** | Evidence Graph Model (UIAO_113), SSOT (UIAO_001), SCuBA Technical Specification (UIAO_002) |
| **Adapter framework** | Adapter Registry (`canon/adapter-registry.yaml`), Adapter Segmentation Overview (UIAO_003) |
| **Drift detection** | Drift specification (UIAO_110), Compliance Orchestrator (UIAO_100) |
| **KSI provenance** | Enforcement Runtime (UIAO_111), Governance layer (UIAO_112), Modernization Registry (`canon/modernization-registry.yaml`) |

## EO 14144 — Strengthening and Promoting Innovation in the Nation's Cybersecurity

- **Signed:** January 16, 2025 (Biden administration)
- **Status:** Partially amended by EO 14306 (Trump, June 6, 2025). The
  third-party software supply-chain, post-quantum cryptography,
  AI-cyber, and IoT-security provisions are preserved.
- **Scope summary:** Expanded the EO 14028 (May 2021) cybersecurity
  baseline into four forward-looking domains: third-party software
  supply-chain attestation, quantum-resistant cryptography readiness,
  AI-specific cyber hardening, and Internet-of-Things device security.
  Further operationalized zero-trust adoption across federal networks.

### UIAO provisions that satisfy EO 14144

| EO 14144 provision | UIAO artifact | How UIAO satisfies it |
|---|---|---|
| Third-party software supply-chain attestation | Adapter Registry; SSOT schema | Every adapter registered in UIAO carries provenance, SBOM linkage, and attestation metadata. The SSOT schema treats attestations as first-class claims in the evidence fabric. |
| Post-quantum cryptography readiness | Zero-Trust Integration Layer (UIAO_120); SSOT crypto-agility metadata | Crypto primitives are tagged with agility metadata in the SSOT; adapters declare PQC-readiness at the registry boundary so Compliance Orchestrator can flag non-PQC-ready paths. |
| AI-specific cyber hardening | Enforcement Runtime (UIAO_111); adapter AI-boundary annotations | AI adapters carry an AI-boundary annotation that triggers additional enforcement rules (input/output provenance, model-artifact attestation). |
| IoT device security | Adapter Segmentation Overview (UIAO_003) | IoT adapters are segmented at the runtime boundary and must satisfy the IoT profile of the evidence fabric before being admitted to KSI runs. |
| Zero-trust federal networks | Zero-Trust Integration Layer (UIAO_120); Evidence Graph (UIAO_113) | UIAO's zero-trust layer records every policy-decision point as a claim in the evidence graph, producing continuous zero-trust telemetry for federal audit. |

## EO 14306 — Sustaining Select Efforts to Strengthen the Nation's Cybersecurity and Amending Executive Order 13694 and Executive Order 14144

- **Signed:** June 6, 2025 (Trump administration, second term)
- **Status:** In force. Controlling cybersecurity EO for UIAO.
- **Scope summary:** Preserves the cybersecurity mission of EOs 13694
  (cyber sanctions) and 14144 while redirecting federal regulatory and
  policy focus to: **(1)** third-party software supply-chain security,
  **(2)** quantum cryptography, **(3)** artificial intelligence, and
  **(4)** Internet-of-Things devices. Rolls back certain
  contractor-specific security requirements from the Biden-era
  baseline and amends the cyber sanctions regime.

### UIAO provisions that satisfy EO 14306

| EO 14306 provision | UIAO artifact | How UIAO satisfies it |
|---|---|---|
| Third-party software supply-chain security | Adapter Registry; SSOT; SCuBA Technical Specification (UIAO_002) | Adapter attestations are continuously validated against current supply-chain signals; SCuBA-driven evidence runs produce auditable supply-chain posture reports. |
| Quantum cryptography | Zero-Trust Integration Layer (UIAO_120); Drift spec (UIAO_110) | PQC-readiness is tracked as a first-class attribute; the drift engine flags agencies whose crypto posture regresses from PQC-ready to non-PQC-ready. |
| Artificial intelligence (cyber hardening) | Enforcement Runtime (UIAO_111); Evidence Graph (UIAO_113) | AI model-artifact provenance, prompt-boundary logging, and output attestation are captured as claims in the evidence graph. |
| Internet of Things | Adapter Segmentation Overview (UIAO_003) | IoT adapters operate in a segmented boundary with mandatory evidence-fabric participation. |
| Contractor-specific security rollback | Governance layer (UIAO_112); Modernization Registry | UIAO's governance layer exposes policy versioning so agencies can re-baseline contractor controls against the new EO 14306 posture without losing historical evidence. |
| Cyber sanctions regime changes | Adapter Registry country-of-origin metadata | Adapter country-of-origin is a first-class field; sanctions-regime changes re-evaluate adapter admissibility on the next Compliance Orchestrator run. |

## EO 14390 — Combating Cybercrime, Fraud, and Predatory Schemes Against American Citizens

- **Signed:** March 6, 2026 (Trump administration, second term)
- **Status:** In force.
- **Scope summary:** Directs federal law-enforcement, Treasury, and
  designated interagency bodies to disrupt cybercrime, fraud, and
  predatory-financial schemes targeting U.S. citizens. Accompanied by
  the *President Trump's Cyber Strategy for America* (March 2026), which
  sets strategic priorities across federal cybersecurity modernization,
  cloud transition, and efficient cybersecurity practice.

### UIAO provisions that satisfy EO 14390 and the Cyber Strategy for America

| EO 14390 / Cyber Strategy theme | UIAO artifact | How UIAO satisfies it |
|---|---|---|
| Forensic-grade evidence chains for cybercrime enforcement | Evidence Graph Model (UIAO_113); Evidence Bundle lifecycle (see `uiao-docs` ADR-016) | Evidence bundles progress through ASSEMBLING → SEALED → SUBMITTED → CLOSED lifecycle states; once SEALED, bundles are immutable and suitable for regulatory or law-enforcement submission. |
| Federal cybersecurity modernization | Modernization Registry (`canon/modernization-registry.yaml`); SCuBA Technical Specification (UIAO_002) | Modernization work items are tracked with EO provenance and outcome evidence; SCuBA provides the continuous-compliance baseline against which modernization is measured. |
| FedRAMP / cloud transition | Adapter Framework; Adapter Segmentation Overview (UIAO_003) | Cloud adapters are first-class UIAO objects with FedRAMP-boundary metadata (GCC-Moderate, GCC-High, DoD, Commercial); the GCC-Moderate baseline is declared in every repository's `CLAUDE.md`. |
| Efficient cybersecurity practice / continuous compliance | Compliance Orchestrator (UIAO_100); Drift spec (UIAO_110); KSI provenance (UIAO_111) | Compliance Orchestrator runs SCuBA and KSI evaluations on schedule; drift engine detects regression between runs; KSI provenance carries the reasoning chain for each compliance claim so agencies can answer "why" as well as "what". |
| Interagency data sharing for enforcement | SSOT (UIAO_001); Governance layer (UIAO_112) | SSOT claim identifiers are stable across agencies; governance layer controls per-agency visibility and redaction so interagency sharing remains compliant with privacy and classification rules. |

## Referenced instruments

- **EO 14028** — "Improving the Nation's Cybersecurity" (Biden, May 12,
  2021). Foundational. Explicitly preserved by EO 14306.
- **EO 13694** — Cyber sanctions framework. Amended by EO 14306.
- **President Trump's Cyber Strategy for America** — March 2026.
  Strategic companion to EO 14390.

## Explicit out-of-scope EOs

For traceability, the following IT-adjacent Executive Orders are **not**
addressed by this document and should not be cited as UIAO authorities:

- EO 13800 / 13833 / 13870 / 13873 / 13920 / 13942 / 13943 / 13984
  (Trump 1st term — covered by predecessor documents and superseded in
  relevant part by EO 14028 and EO 14306)
- EO 14148 (Rescissions — not a cyber EO)
- EO 14158 (DOGE — government efficiency, not UIAO's cybersecurity scope)
- EO 14179 + July 2025 AI Action Plan EOs + December 2025 AI-framework
  EO (AI-leadership, not cybersecurity)

If a downstream agency implementation requires UIAO support for any of
these out-of-scope EOs, open a Canon Change Request against `uiao-core`;
do not back-fill citations into this document without a traceable source.

## Maintenance

Update this document when:
1. An amending EO is signed against any of EO 14144 / 14306 / 14390.
2. The *President Trump's Cyber Strategy for America* is revised.
3. A UIAO artifact referenced in a mapping table is renamed, split, or
   deprecated.
4. An agency implementation requires a new UIAO-to-EO mapping and that
   mapping can be justified from the EO's operative text.

Updates must be accompanied by the `updated_at` frontmatter refresh and,
when the artifact registry changes, a corresponding edit to
`canon/document-registry.yaml`.
