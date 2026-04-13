---
title: "UIAO Modernization Timeline"
version: "1.0"
classification: "CUI/FOUO"
---

# UIAO Modernization Timeline

**Version 1.0**

---

## 1. Modernization Drivers

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

## 2. Architectural Foundations

UIAO consolidates four infrastructure layers that currently operate as separate programs under
separate ownership: identity (Active Directory and Entra ID), addressing (DNS/DHCP/IPAM), network
routing (TIC-compliant SD-WAN), and telemetry (Splunk correlation feeds). Today these layers are
managed by different teams, procured on different cycles, and monitored against different baselines.
When something breaks at the intersection — and it regularly does — the diagnosis takes days because
no single team owns the full picture.

The program is organized around four control planes, each with a defined vendor, a defined OSCAL
component definition, and a defined set of FedRAMP Moderate controls it satisfies. Identity goes to
Entra ID and CyberArk. Network goes to Cisco SD-WAN with TIC 3.0 policy enforcement. Addressing goes
to Infoblox DDI. Telemetry goes to Splunk with Palo Alto Prisma for inline inspection.

Each plane is independently deployable. The agency does not need to cut over everything at once.
Phase 1 can deliver cloud-first routing and Entra ID consolidation without touching IPAM. That matters
because the legacy PKI dependency in the case management platform cannot be resolved until FY27 at
the earliest, and the program is designed to work around it.


The following diagram illustrates the legacy-to-modernized state transformation that the UIAO program delivers across all four control planes.

<img src="assets/images/plantuml/diagram_1.png" alt="diagram_1" />

---

## 3. Control Plane Sequencing

The modernization program is sequenced across control planes, with each phase building on the foundations established in prior phases. The following sections detail each phase and its deliverables.


### Phase 1 — Identity Control Plane

The Identity Control Plane is anchored in Entra ID and reinforced by
ICAM governance, Conditional Access, Privileged Identity Management,
and lifecycle automation. Identity becomes the authoritative source
for access, addressing, certificates, and policy.



### Phase 2 — Network Control Plane

The Network Control Plane uses Cisco SD-WAN to deliver cloud-first
routing, performance-optimized paths for M365, and identity-aware
segmentation. Integration with INR enables location-aware routing and
emergency services readiness.



### Phase 3 — Addressing Control Plane

The Addressing Control Plane modernizes IPAM through InfoBlox,
replacing spreadsheets with authoritative, identity-derived
addressing. DNS and DHCP are unified across cloud and on-prem
environments, enabling consistent policy enforcement and accurate
telemetry correlation.



### Phase 4 — Telemetry & Location Control Plane

The Telemetry and Location Control Plane consolidates signals from
M365, SD-WAN, endpoints, DNS, CDM/CLAW, and SIEM platforms. Telemetry
becomes a real-time control input for routing, security, and
compliance, enabling conversation-level visibility across the
enterprise.



### Phase 5 — Security & Compliance Plane

The Security and Compliance Plane aligns the architecture with TIC
3.0, Zero Trust, FedRAMP 20x Phase 2, NIST 800-63, and ICAM governance.
Security becomes embedded in the architecture rather than bolted on,
with automated enforcement replacing manual review.




---

## 4. Implementation Roadmap

The following diagram provides a phased view of the implementation roadmap, showing how foundations, plane integration, and overlay scaling progress across the program timeline.

<img src="assets/images/plantuml/diagram_2.png" alt="diagram_2" />

---

## 5. Timeline Summary (18-Month Program)

| Phase | Workstream | Milestone | Duration | Dependencies |
| :--- | :--- | :--- | :--- | :--- |


---

## 6. Workstream Summary



---

## 7. Expected Outcomes

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

## 8. Mission-to-Technology Mapping

The following diagram maps the technical control planes to the strategic outcomes they enable, demonstrating how each investment drives measurable mission value.

<img src="assets/images/plantuml/diagram_3.png" alt="diagram_3" />

---

## 9. Regional Scaling Model

The UIAO architecture scales from small branch offices to large data centers using the same canonical patterns. The following diagram illustrates the scaling model.

<img src="assets/images/plantuml/diagram_4.png" alt="diagram_4" />

---

*Generated from UIAO data layer — Modernization Timeline v1.0*