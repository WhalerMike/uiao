---
title: "00 Controlplanearchitecture"
author: "UIAO Modernization Program"
date: today
date-format: "MMMM D, YYYY"
format:
  html: default
  docx: default
  pdf: default
  gfm: default
---

# Unified Identity-Addressing-Overlay Architecture (UIAO)

## Control Plane Architecture

| Field | Value |
|---|---|
| Version | 1.0 |
| Date | 2026-03 |
| Classification | CUI/FOUO |
| Source Plane(s) | Identity, Network, Addressing, Telemetry, Security, Management |
| Document Type | Architectural Specification (00_Core) |

---

## 2. Purpose

This document defines the six control planes that form the foundation of the Unified Identity-Addressing-Overlay (UIAO) architecture. It establishes the authoritative structure, responsibilities, boundaries, and interactions of each plane, ensuring deterministic behavior across identity, network, addressing, telemetry, security, and management domains.

---

## 3. Scope

### Included

- Canonical definitions of all six control planes
- Responsibilities and boundaries for each plane
- Cross-plane interactions
- Runtime alignment with UIAO's conversation-centric model
- Compliance and governance anchors

### Excluded

- Implementation-specific configurations
- Vendor-specific deployment guides
- Project plans (covered in modernization appendices)
- Diagrams (referenced but not embedded)

---

## 4. Control Plane Alignment

This document defines all six UIAO control planes and establishes their relationships.

| Plane | Role |
|---|---|
| Identity | Primary source of truth for identity, assurance, and access |
| Network | Routing, segmentation, and path selection |
| Addressing | Deterministic IPAM, DNS, DHCP, and identity-derived addressing |
| Telemetry & Location | Real-time signals for routing, security, and compliance |
| Security & Compliance | Zero Trust enforcement, FedRAMP alignment, TIC 3.0 |
| Management | Governance, drift detection, CMDB, device compliance |

All other UIAO documents reference this plane model.

---

## 5. Core Concepts

The eight core principles governing UIAO are defined in a single source-of-truth document:

> **Canonical reference:** [00_CorePrinciples.md](00_CorePrinciples.md)

All UIAO documents MUST reference that file rather than duplicating principle text.
Any expansion, amendment, or reordering of the principles MUST occur in
`00_CorePrinciples.md` first; downstream documents inherit by pointer.

For quick orientation the eight principles are:

1. Single Source of Truth (SSOT)
2. Conversation as the Atomic Unit
3. Identity as the Root Namespace
4. Deterministic Addressing
5. Certificate-Anchored Overlay
6. Telemetry as Control
7. Embedded Governance & Automation
8. Public Service First

See `00_CorePrinciples.md` for full definitions, rationale, and compliance anchors.

---

## 6. Architecture Model

### 6.1 Overview

The UIAO architecture replaces legacy perimeter-centric models with a federated, identity-driven, telemetry-informed control plane system. Each plane is authoritative for a specific domain but interoperates through deterministic, identity-anchored relationships.

### 6.2 Plane Definitions

#### Identity Control Plane

- **Authoritative System:** Microsoft Entra ID
- **Responsibilities:**
  - Identity lifecycle (joiner/mover/leaver)
  - Authentication and assurance
  - Conditional Access
  - Privileged Identity Management
  - Device trust (via Intune)
  - Identity-derived addressing and policy
- **Inputs:** HRIS, device compliance, certificate status
- **Outputs:** Tokens, claims, identity attributes, assurance signals

#### Network Control Plane

- **Authoritative System:** Cisco Catalyst SD-WAN
- **Responsibilities:**
  - Routing and path selection
  - Identity-aware segmentation
  - Cloud OnRamp for M365
  - DIA and branch modernization
  - mTLS-anchored overlay enforcement
- **Inputs:** Identity attributes, addressing, telemetry
- **Outputs:** Segmentation decisions, path selection, overlay tunnels

#### Addressing Control Plane

- **Authoritative System:** Infoblox BloxOne IPAM
- **Responsibilities:**
  - Deterministic IP assignment
  - DNS/DHCP modernization
  - Cloud/on-prem reconciliation
  - Identity-derived addressing
  - Location inference
- **Inputs:** Identity attributes, network boundaries
- **Outputs:** IP allocations, DNS records, DHCP leases

#### Telemetry & Location Control Plane

