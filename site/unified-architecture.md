# Unified Identity-Addressing-Overlay Architecture - Unified Architecture

The architecture is composed of five interlocking control planes.

---


## Identity Control Plane

- Entra ID

- ICAM governance

- Conditional Access

- PIM

- Lifecycle automation


---


## Network Control Plane

- Cisco Catalyst SD-WAN

- Cloud OnRamp for M365

- INR integration

- Zero Trust segmentation


---


## Addressing Control Plane

- InfoBlox IPAM

- DNS/DHCP modernization

- Cloud IPAM reconciliation


---


## Telemetry and Location Control Plane

- M365 Network Telemetry

- SD-WAN telemetry (IPFIX/SNMP/syslog)

- Endpoint telemetry (Defender/Intune)

- DNS telemetry (InfoBlox)

- CDM/CLAW reporting

- SIEM ingestion


---


## Security and Compliance Plane

- TIC 3.0 Cloud + Branch

- Zero Trust

- FedRAMP alignment

- NIST 800-63

- ICAM governance


---


## Seven Core Concepts


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

## Architectural Principles

- Zero Trust by default

- Identity as the new perimeter

- Telemetry as the truth source

- Cloud-first routing

- Incremental modernization (no big-bang)

- FedRAMP-aligned controls

- Modular, extensible architecture


---

## Frozen State Analysis

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

*Generated from UIAO data layer - March 2026*