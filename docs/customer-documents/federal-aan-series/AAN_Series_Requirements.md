# Federal Application-Aware Networking (AAN) Series

> Detailed Requirements Document  |  Draft v0.1  |  Date Code: 2026-07-18 10:02 ET

> Related Volumes: Vol 0 (Program & Executive), Vols I–IV (Architecture), Vol V (Training & Certification), Vol VI (Implementation), Vol VII (ServiceNow Automation), Vol VIII (Multi-Cloud DDI), Vol IX (Day-2 Operations)

## 1. Overview & Purpose

This document defines the detailed functional and non-functional requirements for the Federal Application-Aware Networking (AAN) program — the architectural substrate SSA requires to satisfy NIST SP 800-53 Rev 5 controls (FedRAMP Moderate baseline) and FedRAMP 20x Key Security Indicators under the Consolidated Rules (CR26) effective January 1, 2027. The AAN Federal Series documents this program as ten volumes (Vol 0–IX): a program volume, four architecture volumes, a training volume, and four volumes that make the architecture buildable and operable (implementation-as-code, ServiceNow coordination, multi-cloud DDI automation, and Day-2 operations).

The unifying thesis of the series: TIC 3.0, SD-WAN, and IPAM/DDI are not preferred technologies — they are the only closure mechanisms for a specific, enumerable set of NIST SP 800-53 Rev 5 controls and FedRAMP 20x KSIs. Every requirement below traces to that closure arithmetic: 146 distinct controls series-wide and the internal 29-rule KSI decomposition, of which 19 rules bind to evidence slots that exist only because the architecture is built.

**Primary Objectives:**

- Establish authoritative truth planes — IPAM/DDI naming and addressing, HRIT identity and organizational SSOT, and PKI cryptographic identity — on which every downstream control closure and KSI evidence slot depends.
- Modernize transport and identity (MPLS → DIA + SD-WAN under TIC 3.0; Entra ID, ZTNA, and active governance), closing 34 distinct controls across the original six tracks.
- Operationalize security operations — privileged access, vulnerability and patch management, cloud-native posture, data protection, and SIEM/XDR detection — across the AC, RA, MP, SC, AU, SI, IR, and CP families.
- Generate continuous, machine-readable KSI evidence and OSCAL-compatible artifacts for ConMon and the authorization package (CA-2, CA-5, CA-7).
- Make the architecture buildable and operable: landing-zone and network IaC (Vol VI), ServiceNow coordination of control state into tracked work (Vol VII), governed multi-cloud DDI change (Vol VIII), and a governed Day-2 catalog (Vol IX).
- Teach the corpus and produce the training-slot evidence (KSI-CED) the authorization package depends on (Vol V).

## 2. Scope

**In Scope:**

- FedRAMP Moderate and Microsoft GCC Moderate boundary exclusively; control mappings use the FedRAMP Moderate baseline of NIST SP 800-53 Rev 5.
- The six functional planes: transport; naming & addressing; identity; policy enforcement; application/experience; and evidence & telemetry. Truth is separated from enforcement — naming, identity, and evidence are truth planes; transport and policy enforcement are enforcement planes.
- Volumes I–IV architecture: DDI/IPAM landing zone, NAC (802.1X EAP-TLS), certificates and tokens, HRIT Org SSOT, network/identity/telecom modernization, network enforcement substrate, SQL Server authentication modernization and consolidation, security operations, and governance & assurance.
- Volume V training and certification: compliance track, implementation track, assessment and certification, and vendor training & labs.
- Volume VI implementation-as-code: landing-zone and network IaC, identity-as-code, detection-rule and SOAR-playbook libraries, configuration baselines, the evidence/ConMon pipeline, and validation harnesses.
- Volume VII ServiceNow coordination: CMDB reconciliation to the IPAM/DDI asset identity, M365 and Azure compliance automation, attestation/evidence/KSI workflow, and the scoped compliance application.
- Volume VIII multi-cloud DDI landing-zone automation across Azure, AWS, GCP, OCI, and VMware — the series' one deliberate multi-CSP breadth exception — with ServiceNow as the governed front door for DDI change.
- Volume IX ServiceNow Day-2 operations: helpdesk/ITSM catalog, landing-zone front door, app-registration governance, Teams telephony, and SaaS integration governance.
**Out of Scope (Program Boundaries):**

