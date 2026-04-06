---
title: "UIAO Zero Trust Narrative"
version: "1.0"
classification: "CUI/FOUO"
---

# UIAO Zero Trust Narrative  
**Version 1.0**

---

# Zero Trust Imperative
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

# Identity as the Perimeter
The Identity Control Plane is anchored in Entra ID and reinforced by
ICAM governance, Conditional Access, Privileged Identity Management,
and lifecycle automation. Identity becomes the authoritative source
for access, addressing, certificates, and policy.


---

# Telemetry as Truth
The Telemetry and Location Control Plane consolidates signals from
M365, SD-WAN, endpoints, DNS, CDM/CLAW, and SIEM platforms. Telemetry
becomes a real-time control input for routing, security, and
compliance, enabling conversation-level visibility across the
enterprise.


---

# Governance as Automation
Telemetry becomes an active control input for routing, security, and
compliance decisions rather than a passive reporting mechanism.


---

# Zero Trust Outcomes
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

*End of Zero Trust Narrative v1.0*