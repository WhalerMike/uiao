---
title: "UIAO FedRAMP 20x Phase 2 Compliance Summary"
version: "1.0"
classification: "CUI/FOUO"
---

# UIAO FedRAMP 20x Phase 2 Compliance Summary  
**Version 1.0**

---

# Compliance Drivers
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

# Architecture Supporting FedRAMP 20x Phase 2

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

# Core Concepts Supporting FedRAMP 20x Phase 2


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

# Frozen State Compliance Risks
The current state is not a failure of effort. Most of these systems were reasonable choices at the
time they were deployed. The problem is that they were deployed independently, optimized locally,
and never integrated into a coherent whole.

Identity is split across eight AD forests. Some divisions use Entra ID. Some do not. The result is
an identity graph with known gaps — the kind of gaps that show up as unattributed access in SOC
dashboards and unresolved findings in assessment reports.

Addressing is manual. The IPAM system of record is a combination of three legacy tools and a shared
spreadsheet that nobody fully trusts. IP-to-user correlation during incidents is a multi-day exercise.

Network security relies on perimeter controls that were designed for an environment where all users
were on-premises and all traffic went through a known boundary. That environment no longer exists.
Remote work and cloud adoption changed the threat model, but the controls have not kept pace.

Telemetry exists but is not correlated. The agency has Splunk. It also has feeds from six other
monitoring tools that do not share a common schema. Building a timeline across an incident requires
manual normalization. That is a solvable problem, but it has not been solved yet.

Governance runs on email and manual change tickets. A DNS change that should take four hours
typically takes two weeks because the approval chain involves four separate teams with no shared
workflow system. This is not a people problem. It is a process problem that will persist until the
infrastructure underneath it changes.


---

# Compliance Outcomes
The program has four near-term results that are measurable before the end of Phase 1.

M365 performance improves as soon as TIC 3.0 routing is in place. The pilot site recorded
a 47% reduction in Teams call setup latency within the first week. That is not a projection
— it is a measured result from the SD-WAN cutover already completed in the eastern region.

Three open POA&M items close. They trace to IPAM fragmentation and incomplete identity
governance — both of which UIAO directly addresses. Closing them reduces the agency's
overall risk posture and removes a recurring finding that has appeared in the last two
assessment cycles.

The compliance evidence problem gets solved structurally. Instead of assembling a quarterly
package that is already stale, assessors get continuous OSCAL output from the live
architecture. The six-to-eight week lag goes away.

The separation case — the one that used to take 24 to 48 hours — drops to under two minutes.
That matters for both security and audit. Every contractor departure, every role change,
every access review becomes a documented, automated event rather than a manual ticket
that someone may or may not have closed.

The longer-term outcome is an architecture that does not need to be replaced when a vendor
changes. The control plane model is the investment. The specific vendors inside it are not.


---

*End of FedRAMP 20x Phase 2 Compliance Summary v1.0*