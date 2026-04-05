---
title: "System Inventory And Components V1.0"
author: "UIAO Modernization Program"
date: today
date-format: "MMMM D, YYYY"
format:
  html: default
  docx: default
  pdf: default
  gfm: default
---


# System Inventory and Components

**Classification:** CUI/FOUO  
**Version:** 1.0  
**Generated:** Auto-generated  

---



## 1. Overview

### 1.1 Purpose

This document provides the authoritative component inventory for the
UIAO system. It is machine-generated from
structured YAML data to ensure accuracy, prevent version drift, and
satisfy NIST 800-53 Rev 5 CM-8 (System Component Inventory) requirements.

- **System:** UIAO (UIAO)
- **Authorization Level:** FedRAMP Moderate
- **Classification:** CUI/FOUO

### 1.2 Inventory Maintenance

This inventory is updated automatically by the UIAO-Core Documentation-as-Code pipeline
on every push to the `main` branch. Manual edits to generated files are prohibited;
all changes must be made in the source YAML files under `data/`.

---

## 2. Hardware Inventory

### 2.1 On-Premises Hardware


| Asset ID | Device Type | Manufacturer | Location | UIAO Role | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| SDWAN-001 | SD-WAN Edge Router | Cisco | HQ Data Center | Overlay Fabric — Primary | Active |
| SDWAN-002 | SD-WAN Edge Router | Cisco | DR Data Center | Overlay Fabric — Secondary | Active |
| SDWAN-BRN-* | SD-WAN Branch Nodes | Cisco | Branch Offices | Branch Connectivity (×12) | Active |
| FW-001 | Next-Gen Firewall | Palo Alto / Cisco | HQ Perimeter | Perimeter Security | Active |
| DNS-001 | IPAM / DNS Appliance | InfoBlox | HQ Data Center | Authoritative DNS / DHCP | Active |
| SRV-MGMT-* | Management Servers | Dell / HPE | HQ Data Center | Orchestration / Policy (×4) | Active |


### 2.2 Hardware Lifecycle Status

All hardware components are subject to the UIAO Hardware Lifecycle Policy:
- **Active:** In production and within vendor support lifecycle
- **EOS (End of Support):** Vendor support expired; remediation required within 90 days
- **EOL (End of Life):** Hardware decommissioned or scheduled for replacement

---

## 3. Software Inventory

### 3.1 Core Software Components


| Software | Version | Vendor | UIAO Plane | FedRAMP Status | License |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Microsoft Entra ID | Current (Evergreen) | Microsoft | Identity | Authorized (High) | M365 Government |
| Microsoft Sentinel | Current (Evergreen) | Microsoft | Telemetry | Authorized (High) | Per-GB / Commit Tier |
| Cisco Catalyst SD-WAN | IOS-XE 17.12.1a+ | Cisco | Network | Authorized (Moderate) | DNA Advantage |
| InfoBlox BloxOne | NIOS 9.0.8 / 2026.1 | InfoBlox | Addressing | Authorized (Moderate) | DDI Subscription |
| CyberArk PAM | 14.x | CyberArk | Identity | Authorized (Moderate) | Privileged Cloud |
| Microsoft Intune | Current (Evergreen) | Microsoft | Management | Authorized (High) | M365 Government |


### 3.2 Open Source and COTS Utilities

| Component | Version | Language | Purpose | Repository |
| :--- | :--- | :--- | :--- | :--- |
| uiao-core | 1.0 | Python 3.12+ | Documentation pipeline | GitHub |
| Jinja2 | Current | Python | Template rendering | PyPI |
| MkDocs | Current | Python | Documentation site | PyPI |
| Mermaid | Current | JavaScript | Diagram generation | npm |
| python-docx | Current | Python | DOCX export | PyPI |
| OPA (Open Policy Agent) | Current | Go | Policy engine | GitHub |

---

## 4. Network Components

### 4.1 Network Component Inventory

<img src="assets/images/mermaid/flowchart_lr.png" alt="flowchart_lr" />

### 4.2 Network Segment Definitions

| Segment | VLAN / VPN | Subnet Range | Purpose | Access Policy |
| :--- | :--- | :--- | :--- | :--- |
| Identity Zone | VPN-100 | 10.100.0.0/24 | IdP and PAM services | Privileged access only |
| Application Zone | VPN-200 | 10.200.0.0/22 | Agency workloads and APIs | Identity-verified access |
| Data Zone | VPN-300 | 10.300.0.0/24 | Databases and file stores | Application-tier only |
| Telemetry Zone | VPN-400 | 10.400.0.0/24 | SIEM and log aggregation | Log-writer service accounts |
| Management Zone | VPN-500 | 10.500.0.0/24 | Orchestration and policy engines | Break-glass + PAM session |
| DMZ | VPN-010 | 10.10.0.0/28 | Internet-facing gateways | Public-facing; WAF enforced |

---

## 5. Cloud Services (Azure / AWS)

### 5.1 Azure GovCloud Services

