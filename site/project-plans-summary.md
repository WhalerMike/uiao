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
