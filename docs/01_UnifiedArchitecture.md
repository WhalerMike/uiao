---
title: "01 Unifiedarchitecture"
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

## Unified Architecture Specification

| Field | Value |
|---|---|
| Version | 1.0 |
| Date | 2026-03 |
| Classification | CUI/FOUO |
| Source Plane(s) | Identity, Network, Addressing, Telemetry, Security, Management |
| Document Type | Architectural Specification (00_Core) |

---

## 2. Purpose

This document defines the unified architecture of the Unified Identity-Addressing-Overlay (UIAO) system. It integrates all six control planes into a single, coherent, identity-driven, telemetry-informed modernization framework. It serves as the architectural foundation for project plans, compliance mappings, modernization timelines, and executive briefings.

---

## 3. Scope

### Included

- Unified architectural model across all six control planes
- Cross-plane interactions and dependencies
- Core concepts and runtime behavior
- Architectural principles and modernization rationale
- Frozen state analysis and required state transitions

### Excluded

- Detailed plane-specific specifications (see `00_ControlPlaneArchitecture.md`)
- Implementation guides
- Vendor-specific deployment instructions
- Project plan details (covered in modernization appendices)

---

## 4. Control Plane Alignment

This document describes the unified behavior of all six UIAO control planes:

| Plane | Role in Unified Architecture |
|---|---|
| Identity | Root namespace and assurance engine |
| Network | Routing, segmentation, and overlay transport |
| Addressing | Deterministic IPAM and DNS/DHCP authority |
| Telemetry & Location | Real-time signals for routing, security, and compliance |
| Security & Compliance | Zero Trust enforcement and FedRAMP alignment |
| Management | Governance, drift detection, CMDB, device compliance |

The unified architecture is the composition of these planes operating deterministically.

---

## 5. Core Concepts

The unified architecture is governed by the Eight Core Concepts, which must appear identically across all UIAO documents:

1. Conversation as the atomic unit
2. Identity as the root namespace
3. Deterministic addressing
4. Certificate-anchored overlay
5. Telemetry as control
6. Embedded governance & automation
7. Public service first

These concepts define the architectural philosophy and runtime behavior of UIAO.

---

## 6. Architecture Model

### 6.1 Overview

The UIAO architecture replaces legacy perimeter-centric, device-centric, and location-centric models with a federated, identity-driven, telemetry-informed control plane system. Each plane is authoritative for its domain, but all planes operate as a single, deterministic system.

The architecture is designed to:

- Eliminate TIC 2.0 bottlenecks
- Replace static addressing with identity-derived addressing
- Replace siloed logs with conversation-level telemetry
- Replace manual governance with automated enforcement
- Replace perimeter trust with continuous Zero Trust evaluation

### 6.2 Architectural Principles

The unified architecture is governed by the following principles:

- Zero Trust by default
- Identity as the new perimeter
- Telemetry as the truth source
- Cloud-first routing
- Incremental modernization (no big-bang)
- FedRAMP-aligned controls
- Modular, extensible architecture

These principles are mandatory across all UIAO implementations.

### 6.3 Plane Interactions

#### Identity <-> Network

Identity provides segmentation attributes; network enforces identity-aware routing.

#### Network <-> Addressing

Addressing provides deterministic IPs; network uses them for segmentation and telemetry correlation.

#### Addressing <-> Telemetry

IPAM provides identity-derived IPs; telemetry uses them for location inference and conversation correlation.

#### Telemetry <-> Security

Telemetry provides real-time assurance; security enforces Zero Trust decisions.

#### Security <-> Management

Security defines policy; management enforces drift detection and remediation.

#### Management <-> Identity

Device compliance and lifecycle events feed identity assurance.

This creates a closed-loop, self-governing architecture.

### 6.4 Frozen State Analysis

The unified architecture addresses the following legacy constraints:

| Domain | Frozen State | Required State |
|---|---|---|
| Identity | On-prem AD, siloed | Unified identity graph |
| Addressing | Static spreadsheets | Deterministic identity-derived addressing |
| Network Security | L3/L4 firewalls | Identity-aware segmentation |
| Endpoint | Mixed tooling | Unified posture signal |
| App Delivery | Monolithic, local auth | Workload identity |
| Telemetry | Siloed logs | Conversation-level correlation |
| Governance | Email/ticket-based | Automated enforcement |
| Data Protection | Manual classification | Data-aware routing |

The unified architecture provides the required state.

### 6.5 Adapter Layer

Adapters bridge external source systems (Entra ID, Infoblox, ServiceNow, etc.) to the UIAO control planes. Each adapter conforms to a ten-domain contract covering discovery, normalization, provenance, drift detection, health, error classification, confidence scoring, metrics, and lifecycle management.

The adapter contract is defined in:

- `adapters/base_adapter.py` — Abstract base class (Python ABC)
- `adapters/__init__.py` — In-process adapter registry
- `docs/adapters/adapter-contract.md` — Human-readable contract specification

Vendor-specific adapter implementations live in separate repositories (e.g., `uiao-adapter-entra`, `uiao-adapter-infoblox`). See `docs/13_FIMF_AdapterRegistry.md` for the full FIMF adapter registry and onboarding checklist.

---

## 7. Runtime Model

UIAO operates on conversations as the atomic unit of runtime behavior.

### 7.1 Conversation Flow

1. Identity initiates
2. Addressing binds
3. Certificates authenticate
4. Overlay establishes path
5. Telemetry validates
6. Policy evaluates continuously

### 7.2 Deterministic Behavior

Given identical identity, boundary, telemetry, and assurance inputs, the system must produce the same decision across:

- Clouds
- Agencies
- Implementations

### 7.3 Continuous Evaluation

Telemetry modifies routing, access, and segmentation decisions in real time.

### 7.4 Assurance Signals

- Identity assurance
- Device posture
- Path quality
- Location inference
- Certificate validity

These signals drive continuous policy evaluation.

---

## 8. Compliance Mapping

### 8.1 FedRAMP 20x Alignment

The unified architecture supports:

- Class C (Moderate)
- Telemetry-based validation
- OSCAL machine-readability
- Automated evidence generation

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

### Upstream Dependencies

- HRIS
- PKI
- CMDB
- Network underlay

### Downstream Dependencies

- Modernization project plans (A-D)
- FedRAMP crosswalk
- Leadership briefing
- TIC 3.0 use cases

### Timeline Alignment

This document maps to all phases of the modernization timeline.

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

*Frozen State Analysis table is embedded in Section 6.4. Control Plane Alignment table is in Section 4.*

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
| 1.1 | 2026-04 | UIAO Adapter Layer | Added Section 6.5 Adapter Layer cross-reference |