- FedRAMP High, GCC High, and DoD boundaries — the series never cites, maps to, or claims FedRAMP High; higher-authorized services are referred to only as “FedRAMP-authorized.”
- Multi-CSP breadth beyond the Volume VIII DDI exception (AWS/OCI/VMware coordination is documented as coordination doctrine, not as parallel full-depth stacks).
- Organizational assignment of responsibilities, procurement decisions, and budget authority — the series describes functions, never owners, and is a draft proposal pending CIO Office and OIS review.
- Direct actuation from the coordination plane — ServiceNow coordinates (owner, SLA, approval, evidence); actuation stays platform-native (Microsoft Graph, Azure Policy, Update Manager).

## 3. Functional Requirements

### 3.1 Substrate & Truth Planes (Vol I Books 01–04)

| Req ID | Requirement |
|---|---|
| FR-SUB-001 | Establish an authoritative IPAM/DDI naming-and-addressing plane (DNS, DHCP, IPAM) as the single source of truth for network identity, closing SC-20, SC-20(1), SC-21, SC-22, and keying the CM-8 authoritative component inventory to addresses. |
| FR-SUB-002 | Enforce device identity at the port via 802.1X EAP-TLS network access control (RADIUS), binding devices to addresses for IA-3. |
| FR-SUB-003 | Provide the cryptographic identity layer — certificate issuance and token services (OAuth/OIDC, certificate-based authentication) — that every session-less architecture component depends on. |
| FR-SUB-004 | Integrate the HRIT Identity & Org SSOT as the authoritative source for worker records, organizational structure, and supervisory relationships underpinning every token, account, and access decision. |
| FR-SUB-005 | Keep truth planes separated from enforcement planes: enforcement platforms may be re-platformed or absorbed; truth planes (naming, identity, evidence) may only be depended on, never replaced by downstream copies. |

### 3.2 Transport & Identity Modernization (Vol I Books 05–07, Vol II)

| Req ID | Requirement |
|---|---|
| FR-MOD-001 | Replace MPLS hairpins with DIA + SD-WAN under TIC 3.0: encrypted, application-aware overlay (SC-8, SC-8(1)), traffic-class separation (SC-5), application-layer telemetry on transport (SI-4), and distributed policy enforcement at SASE PEPs (SC-7, SC-7(7), AC-4). Bare DIA satisfies zero controls and must never be deployed without the governing stack. |
| FR-MOD-002 | Modernize identity to Entra ID with ZTNA and active governance (conditional access, least privilege, continuous evaluation) per Vol I Book 05. |
| FR-MOD-003 | Modernize federal telecommunications (SD-WAN, SASE) per Vol I Book 06, retiring the legacy WAN edge; the load-balancer tier dissolves upward into cloud-native delivery services and downward into the DNS control plane. |
| FR-MOD-004 | Close customer-edge SC-7/SC-8/IA-3 via the network enforcement substrate: NIAP / DISA STIG / FIPS 140-3 / DoDIN APL accreditation gate for Cisco, Palo Alto, and Juniper gear (Vol I Book 07). |
| FR-MOD-005 | Modernize SQL Server authentication (Entra-integrated, no legacy SQL auth) and consolidate databases respecting network physics (Vol II Books 01–03). |

### 3.3 Security Operations & Data Protection (Vol III)

| Req ID | Requirement |
|---|---|
| FR-SEC-001 | Operate privileged access management with multi-CSP coordination (Vol III Book 01). |
| FR-SEC-002 | Run continuous vulnerability management and patch/systems management across the Azure/Intune stack, with AWS, OCI, VMware, and Red Hat native stacks coordinating rather than living under one Microsoft plane (Vol III Books 02–03, RA-5, SI-2). |
| FR-SEC-003 | Maintain cloud-native security posture and container security (Vol III Book 04). |
| FR-SEC-004 | Protect data with Purview-based classification and protection (Vol III Book 05). |
| FR-SEC-005 | Detect and respond via SIEM/XDR with detection rules as code (Vol III Book 06), feeding the evidence & telemetry plane. |
| FR-SEC-006 | Aggregate multi-cloud evidence into a single evidence fabric (Vol III Book 07). |

### 3.4 Governance, Assurance & Training (Vols IV–V)

| Req ID | Requirement |
|---|---|
| FR-GOV-001 | Maintain business continuity, supply-chain risk management, program governance, PII processing transparency, and cybersecurity training & awareness books (Vol IV Books 01–05). |
| FR-GOV-002 | Assemble and maintain the authorization package and ConMon posture (Vol IV Book 06; CA-2, CA-5, CA-7). |
| FR-GOV-003 | Deliver the Volume V training academy (compliance track, implementation track, assessment & certification, vendor training & labs) and produce KSI-CED training-slot evidence. |

### 3.5 Implementation, Coordination & Day-2 Operations (Vols VI–IX)

