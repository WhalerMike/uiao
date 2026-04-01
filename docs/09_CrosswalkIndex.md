---
title: "09 Crosswalkindex"
author: "UIAO Modernization Program"
date: today
date-format: "MMMM D, YYYY"
format:
  html: default
  docx: default
  pdf: default
  gfm: default
---

# UIAO Crosswalk Index

## 1. Title Page

| Field | Value |
|---|---|
| **Version** | 1.0 |
| **Date** | March 2026 |
| **Classification** | CUI/FOUO |
| **Source Planes** | Identity, Network, Addressing, Telemetry, Security, Management |
| **Document Type** | Index and Reference (02_Appendices) |

---

## 2. Purpose

This document provides the authoritative index for all crosswalks, mappings, and compliance references within the Unified Identity-Addressing-Overlay (UIAO) canon. It ensures that every mapping — FedRAMP, NIST, TIC 3.0, SCuBA, KSI, and control-plane alignment — is discoverable, consistent, and traceable across the entire documentation set.

---

## 3. Scope

### Included

- Index of all crosswalks in the UIAO canon
- Mapping references across FedRAMP, NIST, TIC 3.0, SCuBA, and KSI
- Control-plane alignment references
- Document-to-document linkage
- Evidence source index

### Excluded

- Full crosswalk content (see `03_FedRAMP20x_Crosswalk.md`)
- Detailed compliance narratives
- Project plans and timelines

---

## 4. Control Plane Alignment

This index spans all six UIAO control planes:

| Plane | Crosswalk Role |
|---|---|
| Identity | NIST 800-63, IA-2, AC-2, ICAM governance |
| Network | AC-4, SC-7, TIC 3.0 Cloud and Branch |
| Addressing | CM-8, AC-4, deterministic IPAM |
| Telemetry and Location | CA-7, SI-4, KSI-MLA |
| Security and Compliance | FedRAMP 20x, Zero Trust, SCuBA |
| Management | CM-2, CM-3, CM-6, CM-8, CA-7 |

The index ensures each plane's compliance responsibilities are traceable.

---

## 5. Core Concepts

The Crosswalk Index is governed by the Eight Core Concepts:

1. **Single Source of Truth (SSOT)** — UIAO operates on the principle that every claim has one authoritative origin. All other representations are pointers, not copies. This ensures provenance, prevents drift, and enables federated truth resolution across boundaries.
2. **Conversation as the atomic unit**
3. **Identity as the root namespace**
4. **Deterministic addressing**
5. **Certificate-anchored overlay**
6. **Telemetry as control**
7. **Embedded governance and automation**
8. **Public service first**

These concepts appear consistently across all crosswalks.

---

## 6. Architecture Model

### 6.1 Crosswalk Categories

UIAO crosswalks fall into five canonical categories:

- **FedRAMP 20x Crosswalk**
- **NIST SP 800-53 Rev 5 Mapping**
- **TIC 3.0 Cloud and Branch Alignment**
- **SCuBA (M365) Hardening Alignment**
- **KSI (Key Security Indicator) Framework**

This index links each category to its authoritative document.

### 6.2 Document-Level Crosswalk Index

| Document | Crosswalk Type | Reference |
|---|---|---|
| `03_FedRAMP20x_Crosswalk.md` | FedRAMP 20x to UIAO | Primary crosswalk |
| `04_FedRAMP20x_Phase2_Summary.md` | FedRAMP 20x to Modernization | Summary mapping |
| `05_ManagementStack.md` | NIST CM/IR/AC/IA to ServiceNow/Intune | Management mappings |
| `00_ControlPlaneArchitecture.md` | Control planes to NIST | Plane-level mapping |
| `01_UnifiedArchitecture.md` | Core concepts to NIST | Conceptual mapping |
| `02_CanonSpecification.md` | Canon to NIST/TIC/SCuBA | Doctrinal mapping |
| `15_ProvenanceProfile.md` | Provenance to AU-3/AU-9/SI-7/AC-4 | Phase 5 — Data Governance Substrate |
| `16_DriftDetectionStandard.md` | Drift to CM-3/SI-7/CA-7/IR-6 | Phase 5 — Data Governance Substrate |
| `17_ConsentEnvelope.md` | Consent to AC-4/AC-22/AR-4/IP-1 | Phase 5 — Data Governance Substrate |
| `18_ClaimCatalog.md` | Claims to CM-8/SA-4/SI-12 | Phase 5 — Data Governance Substrate |
| `19_ReconciliationModel.md` | Reconciliation to AU-3/IR-4/SA-9/PM-16 | Phase 5 — Data Governance Substrate |

This table is the master reference for all compliance-related documents.

---

## 7. Runtime Model

The Crosswalk Index follows the UIAO runtime model:

### 7.1 Conversation-Level Mapping

Every crosswalk ties back to:

- Identity
- Addressing
- Certificates
- Path
- Telemetry
- Policy

