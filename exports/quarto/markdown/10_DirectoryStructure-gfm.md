# 10 Directorystructure
UIAO Modernization Program
March 31, 2026

- [<span class="toc-section-number">1</span> UIAO Canonical Directory
  Structure](#uiao-canonical-directory-structure)
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
    - [<span class="toc-section-number">1.6.1</span> 6.1 Canonical
      Directory Layout](#61-canonical-directory-layout)
    - [<span class="toc-section-number">1.6.2</span> 6.2 Numbering
      Rules](#62-numbering-rules)
  - [<span class="toc-section-number">1.7</span> 7. Runtime
    Model](#7-runtime-model)
    - [<span class="toc-section-number">1.7.1</span> 7.1 Conversation
      Flow to Document Flow](#71-conversation-flow-to-document-flow)
    - [<span class="toc-section-number">1.7.2</span> 7.2 Deterministic
      Navigation](#72-deterministic-navigation)
    - [<span class="toc-section-number">1.7.3</span> 7.3 Continuous
      Evaluation](#73-continuous-evaluation)
  - [<span class="toc-section-number">1.8</span> 8. Directory Structure
    (Canonical Table)](#8-directory-structure-canonical-table)
  - [<span class="toc-section-number">1.9</span> 9. Dependencies and
    Sequencing](#9-dependencies-and-sequencing)
    - [<span class="toc-section-number">1.9.1</span> Upstream
      Dependencies](#upstream-dependencies)
    - [<span class="toc-section-number">1.9.2</span> Downstream
      Dependencies](#downstream-dependencies)
    - [<span class="toc-section-number">1.9.3</span> Critical
      Path](#critical-path)
  - [<span class="toc-section-number">1.10</span> 10. Governance and
    Drift Controls](#10-governance-and-drift-controls)
    - [<span class="toc-section-number">1.10.1</span> Source of
      Authority](#source-of-authority)
    - [<span class="toc-section-number">1.10.2</span> Drift
      Detection](#drift-detection)
    - [<span class="toc-section-number">1.10.3</span> Repository Drift
      Controls](#repository-drift-controls)
    - [<span class="toc-section-number">1.10.4</span> Remediation
      Workflow](#remediation-workflow)
  - [<span class="toc-section-number">1.11</span> 11.
    Appendices](#11-appendices)
    - [<span class="toc-section-number">1.11.1</span> Appendix A:
      Definitions](#appendix-a-definitions)
    - [<span class="toc-section-number">1.11.2</span> Appendix B:
      Tables](#appendix-b-tables)
    - [<span class="toc-section-number">1.11.3</span> Appendix C:
      Evidence Sources](#appendix-c-evidence-sources)
  - [<span class="toc-section-number">1.12</span> 12. Revision
    History](#12-revision-history)

# UIAO Canonical Directory Structure

## 1. Title Page

| Field | Value |
|----|----|
| **Version** | 1.0 |
| **Date** | March 2026 |
| **Classification** | CUI/FOUO |
| **Source Planes** | Identity, Network, Addressing, Telemetry, Security, Management |
| **Document Type** | Repository Structure (02_Appendices) |

------------------------------------------------------------------------

## 2. Purpose

This document defines the authoritative directory structure for the
Unified Identity-Addressing-Overlay (UIAO) repository. It establishes
the canonical layout, naming conventions, numbering rules, and document
placement required to maintain a deterministic, drift-resistant,
self-navigating modernization canon.

------------------------------------------------------------------------

## 3. Scope

### Included

- Canonical folder structure
- Naming conventions
- Numbering rules
- Document placement rules
- Cross-reference expectations
- Governance and drift-control requirements

### Excluded

- GitHub Actions workflows
- Build pipelines
- Export automation

------------------------------------------------------------------------

## 4. Control Plane Alignment

The directory structure supports all six UIAO control planes:

| Plane                   | Directory Role                                |
|-------------------------|-----------------------------------------------|
| Identity                | Root namespace for identity-aligned documents |
| Network                 | SD-WAN, segmentation, routing artifacts       |
| Addressing              | IPAM, DNS/DHCP, deterministic addressing      |
| Telemetry and Location  | Telemetry, INR, E911, SIEM                    |
| Security and Compliance | FedRAMP, TIC 3.0, SCuBA                       |
| Management              | CMDB, Intune, drift detection                 |

Each plane has a predictable location in the repository.

------------------------------------------------------------------------

## 5. Core Concepts

The directory structure operationalizes the Eight Core Concepts:

1. **Single Source of Truth (SSOT)** — UIAO operates on the principle that every claim has one authoritative origin. All other representations are pointers, not copies. This ensures provenance, prevents drift, and enables federated truth resolution across boundaries.
2.  **Conversation as the atomic unit** — Document relationships reflect
    runtime flow
3.  **Identity as the root namespace** — Identity documents appear first
4.  **Deterministic addressing** — Numbering is deterministic and stable
5.  **Certificate-anchored overlay** — Security documents grouped
    consistently
6.  **Telemetry as control** — Telemetry documents grouped under
    compliance
7.  **Embedded governance and automation** — Structure supports
    automation
8.  **Public service first** — Clear, accessible, predictable layout

------------------------------------------------------------------------

## 6. Architecture Model

### 6.1 Canonical Directory Layout

The UIAO repository uses a 12-document canon organized into four phases:

    /docs
       00_ControlPlaneArchitecture.md
       01_UnifiedArchitecture.md
       02_CanonSpecification.md

       03_FedRAMP20x_Crosswalk.md
       04_FedRAMP20x_Phase2_Summary.md
       05_ManagementStack.md

       06_ProgramVision.md
       07_LeadershipBriefing.md
       08_ModernizationTimeline.md

       09_CrosswalkIndex.md
       10_DirectoryStructure.md
       11_GlossaryAndDefinitions.md

This structure is deterministic and must not be altered.

### 6.2 Numbering Rules

**Rule 1 — Two-Digit Prefix**

Every document begins with a two-digit prefix:

- 00-02: Foundational Architecture
- 03-05: Compliance and Governance
- 06-08: Program and Leadership
- 09-11: Index and Metadata

**Rule 2 — No Gaps**

Numbers must remain contiguous. If a document is removed, its number is
retired permanently.

**Rule 3 — No Renumbering**

Once assigned, a number is immutable.

**Rule 4 — Appendices Use Suffixes**

Appendices follow the pattern:

- `A_*.md`
- `B_*.md`
- `C_*.md`

**Rule 5 — No Nested Directories for Canon Documents**

All 12 canonical documents live directly under `/docs`.

------------------------------------------------------------------------

## 7. Runtime Model

The directory structure mirrors the UIAO runtime model:

### 7.1 Conversation Flow to Document Flow

Identity - Addressing - Certificates - Overlay - Telemetry - Policy

maps to

00 - 01 - 02 - 03 - 04 - 05 - 06 - 07 - 08 - 09 - 10 - 11

### 7.2 Deterministic Navigation

Given the number, the document’s role is always known.

### 7.3 Continuous Evaluation

Crosswalks and governance documents (03-05, 09-11) support continuous
monitoring.

------------------------------------------------------------------------

## 8. Directory Structure (Canonical Table)

| Number | Document | Category | Description |
|----|----|----|----|
| 00 | ControlPlaneArchitecture | Architecture | Defines the six control planes |
| 01 | UnifiedArchitecture | Architecture | Cross-plane architectural model |
| 02 | CanonSpecification | Architecture | Doctrinal modernization canon |
| 03 | FedRAMP20x_Crosswalk | Compliance | Full FedRAMP 20x mapping |
| 04 | FedRAMP20x_Phase2_Summary | Compliance | Modernization-focused summary |
| 05 | ManagementStack | Governance | ServiceNow + Intune control plane |
| 06 | ProgramVision | Leadership | Strategic modernization vision |
| 07 | LeadershipBriefing | Leadership | Executive slide-deck narrative |
| 08 | ModernizationTimeline | Leadership | PMO-ready sequencing plan |
| 09 | CrosswalkIndex | Index | Master index of all crosswalks |
| 10 | DirectoryStructure | Index | This document |
| 11 | GlossaryAndDefinitions | Index | Canonical glossary |

------------------------------------------------------------------------

## 9. Dependencies and Sequencing

### Upstream Dependencies

- Identity modernization
- IPAM modernization
- SD-WAN overlay deployment

### Downstream Dependencies

- Automation pipelines
- Crosswalk generation
- Leadership reporting

### Critical Path

00 - 01 - 02 - 03 - 04 - 05 - 06 - 07 - 08 - 09 - 10 - 11

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

### Repository Drift Controls

- No renumbering
- No renaming
- No relocation
- No duplication
- No cross-document redefinition

### Remediation Workflow

- GitHub PR review
- Canon steward approval
- Automated structure validation

------------------------------------------------------------------------

## 11. Appendices

### Appendix A: Definitions

*See `docs/glossary.md`*

### Appendix B: Tables

*Directory Structure canonical table is in Section 8.*

### Appendix C: Evidence Sources

*See `data/parameters.yml` and control-library entries for evidence
source catalogs.*

------------------------------------------------------------------------

## 12. Revision History

| Version | Date    | Author            | Summary                   |
|---------|---------|-------------------|---------------------------|
| 1.0     | 2026-03 | UIAO Canon Engine | Initial canonical release |
