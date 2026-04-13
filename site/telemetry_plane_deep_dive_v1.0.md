---
title: "UIAO Telemetry Plane Deep Dive"
version: "1.0"
classification: "CUI/FOUO"
---

# Telemetry & Location Control Plane Deep Dive  
**Version 1.0**

---

# Telemetry Plane Overview
The Telemetry and Location Control Plane consolidates signals from
M365, SD-WAN, endpoints, DNS, CDM/CLAW, and SIEM platforms. Telemetry
becomes a real-time control input for routing, security, and
compliance, enabling conversation-level visibility across the
enterprise.


---

# Telemetry as Control
Certificates and mutual TLS anchor tunnels, services, and trust
relationships across the enterprise.


---

# Frozen State Telemetry Gaps
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

# Telemetry‑Driven Outcomes
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

*End of Telemetry Plane Deep Dive v1.0*