| Service | Tier / SKU | Purpose | FedRAMP Package | Region |
| :--- | :--- | :--- | :--- | :--- |
| Azure Active Directory (Entra ID) | P2 | Identity Provider | GCC High (IL4) | US Gov Virginia |
| Microsoft Sentinel | Standard | SIEM / SOAR | GCC High | US Gov Virginia |
| Log Analytics Workspace | Per-GB | Log aggregation | GCC High | US Gov Virginia |
| Azure Key Vault | Premium (HSM) | Key and secret management | GCC High | US Gov Virginia |
| Azure Monitor | Standard | Metrics and alerting | GCC High | US Gov Virginia |
| Azure Policy | Standard | Configuration governance | GCC High | US Gov Virginia |
| Microsoft Intune | Government | MDM / MAM | GCC High | US Gov Virginia |
| Microsoft Defender for Cloud | Standard | CSPM / CWPP | GCC High | US Gov Virginia |

### 5.2 AWS GovCloud Services (if applicable)

| Service | Purpose | FedRAMP Package | Region |
| :--- | :--- | :--- | :--- |
| AWS GovCloud (VPC) | Isolated cloud workloads | High Authorized | us-gov-west-1 |
| AWS Direct Connect | Dedicated WAN connectivity | High Authorized | us-gov-west-1 |
| AWS CloudTrail | API audit logging | High Authorized | us-gov-west-1 |

---

## 6. Interconnections

### 6.1 System Interconnections

All system interconnections are documented via an Interconnection Security Agreement (ISA)
and a Memorandum of Understanding (MOU) as required by NIST 800-47.

| System | Owner | Connection Type | Data Exchanged | Agreement | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Agency HRIS | Human Resources | REST API (HTTPS) | Employee identity events (JML) | ISA-001 | Active |
| Agency PKI / CA | Security | LDAP (636/TLS) | Certificate validation | ISA-002 | Active |
| CDM/CLAW (DHS) | DHS / CISA | HTTPS API | Asset telemetry, vulnerability data | ISA-003 | Active |
| US-CERT Portal | CISA | HTTPS | Incident reports | ISA-004 | Active |
| ServiceNow | ITSM | REST API (HTTPS) | Ticketing, POAM workflow | ISA-005 | Active |
| Agency Data Warehouse | Analytics | SFTP / TLS | Compliance metrics exports | ISA-006 | Review Pending |

---

## 7. Component Status Dashboard

### 7.1 Control Plane Health Summary


| Control Plane | Key Components | Operational Status | FedRAMP Evidence |
| :--- | :--- | :--- | :--- |
| Identity Plane | Entra ID, ICAM, CyberArk PAM | ✅ Active | Entra ID sign-in logs |
| Network Plane | Cisco SD-WAN, UIAO Gateway | ✅ Active | SD-WAN IPFIX flows |
| Addressing Plane | InfoBlox IPAM, DNS/DHCP | ✅ Active | DDI API bindings |
| Telemetry Plane | Sentinel, CDM/CLAW | ✅ Active | Sentinel analytics |
| Management Plane | OPA Policy Engine, Terraform | ✅ Active | Terraform state audit |


### 7.2 Vendor Support Status


| Vendor | Product | Support Status | Critical Version |
| :--- | :--- | :--- | :--- |
| Microsoft | Entra ID + Sentinel | ✅ Supported (Evergreen) | Current |
| Cisco | Catalyst SD-WAN | ✅ Supported | IOS-XE 17.12.1a+ |
| InfoBlox | BloxOne | ✅ Supported | NIOS 9.0.8+ |
| CyberArk | PAM Cloud | ✅ Supported | 14.x |


---

## 8. Inventory Maintenance Procedures

### 8.1 Update Frequency

| Inventory Type | Update Frequency | Trigger | Owner |
| :--- | :--- | :--- | :--- |
| Software Inventory | On every release | CI/CD pipeline | DevSecOps |
| Network Components | Quarterly | Change control review | Network Team |
| Cloud Services | On provisioning/decommission | Terraform state change | Cloud Team |
| Interconnections | On new ISA approval | ISA workflow | ISSO |
| Hardware | Semi-annually | Physical audit | Operations |

### 8.2 CM-8 Control Implementation

This document satisfies the following NIST 800-53 Rev 5 CM-8 sub-controls:

| Sub-Control | Requirement | Implementation |
| :--- | :--- | :--- |
| CM-8(a) | Develop inventory of system components | This document, auto-generated from YAML source |
| CM-8(b) | Review and update inventory | CI/CD pipeline updates on every merge to `main` |
| CM-8(1) | Updates during installations/removals | Terraform state changes trigger inventory refresh |
| CM-8(2) | Automated maintenance | `scripts/generate_docs.py` maintains inventory currency |
| CM-8(3) | Automated unauthorized component detection | CDM/CLAW + Sentinel analytics alert on unregistered assets |

---

## 9. Related Documents

- `docs/authorization_boundary_v1.0.md` — Authorization boundary definition
- `docs/fedramp_ssp_narrative_full_v1.0.md` — Full SSP narrative
- `docs/vendor_stack_v1.0.md` — Vendor registry and compliance status
- `data/control-planes.yml` — Source data for control plane components
- `data/vendor-stack.yml` — Source data for vendor inventory
- `exports/oscal/` — Machine-readable OSCAL component inventory artifacts

---

*Generated by the UIAO-Core Pipeline*