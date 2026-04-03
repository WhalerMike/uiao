---
title: "Fedramp Ssp Narrative Full V1.0"
author: "UIAO Modernization Program"
date: today
date-format: "MMMM D, YYYY"
format:
  html: default
  docx: default
  pdf: default
  gfm: default
---

# FedRAMP System Security Plan — Full Narrative

**Classification:** CUI/FOUO  
**Version:** 1.0  
**Generated:** Auto-generated  

---



## 1. System Description

### 1.1 Program and System Identification

- **Program Name:** UIAO
- **System Name:** UIAO
- **Authorization Level:** FedRAMP Moderate (NIST 800-53 Rev 5)
- **Version:** 1.0
- **Classification:** CUI/FOUO

### 1.2 System Purpose

A fully modernized, identity-driven, cloud-optimized, telemetry-rich federal network is a federal modernization initiative
that unifies identity, addressing, overlay networking, telemetry, and governance
into a coherent, Zero Trust-aligned architecture.





### 1.3 System Owner and Contacts

| Role | Name | Organization |
| :--- | :--- | :--- |
| System Owner | TBD | Agency |
| AO (Authorizing Official) | TBD | Agency CISO |
| ISSO | TBD | Security Operations |
| ISSM | TBD | Agency Security |

---

## 2. Authorization Boundary

### 2.1 Boundary Overview

The UIAO authorization boundary encompasses all components that process, store,
or transmit federal information as part of the modernization program. The boundary is
defined by the five control planes and the services they govern.

<img src="assets/images/mermaid/flowchart_lr.png" alt="flowchart_lr" />

### 2.2 Control Planes in Boundary





- **Identity Control Plane:** 

- **Network Control Plane:** 

- **Addressing Control Plane:** 

- **Telemetry and Location Control Plane:** 

- **Security and Compliance Plane:** 




---

## 3. Data Flow

### 3.1 End-to-End Data Flow Narrative

All user requests traverse the following path within the UIAO boundary:

1. **Authentication** — User credentials are validated by the Identity Plane (Entra ID + ICAM).
2. **Policy Evaluation** — The Zero Trust Policy Engine evaluates identity, device, location, and risk signals.
3. **Routing** — Approved sessions are routed through the Cisco SD-WAN mTLS fabric.
4. **Service Resolution** — DNS / IPAM (InfoBlox) resolves internal service endpoints deterministically.
5. **Telemetry** — All sessions produce telemetry records ingested by Microsoft Sentinel and CDM.
6. **Continuous Monitoring** — Telemetry feeds back to the Management Plane for ongoing policy adjustment.

### 3.2 Data Flow Diagram

<img src="assets/images/mermaid/flowchart_lr.png" alt="flowchart_lr" />

---

## 4. Security Controls

### 4.1 Access Control (AC) Family




**Identity Control Plane:**

The Identity Control Plane is anchored in Entra ID and reinforced by ICAM governance, Conditional Access, Privileged Identity Management, and lifecycle automation. Identity becomes the authoritative source for access, addressing, certificates, and policy.














| Control ID | Control Name | Implementation Summary |
| :--- | :--- | :--- |
| AC-1 | Access Control Policy | Documented in UIAO Access Control Policy; enforced via Entra ID Conditional Access. |
| AC-2 | Account Management | JML automation via Entra ID and HRIS integration; Privileged Identity Management (PIM) enforced. |
| AC-3 | Access Enforcement | RBAC + ABAC policies evaluated by Zero Trust Policy Engine per session. |
| AC-4 | Information Flow Enforcement | Cisco SD-WAN enforces segmentation; mTLS ensures encrypted east-west traffic only. |
| AC-17 | Remote Access | All remote access traverses UIAO Gateway; no split-tunnel VPN; session telemetry logged. |
| AC-19 | Access Control for Mobile Devices | Intune MDM enforces device compliance; Conditional Access blocks non-compliant devices. |

### 4.2 Audit and Accountability (AU) Family

| Control ID | Control Name | Implementation Summary |
| :--- | :--- | :--- |
| AU-2 | Event Logging | Sign-in logs, CA outcomes, SD-WAN flow records, and DNS query logs are collected. |
| AU-3 | Content of Audit Records | Logs include timestamp, user identity, source IP, resource accessed, and outcome. |
| AU-6 | Audit Record Review | Microsoft Sentinel analytics rules provide automated alerting and SIEM review workflows. |
| AU-9 | Protection of Audit Information | Audit logs written to immutable storage; RBAC limits access to log readers only. |
| AU-12 | Audit Record Generation | All five control planes generate audit records; centralized via Log Analytics Workspace. |

### 4.3 Identification and Authentication (IA) Family








**Identity as the Root Namespace:**

Identity becomes the root namespace for all resources, ensuring that every IP address, certificate, subnet, policy, and telemetry event is derived from or bound to identity.
















