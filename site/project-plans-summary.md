# Unified Identity-Addressing-Overlay Architecture - Project Plans Summary

All modernization workstream project plans generated from canonical data.

---

## Workstream A: Entra ID + ICAM Modernization

**ID:** A1 | **Status:** Ready for PMO intake | **Owner:** Identity Engineering / Security Architecture

### Purpose
Modernize identity, authentication, authorization, and governance

- Microsoft Entra ID as the primary identity provider

- ICAM-aligned governance (NIST 800-63, OMB M-19-17)

- Zero Trust identity enforcement

- Lifecycle automation and privileged access controls


### Scope
#### In Scope

- Entra ID tenant baseline configuration

- Conditional Access baseline policies

- MFA/SSPR modernization

- Identity lifecycle automation

- Privileged Identity Management (PIM)

- Access Reviews and governance workflows

- ICAM alignment and documentation

- Integration with SD-WAN identity-aware routing

- Integration with InfoBlox IPAM for location inference

- Integration with Telemetry for Zero Trust signals


#### Out of Scope

- On-prem AD restructuring (handled separately)

- HR system modernization

- Non-FedRAMP cloud identity providers


### Objectives

- Establish Entra ID as the identity control plane

- Implement ICAM governance and credentialing

- Enforce Zero Trust identity policies across cloud and branch

- Reduce identity risk and eliminate legacy authentication

- Enable identity-driven routing (INR) and telemetry correlation


### Milestones
| Milestone | Description | Target |
|-----------|-------------|--------|

| M1 | Entra ID baseline complete | Month 1 |

| M2 | Conditional Access baseline | Month 2 |

| M3 | MFA/SSPR modernization | Month 3 |

| M4 | PIM + Access Reviews | Month 4 |

| M5 | ICAM governance package | Month 5 |

| M6 | Identity > SD-WAN integration | Month 6 |

| M7 | Identity > Telemetry integration | Month 6 |


### Risks & Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|

| Legacy authentication still in use | High | Enforce phased CA policies |

| Incomplete identity lifecycle data | Medium | Integrate HRIS + automation |

| User disruption during MFA rollout | Medium | Staged rollout + comms plan |

| ICAM documentation gaps | Medium | Early governance workshops |

| SD-WAN not ready for identity signals | Low | Align timelines with Workstream B |


### Acceptance Criteria

- All legacy authentication blocked

- Conditional Access baseline enforced

- MFA/SSPR fully deployed

- PIM operational with approval workflows

- Access Reviews automated

- ICAM documentation approved by governance board

- Identity telemetry integrated with SD-WAN and SIEM

- Identity lifecycle automation operational


---

## Workstream B: Cisco Catalyst SD-WAN Modernization

**ID:** B1 | **Status:** Ready for PMO intake | **Owner:** Network Engineering / Infrastructure Architecture

### Purpose
Modernize transport and routing architecture

- Cisco Catalyst SD-WAN as the network control plane

- Direct Internet Access (DIA) at branches

- Cloud OnRamp for Microsoft 365

- Identity-aware routing (INR readiness)

- Zero Trust segmentation

- Telemetry-driven path selection


### Scope
#### In Scope

- SD-WAN fabric design and deployment

- DIA rollout to branches

- Cloud OnRamp for M365 configuration

- Zero Trust segmentation baseline

- Telemetry export (IPFIX/SNMP/syslog)

- Integration with Entra ID identity signals

- Integration with InfoBlox IPAM for location inference

- Integration with Telemetry pipeline for routing decisions

- INR readiness configuration


#### Out of Scope

- Legacy router refresh (handled separately)

- MPLS contract renegotiation

- Non-Cisco SD-WAN platforms


### Objectives

- Replace TIC 2.0 hairpin routing with DIA

- Improve M365 performance using Cloud OnRamp

- Enable identity-aware routing (INR)

- Establish Zero Trust segmentation across branches

- Integrate SD-WAN telemetry into the unified pipeline

- Support E911 and location inference via IPAM + LLDP/BSSID

- Prepare for TIC 3.0 Cloud + Branch certification


### Milestones
| Milestone | Description | Target |
|-----------|-------------|--------|

| M1 | SD-WAN HLD complete | Month 1 |

| M2 | SD-WAN LLD complete | Month 2 |

| M3 | DIA pilot branches live | Month 3 |

| M4 | Cloud OnRamp for M365 pilot | Month 3 |

| M5 | Segmentation baseline deployed | Month 4 |

| M6 | Telemetry export operational | Month 4 |

| M7 | Identity-aware routing integration | Month 5 |

| M8 | INR readiness complete | Month 6 |


### Risks & Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|

| Branch circuits not DIA-ready | High | Pre-checklist + ISP coordination |

| Cloud OnRamp misconfiguration | Medium | Vendor validation + pilot testing |

| Segmentation too aggressive | Medium | Phased rollout + monitoring |

| Telemetry gaps | Medium | Align with Workstream D |

| Identity signals unavailable | Low | Coordinate with Workstream A |


### Acceptance Criteria

- SD-WAN fabric deployed and validated

- DIA operational at pilot and production branches

- Cloud OnRamp for M365 improving performance

- Segmentation enforced with no critical outages

- Telemetry exported to SIEM and Telemetry pipeline

- Identity signals consumed for routing decisions

- INR readiness validated with Microsoft

- TIC 2.0 hairpin dependency removed for pilot sites


---

## Workstream C: InfoBlox IPAM Modernization

**ID:** C1 | **Status:** Ready for PMO intake | **Owner:** Network Services / Infrastructure Architecture

### Purpose
Modernize addressing, DNS, and DHCP architecture

