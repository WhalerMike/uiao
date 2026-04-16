---
title: "UIAO Control Plane Architecture"
version: "1.0"
classification: "CUI"
diagram-owner: gemini
---

# UIAO Control Plane Architecture

**Version 1.0 | Classification: CUI | Leadership Briefing Quality**

---

## 1. Overview

The UIAO Control Plane Architecture defines the six control planes that form the unified
modernization architecture for the agency. Each plane is a distinct operational domain with
clear ownership, integration points, and compliance responsibilities under FedRAMP Moderate.

The six control planes are:

1. **Identity Plane** — Authentication, authorization, and access governance
2. **Addressing Plane** — IP lifecycle, DNS, and DHCP management
3. **Overlay Plane** — Encrypted network fabric and micro-segmentation
4. **Telemetry Plane** — Security monitoring, KSI collection, and OSCAL evidence
5. **Management Plane** — Policy orchestration, automation, and configuration governance
6. **Compliance Plane** — Continuous ATO, OSCAL artifact management, and audit readiness

---

## 2. High-Level Control Plane Architecture

The diagram below provides a leadership-quality architectural overview showing all six control
planes and their primary integration relationships.

```diagram
UIAO Six-Plane Control Architecture diagram for a US federal agency leadership briefing.
Show six colored rectangular planes arranged in a 2×3 grid with a Policy Engine hub in the center connecting all planes:
1. Identity Plane (blue) — top-left: Microsoft Entra ID, CyberArk PAM, ICAM, MFA/PIV
2. Addressing Plane (green) — top-center: InfoBlox DDI, DNS, DHCP, IPAM
3. Overlay Plane (orange) — top-right: Cisco SD-WAN, ZTNA, Micro-Segmentation
4. Telemetry Plane (purple) — bottom-left: Microsoft Sentinel, CDM/CLAW, KSI Dashboard
5. Management Plane (teal) — bottom-center: Terraform, Ansible, OPA Policy Engine
6. Compliance Plane (indigo) — bottom-right: OSCAL, FedRAMP 20x, Continuous ATO
In the center: Policy Engine (dark hexagon) with bidirectional arrows to all planes.
Label each plane with its primary technology vendor logos in text.
Add a "Zero Trust Architecture" banner across the top.
Professional, high-resolution, federal government quality. White background. Clean sans-serif typography.
FedRAMP Moderate badge in the corner.
```

---

## 3. Identity Plane

### 3.1 Architecture

The Identity Plane is the cornerstone of the UIAO Zero Trust implementation. It establishes
**who** is authenticated and **what** they are authorized to access before any network traffic
is permitted.

```diagram
Identity Plane architecture diagram for a US federal agency Zero Trust implementation.
Show a layered architecture:
Layer 1 (Entry): PIV/CAC smart card and MFA inputs on the left
Layer 2 (Authentication): Microsoft Entra ID (Azure AD) with Conditional Access Policies in the center
Layer 3 (Governance): ICAM Platform (lifecycle, provisioning, access reviews) above Entra ID
Layer 4 (Privileged Access): CyberArk PAM (session recording, just-in-time access) below Entra ID
Layer 5 (Output): Access Tokens / SAML Assertions flowing right to the Policy Engine
Draw arrows showing the authentication flow from PIV/MFA → Entra ID → CyberArk (for privileged) or Policy Engine (for standard).
Include a "Risk Score" feedback loop from Telemetry Plane back to Conditional Access.
White background, clean typography, professional blue color scheme.
```

### 3.2 Components

| Component | Role | FedRAMP Level |
|:---|:---|:---|
| Microsoft Entra ID | Primary Identity Provider and SSO | High Authorized |
| ICAM Platform | Identity lifecycle, credentialing, access reviews | Agency-managed |
| CyberArk PAM | Privileged access management and session recording | Moderate Authorized |
| Microsoft Intune | Device compliance and MDM posture enforcement | High Authorized |

### 3.3 Key Controls (NIST SP 800-53 Rev 5)

- **IA-2:** Identification and Authentication (Multi-Factor)
- **AC-2:** Account Management (ICAM lifecycle governance)
- **AC-17:** Remote Access (Conditional Access + ZTNA)
- **AU-12:** Audit Record Generation (CyberArk session recording)

---

## 4. Addressing Plane

### 4.1 Architecture

The Addressing Plane provides authoritative IP address management, DNS, and DHCP across all
network environments. InfoBlox DDI is the single source of truth for all IP address space,
eliminating manual processes and enabling automated network provisioning.

### 4.2 Components

| Component | Role | FedRAMP Level |
|:---|:---|:---|
| InfoBlox BloxOne IPAM | Authoritative IP address management | Moderate Authorized |
| InfoBlox BloxOne DNS | DNSSEC-enforced authoritative DNS | Moderate Authorized |
| InfoBlox BloxOne TD | DNS threat defense and query logging | Moderate Authorized |
| DHCP Server (InfoBlox) | Lease management and rogue device detection | Moderate Authorized |

### 4.3 Key Controls

- **CM-8:** Information System Component Inventory (IPAM as network asset register)
- **SC-20:** Secure Name / Address Resolution (DNSSEC)
- **SC-21:** Secure Name / Address Resolution — Recursive Resolution

---

## 5. Overlay Plane

### 5.1 Architecture

The Overlay Plane governs **how** traffic flows between all resources, applying encryption and
micro-segmentation at scale. Cisco Catalyst SD-WAN provides the encrypted fabric, while ZTNA
policies enforce least-privilege network access from any location.

