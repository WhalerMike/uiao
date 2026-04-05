---
title: "UIAO Modernization Timeline"
version: "1.0"
classification: "CUI/FOUO"
---

# UIAO Modernization Timeline

**Version 1.0**

---

## 1. Modernization Drivers

The agency’s current environment is constrained by legacy TIC 2.0 routing patterns that force traffic through centralized bottlenecks, degrading performance and limiting cloud adoption. Identity remains anchored in on-premises Active Directory, creating governance gaps and inconsistent enforcement across divisions. Addressing is fragmented across spreadsheets and disconnected IPAM tools, making it difficult to correlate identity, device, and network activity. Telemetry is incomplete and siloed, preventing conversation-level visibility and limiting the agency’s ability to support INR, E911, or Zero Trust enforcement.
These limitations have direct mission impact. M365 performance is degraded by unnecessary hairpinning. Cyber risk increases when identity governance is inconsistent and telemetry is incomplete. Compliance gaps emerge when the agency cannot meet TIC 3.0, FedRAMP 20x Phase 2, or SCuBA expectations. Operational inefficiencies multiply when governance depends on manual tickets instead of automated workflows. Modernization is required to support mission readiness, cyber resilience, and citizen-facing services.


---

## 2. Architectural Foundations

The Unified Identity-Addressing-Overlay Architecture (UIAO) is a modernization initiative designed to unify identity, addressing, routing, telemetry, and governance into a coherent, Zero Trust-aligned federal architecture. It integrates Microsoft Entra ID as the identity control plane, ICAM as the governance backbone, InfoBlox as the authoritative IPAM, Cisco SD-WAN as the routing control plane, and cloud-native telemetry and location services as the truth source for operational decisions. Together, these components form a coordinated modernization effort that replaces fragmented legacy systems with a cloud-optimized, identity-driven, telemetry-informed enterprise.
The strategic goal is to transform the agency into a modern federal network where identity is the perimeter, telemetry is the truth, routing is cloud-first, and governance is automated. UIAO provides the architectural foundation needed to meet Zero Trust expectations, TIC 3.0 requirements, and FedRAMP-aligned controls while improving mission performance and citizen experience.


The following diagram illustrates the legacy-to-modernized state transformation that the UIAO program delivers across all four control planes.

<img src="assets/images/mermaid/diagram_1.png" alt="diagram_1" />

---

## 3. Control Plane Sequencing

The modernization program is sequenced across control planes, with each phase building on the foundations established in prior phases. The following sections detail each phase and its deliverables.


### Phase 1 — Identity Control Plane

The Identity Control Plane is anchored in Entra ID and reinforced by ICAM governance, Conditional Access, Privileged Identity Management, and lifecycle automation. Identity becomes the authoritative source for access, addressing, certificates, and policy.



### Phase 2 — Network Control Plane

The Network Control Plane uses Cisco SD-WAN to deliver cloud-first routing, performance-optimized paths for M365, and identity-aware segmentation. Integration with INR enables location-aware routing and emergency services readiness.



### Phase 3 — Addressing Control Plane

The Addressing Control Plane modernizes IPAM through InfoBlox, replacing spreadsheets with authoritative, identity-derived addressing. DNS and DHCP are unified across cloud and on-prem environments, enabling consistent policy enforcement and accurate telemetry correlation.



### Phase 4 — Telemetry & Location Control Plane

The Telemetry and Location Control Plane consolidates signals from M365, SD-WAN, endpoints, DNS, CDM/CLAW, and SIEM platforms. Telemetry becomes a real-time control input for routing, security, and compliance, enabling conversation-level visibility across the enterprise.



### Phase 5 — Security & Compliance Plane

The Security and Compliance Plane aligns the architecture with TIC 3.0, Zero Trust, FedRAMP 20x Phase 2, NIST 800-63, and ICAM governance. Security becomes embedded in the architecture rather than bolted on, with automated enforcement replacing manual review.




---

## 4. Implementation Roadmap

The following diagram provides a phased view of the implementation roadmap, showing how foundations, plane integration, and overlay scaling progress across the program timeline.

<img src="assets/images/mermaid/diagram_2.png" alt="diagram_2" />

---

## 5. Timeline Summary (18-Month Program)

| Phase | Workstream | Milestone | Duration | Dependencies |
| :--- | :--- | :--- | :--- | :--- |


---

## 6. Workstream Summary



---

## 7. Expected Outcomes

UIAO delivers measurable improvements across performance, security, compliance, and mission readiness. Cloud-first routing and identity- driven segmentation reduce latency and improve M365 performance. Stronger identity governance and deterministic addressing enhance Zero Trust enforcement. Unified telemetry enables accurate location inference, conversation-level visibility, and real-time decision-making. The architecture aligns the agency with TIC 3.0, FedRAMP 20x Phase 2, and NIST 800-63 requirements, reducing compliance risk. Most importantly, the modernization improves citizen experience by delivering faster, more reliable, and more secure services.

  management_and_governance:
