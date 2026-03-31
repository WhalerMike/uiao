---
title: "Document-Skeleton"
author: "UIAO Modernization Program"
date: today
date-format: "MMMM D, YYYY"
format:
  html: default
  docx: default
  pdf: default
  gfm: default
---

# UIAO Canonical Document Skeleton v1.0

> A deterministic, plane-aligned, canon-aligned structure for all UIAO documents.

| Field | Value |
|---|---|
| **Version** | 1.0 |
| **Date** | 2026-03-26 |
| **Status** | Active |
| **Governed by** | `docs/STYLE-GUIDE.md`, `data/style-guide.yml` |
| **Template** | `templates/canonical-skeleton.md.j2` |
| **Machine-readable** | `data/document-skeleton.yml` |

---

## Overview

This skeleton is intentionally rigid. It is the architectural equivalent of a federal form: predictable, complete, and enforceable.

Every UIAO document -- from Identity Plane specs to FedRAMP crosswalks to modernization appendices -- must follow this exact structure unless explicitly exempted via `data/style-guide.yml`.

The skeleton enforces:

- Structural determinism across all documents
- Plane-aligned interoperability
- Consistent compliance mapping
- Self-governing canon integrity
- Automated document generation readiness

---

## Section 1: Title Page

Every document begins with a metadata block.

| Field | Required | Description |
|---|---|---|
| Title | Yes | Document title |
| Subtitle | No | Clarifying subtitle if needed |
| Version | Yes | Semantic version (e.g., 1.0) |
| Date | Yes | ISO 8601 date (YYYY-MM-DD) |
| Classification | Yes | CUI, FOUO, or Unclassified |
| Source Plane(s) | Yes | One or more of the Six Control Planes |
| Document Type | Yes | Canon Volume, Architecture Spec, Appendix, Crosswalk, Project Plan, Leadership Briefing |

---

## Section 2: Purpose

A concise statement describing:

- **Why** this document exists
- **What** architectural or governance function it serves
- **Which audience** it supports

### Template Language

> This document defines the [PLANE/COMPONENT] architecture and its role in the Unified Identity-Addressing-Overlay (UIAO) modernization framework. It serves [AUDIENCE] by providing [FUNCTION].

---

## Section 3: Scope

Define:

| Element | Description |
|---|---|
| Included | What this document covers |
| Excluded | What is explicitly out of scope |
| Boundaries | Logical or organizational boundaries |
| Assumptions | Preconditions that must be true |
| Dependencies | Other documents this depends on |

This prevents overlap and drift between documents.

---

## Section 4: Control Plane Alignment

A mandatory section declaring how this document relates to the Six Control Planes.

| Plane | Role |
|---|---|
| Identity Control Plane | [Primary / Dependent / Referenced / Not Applicable] |
| Network Control Plane | [Primary / Dependent / Referenced / Not Applicable] |
| Addressing Control Plane | [Primary / Dependent / Referenced / Not Applicable] |
| Telemetry and Location Control Plane | [Primary / Dependent / Referenced / Not Applicable] |
| Security and Compliance Plane | [Primary / Dependent / Referenced / Not Applicable] |
| Management Plane (ServiceNow + Intune) | [Primary / Dependent / Referenced / Not Applicable] |

Rules:

- Every document must have at least one **Primary** plane
- **Dependent** means this document consumes data from that plane
- **Referenced** means the plane is mentioned but not central
- **Not Applicable** means no interaction

---

## Section 5: Core Concepts

This section references the Seven Core Concepts from `data/style-guide.yml`. Only concepts relevant to the document are expanded; all seven are listed.

| # | Concept | Relevant |
|---|---|---|
| 1 | Conversation as the atomic unit | [Yes/No] |
| 2 | Identity as the root namespace | [Yes/No] |
| 3 | Deterministic addressing | [Yes/No] |
| 4 | Certificate-anchored overlay | [Yes/No] |
| 5 | Telemetry as control | [Yes/No] |
| 6 | Embedded governance and automation | [Yes/No] |
| 7 | Public service first | [Yes/No] |

Each relevant concept is described using the canonical definitions from `data/style-guide.yml` frozen_definitions section.

---

## Section 6: Architecture Model

The technical heart of the document. Include all applicable subsections.

### 6.1 Architectural Overview

Narrative description of the plane or component. Written in the UIAO voice: authoritative, declarative, technically precise.

### 6.2 Architecture Diagram References

| Diagram | File Path | Description |
|---|---|---|
| [Name] | `docs/images/[filename].png` | [Description] |
| [Name] | `assets/[filename].drawio` | [Description] |

### 6.3 Component Definitions

Each component follows this pattern:

| Field | Value |
|---|---|
| **Name** | [Component name] |
| **Purpose** | [What it does] |
| **Inputs** | [What it consumes] |
| **Outputs** | [What it produces] |
| **Dependencies** | [What it requires] |
| **Evidence Sources** | [Logs, APIs, dashboards] |