| Req ID | Requirement |
|---|---|
| FR-OPS-001 | For every control an architecture book closes, provide the matching deployable artifact as code (Vol VI): landing-zone/network IaC, identity-as-code, detection and SOAR libraries, configuration baselines, evidence/ConMon pipeline, and validation harnesses. |
| FR-OPS-002 | Coordinate M365 and Azure control state into tracked ServiceNow work — drift to an owner, change gated (CM-3), posture rolled up to ConMon (CA-7) — with the CMDB reconciling to the authoritative IPAM/DDI asset identity (CM-8 join key), never replacing it (Vol VII). |
| FR-OPS-003 | Ship the ServiceNow compliance application as a scoped app: connectors, Flows, machine-readable control map projected from the compliance spine, ATF test coverage, and update-set packaging (Vol VII Book 05). |
| FR-OPS-004 | Automate multi-cloud DDI landing-zone provisioning (Azure, AWS, GCP, OCI, VMware) with ServiceNow as the governed front door for DDI change, adding separation of duties over DDI change (CM-5) — the series' single genuinely-new control number (Vol VIII). |
| FR-OPS-005 | Govern routine Entra/M365/Azure day-2 work through catalog items: helpdesk/ITSM, landing-zone front door, app-registration governance, Teams telephony, and SaaS integration governance with FedRAMP Marketplace verification before configuration (SA-9) (Vol IX). |

### 3.6 Evidence Generation & KSI Support

The series must produce continuous, machine-readable evidence for the 29-rule KSI decomposition and the series control crosswalk. Evidence must be exportable in OSCAL-compatible format.

FR-EVD-001: Fill all 29 KSI rule evidence slots — the 10 conformance-tool-attestable rules (SCuBA-based, KSI-001..010) and the 19 rules whose evidence slots exist only because the architecture is built (identity, network, telemetry, endpoint, security, continuity, and training slots).

FR-EVD-002: Maintain the compliance spine (aan-compliance-spine.yml) as the machine-readable SSOT for volumes, books, and control closures; every book's “Authorities Closed Here” table is generated from it and CI-checked against it (regen-and-diff discipline).

FR-EVD-003: Track the series control crosswalk — 146 distinct controls — in Vol 0's appendix, reconciling every volume's contribution.

FR-EVD-004: Export evidence packages via the `<engine> oscal bundle` export or native OSCAL JSON/XML emitter for authorization packages and ConMon.

FR-EVD-005: Stamp every deliverable with a Date Code accurate to the minute (YYYY-MM-DD HH:MM ET); newest code wins, and source and derived artifacts must never carry the same code with different content.

## 4. Integration Requirements

| System / Component | Data / Capability | Direction |
|---|---|---|
| InfoBlox BloxOne DDI Federal (FedRAMP Moderate) | Authoritative DNS/DHCP/IPAM — naming & addressing truth plane; CM-8 join key | Source of truth (all planes reconcile to it) |
| Microsoft Entra ID (Graph API, GCC Moderate) | Users, groups, conditional access, sign-in and audit logs | Read + scoped, logged, approved write |
| OPM HRIT Identity & Org SSOT | Worker records, organizational structure, supervisory relationships, position data | Read (primary source of truth) |
| ServiceNow Government Cloud (FedRAMP-authorized) | Workflow, CMDB (reconciled to IPAM/DDI), change gating, attestation, evidence coordination | Bidirectional (coordination only; no actuation) |
| Azure (GCC Moderate boundary) | Landing zones, Azure Policy, Defender, Update Manager state | Read + platform-native actuation |
| SIEM/XDR (Sentinel) | Detections, telemetry, evidence & telemetry plane | Read + alert-driven workflow |
| SD-WAN / SASE stack | Encrypted overlay, TIC 3.0 PEP policy, transport telemetry | Managed via enforcement plane |
| `<engine> oscal bundle` / OSCAL emitter | Evidence packaging for authorization packages and ConMon | Export |

## 5. Non-Functional Requirements

Security & Compliance: FedRAMP Moderate and Microsoft GCC Moderate exclusively. Never cite, map to, or claim FedRAMP High; where an underlying service holds a higher authorization, refer to it only as “FedRAMP-authorized.” Vendor authorization claims state the CSO's actual level and are verified against the FedRAMP Marketplace at procurement time. In-boundary by construction: MID Servers inside the ATO boundary; least-privilege connector identities — read plus scoped/logged/approved write, never standing admin.

Evidence Integrity: evidence records immutable once generated; machine-readable first (OSCAL/KSI JSON), human-readable as a projection.

Maintainability: everything as code, checked against the SSOT — the compliance spine is the machine-readable registry; generated tables must match their partials byte-for-byte (drift gate green). ServiceNow apps carry ATF coverage; derivative artifacts (docx, pptx, html) are rebuilt from qmd sources, never hand-edited.

