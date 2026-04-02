# 01 Unifiedarchitecture
UIAO Modernization Program
April 2, 2026

- [<span class="toc-section-number">1</span> Unified
  Identity-Addressing-Overlay Architecture
  (UIAO)](#unified-identity-addressing-overlay-architecture-uiao)
  - [<span class="toc-section-number">1.1</span> Unified Architecture
    Specification](#unified-architecture-specification)
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
    - [<span class="toc-section-number">1.6.1</span> 6.1
      Overview](#61-overview)
    - [<span class="toc-section-number">1.6.2</span> 6.2 Architectural
      Principles](#62-architectural-principles)
    - [<span class="toc-section-number">1.6.3</span> 6.3 Plane
      Interactions](#63-plane-interactions)
    - [<span class="toc-section-number">1.6.4</span> 6.4 Frozen State
      Analysis](#64-frozen-state-analysis)
    - [<span class="toc-section-number">1.6.5</span> 6.5 Adapter
      Layer](#65-adapter-layer)
  - [<span class="toc-section-number">1.7</span> 7. Runtime
    Model](#7-runtime-model)
    - [<span class="toc-section-number">1.7.1</span> 7.1 Conversation
      Flow](#71-conversation-flow)
    - [<span class="toc-section-number">1.7.2</span> 7.2 Deterministic
      Behavior](#72-deterministic-behavior)
    - [<span class="toc-section-number">1.7.3</span> 7.3 Continuous
      Evaluation](#73-continuous-evaluation)
    - [<span class="toc-section-number">1.7.4</span> 7.4 Assurance
      Signals](#74-assurance-signals)
  - [<span class="toc-section-number">1.8</span> 8. Compliance
    Mapping](#8-compliance-mapping)
    - [<span class="toc-section-number">1.8.1</span> 8.1 FedRAMP 20x
      Alignment](#81-fedramp-20x-alignment)
    - [<span class="toc-section-number">1.8.2</span> 8.2 NIST 800-53 Rev
      5 Controls](#82-nist-800-53-rev-5-controls)
    - [<span class="toc-section-number">1.8.3</span> 8.3 KSI
      Categories](#83-ksi-categories)
  - [<span class="toc-section-number">1.9</span> 9. Dependencies &
    Sequencing](#9-dependencies--sequencing)
    - [<span class="toc-section-number">1.9.1</span> Upstream
      Dependencies](#upstream-dependencies)
    - [<span class="toc-section-number">1.9.2</span> Downstream
      Dependencies](#downstream-dependencies)
    - [<span class="toc-section-number">1.9.3</span> Timeline
      Alignment](#timeline-alignment)
  - [<span class="toc-section-number">1.10</span> 10. Governance & Drift
    Controls](#10-governance--drift-controls)
  - [<span class="toc-section-number">1.11</span> 11.
    Appendices](#11-appendices)
    - [<span class="toc-section-number">1.11.1</span> Appendix A:
      Definitions](#appendix-a-definitions)
    - [<span class="toc-section-number">1.11.2</span> Appendix B:
      Tables](#appendix-b-tables)
    - [<span class="toc-section-number">1.11.3</span> Appendix C:
      Diagram References](#appendix-c-diagram-references)
    - [<span class="toc-section-number">1.11.4</span> Appendix D:
      Crosswalk References](#appendix-d-crosswalk-references)
    - [<span class="toc-section-number">1.11.5</span> Appendix E:
      Evidence Sources](#appendix-e-evidence-sources)
  - [<span class="toc-section-number">1.12</span> 12. Revision
    History](#12-revision-history)

# Unified Identity-Addressing-Overlay Architecture (UIAO)

## Unified Architecture Specification

| Field | Value |
|----|----|
| Version | 1.0 |
| Date | 2026-03 |
| Classification | CUI/FOUO |
| Source Plane(s) | Identity, Network, Addressing, Telemetry, Security, Management |
| Document Type | Architectural Specification (00_Core) |

------------------------------------------------------------------------

## 2. Purpose

This document defines the unified architecture of the Unified
Identity-Addressing-Overlay (UIAO) system. It integrates all six control
planes into a single, coherent, identity-driven, telemetry-informed
modernization framework. It serves as the architectural foundation for
project plans, compliance mappings, modernization timelines, and
executive briefings.

------------------------------------------------------------------------

## 3. Scope

### Included

- Unified architectural model across all six control planes
- Cross-plane interactions and dependencies
- Core concepts and runtime behavior
- Architectural principles and modernization rationale
- Frozen state analysis and required state transitions

### Excluded

- Detailed plane-specific specifications (see
  `00_ControlPlaneArchitecture.md`)
- Implementation guides
- Vendor-specific deployment instructions
- Project plan details (covered in modernization appendices)

------------------------------------------------------------------------

## 4. Control Plane Alignment

This document describes the unified behavior of all six UIAO control
planes:

| Plane | Role in Unified Architecture |
|----|----|
| Identity | Root namespace and assurance engine |
| Network | Routing, segmentation, and overlay transport |
| Addressing | Deterministic IPAM and DNS/DHCP authority |
| Telemetry & Location | Real-time signals for routing, security, and compliance |
| Security & Compliance | Zero Trust enforcement and FedRAMP alignment |
| Management | Governance, drift detection, CMDB, device compliance |

The unified architecture is the composition of these planes operating
deterministically.

------------------------------------------------------------------------

## 5. Core Concepts

The unified architecture is governed by the Eight Core Concepts, which
must appear identically across all UIAO documents:

1.  **Single Source of Truth (SSOT)** — UIAO operates on the principle
    that every claim has one authoritative origin. All other
    representations are pointers, not copies. This ensures provenance,
    prevents drift, and enables federated truth resolution across
    boundaries.
2.  Conversation as the atomic unit
3.  Identity as the root namespace
4.  Deterministic addressing
5.  Certificate-anchored overlay
6.  Telemetry as control
7.  Embedded governance & automation
8.  Public service first

These concepts define the architectural philosophy and runtime behavior
of UIAO.

------------------------------------------------------------------------

## 6. Architecture Model

### 6.1 Overview

The UIAO architecture replaces legacy perimeter-centric, device-centric,
and location-centric models with a federated, identity-driven,
telemetry-informed control plane system. Each plane is authoritative for
its domain, but all planes operate as a single, deterministic system.

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

#### Identity \<-\> Network

Identity provides segmentation attributes; network enforces
identity-aware routing.

#### Network \<-\> Addressing

Addressing provides deterministic IPs; network uses them for
segmentation and telemetry correlation.

#### Addressing \<-\> Telemetry

IPAM provides identity-derived IPs; telemetry uses them for location
inference and conversation correlation.

#### Telemetry \<-\> Security

Telemetry provides real-time assurance; security enforces Zero Trust
decisions.

#### Security \<-\> Management

Security defines policy; management enforces drift detection and
remediation.

#### Management \<-\> Identity

Device compliance and lifecycle events feed identity assurance.

This creates a closed-loop, self-governing architecture.

### 6.4 Frozen State Analysis

The unified architecture addresses the following legacy constraints:

| Domain | Frozen State | Required State |
|----|----|----|
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

Adapters bridge external source systems (Entra ID, Infoblox, ServiceNow,
etc.) to the UIAO control planes. Each adapter conforms to a ten-domain
contract covering discovery, normalization, provenance, drift detection,
health, error classification, confidence scoring, metrics, and lifecycle
management.

The adapter contract is defined in:

- `adapters/base_adapter.py` — Abstract base class (Python ABC)
- `adapters/__init__.py` — In-process adapter registry
- `docs/adapters/adapter-contract.md` — Human-readable contract
  specification

Vendor-specific adapter implementations live in separate repositories
(e.g., `uiao-adapter-entra`, `uiao-adapter-infoblox`). See
`docs/13_FIMF_AdapterRegistry.md` for the full FIMF adapter registry and
onboarding checklist.

------------------------------------------------------------------------

## 7. Runtime Model

UIAO operates on conversations as the atomic unit of runtime behavior.

### 7.1 Conversation Flow

1.  Identity initiates
2.  Addressing binds
3.  Certificates authenticate
4.  Overlay establishes path
5.  Telemetry validates
6.  Policy evaluates continuously

### 7.2 Deterministic Behavior

Given identical identity, boundary, telemetry, and assurance inputs, the
system must produce the same decision across:

- Clouds
- Agencies
- Implementations

### 7.3 Continuous Evaluation

Telemetry modifies routing, access, and segmentation decisions in real
time.

### 7.4 Assurance Signals

- Identity assurance
- Device posture
- Path quality
- Location inference
- Certificate validity

These signals drive continuous policy evaluation.

------------------------------------------------------------------------

## 8. Compliance Mapping

### 8.1 FedRAMP 20x Alignment

The unified architecture supports:

- Class C (Moderate)
- Telemetry-based validation
- OSCAL machine-readability
- Automated evidence generation

### 8.2 NIST 800-53 Rev 5 Controls

Mapped via the canonical crosswalk:

| Control ID | Control Name                                      |
|------------|---------------------------------------------------|
| AC-4       | Information Flow Enforcement (segmentation)       |
| IA-2       | Identification and Authentication                 |
| IA-5       | Authenticator Management                          |
| CM-8       | Information System Component Inventory            |
| SC-8       | Transmission Confidentiality and Integrity (mTLS) |
| CA-7       | Continuous Monitoring                             |
| SI-4       | Information System Monitoring (telemetry)         |

### 8.3 KSI Categories

- KSI-IAM
- KSI-PIY
- KSI-MLA
- KSI-SVC
- KSI-CMT
- KSI-CNA
- KSI-CED

------------------------------------------------------------------------

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

------------------------------------------------------------------------

## 10. Governance & Drift Controls

| Element | Value |
|----|----|
| Source of Authority | HR (human identity), Network architecture (addressing), System owners (configuration), PKI (credential trust) |
| Drift Detection | ServiceNow CMDB reconciliation, Intune compliance, SD-WAN overlay validation, IPAM reconciliation |
| Remediation Workflow | Automated ServiceNow change, Conditional Access enforcement, Certificate renewal, IPAM correction |
| Audit Anchors | Entra ID logs, Infoblox API records, SD-WAN telemetry, Intune compliance reports, ServiceNow audit trails |

------------------------------------------------------------------------

## 11. Appendices

### Appendix A: Definitions

*See `docs/glossary.md`*

### Appendix B: Tables

*Frozen State Analysis table is embedded in Section 6.4. Control Plane
Alignment table is in Section 4.*

### Appendix C: Diagram References

*See `docs/images/` for all referenced architecture diagrams.*

### Appendix D: Crosswalk References

*See `data/crosswalk-index.yml` and `docs/fedramp22_summary_v1.0.md`.*

### Appendix E: Evidence Sources

*See `data/parameters.yml` and control-library entries for evidence
source catalogs.*

------------------------------------------------------------------------

## 12. Revision History

| Version | Date | Author | Summary of Changes |
|----|----|----|----|
| 1.0 | 2026-03 | UIAO Canon Engine | Initial canonical release |
| 1.1 | 2026-04 | UIAO Adapter Layer | Added Section 6.5 Adapter Layer cross-reference |
