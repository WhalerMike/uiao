# Leadership Briefing - Unified Identity-Addressing-Overlay Architecture

Format: Markdown slide deck
Audience: CIO, CISO, CTO, PMO, Network/Identity Leadership
Version: 1.0 (March 2026)
Classification: CUI/FOUO or as appropriate

---

# Slide 1 - Program Overview

## Unified Identity-Addressing-Overlay Architecture (UIAO)

A coordinated modernization effort across:

- Microsoft Entra ID (Identity control plane)

- ICAM (NIST 800-63, OMB M-19-17) (Governance backbone)

- InfoBlox IPAM (Authoritative IPAM)

- Cisco Catalyst SD-WAN (Routing control plane)

- Cloud Telemetry + Location Services (Telemetry and location)

- TIC 3.0 Cloud + Branch (Security and compliance)


## Strategic Goal

Transform the agency into a cloud-optimized, identity-driven, telemetry-informed, Zero Trust-aligned, TIC 3.0-compliant federal enterprise

---

# Slide 2 - Why Modernization Is Required

## Current State Challenges

- TIC 2.0 hairpin bottlenecks

- AD-centric identity with limited governance

- Fragmented IPAM across cloud and on-prem

- Limited telemetry visibility

- No INR or E911 readiness

- Inconsistent Zero Trust enforcement


## Mission Impact

- Poor M365 performance

- Increased cyber risk

- Compliance gaps

- Operational inefficiencies


---

# Slide 3 - Program Vision

## End State

A fully modernized, identity-driven, cloud-optimized, telemetry-rich federal network

## Guiding Principles

- Zero Trust by default

- Identity as the new perimeter

- Telemetry as the truth source

- Cloud-first routing

- Incremental modernization (no big-bang)

- FedRAMP-aligned controls

- Modular, extensible architecture


## Design Principle

> If it degrades the citizen interaction, it does not ship

---

# Slide 4 - Five Control Planes


## Identity Control Plane

- Entra ID

- ICAM governance

- Conditional Access

- PIM

- Lifecycle automation



## Network Control Plane

- Cisco Catalyst SD-WAN

- Cloud OnRamp for M365

- INR integration

- Zero Trust segmentation



## Addressing Control Plane

- InfoBlox IPAM

- DNS/DHCP modernization

- Cloud IPAM reconciliation



## Telemetry and Location Control Plane

- M365 Network Telemetry

- SD-WAN telemetry (IPFIX/SNMP/syslog)

- Endpoint telemetry (Defender/Intune)

- DNS telemetry (InfoBlox)

- CDM/CLAW reporting

- SIEM ingestion



## Security and Compliance Plane

- TIC 3.0 Cloud + Branch

- Zero Trust

- FedRAMP alignment

- NIST 800-63

- ICAM governance



---

# Slide 5 - Seven Core Concepts


### 1. Conversation as atomic unit
Every interaction is a conversation with identity, certificates, addressing, path, QoS, and telemetry bound together


### 2. Identity as root namespace
Every IP, certificate, subnet, policy, and telemetry event is derived from or bound to identity


### 3. Deterministic addressing
Addressing is derived from identity attributes and policy, not ad-hoc assignment


### 4. Certificate-anchored overlay
Certificates and mutual TLS anchor tunnel and service authentication


### 5. Telemetry as control
Telemetry is a control plane input to automated decisions, not passive reporting


### 6. Embedded governance and automation
Governance is executed through orchestrated workflows, not manual tickets


### 7. Public service first
Citizen experience, accessibility, and privacy are top-level design constraints


---

# Slide 6 - Frozen State Analysis

| Domain | Current State | Gap |
|--------|--------------|-----|

| identity | On-prem Active Directory, siloed per division | No unified identity graph |

| addressing | Static IP managed in spreadsheets | No identity-to-address binding |

| network-security | Perimeter firewalls (L3/L4) | No identity-aware segmentation |

| endpoint | Mixed tooling | No unified posture signal |

| app-delivery | Monolithic apps, local auth per app | No workload identity |

| telemetry | SIEM collects logs but no correlation | No conversation-level correlation |

| governance | Change management by email and tickets | No automated policy enforcement |

| data-protection | Manual classification, noisy DLP | No data-aware routing |


---

# Slide 7 - Program Outcomes

- Reduced latency and improved M365 performance

- Stronger identity governance and compliance

- Accurate addressing and location inference

- Real-time telemetry for routing and security

- TIC 3.0 compliance across cloud and branch

- A unified, future-proof modernization foundation


---

*Generated from UIAO data layer - March 2026*