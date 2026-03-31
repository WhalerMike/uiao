# TIC 3.0 Transition and F5 Proxy Retirement Roadmap

**Source:** Copilot thread "Phasing Out F5 Proxies in a TIC 3.0 World"
**Phase:** Phase 4 — Network Modernization
**Status:** Canonical Reference

---

## Executive Summary

Outbound F5 proxies are a TIC 2.0 artifact incompatible with M365, multi-cloud, and UIAO architecture. TIC 3.0 Cloud Use Case eliminates the need for centralized egress chokepoints, replacing them with identity-first, telemetry-driven, direct-to-cloud access patterns.

## Why Outbound F5 Proxies Must Be Retired

### Architectural Incompatibility

| Legacy Pattern (TIC 2.0) | Modern Pattern (UIAO/TIC 3.0) |
|---|---|
| Centralized egress chokepoints | Direct-to-service access |
| TLS interception | End-to-end TLS, cert pinning, ECH |
| Perimeter-based trust | Identity-first trust |
| Static routing | Dynamic, cloud-aware pathing |
| Boundary control | Continuous trust evaluation |
| Inspection at choke | Attestation and telemetry |

### M365 Services Broken by Outbound Proxies

- Teams media pathing
- Informed Network Routing (INR)
- E911 location services
- Telemetry collection
- Conditional Access signals
- Copilot performance
- SharePoint/Exchange latency
- TLS service classification

## UIAO-Aligned Replacement Stack

| Component | Purpose |
|---|---|
| SD-WAN with local DIA breakout | M365 traffic breaks out locally, uninspected |
| Entra ID + Conditional Access | Identity-first policy enforcement |
| Defender for Endpoint/Cloud Apps | Cloud-native security controls |
| SASE/ZTNA (Zscaler, Netskope, Prisma) | Non-M365 traffic security |
| DNS-layer security (Infoblox, BlueCat) | DNS resolution and threat protection |
| No TLS interception for M365 | Non-negotiable requirement |

## Where F5 Remains Valid

| Valid Role | Invalid Role |
|---|---|
| Inbound application delivery (BIG-IP, NGINX) | Outbound proxy |
| API gateways | TLS interception for SaaS |
| WAF for custom apps | M365 traffic inspection |
| Internal load balancing (transitional) | Centralized egress chokepoint |
| Distributed Cloud (XC) for edge | — |

## Internal Load Balancing Transition

F5 remains needed for internal LB only for legacy workloads that cannot yet be containerized or moved to cloud-native LB. This role is **transitional, not strategic**.

### Retirement Phases

| Phase | F5 Role | Cloud-Native Equivalent |
|---|---|---|
| Phase 1 — Today | Internal LB for legacy workloads | — |
| Phase 2 — Transition | Apps move to Azure App Service, AWS ECS/EKS, K8s | Azure Front Door, App Gateway, AWS ALB/NLB |
| Phase 3 — UIAO Steady State | Minimal: handful of legacy systems only | Cloud-native LB dominates |

## Workforce Modernization Blueprint

### Core Identity Shift

**From:** "We manage the F5s."
**To:** "We engineer the agency's application delivery and access fabric."

### Skills Translation Map

| Legacy Skill | Future Value |
|---|---|
| VIPs, pools, health checks | Cloud LB (ALB/NLB, App Gateway, Front Door) |
| TLS termination, cert chains | Zero Trust, identity-bound TLS, service mesh mTLS |
| iRules, traffic steering | API gateways, routing policies, mesh traffic shaping |
| Troubleshooting flows | Multi-cloud observability, distributed tracing |
| Understanding app quirks | App modernization mapping and dependency analysis |
| High-stakes outage response | Cloud incident response and SRE patterns |

### Four Future Roles for F5 Engineers

1. **Cloud Load Balancing Engineer** — Azure Front Door, App Gateway, AWS ALB/NLB
2. **API Gateway & Service Mesh Engineer** — APIM, Kong, Istio, Linkerd, Envoy
3. **Zero Trust Access & Traffic Policy Engineer** — Conditional Access, SASE/ZTNA
4. **Application Modernization Flow Architect** — Dependency mapping, cutover design

### 90-Day Transition Playbook

| Phase | Weeks | Activities |
|---|---|---|
| Reframe | 1-2 | Communicate new mission; show skills mapping; remove fear |
| Upskill | 3-8 | Azure Front Door, AWS ALB, APIM, Istio/Envoy, Conditional Access, SD-WAN, cloud networking |
| Shadow & Swap | 9-12 | Own cloud LB configs, write API gateway policies, replace F5 VIPs with cloud-native equivalents |

## Governance Replacement Pattern

Outbound proxies provided an **illusion of control**. UIAO replaces this with:

| Old Model | New Model |
|---|---|
| Boundary control | Identity control |
| Chokepoints | Telemetry |
| Inspection | Attestation |
| Perimeter trust | Continuous trust evaluation |
| Centralized enforcement | Federated governance |

## Federal Workforce Modernization Context

GAO and CIO.gov reports consistently identify workforce skills gaps as a primary barrier to modernization across all federal agencies. Modernization documents should explicitly recommend repurposing personnel from obsolete technologies into cloud, Zero Trust, and application delivery roles.

### Key Federal Findings

- GAO 2025: 11 of most critical systems use outdated languages; 7 have known cybersecurity vulnerabilities
- CIO.gov: Workforce skills are a primary barrier to Zero Trust and cloud adoption
- VA lost 12% of IT workforce in one year; relied on cross-training and upskilling

## Cross-References

- `docs/01_UnifiedArchitecture.md` — UIAO identity-first architecture
- `docs/08_ModernizationTimeline.md` — Phase sequencing
- `docs/03_FedRAMP20x_Crosswalk.md` — TIC 3.0 alignment
- `docs/12_AI_SecurityPrinciples.md` — AI security controls