- **Authoritative Systems:** M365 Network Telemetry, SD-WAN telemetry, Defender/Intune, DNS telemetry
- **Responsibilities:**
  - Real-time conversation-level telemetry
  - Location inference (INR, IPAM, SD-WAN)
  - E911 readiness
  - SIEM ingestion
  - Automated control inputs
- **Inputs:** Network flows, identity events, device posture
- **Outputs:** Assurance signals, routing modifiers, compliance indicators

#### Security & Compliance Plane

- **Authoritative Systems:** TIC 3.0, Zero Trust, FedRAMP 20x
- **Responsibilities:**
  - Zero Trust enforcement
  - FedRAMP 20x telemetry-based validation
  - NIST 800-63 identity governance
  - Policy enforcement across planes
- **Inputs:** Identity, telemetry, addressing, device posture
- **Outputs:** Allow/deny decisions, audit artifacts, compliance posture

#### Management Plane

- **Authoritative Systems:** ServiceNow, Microsoft Intune
- **Responsibilities:**
  - CMDB and asset inventory
  - Drift detection and remediation
  - Device compliance enforcement
  - Change control and incident lifecycle
  - Continuous Authorization (CA-7)
- **Inputs:** Telemetry, configuration baselines, identity lifecycle
- **Outputs:** Governance actions, remediation workflows, audit trails

---

## 7. Runtime Model

UIAO operates on conversations as the atomic unit.

### 7.1 Conversation Flow

1. Identity initiates
2. Addressing binds
3. Certificates authenticate
4. Overlay establishes path
5. Telemetry validates
6. Policy evaluates continuously

### 7.2 Determinism

Given identical identity, boundary, telemetry, and assurance inputs, the system must produce the same decision across clouds, agencies, and implementations.

### 7.3 Continuous Evaluation

Telemetry modifies routing, access, and segmentation decisions in real time.

---

## 8. Compliance Mapping

### 8.1 FedRAMP 20x Alignment

- Class C (Moderate)
- Telemetry-based validation
- OSCAL machine-readability

### 8.2 NIST 800-53 Rev 5 Controls

Mapped via the canonical crosswalk:

| Control ID | Control Name |
|---|---|
| AC-4 | Information Flow Enforcement (segmentation) |
| IA-2 | Identification and Authentication |
| IA-5 | Authenticator Management |
| CM-8 | Information System Component Inventory |
| SC-8 | Transmission Confidentiality and Integrity (mTLS) |
| CA-7 | Continuous Monitoring |
| SI-4 | Information System Monitoring (telemetry) |

### 8.3 KSI Categories

- KSI-IAM
- KSI-PIY
- KSI-MLA
- KSI-SVC
- KSI-CMT
- KSI-CNA
- KSI-CED

---

## 9. Dependencies & Sequencing

### Upstream

- HRIS
- PKI
- CMDB
- Network underlay

### Downstream

- Project plans (A-D)
- Modernization timeline
- FedRAMP crosswalk
- Leadership briefing

---

## 10. Governance & Drift Controls

| Element | Value |
|---|---|
| Source of Authority | HR (human identity), Network architecture (addressing), System owners (configuration), PKI (credential trust) |
| Drift Detection | ServiceNow CMDB reconciliation, Intune compliance, SD-WAN overlay validation, IPAM reconciliation |
| Remediation Workflow | Automated ServiceNow change, Conditional Access enforcement, Certificate renewal, IPAM correction |
| Audit Anchors | Entra ID logs, Infoblox API records, SD-WAN telemetry, Intune compliance reports, ServiceNow audit trails |

---

## 11. Appendices

### Appendix A: Definitions

*See `docs/glossary.md`*

### Appendix B: Tables

*Control plane summary tables are embedded in Section 4 and Section 6.*

### Appendix C: Diagram References

*See `docs/images/` for all referenced architecture diagrams.*

### Appendix D: Crosswalk References

*See `data/crosswalk-index.yml` and `docs/fedramp22_summary_v1.0.md`.*

### Appendix E: Evidence Sources

*See `data/parameters.yml` and control-library entries for evidence source catalogs.*

---

## 12. Revision History

| Version | Date | Author | Summary of Changes |
|---|---|---|---|
| 1.0 | 2026-03 | UIAO Canon Engine | Initial canonical release |
