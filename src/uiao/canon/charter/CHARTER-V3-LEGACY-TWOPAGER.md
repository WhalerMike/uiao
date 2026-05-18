---
document_id: CHARTER-V3-LEGACY-TWOPAGER
title: "UIAO Charter — V3 TwoPager (LEGACY, superseded by CHARTER-001)"
version: "1.0"
status: Deprecated
classification: CANONICAL
owner: Michael Stratton
boundary: GCC-Moderate
created_at: "2026-02-26"
updated_at: "2026-05-15"
tier: foundational
supersedable: true
superseded_by:
  - "CHARTER-001 (UIAO-V1, Mar 9 2026 — current authoritative charter)"
  - "CHARTER-002 + CHARTER-003 (V4U Core Canon Introduction + V4U Master Reference, Mar 7 2026)"
load_order: 0
charter_chain:
  - "V3 (Feb 26 2026): this document — original UIAO TwoPager executive summary"
  - "V4 / V4U (Mar 7-9 2026): unified merger of V4G/V4P/V4C audience variants — CHARTER-002 + CHARTER-003"
  - "UIAO-V1 (Mar 9 2026): current authoritative charter — CHARTER-001"
provenance:
  source: "OneDrive: Application_Aware_Networking_White_Paper_by_Mike/V3/TwoPager Unified Identity-Addressing-Overlay Architecture (v3).docx (Feb 26 2026 14:41)"
  version: "1.0"
  derived_at: "2026-05-15"
  derived_by: "Charter Restoration Plan PR-A5"
  editorial_pass: "Light — pandoc-converted via `pandoc -t gfm`. 91 non-breaking hyphens (U+2011) normalized to ASCII. Trailing AI-conversation drafting artifact (the source's last paragraph: 'If you want, I can now generate a single integrated briefing deck outline, a one-page executive graphic, or a federal ATO-ready narrative...') was stripped per ADR-070's editorial-pass mandate. Body otherwise preserved verbatim. Note: source uses bold pseudo-headings (`**Title**`) instead of markdown H1/H2; preserved as-is for legacy/provenance fidelity."
ingestion_role: "Provenance retention only. Executive-summary companion to CHARTER-V3-LEGACY-INTRO. Does NOT carry current canon authority."
v3_known_gaps: "OMB M-21-31 logging maturity (EL3) is mentioned in this TwoPager only and not in the V3 long-form Introduction. This was identified during the V4U/UIAO-V1 charter audit as a TwoPager-only mandate citation worth reconciling into long-form charter docs (see Charter Restoration Plan §Decisions still needed before PR 1, decision #6 — confirmed for reconciliation in long-form CHARTER-001)."
---

> **Supersession note (2026-05-15):** This document is the original
> V3 TwoPager (executive-summary form), dated Feb 26 2026. It is
> **explicitly superseded** by V4U (CHARTER-002 + CHARTER-003) and
> UIAO-V1 (CHARTER-001). It does **not carry current canon authority**.
>
> The TwoPager is the executive-summary companion to
> [CHARTER-V3-LEGACY-INTRO](CHARTER-V3-LEGACY-INTRO.md). Read this
> document for the original two-page executive framing before V4U
> unification. For current authoritative charter, read
> [CHARTER-001](CHARTER-001.md).

A two-page leadership briefing, a diagram-ready version, and a
congressional/oversight version each serve a different audience and
rhetorical purpose. To keep this clean and aligned with your v3
architecture, I’ll produce **all three**, each in its own fully-formed,
publication-ready format.

**1. Two-Page Leadership Briefing (SES / CIO / CTO / Chief Architect)**

*(~900 words, fits on two printed pages with standard margins)*

**Unified Identity-Addressing-Overlay Architecture (v3)**

**Executive Leadership Briefing**

Federal agencies are operating in increasingly complex hybrid-cloud
environments where mission-critical workloads—Microsoft 365
collaboration, voice/video communications, call centers, and hybrid
applications—must remain resilient, compliant, and low-latency across
on-premises and cloud boundaries. Traditional session-centric security
models cannot meet these requirements.

