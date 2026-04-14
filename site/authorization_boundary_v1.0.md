
# Authorization Boundary

**Classification:** Public  
**Version:** 1.0  
**Generated:** Auto-generated  

---



## 1. Boundary Overview

### 1.1 System Identification

- **System Name:** UIAO
- **Acronym:** UIAO
- **Authorization Level:** FedRAMP Moderate (NIST 800-53 Rev 5)
- **Boundary Owner:** UIAO Program Office
- **Classification:** Public

### 1.2 Boundary Definition

The UIAO authorization boundary is defined as all hardware,
software, infrastructure, data, people, procedures, and facilities that
are necessary to operate the system and are under the direct management
and security control of the system owner.

Components **inside** the boundary:
- All control plane services managed by the agency
- Identity provider and ICAM infrastructure
- Network fabric (SD-WAN nodes managed by the agency)
- IPAM / DNS platform instances
- SIEM and telemetry aggregation infrastructure
- Management plane policy engines and orchestration systems

Components **outside** the boundary (leveraged services):
- FedRAMP-authorized cloud service providers (CSPs)
- Third-party SaaS tools with separate ATO packages
- Agency physical infrastructure shared with other systems

---

## 2. Network Architecture

### 2.1 High-Level Architecture

<img src="assets/images/plantuml/flowchart_td.png" alt="flowchart_td" />

### 2.2 Network Segmentation

The UIAO network is segmented into the following zones:

| Zone | Description | Controls Applied |
| :--- | :--- | :--- |
| External / Untrusted | Internet-facing; no direct system access | CDN, WAF, NGFW filtering |
| DMZ / Perimeter | Gateway and proxy services | TLS termination, API gateway, WAF rules |
| Identity Zone | IdP and PAM services | Zero Trust Policy Engine, Entra ID CA |
| Network Fabric | SD-WAN overlay | mTLS encryption, micro-segmentation |
| Data Zone | Backend services and data stores | Encryption at rest, RBAC, audit logging |
| Telemetry Zone | SIEM and monitoring | Immutable log storage, restricted write access |
| Management Zone | Orchestration and policy | Break-glass procedures, session recording |

---

## 3. External Connections

### 3.1 External Connection Inventory

All external connections to the UIAO system boundary are documented below.
Connections are reviewed quarterly and updated in this canonical document.

| Connection | Direction | Protocol | Encryption | Purpose | Risk Level |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Agency Staff → UIAO Gateway | Inbound | HTTPS (443) | TLS 1.3 | User access | Medium |
| UIAO → Entra ID (Microsoft 365) | Outbound | HTTPS (443) | TLS 1.3 | Identity federation | Low |
| UIAO → InfoBlox Cloud | Outbound | HTTPS/DNS | TLS 1.3 / DNSSEC | IPAM / DNS | Low |
| Cisco SD-WAN → vManage | Bidirectional | HTTPS / NETCONF | TLS 1.3 | SD-WAN control plane | Low |
| UIAO → Microsoft Sentinel | Outbound | HTTPS (443) | TLS 1.3 | Log ingestion | Low |
| UIAO → CDM/CLAW | Outbound | HTTPS (443) | TLS 1.3 | Asset telemetry | Low |
| UIAO → CSP (Azure GovCloud) | Bidirectional | HTTPS / ExpressRoute | TLS 1.3 / IPSec | Cloud workloads | Medium |

### 3.2 Inherited Controls from Cloud Service Providers


- **Microsoft (Entra ID + Sentinel):** FedRAMP High Authorized (Azure Government)
- **Cisco (SD-WAN):** FedRAMP Moderate Authorized
- **InfoBlox (BloxOne):** FedRAMP Moderate Authorized
- **CyberArk (PAM):** FedRAMP Moderate Authorized


---

## 4. Internal Components

### 4.1 Component Summary by Plane





#### 4.1.1. identity

**Description:** Manages user and device identity, authentication, and access control across the UIAO architecture.



| Component | Role |
| :--- | :--- |

| Microsoft Entra ID | Primary Identity Provider |

| ICAM Governance | Identity governance and compliance |

| Zero Trust Policy Engine | Continuous access evaluation |




#### 4.1.2. addressing

**Description:** Manages IP address space, DNS resolution, and asset tracking across the enterprise network.



| Component | Role |
| :--- | :--- |

| InfoBlox IPAM | Authoritative Source of Truth |

| DNS Management | Authoritative DNS zones |

| DHCP Management | Scope governance |

| Cloud IPAM Reconciliation | Multi-cloud addressing truth |




#### 4.1.3. overlay

**Description:** Provides secure overlay networking, zero-trust network access, and microsegmentation capabilities.



