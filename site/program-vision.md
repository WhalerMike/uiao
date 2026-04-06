---
title: "UIAO Program Vision"
version: "1.0"
classification: "CUI/FOUO"
---

# UIAO Program Vision  
**Version 1.0**

---

# Vision Statement
The end state is not complicated to describe. The hard part is getting there without breaking
operations along the way.

In the target architecture, a user's Entra ID identity is the root of every access decision. When
they connect — from any location, on any device — Conditional Access evaluates their posture, their
role, and their network path before the session is established. There is no separate VPN decision,
no separate IPAM lookup, no separate compliance check. Those happen in the background, continuously,
against live telemetry rather than a quarterly snapshot.

Network routing follows TIC 3.0 policy natively through Cisco SD-WAN. M365 traffic no longer
backhauls through legacy concentrators. The latency savings are measurable and immediate — the pilot
site showed a 47% reduction in average Teams call setup time in the first week.

DNS is authoritative. Every device that gets an address gets it from Infoblox with a corresponding
identity binding. That binding flows into Splunk. When the SOC needs to attribute a connection, the
answer is available in under a minute, not five days.

Compliance evidence is generated continuously from the same control plane telemetry. The OSCAL
artifacts produced by this pipeline are not a separate documentation effort — they are a live output
of the architecture. Assessors can pull current evidence on demand rather than waiting for a
quarterly package.

The architecture is designed to survive vendor changes. If a better identity provider emerges, or
if a contract changes, the control plane model allows substitution without rearchitecting the rest
of the program. That is the structural value of UIAO — not any single vendor, but the framework
that makes vendors interchangeable.


---

# The Five Control Planes (Vision View)

### 1. Identity Control Plane
The Identity Control Plane is anchored in Entra ID and reinforced by
ICAM governance, Conditional Access, Privileged Identity Management,
and lifecycle automation. Identity becomes the authoritative source
for access, addressing, certificates, and policy.



### 2. Network Control Plane
The Network Control Plane uses Cisco SD-WAN to deliver cloud-first
routing, performance-optimized paths for M365, and identity-aware
segmentation. Integration with INR enables location-aware routing and
emergency services readiness.



### 3. Addressing Control Plane
The Addressing Control Plane modernizes IPAM through InfoBlox,
replacing spreadsheets with authoritative, identity-derived
addressing. DNS and DHCP are unified across cloud and on-prem
environments, enabling consistent policy enforcement and accurate
telemetry correlation.



### 4. Telemetry & Location Control Plane
The Telemetry and Location Control Plane consolidates signals from
M365, SD-WAN, endpoints, DNS, CDM/CLAW, and SIEM platforms. Telemetry
becomes a real-time control input for routing, security, and
compliance, enabling conversation-level visibility across the
enterprise.



### 5. Security & Compliance Plane
The Security and Compliance Plane aligns the architecture with TIC
3.0, Zero Trust, FedRAMP 20x Phase 2, NIST 800-63, and ICAM governance.
Security becomes embedded in the architecture rather than bolted on,
with automated enforcement replacing manual review.




---

# The Eight Core Concepts (Vision View)


### 1. Single Source of Truth (SSOT)
The canonical data repository is the authoritative origin for all
architectural definitions. Every document, template, and generated
artifact derives its definitions from this single source of truth,
ensuring consistency and preventing drift across the architecture.



### 2. Conversation as the Atomic Unit
Every interaction—identity, certificate, addressing, path, QoS, and
telemetry—is treated as a single, correlated conversation rather than
isolated events.



### 3. Identity as the Root Namespace
Identity becomes the root namespace for all resources, ensuring that
every IP address, certificate, subnet, policy, and telemetry event is
derived from or bound to identity.



### 4. Deterministic Addressing
Addressing becomes deterministic and policy-driven, replacing ad-hoc
assignment with identity-derived logic that enables accurate
correlation and automated governance.



### 5. Certificate-Anchored Overlay
Certificates and mutual TLS anchor tunnels, services, and trust
relationships across the enterprise.



### 6. Telemetry as Control
Telemetry becomes an active control input for routing, security, and
compliance decisions rather than a passive reporting mechanism.



### 7. Embedded Governance & Automation
Governance is executed through orchestrated workflows that enforce
policy consistently and reduce operational burden.



### 8. Public Service First
Citizen experience, accessibility, and privacy remain top-level
design constraints.




---

# Why This Vision Matters
The current environment has three problems that are getting worse, not better.

First, identity. The agency runs Active Directory across eight separately managed forests, several of
which have no documented owner since the last reorganization. Conditional Access policies exist on paper
but are inconsistently enforced — the Security Operations Center identified 14 accounts with Tier 0
access that had not been reviewed in over 18 months. Entra ID is in use but has not been fully
synchronized, which means the identity graph is incomplete and cannot be relied upon for Zero Trust
enforcement decisions.

Second, addressing. IPAM is managed primarily through spreadsheets maintained by individual network
branches. There is no authoritative source for IP-to-identity correlation. When the SOC needs to
attribute a suspicious IP to a user and device during an incident, that correlation typically takes
three to five business days. That is not a tooling problem — it is a structural one.

Third, compliance posture. The agency's current FedRAMP compliance evidence is collected manually,
assembled quarterly, and reflects a point-in-time snapshot that is usually six to eight weeks stale
by the time an assessor sees it. Three of the agency's current open POA&M items trace directly to
gaps in identity governance and telemetry coverage that UIAO is designed to close.

TIC 3.0 transition requirements and FedRAMP 20x Phase 2 expectations add deadline pressure. Neither
can be met by continuing to optimize the current architecture.


---

*End of Program Vision v1.0*