### 6.4 Data Flows

Describe conversation-level flows, identity flows, telemetry flows, or addressing flows as applicable.

### 6.5 Integration Points

Cross-plane and cross-system integrations. Reference the Control Plane Alignment table from Section 4.

---

## Section 7: Runtime Model

Describes how the architecture behaves at runtime.

### 7.1 Conversation Flow

The canonical runtime sequence:

1. Identity initiates
2. Addressing binds
3. Certificates authenticate
4. Overlay routes
5. Telemetry informs
6. Policy evaluates continuously

### 7.2 Deterministic Decisioning

Same inputs produce same outputs across clouds and agencies. Document any decision points specific to this component.

### 7.3 Continuous Evaluation

How telemetry modifies decisions in real time. Reference `data/monitoring-sources.yml` for telemetry sources.

### 7.4 Assurance Signals

| Signal Type | Source | Evaluation |
|---|---|---|
| Identity assurance | Entra ID / CyberArk | [Description] |
| Device assurance | Intune / CrowdStrike | [Description] |
| Path assurance | Cisco Catalyst SD-WAN | [Description] |
| Location assurance | Infoblox DDI | [Description] |

---

## Section 8: Compliance Mapping

Mandatory for all documents, even if the mapping is minimal.

### 8.1 FedRAMP 20x Alignment

| Element | Value |
|---|---|
| Baseline | Moderate / High |
| FedRAMP 20x Class | Class C |
| Validation Method | Telemetry-based / Manual / Hybrid |
| Reference | `data/fedramp-20x.yml` |

### 8.2 NIST 800-53 Rev 5 Controls

| Control ID | Control Name | Implementation |
|---|---|---|
| [ID] | [Name] | [How this document implements or supports the control] |

All mappings must reference `data/crosswalk-index.yml` and `data/nist_crosswalk.yml`.

### 8.3 Evidence Sources

| Evidence Type | Source | Location |
|---|---|---|
| Logs | [System] | [Path or API endpoint] |
| Configuration | [System] | [Export method] |
| Dashboard | [System] | [URL or reference] |

### 8.4 KSI Categories

| KSI Category | Relevance |
|---|---|
| KSI-IAM | [Description] |
| KSI-PIY | [Description] |
| KSI-MLA | [Description] |

Reference `data/ksi-mappings.yml` for authoritative KSI definitions.

---

## Section 9: Dependencies and Sequencing

### 9.1 Upstream Dependencies

| Dependency | Document/System | Status |
|---|---|---|
| [What must exist first] | [Reference] | [Active / Planned / Blocked] |

### 9.2 Downstream Dependencies

| Dependent | Document/System | Impact |
|---|---|---|
| [What relies on this] | [Reference] | [Description of dependency] |

### 9.3 Modernization Timeline References

Link to integrated Gantt timeline and `data/roadmap.yml` for sequencing context.

---

## Section 10: Governance and Drift Controls

### 10.1 Source of Authority

| Element | Authority |
|---|---|
| Data creation | [Role or system] |
| Data modification | [Role or system] |
| Data revocation | [Role or system] |

### 10.2 Drift Detection

| Method | Source | Frequency |
|---|---|---|
| Telemetry-based | [Sentinel, Splunk, INR] | [Real-time / Polling interval] |
| CMDB-based | [ServiceNow] | [Sync interval] |
| Configuration-based | [Intune, SD-WAN] | [Scan interval] |

### 10.3 Remediation Workflow

| Trigger | Workflow | System |
|---|---|---|
| [Drift condition] | [Remediation action] | [ServiceNow, Intune, SD-WAN, IPAM] |

### 10.4 Audit Anchors

| Artifact | Purpose | Location |
|---|---|---|
| [Evidence artifact] | [Annual assessment support] | [Path or export method] |

---

## Section 11: Appendices

Appendices follow a strict order. Not all appendices are required for every document.

| Appendix | Title | Required |
|---|---|---|
| A | Definitions | As needed |
| B | Tables | As needed |
| C | Diagrams | As needed |
| D | Crosswalks | As needed |
| E | Project Plans | As needed |
| F | Canon Volume References | As needed |
| G | Modernization Appendices | As needed |
| H | Evidence Artifacts | As needed |

**Rule**: No appendix may redefine anything in the core document. Appendices supplement; they do not override.

---

## Section 12: Revision History

| Version | Date | Author | Summary of Changes |
|---|---|---|---|
| 1.0 | [YYYY-MM-DD] | [Author] | Initial release |

---

## Related Files

| File | Purpose |
|---|---|
| `docs/STYLE-GUIDE.md` | Writing and formatting governance |
| `data/style-guide.yml` | Machine-readable style rules |
| `data/document-skeleton.yml` | Machine-readable skeleton structure |
| `templates/canonical-skeleton.md.j2` | Jinja2 template for document generation |
| `data/canon-spec.yml` | Canon specification |