| Component | Role |
| :--- | :--- |

| ZTNA Gateway | TBD |

| SD-WAN Controller | TBD |

| Microsegmentation Engine | TBD |




#### 4.1.4. telemetry

**Description:** Collects, aggregates, and analyzes security telemetry from all planes to enable continuous monitoring and threat detection.



| Component | Role |
| :--- | :--- |

| Splunk / Sentinel | Aggregation, correlation, compliance |

| Azure Monitor / CloudWatch | Cloud-native telemetry |

| ThousandEyes / Riverbed | Network path truth |

| InfoBlox | DNS/DHCP/IPAM evidence |

| Defender / MINR | Endpoint truth |




#### 4.1.5. management

**Description:** Orchestrates policy enforcement, automation, and continuous compliance monitoring across all UIAO planes.



| Component | Role |
| :--- | :--- |

| Policy Engine | TBD |

| ConMon Dashboard | TBD |

| Automation Orchestrator | TBD |




#### 4.1.6. network

**Description:** Manages physical and virtual network connectivity, routing, and traffic engineering.



| Component | Role |
| :--- | :--- |

| vManage | Centralized policy engine |

| vSmart | Control-plane orchestrator |

| vBond | Secure orchestration |

| WAN Edge Devices | Enforcement points |




#### 4.1.7. endpoint

**Description:** Control plane component.


| Component | Role |
| :--- | :--- |

| Defender / MINR | Endpoint detection and response |

| Intune | Configuration and compliance management |

| Entra ID Device Objects | Device identity anchoring |







---

## 5. Data Flow Across Boundary

### 5.1 Boundary Crossing Data Flows

All data crossing the authorization boundary is encrypted in transit using
TLS 1.3 or IPSec. The following data types traverse the boundary:

| Data Type | Classification | Boundary Direction | Encryption | Justification |
| :--- | :--- | :--- | :--- | :--- |
| Authentication Tokens (JWT/SAML) | CUI | Inbound / Outbound | TLS 1.3 | Identity federation with Entra ID |
| Network Flow Records (IPFIX) | CUI | Outbound | TLS 1.3 | Telemetry to Sentinel |
| DNS Query Logs | CUI | Outbound | TLS 1.3 | InfoBlox API to SIEM |
| Device Compliance Status | CUI | Inbound | TLS 1.3 | Intune MDM compliance check |
| OSCAL Evidence Artifacts | CUI | Outbound | TLS 1.3 | Compliance reporting |
| SD-WAN Configuration | CUI | Outbound | TLS 1.3 | vManage control plane |

### 5.2 Data Flow Diagram

<img src="assets/images/plantuml/flowchart_lr.png" alt="flowchart_lr" />

---

## 6. Ports, Protocols, and Services

### 6.1 Allowed Inbound Ports

| Port | Protocol | Service | Source | Justification |
| :--- | :--- | :--- | :--- | :--- |
| 443 | TCP / HTTPS | UIAO Gateway | All agency users | Application access (TLS 1.3 required) |
| 443 | TCP / HTTPS | Entra ID federation | Microsoft cloud | SSO and SAML assertion delivery |
| 53 | UDP / DNS | InfoBlox DNS | Internal clients | Name resolution (DNSSEC enforced) |

### 6.2 Allowed Outbound Ports

| Port | Protocol | Service | Destination | Justification |
| :--- | :--- | :--- | :--- | :--- |
| 443 | TCP / HTTPS | Microsoft Sentinel | Azure GovCloud | Log ingestion and SIEM telemetry |
| 443 | TCP / HTTPS | InfoBlox BloxOne | InfoBlox Cloud | IPAM data synchronization |
| 443 | TCP / HTTPS | Cisco vManage | Cisco cloud | SD-WAN control plane management |
| 443 | TCP / HTTPS | CDM/CLAW | DHS CDM SaaS | Asset visibility and reporting |
| 500 / 4500 | UDP / IKEv2 | SD-WAN IPSec | Branch / WAN | Encrypted WAN tunnels |

### 6.3 Blocked / Denied Traffic

All traffic not explicitly permitted by the above allowlists is denied at the
perimeter firewall and UIAO Gateway. Denied traffic events are logged to
Microsoft Sentinel for analysis.

---

## 7. Related Documents

- `docs/fedramp_ssp_narrative_full_v1.0.md` — Full SSP narrative with control implementation
- `docs/system_inventory_and_components_v1.0.md` — Component inventory details
- `docs/vendor_stack_v1.0.md` — Vendor registry and FedRAMP authorization status
- `exports/oscal/` — Machine-readable OSCAL boundary artifacts

---

*Generated by the UIAO-Core Pipeline*