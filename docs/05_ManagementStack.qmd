---
title: "05 Managementstack"
author: "UIAO Modernization Program"
date: today
date-format: "MMMM D, YYYY"
format:
  html: default
  docx: default
  pdf: default
  gfm: default
---

# UIAO Management Stack — FedRAMP Control Definitions

| Field | Value |
|---|---|
| Version | 1.0 |
| Date | 2026-03 |
| Classification | CUI/FOUO |
| Source Plane(s) | Management, Identity, Security, Telemetry |
| Document Type | Architectural Specification (00_Core) |

---

## 2. Purpose

This document defines the Management Plane of the Unified Identity-Addressing-Overlay (UIAO) architecture. It establishes ServiceNow and Microsoft Intune as the authoritative governance systems responsible for drift detection, configuration integrity, device compliance, continuous authorization, and operational lifecycle management. It also maps their capabilities to NIST SP 800-53 Rev 5 controls required for FedRAMP 20x (Class C) authorization.

---

## 3. Scope

### Included

- Canonical definition of the Management Plane
- ServiceNow and Intune roles, responsibilities, and evidence sources
- NIST 800-53 Rev 5 control mappings
- Integration bindings across UIAO control planes
- Governance and drift-remediation workflows

### Excluded

- Vendor-specific deployment instructions
- Detailed CMDB schema design
- Device configuration baselines (covered in Intune profiles)

---

## 4. Control Plane Alignment

The Management Plane governs and enforces configuration integrity across all six UIAO control planes:

| Plane | Management Role |
|---|---|
| Identity | Device trust, lifecycle synchronization |
| Network | Overlay drift detection, segmentation enforcement |
| Addressing | IPAM reconciliation, authoritative inventory |
| Telemetry | Continuous monitoring, evidence generation |
| Security & Compliance | Zero Trust enforcement, FedRAMP alignment |
| Management | CMDB, change control, compliance posture |

ServiceNow and Intune jointly form the authoritative Management Plane.

---

## 5. Core Concepts

The Management Plane operationalizes the Eight Core Concepts:

1. **Single Source of Truth (SSOT)** — UIAO operates on the principle that every claim has one authoritative origin. All other representations are pointers, not copies. This ensures provenance, prevents drift, and enables federated truth resolution across boundaries.
2. Conversation as the atomic unit → Incident, change, and configuration events tied to identity and device
3. Identity as the root namespace → Device trust and configuration bound to identity
4. Deterministic addressing → CMDB reconciliation with IPAM as source of truth
5. Certificate-anchored overlay → Certificate drift detection and renewal workflows
6. Telemetry as control → Compliance signals drive access decisions
7. Embedded governance & automation → Automated remediation replaces manual tickets
8. Public service first → Reduced downtime, faster remediation, higher reliability

---

## 6. Architecture Model

### 6.1 Overview

The Management Plane ensures that UIAO remains drift-resistant, continuously authorized, and operationally compliant. It integrates:

- **ServiceNow** → System of record for incidents, changes, CMDB, and governance
- **Microsoft Intune** → Device compliance, configuration baselines, and hardware/software inventory

Together, they provide:

- Authoritative asset inventory (CM-8)
- Baseline configuration enforcement (CM-2, CM-6)
- Drift detection and remediation (CM-3, CA-7)
- Device trust for Conditional Access (AC-19)
- Evidence for FedRAMP 20x telemetry validation

### 6.2 ServiceNow — GovCommunityCloud

#### Role

ServiceNow is the system of record for:

- Incident lifecycle management
- Change control
- CMDB asset inventory
- Continuous authorization
- Overlay drift detection
- Automated remediation workflows

#### FedRAMP Authorization

| Field | Value |
|---|---|
| Package Type | JAB P-ATO |
| Impact Level | High |
| FedRAMP 20x Class | Class C |
| Controls Assessed | 421 |
| Framework | NIST SP 800-53 Rev 5 |

#### NIST Control Mappings

| Control | Function | Evidence Source |
|---|---|---|
| IR-4 | Incident handling | Incident audit trail |
| IR-5 | Incident monitoring | PA dashboards, SLA logs |
| IR-6 | Incident reporting | Notification engine logs |
| IR-8 | Incident response plan | GRC policy version history |
| CM-3 | Change control | CAB approvals, risk scoring |
| CM-8 | Asset inventory | CMDB + Discovery |
| CA-7 | Continuous monitoring | Continuous Authorization module |
| SA-9 | External system services | Vendor Risk Management |