The Unified Identity-Addressing-Overlay Architecture (v3) establishes a
**deterministic, certificate-anchored control fabric** that unifies
identity, addressing, and overlay transport into a single cohesive
system. This model ensures continuity, compliance, and performance
across hybrid environments while aligning with Zero Trust (NIST SP
800-207), TIC 3.0, FIPS 140-3, E911 dispatchable-location mandates, and
FedRAMP Moderate cloud constraints.

**Mission Drivers**

- **Zero Trust enforcement** through certificate-anchored identity and
  continuous verification.

- **Hybrid-cloud performance and sovereignty**, ensuring low-latency
  operation across on-prem VMware vSphere, GCC Moderate cloud, and
  multi-cloud workloads.

- **E911 compliance**, delivering dispatchable location for softphones
  and nomadic users.

- **TIC 3.0 modernization**, enabling Cloud Case and Branch Office Case
  architectures.

- **Operational efficiency**, reducing OpEx through private IP
  utilization and automated IPAM.

**Core Architectural Pillars**

**1. Identity Layer — Certificate-Anchored Zero Trust Root**

Identity is the **root namespace**, **addressing authority**, and
**trust anchor**.\
The architecture uses:

- Entra ID strictly for IAM

- X.500/LDAP lineage for directory-enabled identity

- X.509 certificates for mTLS, non-repudiation, OCSP/CRL validation

- ACME automation for issuance and renewal

- NAC for pre-admission checks and asset inventory

- Federated identity (Login.gov, id.me) for external authentication

- Location telemetry (geo-IP, Wi-Fi/BSSID, subnet mapping) for Zero
  Trust and E911

Identity metadata—including certificate attributes, device posture, and
behavioral telemetry—drives routing, segmentation, and overlay
decisions.

**2. Addressing Layer — Deterministic, Identity-Derived Routing**

Addressing is **deterministic**, **identity-derived**, and anchored in
**InfoBlox DDI**, the authoritative source for:

- Private IP allocation

- DNS

- DHCP

- Hybrid-cloud IP orchestration

- vSphere IP pools

Routing incorporates:

- Microsoft Informed Network Routing (INR) telemetry

- BGP/eBPF hooks for dynamic path selection

- QUIC multiplexed streams for conversation continuity

- Selective metadata-only DPI

- TLS 1.3 resumption and certificate validation

- ML-driven path computation using telemetry from M365, Azure Network
  Watcher, and vSphere

This ensures low-latency, compliant routing for voice, video, and
real-time collaboration.

**3. Overlay Layer — Certificate-Anchored Execution Substrate**

The overlay is the **execution substrate** that unifies all underlays.
It is built on:

- Cisco Catalyst SD-WAN (FedRAMP Moderate, native INR support)

- VMware NSX for local-cloud overlays

- VXLAN/GENEVE encapsulation carrying identity and certificate metadata

- IPsec/IKEv2 tunnels authenticated with certificates

- VRFs and NSX namespaces for multi-tenancy

- InfoBlox-orchestrated overlay IP space

The overlay ensures deterministic, identity-aware, certificate-anchored
transport across hybrid environments.

**Compliance and Telemetry Integration**

The architecture aligns with:

- Zero Trust Maturity Model (CISA)

- TIC 3.0 Cloud Case and Branch Office Case

- FIPS 140-3 encryption requirements

- E911 dispatchable-location mandates

- CDM and CLAW telemetry requirements

- OMB M-21-31 logging maturity (EL3)

Telemetry is treated as a **security capability**, not a risk.
Pseudonymization ensures FedRAMP-compliant INR telemetry while
preserving sovereignty.

**Implementation Roadmap**

1.  **Baseline**\
    M365 Connectivity Test, Wireshark, certificate chain audits,
    InfoBlox DDI assessment, vSphere inventory.

2.  **Identity Foundation**\
    Entra ID IAM, PKI integration, ACME automation, NAC onboarding,
    certificate-anchored Zero Trust enforcement.

3.  **Addressing + Routing**\
    InfoBlox DDI integration, INR telemetry ingestion, QoS for media
    flows, vSphere IP orchestration.