Scalability: designed for SSA-scale — tens of thousands of users, enterprise-wide network and identity population.

Usability: books are function-framed (no organizational owners) so any reader maps their own org chart onto the six-plane model; executives start at Vol 0 Book 00a (two-page brief); every PPTX slide carries full speaker notes sufficient for a presenter who did not build the deck.

Timeline: the FedRAMP 20x mandatory date of January 1, 2027 is a regulatory requirement, not an internal target; sequencing must close the architectural gap inside that window.

## 6. User Roles & Personas

CSI Team (Cloud Services Infrastructure): authors and maintains the series, the compliance spine, and the implementation artifacts; proposes the roadmap.

Office of Information Security (OIS): reviews security architecture, policy framework, and control ownership; holds assessment methodology and risk acceptance authority.

CIO Office / Enterprise Architecture: strategic direction, architecture alignment, and prioritization; approves the roadmap before commitments are made.

Network / Platform Engineers: consume Vols I–III and VI to deploy the substrate, modernization tracks, and IaC artifacts.

ServiceNow Administrators & Process Owners: operate the Vol VII/IX coordination and Day-2 catalogs, CMDB reconciliation, and attestation workflow.

Security / Compliance Analysts: monitor posture, run ConMon, review KSI evidence and the control crosswalk.

Auditors / Assessors: consume immutable evidence, OSCAL packages, and audit logs during assessment (read-only).

Learners / Trainers (Vol V): complete the compliance and implementation tracks; completions feed KSI-CED training evidence.

## 7. Success Metrics & KPIs

- Control closure: all 146 distinct crosswalk controls trace to a closing book and, where applicable, a deployed Vol VI artifact.
- KSI coverage: all 29 KSI rules producing automated, machine-readable evidence — including the 19 architecture-bound slots conformance tooling cannot fill.
- Drift gate: compliance-spine → authorities-table regeneration green in CI on every change (zero byte-level drift).
- CR26 readiness: authorization-package inputs (OSCAL, KSI evidence, attestations) producible on demand ahead of January 1, 2027.
- Coordination coverage: % of M365/Azure control drift routed to a tracked, owned ServiceNow task within SLA; % of DDI and day-2 changes flowing through governed catalog items rather than portal clicks.
- CMDB accuracy: reconciliation match rate between CMDB and the authoritative IPAM/DDI asset identity (a drifting CMDB is a reconciliation defect).
- Training: Vol V track completion rates feeding KSI-CED evidence.
- Reduction in manual ConMon evidence effort for in-scope processes.

## 8. Dependencies & Assumptions

- Microsoft GCC Moderate tenant and Moderate-targeted Azure boundary are available; Graph and ARM resolve to the commercial endpoints that serve GCC Moderate.
- InfoBlox BloxOne DDI Federal (or equivalent FedRAMP Moderate DDI) is procured and deployed as the naming/addressing truth plane.
- ServiceNow Government Cloud instance is available and appropriately licensed, with MID Server placement inside the ATO boundary.
- OPM HRIT provides reliable identity and organizational data (Vol I Book 04 path).
- host-repo tooling (compliance spine checks, OSCAL bundle, derivative builders) is available and maintained.
- Formal review by the CIO Office, OIS, organizational leaders, and program offices proceeds; this series and its requirements will be revised by that process.
- Vendor FedRAMP authorization claims are re-verified against the FedRAMP Marketplace at procurement time.

## 9. Out of Scope & Future Considerations

Explicit follow-ups, deliberately out of scope now:

- Other CSPs (AWS, OCI, VMware) at full coordination depth and higher boundaries (GCC High, DoD) — the coordination loop is built so they reconcile into the same ServiceNow queues later without reworking the M365/Azure core.
- Full Privileged Access Management / just-in-time provisioning kits beyond the Vol III Book 01 doctrine (candidate separate kit, per the Identity & Access Governance Kit requirements).
- AI-assisted access recommendations, anomaly detection, and risk-scoring analytics.
- Automated remediation playbooks with human-in-the-loop approval (initially evidence + alerting only, per the coordination-not-actuation doctrine).
- Organizational assignment, budgeting, and procurement execution — established through the formal alignment process, not by this document.
---

This is a draft requirements document aligned with the AAN Federal Series (July 2026), developed by the CSI Team as a draft proposal. It has not been reviewed or approved by the SSA CIO Office, OIS, or organizational leadership; all recommendations are subject to revision pending formal review. It is intended for review by CSI, OIS, and ServiceNow stakeholders, and will be refined through workshops and alignment with the CR26 Indicator Mapping effort.