```diagram
UIAO Overlay Plane architecture diagram for a US federal agency SD-WAN and ZTNA deployment.
Show a hub-and-spoke network topology:
- Center hub: "UIAO Overlay Policy Engine" (dark blue hexagon)
- Spoke 1 (left): "Agency HQ" — Cisco SD-WAN edge node, connecting via mTLS tunnel
- Spoke 2 (top-left): "Branch Office A" — SD-WAN branch appliance, connecting via mTLS
- Spoke 3 (top-right): "Branch Office B" — SD-WAN branch appliance, connecting via mTLS
- Spoke 4 (right): "Remote Workers" — ZTNA client, connecting via ZTNA proxy
- Spoke 5 (bottom): "Azure GovCloud" — cloud gateway, connecting via ExpressRoute + IPSec
Draw mTLS encrypted tunnels as thick solid lines between all spokes and the hub.
Label each tunnel with "mTLS / IKEv2" and "AES-256".
Add micro-segmentation zones as dashed boxes around groups of workloads.
Professional SD-WAN architecture style, white background, federal government quality.
```

### 5.2 Components

| Component | Role | FedRAMP Level |
|:---|:---|:---|
| Cisco Catalyst SD-WAN | Encrypted overlay fabric and WAN optimization | Moderate Authorized |
| Cisco vManage | SD-WAN centralized management and policy | Moderate Authorized |
| ZTNA Proxy | Zero Trust Network Access enforcement | Agency-managed |
| Next-Gen Firewall | Perimeter filtering and stateful inspection | Agency-managed |

### 5.3 Key Controls

- **SC-8:** Transmission Confidentiality and Integrity (mTLS/IPSec)
- **SC-7:** Boundary Protection (micro-segmentation, NGFW)
- **AC-17:** Remote Access (ZTNA enforcement)

---

## 6. Telemetry Plane

### 6.1 Architecture

The Telemetry Plane aggregates security events, compliance signals, and performance metrics from
all other control planes. It feeds the KSI Dashboard for continuous authorization decision support
and exports OSCAL evidence artifacts for FedRAMP 20x compliance.

### 6.2 Components

| Component | Role | FedRAMP Level |
|:---|:---|:---|
| Microsoft Sentinel | SIEM / SOAR platform | High Authorized |
| CDM/CLAW | Continuous Diagnostics and Mitigation (DHS) | FedRAMP SaaS |
| KSI Dashboard | Key Security Indicator real-time dashboard | Agency-managed |
| OSCAL Evidence Bundler | Automated OSCAL artifact generation | Agency-managed |

### 6.3 Key Controls

- **AU-2:** Event Logging
- **AU-6:** Audit Record Review, Analysis, and Reporting
- **SI-4:** System Monitoring (CDM/CLAW)
- **CA-7:** Continuous Monitoring

---

## 7. Management Plane

### 7.1 Architecture

The Management Plane provides infrastructure-as-code automation, policy orchestration, and
configuration governance across all control planes. All changes flow through peer-reviewed
pull requests and are applied by automated pipelines, eliminating manual configuration drift.

### 7.2 Components

| Component | Role |
|:---|:---|
| Terraform | Infrastructure-as-code provisioning |
| Ansible | Configuration management and remediation automation |
| OPA (Open Policy Agent) | Policy-as-code evaluation and enforcement |
| GitHub Actions | CI/CD pipeline and audit trail |

### 7.3 Key Controls

- **CM-2:** Baseline Configuration (infrastructure-as-code)
- **CM-3:** Configuration Change Control (pull request workflow)
- **CM-6:** Configuration Settings (Ansible enforcement)

---

## 8. Compliance Plane

### 8.1 Architecture

The Compliance Plane manages continuous ATO through automated OSCAL artifact generation,
FedRAMP evidence collection, and POA&M management. It is the machine-readable layer that
enables FedRAMP 20x continuous authorization without annual re-authorization cycles.

### 8.2 Components

| Component | Role |
|:---|:---|
| UIAO-Core Pipeline | Canon YAML → OSCAL artifact generation |
| OSCAL SSP Generator | System Security Plan in OSCAL JSON/YAML format |
| OSCAL POA&M Manager | Plan of Action & Milestones tracking and export |
| FedRAMP 20x Evidence Store | KSI evidence collection and continuous reporting |

### 8.3 Key Controls

- **CA-2:** Control Assessments
- **CA-5:** Plan of Action and Milestones
- **CA-7:** Continuous Monitoring (FedRAMP 20x automation)
- **PL-2:** System Security Plan

---

## 9. Cross-Plane Integration Matrix

| From Plane | To Plane | Data / Signal | Protocol |
|:---|:---|:---|:---|
| Identity | Overlay | Access Tokens, Session Context | HTTPS / SAML |
| Identity | Telemetry | Auth Events, Failed Logins | HTTPS / CEF |
| Addressing | Overlay | IP Assignments, DNS Lookups | HTTPS / DNS |
| Addressing | Telemetry | DNS Query Logs, DHCP Leases | HTTPS / Syslog |
| Overlay | Telemetry | Flow Records, Policy Hits | IPFIX / HTTPS |
| Telemetry | Management | Alert Triggers, KSI Scores | HTTPS / Webhook |
| Telemetry | Compliance | KSI Evidence, OSCAL Artifacts | HTTPS / OSCAL |
| Management | All Planes | Configuration Enforcement | Terraform / Ansible |
| Compliance | All Planes | Control Assessment Status | OSCAL / REST |

---

*Source: UIAO-Core Architecture — Control Plane Architecture v1.0*