- InfoBlox as the authoritative IPAM platform

- Unified DNS/DHCP governance

- Cloud IPAM reconciliation (Azure/AWS/GCP)

- IPAM-driven location inference for E911 and INR

- Integration with SD-WAN and Telemetry pipelines

- Alignment with TIC 3.0 visibility requirements


### Scope
#### In Scope

- InfoBlox IPAM authoritative design

- DNS/DHCP modernization

- Cloud IPAM reconciliation (Azure, AWS, GCP)

- IPAM to SD-WAN integration (location inference)

- IPAM to Telemetry integration (correlation)

- IPAM to CMDB synchronization

- Delegated DNS zones for cloud VNETs/VPCs

- IPAM governance model and lifecycle

- Addressing standards and documentation


#### Out of Scope

- Legacy DNS appliances not part of InfoBlox

- Non-IP-based addressing systems

- IPv6-only deployments (future phase)


### Objectives

- Establish InfoBlox as the authoritative IPAM for all environments

- Modernize DNS/DHCP to support cloud-first routing

- Reconcile cloud-native IPAMs with on-prem IPAM

- Enable accurate location inference for E911 and INR

- Provide addressing telemetry to SD-WAN and SIEM

- Support TIC 3.0 visibility and reporting requirements


### Milestones
| Milestone | Description | Target |
|-----------|-------------|--------|

| M1 | IPAM HLD complete | Month 1 |

| M2 | DNS/DHCP modernization plan | Month 2 |

| M3 | Cloud IPAM reconciliation | Month 3 |

| M4 | IPAM to SD-WAN integration | Month 4 |

| M5 | IPAM to Telemetry integration | Month 4 |

| M6 | IPAM to CMDB sync | Month 5 |

| M7 | Addressing governance approved | Month 5 |

| M8 | IPAM lifecycle automation | Month 6 |


### Risks & Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|

| Inconsistent IPAM data across environments | High | Reconciliation + authoritative governance |

| DNS misconfiguration during migration | High | Phased rollout + validation |

| Cloud teams bypassing IPAM | Medium | Enforce delegated zones + automation |

| CMDB sync failures | Medium | API-based integration + monitoring |

| Telemetry correlation gaps | Medium | Align with Workstream D |


### Acceptance Criteria

- InfoBlox is the authoritative IPAM across all environments

- DNS/DHCP modernization complete and validated

- Cloud IPAMs reconciled with authoritative IPAM

- IPAM telemetry integrated with SD-WAN and SIEM

- IPAM location inference operational for E911 and INR

- Addressing governance approved and enforced

- CMDB synchronization operational

- Address lifecycle automation deployed


---

## Workstream D: Telemetry, Location Services, and TIC 3.0 Modernization

**ID:** D1 | **Status:** Ready for PMO intake | **Owner:** Security Architecture / Network Architecture / Compliance

### Purpose
Modernize telemetry, monitoring, visibility, and compliance architecture

- Unified telemetry pipeline across cloud, network, identity, and endpoints

- Accurate, authoritative location services for E911 and INR

- TIC 3.0 Cloud + Branch compliance

- Real-time routing and Zero Trust enforcement using telemetry signals

- CDM/CLAW reporting alignment


### Scope
#### In Scope

- Unified telemetry pipeline (M365, SD-WAN, IPAM, endpoint)

- Location services modernization (E911, LLDP, BSSID, IPAM inference)

- TIC 3.0 Cloud Use Case package

- TIC 3.0 Branch Use Case package

- CDM/CLAW integration

- SIEM ingestion and normalization

- SLA monitoring and performance baselines

- Telemetry to SD-WAN routing integration

- Telemetry to Zero Trust enforcement integration


#### Out of Scope

- Replacement of SIEM platform (uses existing)

- Endpoint hardware refresh

- Non-FedRAMP cloud telemetry sources


### Objectives

- Establish a unified, authoritative telemetry pipeline

- Fix Cloud Telemetry + Location block for INR and E911

- Provide TIC 3.0 visibility and reporting

- Enable telemetry-driven routing decisions in SD-WAN

- Support Zero Trust enforcement across identity, network, and endpoints

- Integrate telemetry with CDM/CLAW for federal reporting


### Milestones
| Milestone | Description | Target |
|-----------|-------------|--------|

| M1 | Telemetry HLD complete | Month 1 |

| M2 | Location services modernization plan | Month 2 |

| M3 | E911 dynamic location mapping | Month 3 |

| M4 | IPAM-based location inference | Month 3 |

| M5 | SD-WAN telemetry export operational | Month 4 |

| M6 | M365 Network Telemetry integrated | Month 4 |

| M7 | TIC 3.0 Cloud Use Case package | Month 5 |

| M8 | TIC 3.0 Branch Use Case package | Month 6 |

| M9 | CDM/CLAW integration | Month 6 |


### Risks & Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|

| Telemetry gaps across systems | High | Unified pipeline + validation |

| Incorrect location inference | High | IPAM + LLDP/BSSID correlation |

| TIC 3.0 documentation delays | Medium | Early compliance workshops |

| SIEM ingestion failures | Medium | Normalization + monitoring |

| CDM/CLAW reporting gaps | Medium | API-based integration |


### Acceptance Criteria

- Unified telemetry pipeline operational

- Location services accurate and validated

- E911 dynamic location fully functional

- IPAM-based location inference integrated

- SD-WAN telemetry exported and correlated

- M365 Network Telemetry integrated

- TIC 3.0 Cloud + Branch packages approved

- CDM/CLAW reporting operational

- Telemetry signals consumed by SD-WAN and Zero Trust engines


---
