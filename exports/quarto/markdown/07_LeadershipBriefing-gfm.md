# 07 Leadershipbriefing
UIAO Modernization Program
March 31, 2026

- [<span class="toc-section-number">1</span> Leadership Briefing —
  Unified Identity-Addressing-Overlay Architecture
  (UIAO)](#leadership-briefing--unified-identity-addressing-overlay-architecture-uiao)
  - [<span class="toc-section-number">1.1</span> 1. Title
    Page](#1-title-page)
  - [<span class="toc-section-number">1.2</span> 2. Purpose](#2-purpose)
  - [<span class="toc-section-number">1.3</span> 3. Scope](#3-scope)
    - [<span class="toc-section-number">1.3.1</span>
      Included](#included)
    - [<span class="toc-section-number">1.3.2</span>
      Excluded](#excluded)
  - [<span class="toc-section-number">1.4</span> 4. Control Plane
    Alignment](#4-control-plane-alignment)
  - [<span class="toc-section-number">1.5</span> 5. Core
    Concepts](#5-core-concepts)
  - [<span class="toc-section-number">1.6</span> 6. Architecture
    Model](#6-architecture-model)
    - [<span class="toc-section-number">1.6.1</span> Slide 1 — Program
      Overview](#slide-1--program-overview)
    - [<span class="toc-section-number">1.6.2</span> Slide 2 — Why
      Modernization Is
      Required](#slide-2--why-modernization-is-required)
    - [<span class="toc-section-number">1.6.3</span> Slide 3 — Program
      Vision](#slide-3--program-vision)
    - [<span class="toc-section-number">1.6.4</span> Slide 4 — The Six
      Control Planes](#slide-4--the-six-control-planes)
    - [<span class="toc-section-number">1.6.5</span> Slide 5 — Frozen
      State Analysis](#slide-5--frozen-state-analysis)
    - [<span class="toc-section-number">1.6.6</span> Slide 6 — Program
      Outcomes](#slide-6--program-outcomes)
  - [<span class="toc-section-number">1.7</span> 7. Runtime
    Model](#7-runtime-model)
    - [<span class="toc-section-number">1.7.1</span> Conversation
      Flow](#conversation-flow)
    - [<span class="toc-section-number">1.7.2</span>
      Determinism](#determinism)
    - [<span class="toc-section-number">1.7.3</span> Continuous
      Evaluation](#continuous-evaluation)
  - [<span class="toc-section-number">1.8</span> 8. Compliance
    Mapping](#8-compliance-mapping)
    - [<span class="toc-section-number">1.8.1</span> FedRAMP
      20x](#fedramp-20x)
    - [<span class="toc-section-number">1.8.2</span> TIC 3.0](#tic-30)
    - [<span class="toc-section-number">1.8.3</span> NIST
      800-63](#nist-800-63)
  - [<span class="toc-section-number">1.9</span> 9. Dependencies and
    Sequencing](#9-dependencies-and-sequencing)
    - [<span class="toc-section-number">1.9.1</span> Upstream
      Dependencies](#upstream-dependencies)
    - [<span class="toc-section-number">1.9.2</span> Downstream
      Dependencies](#downstream-dependencies)
    - [<span class="toc-section-number">1.9.3</span> Modernization
      Timeline (Summary)](#modernization-timeline-summary)
  - [<span class="toc-section-number">1.10</span> 10. Governance and
    Drift Controls](#10-governance-and-drift-controls)
    - [<span class="toc-section-number">1.10.1</span> Source of
      Authority](#source-of-authority)
    - [<span class="toc-section-number">1.10.2</span> Drift
      Detection](#drift-detection)
    - [<span class="toc-section-number">1.10.3</span> Remediation
      Workflow](#remediation-workflow)
  - [<span class="toc-section-number">1.11</span> 11.
    Appendices](#11-appendices)
    - [<span class="toc-section-number">1.11.1</span> Appendix A:
      Definitions](#appendix-a-definitions)
    - [<span class="toc-section-number">1.11.2</span> Appendix B:
      Tables](#appendix-b-tables)
    - [<span class="toc-section-number">1.11.3</span> Appendix C:
      Diagram References](#appendix-c-diagram-references)
    - [<span class="toc-section-number">1.11.4</span> Appendix D:
      Evidence Sources](#appendix-d-evidence-sources)
  - [<span class="toc-section-number">1.12</span> 12. Revision
    History](#12-revision-history)

# Leadership Briefing — Unified Identity-Addressing-Overlay Architecture (UIAO)

## 1. Title Page

| Field | Value |
|----|----|
| **Format** | Executive Slide-Deck (Markdown) |
| **Version** | 1.0 |
| **Date** | March 2026 |
| **Classification** | CUI/FOUO |
| **Source Planes** | Identity, Network, Addressing, Telemetry, Security, Management |
| **Document Type** | Leadership Briefing (01_Canon) |

------------------------------------------------------------------------

## 2. Purpose

This document provides an executive-level briefing on the Unified
Identity-Addressing-Overlay Architecture (UIAO). It is designed for
CIOs, CISOs, CTOs, PMOs, and mission executives who need to understand
the modernization program at a glance. The briefing is structured as a
slide-deck narrative and covers program overview, challenges, vision,
architecture, compliance alignment, governance, timeline, and outcomes.

------------------------------------------------------------------------

## 3. Scope

### Included

- Program overview and strategic goal
- Current state challenges and mission impact
- End-state vision and guiding principles
- Six Control Planes and Eight Core Concepts
- Frozen state analysis
- Program outcomes
- Runtime model
- Compliance alignment (FedRAMP 20x, TIC 3.0, NIST 800-63)
- Governance and drift controls
- Modernization timeline summary
- Executive summary

### Excluded

- Detailed technical implementation procedures
- Vendor procurement or licensing details
- Operational runbooks or playbooks
- Per-device or per-endpoint configuration

------------------------------------------------------------------------

## 4. Control Plane Alignment

| Plane | Strategic Role |
|----|----|
| Identity | Entra ID, ICAM governance, Conditional Access, PIM, lifecycle automation |
| Network | Cisco Catalyst SD-WAN, Cloud OnRamp for M365, INR integration, identity-aware segmentation |
| Addressing | InfoBlox IPAM, DNS/DHCP modernization, cloud IPAM reconciliation |
| Telemetry | M365 Network Telemetry, SD-WAN telemetry, endpoint telemetry, DNS telemetry, CDM/CLAW, SIEM ingestion |
| Security | TIC 3.0 Cloud + Branch, Zero Trust, FedRAMP alignment, NIST 800-63, ICAM governance |
| Management | ServiceNow (CMDB, change, drift detection), Intune (device trust, compliance, configuration) |

------------------------------------------------------------------------

## 5. Core Concepts

The Eight Core Concepts govern the UIAO architecture:

1. **Single Source of Truth (SSOT)** — UIAO operates on the principle that every claim has one authoritative origin. All other representations are pointers, not copies. This ensures provenance, prevents drift, and enables federated truth resolution across boundaries.
2.  **Conversation as the atomic unit** — Every interaction binds
    identity, certificates, addressing, path, QoS, and telemetry.
3.  **Identity as the root namespace** — Every IP, certificate, subnet,
    policy, and telemetry event is derived from identity.
4.  **Deterministic addressing** — Addressing is identity-derived and
    policy-driven.
5.  **Certificate-anchored overlay** — mTLS anchors tunnels, services,
    and trust relationships.
6.  **Telemetry as control** — Telemetry is a real-time control input,
    not passive reporting.
7.  **Embedded governance and automation** — Governance is executed
    through orchestrated workflows, not manual tickets.
8.  **Public service first** — Citizen experience, accessibility, and
    privacy are top-level design constraints.

------------------------------------------------------------------------

## 6. Architecture Model

### Slide 1 — Program Overview

Unified Identity-Addressing-Overlay Architecture (UIAO) is a coordinated
modernization effort across:

- **Microsoft Entra ID** — Identity Control Plane
- **ICAM (NIST 800-63, OMB M-19-17)** — Governance Backbone
- **InfoBlox IPAM** — Addressing Control Plane
- **Cisco Catalyst SD-WAN** — Network Control Plane
- **Cloud Telemetry + Location Services** — Telemetry Control Plane
- **TIC 3.0 Cloud + Branch** — Security and Compliance Plane

**Strategic Goal:** Transform the agency into a cloud-optimized,
identity-driven, telemetry-informed, Zero Trust-aligned, TIC
3.0-compliant federal enterprise.

### Slide 2 — Why Modernization Is Required

#### Current State Challenges

- TIC 2.0 hairpin bottlenecks
- AD-centric identity with limited governance
- Fragmented IPAM across cloud and on-prem
- Limited telemetry visibility
- No INR or E911 readiness
- Inconsistent Zero Trust enforcement

#### Mission Impact

- Poor M365 performance
- Increased cyber risk
- Compliance gaps (TIC 3.0, FedRAMP 20x, SCuBA)
- Operational inefficiencies
- Slower mission execution

### Slide 3 — Program Vision

**End State:** A fully modernized, identity-driven, cloud-optimized,
telemetry-rich federal network.

**Guiding Principles:**

- Zero Trust by default
- Identity as the new perimeter
- Telemetry as the truth source
- Cloud-first routing
- Incremental modernization (no big-bang)
- FedRAMP-aligned controls
- Modular, extensible architecture

**Design Principle:** If it degrades the citizen interaction, it does
not ship.

### Slide 4 — The Six Control Planes

#### Identity Control Plane

- Entra ID
- ICAM governance
- Conditional Access
- PIM
- Lifecycle automation

#### Network Control Plane

- Cisco Catalyst SD-WAN
- Cloud OnRamp for M365
- INR integration
- Identity-aware segmentation

#### Addressing Control Plane

- InfoBlox IPAM
- DNS/DHCP modernization
- Cloud IPAM reconciliation

#### Telemetry and Location Control Plane

- M365 Network Telemetry
- SD-WAN telemetry
- Endpoint telemetry (Defender/Intune)
- DNS telemetry
- CDM/CLAW reporting
- SIEM ingestion

#### Security and Compliance Plane

- TIC 3.0 Cloud + Branch
- Zero Trust
- FedRAMP alignment
- NIST 800-63
- ICAM governance

#### Management Plane

- ServiceNow (CMDB, change, drift detection)
- Intune (device trust, compliance, configuration)

### Slide 5 — Frozen State Analysis

| Domain           | Current State         | Gap                               |
|------------------|-----------------------|-----------------------------------|
| Identity         | On-prem AD, siloed    | No unified identity graph         |
| Addressing       | Static spreadsheets   | No identity-to-address binding    |
| Network Security | L3/L4 firewalls       | No identity-aware segmentation    |
| Endpoint         | Mixed tooling         | No unified posture signal         |
| App Delivery     | Local auth            | No workload identity              |
| Telemetry        | Siloed logs           | No conversation-level correlation |
| Governance       | Email/tickets         | No automated enforcement          |
| Data Protection  | Manual classification | No data-aware routing             |

### Slide 6 — Program Outcomes

- Reduced latency and improved M365 performance
- Stronger identity governance and compliance
- Accurate addressing and location inference
- Real-time telemetry for routing and security
- TIC 3.0 compliance across cloud and branch
- A unified, future-proof modernization foundation

------------------------------------------------------------------------

## 7. Runtime Model

### Conversation Flow

1.  Identity initiates
2.  Addressing binds
3.  Certificates authenticate
4.  Overlay establishes path
5.  Telemetry validates
6.  Policy evaluates continuously

### Determinism

Given identical identity, boundary, telemetry, and assurance inputs, the
system produces identical decisions across clouds and agencies.

### Continuous Evaluation

Telemetry continuously informs routing, access, segmentation, and
compliance posture.

------------------------------------------------------------------------

## 8. Compliance Mapping

### FedRAMP 20x

- Class C (Moderate)
- Telemetry-based validation
- OSCAL machine-readability
- Automated evidence generation

### TIC 3.0

- Cloud Use Case
- Branch Use Case
- Identity-centric segmentation

### NIST 800-63

- Identity assurance
- Authentication modernization
- ICAM governance

------------------------------------------------------------------------

## 9. Dependencies and Sequencing

### Upstream Dependencies

- `00_ControlPlaneArchitecture.md` — defines the six planes referenced
  throughout
- `01_UnifiedArchitecture.md` — provides the unified architecture model
- `06_ProgramVision.md` — establishes strategic intent and guiding
  principles

### Downstream Dependencies

- `08_ModernizationTimeline.md` — expands the timeline summary in Slide
  11
- `09_CrosswalkIndex.md` — indexes control mappings referenced in
  compliance alignment

### Modernization Timeline (Summary)

Aligned to Workstreams A-D:

| Month   | Milestone                                                |
|---------|----------------------------------------------------------|
| Month 1 | Identity, SD-WAN, IPAM, Telemetry HLDs                   |
| Month 2 | Conditional Access, LLDs, DNS/DHCP, Location Services    |
| Month 3 | MFA/SSPR, DIA pilots, Cloud IPAM, E911                   |
| Month 4 | Segmentation, Telemetry export, IPAM integrations        |
| Month 5 | ICAM governance, Identity-aware routing, TIC 3.0 Cloud   |
| Month 6 | INR readiness, IPAM automation, TIC 3.0 Branch, CDM/CLAW |

------------------------------------------------------------------------

## 10. Governance and Drift Controls

### Source of Authority

- HR — identity lifecycle
- Network architecture — addressing
- PKI — certificate trust
- System owners — configuration baselines

### Drift Detection

- CMDB reconciliation
- Intune compliance
- SD-WAN overlay validation
- IPAM reconciliation

### Remediation Workflow

- Automated ServiceNow change
- Conditional Access enforcement
- Certificate renewal
- IPAM correction

------------------------------------------------------------------------

## 11. Appendices

### Appendix A: Definitions

*See `docs/glossary.md`*

### Appendix B: Tables

*Control Plane Alignment table is in Section 4. Frozen State Analysis is
in Section 6.5. Timeline is in Section 9.*

### Appendix C: Diagram References

*See `docs/images/` for all referenced architecture diagrams.*

### Appendix D: Evidence Sources

*See `data/parameters.yml` and control-library entries for evidence
source catalogs.*

------------------------------------------------------------------------

## 12. Revision History

| Version | Date    | Author            | Summary                   |
|---------|---------|-------------------|---------------------------|
| 1.0     | 2026-03 | UIAO Canon Engine | Initial canonical release |
