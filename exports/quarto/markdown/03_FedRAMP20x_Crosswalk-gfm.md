# 03 Fedramp20X Crosswalk
UIAO Modernization Program
March 31, 2026

- [<span class="toc-section-number">1</span> UIAO FedRAMP 20x Compliance
  Crosswalk](#uiao-fedramp-20x-compliance-crosswalk)
  - [<span class="toc-section-number">1.1</span> 2. Purpose](#2-purpose)
  - [<span class="toc-section-number">1.2</span> 3. Scope](#3-scope)
    - [<span class="toc-section-number">1.2.1</span>
      Included](#included)
    - [<span class="toc-section-number">1.2.2</span>
      Excluded](#excluded)
  - [<span class="toc-section-number">1.3</span> 4. Control Plane
    Alignment](#4-control-plane-alignment)
  - [<span class="toc-section-number">1.4</span> 5. Core
    Concepts](#5-core-concepts)
  - [<span class="toc-section-number">1.5</span> 6. Architecture
    Model](#6-architecture-model)
    - [<span class="toc-section-number">1.5.1</span> 6.1 FedRAMP 20x
      Overview](#61-fedramp-20x-overview)
    - [<span class="toc-section-number">1.5.2</span> 6.2 Fundamental
      Concept Mapping](#62-fundamental-concept-mapping)
  - [<span class="toc-section-number">1.6</span> 7. Runtime
    Model](#7-runtime-model)
    - [<span class="toc-section-number">1.6.1</span> 7.1
      Conversation-Level Telemetry](#71-conversation-level-telemetry)
    - [<span class="toc-section-number">1.6.2</span> 7.2 Deterministic
      Evidence](#72-deterministic-evidence)
    - [<span class="toc-section-number">1.6.3</span> 7.3 Continuous
      Monitoring](#73-continuous-monitoring)
  - [<span class="toc-section-number">1.7</span> 8. Compliance
    Mapping](#8-compliance-mapping)
    - [<span class="toc-section-number">1.7.1</span> 8.1 Mandatory 2026
      Infrastructure
      Requirements](#81-mandatory-2026-infrastructure-requirements)
    - [<span class="toc-section-number">1.7.2</span> 8.2 Audit Anchor
      Summary](#82-audit-anchor-summary)
    - [<span class="toc-section-number">1.7.3</span> 8.3 KSI
      Definitions](#83-ksi-definitions)
  - [<span class="toc-section-number">1.8</span> 9. Dependencies &
    Sequencing](#9-dependencies--sequencing)
    - [<span class="toc-section-number">1.8.1</span> Upstream
      Dependencies](#upstream-dependencies)
    - [<span class="toc-section-number">1.8.2</span> Downstream
      Dependencies](#downstream-dependencies)
    - [<span class="toc-section-number">1.8.3</span> Timeline
      Alignment](#timeline-alignment)
  - [<span class="toc-section-number">1.9</span> 10. Governance & Drift
    Controls](#10-governance--drift-controls)
    - [<span class="toc-section-number">1.9.1</span> Source of
      Authority](#source-of-authority)
    - [<span class="toc-section-number">1.9.2</span> Drift
      Detection](#drift-detection)
    - [<span class="toc-section-number">1.9.3</span> Remediation
      Workflow](#remediation-workflow)
    - [<span class="toc-section-number">1.9.4</span> Audit
      Anchors](#audit-anchors)
  - [<span class="toc-section-number">1.10</span> 11.
    Appendices](#11-appendices)
    - [<span class="toc-section-number">1.10.1</span> Appendix A:
      Definitions](#appendix-a-definitions)
    - [<span class="toc-section-number">1.10.2</span> Appendix B:
      Tables](#appendix-b-tables)
    - [<span class="toc-section-number">1.10.3</span> Appendix C:
      Diagram References](#appendix-c-diagram-references)
    - [<span class="toc-section-number">1.10.4</span> Appendix D:
      Evidence Sources](#appendix-d-evidence-sources)
    - [<span class="toc-section-number">1.10.5</span> Appendix E: KSI
      Reference Model](#appendix-e-ksi-reference-model)
  - [<span class="toc-section-number">1.11</span> 12. Revision
    History](#12-revision-history)

# UIAO FedRAMP 20x Compliance Crosswalk

| Field | Value |
|----|----|
| Version | 1.0 |
| Date | 2026-03 |
| Classification | CUI/FOUO |
| Source Plane(s) | Identity, Network, Addressing, Telemetry, Security, Management |
| Document Type | Compliance Crosswalk (02_Appendices) |

------------------------------------------------------------------------

## 2. Purpose

This document provides the authoritative FedRAMP 20x compliance
crosswalk for the Unified Identity-Addressing-Overlay (UIAO)
architecture. It maps UIAO’s core concepts, control planes, and runtime
model to the NIST SP 800-53 Rev 5 controls required for a FedRAMP
Moderate (Class C) authorization under the 20x telemetry-based
validation framework.

------------------------------------------------------------------------

## 3. Scope

### Included

- Mapping of UIAO concepts to NIST 800-53 Rev 5 controls
- KSI (Key Security Indicator) alignment
- Evidence sources for telemetry-based validation
- Mandatory 2026 infrastructure requirements
- Audit anchors and continuous monitoring expectations

### Excluded

- Implementation-specific configurations
- Vendor deployment guides
- Project plan sequencing (covered in modernization timeline)

------------------------------------------------------------------------

## 4. Control Plane Alignment

This crosswalk spans all six UIAO control planes:

| Plane                 | Compliance Role                               |
|-----------------------|-----------------------------------------------|
| Identity              | Identity assurance, MFA, lifecycle governance |
| Network               | Segmentation, routing, overlay security       |
| Addressing            | Deterministic IPAM, DNS/DHCP integrity        |
| Telemetry & Location  | Continuous monitoring, KSI generation         |
| Security & Compliance | Zero Trust enforcement, FedRAMP alignment     |
| Management            | CMDB, drift detection, remediation workflows  |

Each plane contributes evidence to FedRAMP 20x telemetry validation.

------------------------------------------------------------------------

## 5. Core Concepts

The crosswalk maps the Eight Core Concepts to NIST controls:

1. **Single Source of Truth (SSOT)** — UIAO operates on the principle that every claim has one authoritative origin. All other representations are pointers, not copies. This ensures provenance, prevents drift, and enables federated truth resolution across boundaries.
2.  Conversation as the atomic unit → AC-4, SI-4
3.  Identity as the root namespace → IA-2, AC-2
4.  Deterministic addressing → CM-8, AC-4
5.  Certificate-anchored overlay → SC-8, IA-5
6.  Telemetry as control → CA-7, SI-4
7.  Embedded governance & automation → CM-2, CM-3
8.  Public service first → PT-2 (privacy and minimization)

These mappings are frozen and must appear identically across all UIAO
compliance documents.

------------------------------------------------------------------------

## 6. Architecture Model

### 6.1 FedRAMP 20x Overview

FedRAMP 20x replaces narrative-based compliance with telemetry-based
validation, requiring:

- Machine-readable OSCAL packages
- Real-time Key Security Indicators (KSIs)
- Automated evidence generation
- Continuous monitoring (CA-7)
- Identity-anchored access control
- Deterministic asset inventory

UIAO is designed explicitly to satisfy these requirements.

### 6.2 Fundamental Concept Mapping

| UIAO Concept | NIST Control | KSI Category | Evidence Source |
|----|----|----|----|
| Conversation as Atomic Unit | AC-4 | KSI-CNA | SD-WAN flow telemetry |
| Identity as Root Namespace | IA-2 / AC-2 | KSI-IAM | Entra ID & CyberArk logs |
| Deterministic Addressing | CM-8 / AC-4 | KSI-PIY | Infoblox BloxOne DDI API |
| Certificate-Anchored Overlay | SC-8 / IA-5 | KSI-SVC | SD-WAN mTLS configuration |
| Telemetry as Control | CA-7 / SI-4 | KSI-MLA | M365 & SD-WAN telemetry |
| Embedded Governance | CM-2 | KSI-CMT | GitHub YAML baseline |
| Public Service First | PT-2 | KSI-CED | Identity & overlay minimization |

These mappings are canonical and must not be altered.

------------------------------------------------------------------------

## 7. Runtime Model

UIAO’s runtime model directly supports FedRAMP 20x telemetry validation.

### 7.1 Conversation-Level Telemetry

Every conversation produces:

- Identity metadata
- Addressing metadata
- Certificate metadata
- Path and QoS telemetry
- Security and assurance signals

### 7.2 Deterministic Evidence

Given identical inputs, UIAO produces identical telemetry outputs —
enabling reproducible compliance.

### 7.3 Continuous Monitoring

Telemetry feeds:

- CA-7 continuous monitoring
- SI-4 anomaly detection
- AC-4 segmentation enforcement
- SC-8 certificate validation

This satisfies FedRAMP’s requirement for machine-generated evidence.

------------------------------------------------------------------------

## 8. Compliance Mapping

### 8.1 Mandatory 2026 Infrastructure Requirements

| ID       | Requirement               | Status   | Deadline   |
|----------|---------------------------|----------|------------|
| NTC-0003 | Automated Security Inbox  | Required | 2026-01-05 |
| RFC-0024 | OSCAL Machine-Readability | Required | 2026-09-30 |
| M-24-15  | Phishing-Resistant MFA    | Required | 2026-09-30 |

UIAO satisfies all three through Entra ID, SD-WAN telemetry, and
GitHub-based governance.

### 8.2 Audit Anchor Summary

UIAO provides continuous telemetry via:

- **Identity Pillar:** Entra ID MFA, PIV/FIDO2
- **Addressing Pillar:** Infoblox deterministic IPAM
- **Overlay Pillar:** SD-WAN mTLS service chain
- **Telemetry Pillar:** M365, SD-WAN, DNS, endpoint signals

These anchors form the evidence base for FedRAMP 20x.

### 8.3 KSI Definitions

| KSI     | Description                              |
|---------|------------------------------------------|
| KSI-IAM | Identity authentication logs (Entra ID)  |
| KSI-PIY | Deterministic asset inventory (Infoblox) |
| KSI-MLA | Network health & path telemetry          |
| KSI-SVC | Certificate enforcement (mTLS)           |
| KSI-CMT | Baseline drift detection (GitHub YAML)   |
| KSI-CNA | Packet-level identity metadata           |
| KSI-CED | Data minimization enforcement            |

These KSIs are mandatory for FedRAMP 20x validation.

------------------------------------------------------------------------

## 9. Dependencies & Sequencing

### Upstream Dependencies

- Identity modernization (Workstream A)
- SD-WAN HLD/LLD (Workstream B)
- IPAM modernization (Workstream C)
- Telemetry integration (Workstream D)

### Downstream Dependencies

- TIC 3.0 Cloud & Branch packages
- FedRAMP annual assessment
- Continuous monitoring dashboards
- Governance workflows

### Timeline Alignment

This document aligns with Months 3-6 of the modernization timeline.

------------------------------------------------------------------------

## 10. Governance & Drift Controls

### Source of Authority

| Domain                  | Authority            |
|-------------------------|----------------------|
| Identity lifecycle      | HR                   |
| Addressing              | Network architecture |
| Certificate trust       | PKI                  |
| Configuration baselines | System owners        |

### Drift Detection

- GitHub YAML baseline comparison
- ServiceNow CMDB reconciliation
- Intune compliance
- SD-WAN overlay validation
- IPAM reconciliation

### Remediation Workflow

- Automated ServiceNow change
- Conditional Access enforcement
- Certificate renewal
- IPAM correction

### Audit Anchors

- Entra ID logs
- Infoblox API records
- SD-WAN telemetry
- Intune compliance reports
- ServiceNow audit trails

------------------------------------------------------------------------

## 11. Appendices

### Appendix A: Definitions

*See `docs/glossary.md`*

### Appendix B: Tables

*Fundamental Concept Mapping table is in Section 6.2. KSI Definitions
table is in Section 8.3. Mandatory 2026 Requirements table is in Section
8.1.*

### Appendix C: Diagram References

*See `docs/images/` for all referenced architecture diagrams.*

### Appendix D: Evidence Sources

*See `data/parameters.yml` and control-library entries for evidence
source catalogs.*

### Appendix E: KSI Reference Model

*KSI definitions are in Section 8.3. Machine-readable KSI mappings are
in `data/crosswalk-index.yml`.*

------------------------------------------------------------------------

## 12. Revision History

| Version | Date    | Author            | Summary of Changes        |
|---------|---------|-------------------|---------------------------|
| 1.0     | 2026-03 | UIAO Canon Engine | Initial canonical release |