| Control ID | Control Name | Implementation Summary |
| :--- | :--- | :--- |
| IA-2 | Identification and Authentication | PIV/CAC required for all privileged access; FIDO2 for standard users; MFA enforced. |
| IA-3 | Device Identification | Every device registered in InfoBlox IPAM and Intune; identity-derived IP addressing. |
| IA-5 | Authenticator Management | PIV lifecycle managed via ICAM governance; SSPR enforced for password-based fallback. |
| IA-8 | Non-Organizational Users | External contractor access governed by Entra External ID; reviewed quarterly. |

### 4.4 System and Communications Protection (SC) Family

| Control ID | Control Name | Implementation Summary |
| :--- | :--- | :--- |
| SC-5 | Denial of Service Protection | CDN / WAF absorbs volumetric DDoS; SD-WAN provides path diversity and failover. |
| SC-7 | Boundary Protection | Authorization boundary enforced at UIAO Gateway; micro-segmentation via SD-WAN VPNs. |
| SC-8 | Transmission Confidentiality | All transit encrypted via mTLS (TLS 1.3 minimum); SD-WAN IPSEC tunnels for WAN. |
| SC-12 | Cryptographic Key Establishment | PKI anchored to agency FPKI; certificates issued and rotated by CyberArk PAM. |
| SC-20 | Secure Name/Address Resolution | InfoBlox provides DNSSEC-signed authoritative DNS; split-horizon prevents data exfiltration. |
| SC-28 | Protection of Information at Rest | All data stores encrypted with AES-256; keys stored in Azure Key Vault. |

---

## 5. Continuous Monitoring

### 5.1 Monitoring Strategy

The UIAO continuous monitoring program is aligned to FedRAMP requirements and
the FedRAMP 20x Phase 2 Key Security Indicators (KSIs) framework. Monitoring is automated,
evidence-based, and integrated with the UIAO-Core Documentation-as-Code pipeline.


### 5.2 FedRAMP 20x Control Plane Alignment



| Plane | KSI Mapping | Evidence Method |
| :--- | :--- | :--- |

| identity | TBD | Automated telemetry |

| addressing | TBD | Automated telemetry |

| network | TBD | Automated telemetry |

| telemetry | TBD | Automated telemetry |

| endpoint | TBD | Automated telemetry |

| security | TBD | Automated telemetry |




### 5.3 Evidence Collection Pipeline

<img src="assets/images/mermaid/flowchart_lr.png" alt="flowchart_lr" />

---

## 6. Incident Response

### 6.1 Incident Response Overview

The UIAO incident response capability is automated and integrated with
the telemetry pipeline to ensure rapid detection and containment.

| IR Phase | Capability | Tooling |
| :--- | :--- | :--- |
| Detection | Automated alert generation | Microsoft Sentinel, CDM/CLAW |
| Analysis | SIEM triage and enrichment | Sentinel Workbooks, KQL Analytics |
| Containment | Network quarantine + token revocation | SD-WAN ACL push, Entra ID CAE |
| Eradication | Privileged session termination | CyberArk PAM, Intune Remote Wipe |
| Recovery | Automated re-provisioning | JML automation (Entra ID + HRIS) |
| Post-Incident | Evidence archival to OSCAL | UIAO-Core evidence pipeline |

### 6.2 IR Control Implementation

| Control ID | Control Name | Implementation |
| :--- | :--- | :--- |
| IR-4 | Incident Handling | Sentinel incidents mapped to ServiceNow; SLA tracked via POAM pipeline. |
| IR-5 | Incident Monitoring | 24/7 SOC monitoring; automated enrichment via Sentinel analytics. |
| IR-6 | Incident Reporting | US-CERT reporting within 1 hour; agency CISO notified within 15 minutes. |
| IR-8 | Incident Response Plan | IR Plan maintained in `docs/`; tested annually and after major incidents. |

---

## 7. Roles and Responsibilities

| Role | Responsibility |
| :--- | :--- |
| Authorizing Official (AO) | Final authorization decision; accepts residual risk |
| ISSO | Day-to-day security monitoring; artifact maintenance |
| ISSM | Oversight of ISSO activities; continuous monitoring program |
| System Owner | Resource allocation; remediation prioritization |
| DevSecOps Team | Control implementation; CI/CD pipeline security |

---

## 8. Appendix: Related Documents

- `docs/authorization_boundary_v1.0.md` — Detailed boundary architecture
- `docs/system_inventory_and_components_v1.0.md` — Component inventory
- `docs/zero_trust_narrative_v1.0.md` — Zero Trust implementation narrative
- `docs/vendor_stack_v1.0.md` — Vendor registry and compliance status
- `exports/oscal/` — Machine-readable OSCAL compliance artifacts

---

*Generated by the UIAO-Core Pipeline*