4.  **Overlay Deployment**\
    Cisco Catalyst SD-WAN, NSX overlays, certificate-anchored tunnels,
    identity-aware routing policies.

5.  **Validation**\
    iPerf/QoS tests, Selenium conversation flows, vSphere VMotion/cloud
    bursting tests, chaos engineering.

6.  **Optimization**\
    Prometheus/Grafana telemetry, automated certificate rotation,
    ML-driven path tuning.

**Benefits**

- 99.99% conversation continuity

- 30–50% OpEx reduction

- Certificate-anchored Zero Trust

- Hybrid-cloud mobility

- Compliance-ready telemetry

- Unified visibility and control

**Challenges**

- Certificate lifecycle management

- INR telemetry constraints in GCC Moderate

- Migration from legacy systems

- Coordinating InfoBlox, SD-WAN, vSphere, and identity graphs

**2. Diagram-Ready Version (for slide decks, whiteboards, and
architecture diagrams)**

**Top-Level Diagram Structure**

**Layer 1: Identity (Root Namespace & Trust Fabric)**

- Entra ID (IAM)

- X.500/LDAP lineage

- X.509 certificates (mTLS, OCSP/CRL, ACME)

- NAC + asset inventory

- Location telemetry (geo-IP, Wi-Fi/BSSID, subnet mapping)

- Federated identity (Login.gov, id.me)

**Layer 2: Addressing (Deterministic, Identity-Derived)**

- InfoBlox DDI (DNS/DHCP/IPAM)

- Private IP orchestration

- vSphere IP pools

- INR telemetry

- BGP/eBPF hooks

- QUIC continuity

- Selective metadata-only DPI

- ML path computation

**Layer 3: Overlay (Execution Substrate)**

- Cisco Catalyst SD-WAN (FedRAMP Moderate, INR-native)

- VMware NSX

- VXLAN/GENEVE with identity/cert metadata

- IPsec/IKEv2 with certificate auth

- VRFs / NSX namespaces

- InfoBlox-orchestrated overlay IP space

**Conversation State Machine (Cross-Layer)**

- Identity state

- Policy state

- Media/data/metadata synchronization

- Addressing continuity

- Overlay path determinism

- Certificate-anchored trust

**Compliance Anchors**

- Zero Trust (NIST 800-207)

- TIC 3.0

- FIPS 140-3

- E911

- CDM / CLAW

- OMB M-21-31

**3. Congressional / Oversight Version (Plain-language, policy-aligned,
non-technical)**

**Unified Identity-Addressing-Overlay Architecture (v3)**

**Oversight Summary for Congressional, OMB, and IG Review**

Federal agencies depend on cloud services, collaboration tools, and
hybrid IT systems to deliver essential public services. These systems
must remain secure, resilient, and compliant with federal mandates while
supporting millions of daily interactions between citizens and
government.

The Unified Identity-Addressing-Overlay Architecture provides a modern,
federally compliant framework that ensures:

- **Stronger cybersecurity** through identity-based access controls and
  certificate-anchored trust.

- **Improved performance** for Microsoft 365, voice, video, and call
  center operations.

- **Better protection of personal information (PII)** through
  encryption, access controls, and telemetry safeguards.

- **Compliance with federal mandates**, including Zero Trust, TIC 3.0,
  FIPS 140-3, and E911 dispatchable-location requirements.

- **Operational efficiency**, reducing costs by consolidating legacy
  systems and using private IP addressing.

**Key Benefits for Government Operations**

- **Resilience:** Communications and applications remain available even
  during network disruptions.

- **Security:** Every user, device, and system is continuously verified
  using certificates and identity-based controls.

- **Compliance:** The architecture aligns with CISA, OMB, and statutory
  requirements.

- **Cost Savings:** Agencies can reduce operational expenses by 30–50%
  through modernized IP management and cloud routing.

- **Public Service:** Call centers, telehealth, benefits processing, and
  citizen-facing services operate with lower latency and higher
  reliability.

**Why This Matters**

Legacy systems were not designed for today’s hybrid-cloud, remote-work,
and real-time communication needs. This architecture provides a clear,
federally aligned path forward—strengthening cybersecurity, improving
service delivery, and reducing long-term costs.