#### Integration Bindings

| Target System | Mechanism | Control Supported |
|---|---|---|
| Infoblox IPAM | CMDB import | CM-8 |
| CyberArk | Privileged session events | IR-4 |
| Microsoft Sentinel | Incident sync | IR-5 |
| Microsoft Intune | Device inventory | CM-8 |

### 6.3 Microsoft Intune — M365 GCC High

#### Role

Intune is the device trust gatekeeper for the Identity Plane and the configuration enforcement engine for the Management Plane.

#### FedRAMP Authorization

| Field | Value |
|---|---|
| Package Type | Agency ATO |
| Impact Level | High |
| FedRAMP 20x Class | Class C |
| Parent Package | Microsoft 365 GCC High |

#### NIST Control Mappings

| Control | Function | Evidence Source |
|---|---|---|
| CM-2 | Baseline configuration | Configuration profiles |
| CM-6 | Configuration settings | Security baselines |
| CM-8 | Hardware/software inventory | Device inventory API |
| CM-7 | Least functionality | App protection policies |
| IA-3 | Device identification | Autopilot + certificates |
| AC-19 | Mobile device access control | Compliance policies |
| SI-2 | Flaw remediation | Update rings |
| SC-28 | Encryption at rest | BitLocker/FileVault status |

#### Integration Bindings

| Target System | Mechanism | Control Supported |
|---|---|---|
| Entra ID | Compliance → Conditional Access | AC-19 |
| Defender for Endpoint | Risk score → compliance | SI-2, IA-3 |
| ServiceNow CMDB | Inventory export | CM-8 |
| Cisco SD-WAN | Device posture → network access | AC-4 |

---

## 7. Runtime Model

The Management Plane enforces continuous authorization across all UIAO conversations.

### 7.1 Continuous Evaluation

- Device posture
- Certificate validity
- Configuration baseline
- Identity assurance
- Overlay integrity

### 7.2 Drift Detection

Drift is detected when:

- A device falls out of compliance
- A configuration baseline changes
- An overlay tunnel deviates from the approved baseline
- IPAM records diverge from CMDB
- Certificates expire or mismatch

### 7.3 Automated Remediation

Triggered via:

- ServiceNow change workflows
- Intune compliance enforcement
- Conditional Access policies
- Certificate renewal pipelines
- IPAM reconciliation

---

## 8. Compliance Mapping

The Management Plane provides evidence for:

- CM-2, CM-3, CM-6, CM-7, CM-8
- IR-4, IR-5, IR-6, IR-8
- AC-19
- IA-3
- CA-7
- SC-28

It also generates KSIs:

- KSI-CMT (baseline drift)
- KSI-PIY (inventory)
- KSI-IAM (identity/device trust)
- KSI-MLA (telemetry)

---

## 9. Dependencies & Sequencing

### Upstream

- Identity modernization
- IPAM modernization
- SD-WAN overlay deployment

### Downstream

- TIC 3.0 Cloud & Branch packages
- FedRAMP 20x evidence generation
- CDM/CLAW integration

### Timeline Alignment

This document aligns with Months 2-6 of the modernization timeline.

---

## 10. Governance & Drift Controls

### Source of Authority

| Domain | Authority |
|---|---|
| Identity lifecycle | HR |
| Addressing | Network architecture |
| Certificate trust | PKI |
| Configuration baselines | System owners |

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

### Audit Anchors

- Entra ID logs
- Infoblox API records
- SD-WAN telemetry
- Intune compliance reports
- ServiceNow audit trails

---

## 11. Appendices

### Appendix A: Definitions

*See `docs/glossary.md`*

### Appendix B: Tables

*ServiceNow NIST mappings are in Section 6.2. Intune NIST mappings are in Section 6.3. Integration bindings are in Sections 6.2 and 6.3.*

### Appendix C: Evidence Sources

*See `data/parameters.yml` and control-library entries for evidence source catalogs.*

### Appendix D: Integration Maps

*ServiceNow and Intune integration bindings are defined in Sections 6.2 and 6.3.*

---

## 12. Revision History

| Version | Date | Author | Summary of Changes |
|---|---|---|---|
| 1.0 | 2026-03 | UIAO Canon Engine | Initial canonical release |