### 7.2 Deterministic Mapping

Given identical identity, boundary, telemetry, and assurance inputs, crosswalk outputs remain consistent across:

- Clouds
- Agencies
- Implementations

### 7.3 Continuous Evaluation

Crosswalks support CA-7 continuous monitoring and SI-4 anomaly detection.

---

## 8. Crosswalk Index (Master Table)

Below is the canonical master index of all crosswalks in the UIAO canon.

### 8.1 FedRAMP 20x Crosswalk Index

| Category | Reference | Document |
|---|---|---|
| FedRAMP 20x to UIAO | Full mapping | `03_FedRAMP20x_Crosswalk.md` |
| Phase 2 Summary | Modernization alignment | `04_FedRAMP20x_Phase2_Summary.md` |
| Evidence Sources | Telemetry, identity, addressing | `03_FedRAMP20x_Crosswalk.md` |

### 8.2 NIST SP 800-53 Rev 5 Crosswalk Index

| Control Family | Reference | Document |
|---|---|---|
| AC (Access Control) | Identity, segmentation | `00_ControlPlaneArchitecture.md` |
| IA (Identity and Auth) | Identity assurance | `01_UnifiedArchitecture.md` |
| CM (Configuration Mgmt) | CMDB, Intune, drift | `05_ManagementStack.md` |
| SC (System and Comm) | mTLS, overlay | `00_ControlPlaneArchitecture.md` |
| SI (System Integrity) | Telemetry | `03_FedRAMP20x_Crosswalk.md` |
| CA (Assessment) | Continuous monitoring | `05_ManagementStack.md` |

### 8.3 TIC 3.0 Crosswalk Index

| TIC Use Case | Reference | Document |
|---|---|---|
| Cloud | Identity-aware routing | `04_FedRAMP20x_Phase2_Summary.md` |
| Branch | SD-WAN segmentation | `04_FedRAMP20x_Phase2_Summary.md` |
| Identity | ICAM governance | `06_ProgramVision.md` |

### 8.4 SCuBA (M365) Crosswalk Index

| Category | Reference | Document |
|---|---|---|
| Identity Hardening | MFA, CA, PIM | `06_ProgramVision.md` |
| Telemetry | M365 Network Telemetry | `08_ModernizationTimeline.md` |
| Governance | ICAM alignment | `02_CanonSpecification.md` |

### 8.5 KSI (Key Security Indicator) Index

| KSI | Description | Document |
|---|---|---|
| KSI-IAM | Identity authentication | `03_FedRAMP20x_Crosswalk.md` |
| KSI-PIY | Deterministic inventory | `05_ManagementStack.md` |
| KSI-MLA | Network health | `03_FedRAMP20x_Crosswalk.md` |
| KSI-SVC | Certificate enforcement | `00_ControlPlaneArchitecture.md` |
| KSI-CMT | Baseline drift | `05_ManagementStack.md` |
| KSI-CNA | Conversation metadata | `01_UnifiedArchitecture.md` |
| KSI-CED | Data minimization | `02_CanonSpecification.md` |

### 8.6 Phase 5 — Data Governance Substrate Crosswalk Index

| Document | Crosswalk Type | Reference |
|---|---|---|
| `15_ProvenanceProfile.md` | Provenance to NIST AU/SI/AC | Lineage, audit, integrity |
| `16_DriftDetectionStandard.md` | Drift to NIST CM/SI/CA/IR | Configuration, monitoring, incident |
| `17_ConsentEnvelope.md` | Consent to NIST AC/AR/IP | Information flow, privacy |
| `18_ClaimCatalog.md` | Claims to NIST CM/SA/SI | Inventory, acquisition, retention |
| `19_ReconciliationModel.md` | Reconciliation to NIST AU/IR/SA/PM | Audit, incident, external services |

---

## 9. Dependencies and Sequencing

### Upstream Dependencies

- Identity modernization
- IPAM modernization
- SD-WAN overlay deployment

### Downstream Dependencies

- TIC 3.0 packages
- FedRAMP 20x evidence generation
- Leadership reporting

### Timeline Alignment

The Crosswalk Index supports all phases of the modernization timeline.

---

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

---

## 11. Appendices

### Appendix A: Definitions

*See `docs/glossary.md`*

### Appendix B: Tables

*Crosswalk master tables are in Section 8. Control Plane Alignment table is in Section 4.*

### Appendix C: Evidence Sources

*See `data/parameters.yml` and control-library entries for evidence source catalogs.*

### Appendix D: Crosswalk References

*See `data/crosswalk-index.yml` for machine-readable crosswalk data.*

---

## 12. Revision History

| Version | Date | Author | Summary |
|---|---|---|---|
| 1.0 | 2026-03 | UIAO Canon Engine | Initial canonical release |
| 1.1 | 2026-04 | UIAO Canon Engine | Register Phase 5 docs 15–19; add Section 8.6 |