narrative: >
  The Management and Governance layer provides the operational
  orchestration that binds the five control planes into a continuously
  governed, auditable system. This layer is distinct from the
  Transport and Security tools (Cisco, Palo Alto) that move and
  protect traffic; instead, it focuses on ensuring that the
  architectural fabric remains compliant, healthy, and aligned with
  federal mandates over time.
servicenow:
  role: "System of Record for Overlay Drift"
  narrative: >
    ServiceNow serves as the authoritative system of record for
    detecting and remediating Overlay Drift within the UIAO
    architecture. When the Telemetry Control Plane detects
    configuration deviations in the SD-WAN overlay—such as
    unauthorized tunnel endpoints, expired certificates, or policy
    mismatches against the approved baseline in program.yml—
    ServiceNow automatically generates a Change Request linked to
    the affected Configuration Item in the CMDB. The automated
    remediation workflow re-validates the overlay configuration,
    enforces corrective action, and closes the governance loop by
    updating the Telemetry Plane with the resolution status. This
    ensures that the Overlay Plane never drifts from its authorized
    state without detection, documentation, and remediation.
  fedramp_class: "Class C (Moderate)"
  nist_controls:
    - "IR-4: Incident Handling (Rev 5)"
    - "CA-7: Continuous Monitoring (Rev 5)"
intune:
  role: "Identity Plane Device Trust Gatekeeper"
  narrative: >
    Microsoft Intune ensures that the Identity Control Plane only
    allows healthy, certified devices into the architectural fabric.
    Before any endpoint is granted access through the Overlay Plane,
    Intune validates its compliance posture: OS patch level, disk
    encryption status, EDR agent health, and certificate validity.
    This compliance signal is consumed by Entra ID Conditional
    Access, which enforces a device-trust gate at authentication
    time. Non-compliant devices are quarantined to a restricted VLAN
    segment managed by Cisco ISE, preventing lateral movement within
    the fabric. Device trust is not a one-time check but a
    persistent, real-time control input to the Identity Plane,
    ensuring continuous compliance with NIST 800-53 Rev 5 AC-19
    and CM-8 requirements.
  fedramp_class: "Class C (Moderate)"
  nist_controls:
    - "AC-19: Access Control for Mobile Devices (Rev 5)"
    - "CM-8: System Component Inventory (Rev 5)"

      identity_lifecycle_scenarios:
mover_scenario:
  persona: "Sarah Miller, Senior Analyst"
  event: "Internal Transfer from Field Operations (Dept 400) to Cyber Policy (Dept 800)"
  narrative: >
    The Mover scenario demonstrates Zero-Touch internal transfers.
    When the HRIS updates Sarah's department ID, the Entra ID
    Provisioning Service detects the attribute change within one hour.
    The ABAC engine evaluates her identity against dynamic groups.
    She is automatically removed from Field Ops Users (department eq 400)
    and added to Cyber Policy Users (department eq 800). Access to
    Field Operations SharePoint is revoked while Cyber Policy Teams
    channel, Agency Policy Repository, and Moderate-Security Azure
    enclave are provisioned instantly. Conditional Access updates to
    require phishing-resistant MFA (PIV Card) for policy-specific
    resources. The Sync Orchestrator updates her ServiceNow CI record
    and notifies the Cyber Policy Lead via MS Teams.
  metrics:
    time_to_productivity: "Reduced from 5-7 days to less than 60 minutes"
    security_risk: "Eliminated access creep from accumulated permissions"
    admin_load: "100% reduction in manual group management for transfers"
leaver_scenario:
  persona: "James Vance, Contractor"
  event: "Immediate Separation (End of Contract / High-Risk Departure)"
  narrative: >
    The Leaver scenario demonstrates the automated kill switch.
    When HR finalizes the separation, the HRIS pushes a status update
    setting Employee Status to Terminated with immediate effect.
    Entra ID disables the account within seconds, blocking all new
    sign-in sessions across M365, Azure, ServiceNow, and federated
    apps. Continuous Access Evaluation (CAE) issues a revocation
    signal to all supporting apps, terminating active sessions
    instantly without waiting for token expiry. The Sync Orchestrator
    moves all assigned assets (laptop, PIV card, mobile) to
    In Stock Pending Recovery status in ServiceNow and generates
    a high-priority recovery ticket for Physical Security. Sentinel
    logs the disablement and monitors for failed login attempts.
    A final Atlas Report is sent to the Department Lead and Security
    via MS Teams.
  metrics:
    revocation_latency: "Reduced from hours/days to less than 120 seconds"
    audit_compliance: "100% automated logging for FISMA and GCC-Moderate separation"
    asset_accountability: "Zero-latency flagging of agency hardware for recovery"


---

## 8. Mission-to-Technology Mapping

The following diagram maps the technical control planes to the strategic outcomes they enable, demonstrating how each investment drives measurable mission value.

<img src="assets/images/mermaid/diagram_3.png" alt="diagram_3" />

---

## 9. Regional Scaling Model

The UIAO architecture scales from small branch offices to large data centers using the same canonical patterns. The following diagram illustrates the scaling model.

<img src="assets/images/mermaid/diagram_4.png" alt="diagram_4" />

---

*Generated from UIAO data layer — Modernization Timeline v1.0*