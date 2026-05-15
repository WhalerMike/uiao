---
document_id: CHARTER-003
title: "UIAO Charter — V4U Master Reference (Strategic Content + Crosswalks)"
version: "1.0"
status: Current
classification: CANONICAL
owner: Michael Stratton
boundary: GCC-Moderate
created_at: "2026-03-07"
updated_at: "2026-05-15"
tier: foundational
supersedable: false
load_order: 0
charter_chain:
  - "V3 (Feb 26 2026): original whitepaper, superseded by V4U — pending ingestion as CHARTER-V3-LEGACY"
  - "V4U (Mar 7 2026): unified merger of V4G/V4P/V4C audience variants — this document is the master strategic reference, paired with CHARTER-002 (V4U Core Canon Introduction)"
  - "UIAO-V1 (Mar 9 2026): current authoritative charter — CHARTER-001"
provenance:
  source: "OneDrive: Application_Aware_Networking_White_Paper_by_Mike/V4/Backup/V4U_Master_Reference_All_Sections.md (Mar 7 2026 10:58)"
  version: "1.0"
  derived_at: "2026-05-15"
  derived_by: "Charter Restoration Plan PR-A3"
  editorial_pass: "Light — source was already markdown (not pandoc-converted). Body preserved verbatim. The source's `# Generated: March 7, 2026` and `# Contains all 6 section files in document order` comment lines were retained as provenance markers; they document the 6-source-file concatenation that produced this master reference."
companion: "CHARTER-002 (V4U Core Canon Introduction) is the scaffolding/intent document; this is the substantive content. Together they constitute the V4U feeder set per the Charter Restoration Plan. Distinct in scope from CHARTER-001-APPENDICES (AtoBZ master appendix), which carries the appendix-level technical detail (~104 appendices A–CZ); the V4U/AtoBZ scope split is documented in a forthcoming reconciliation ADR after both PR-A2b and PR-A3 land."
content_summary: "Six concatenated source files: (1) Paradigm Shift + Federal Mandate Crosswalk; (2) Cost of Inaction Sidebar; (3) Source of Authority — Core Section; (4) Source of Authority — Location, Inter-Jurisdictional, Inter-Agency; (5) Federal Identity Fragmentation + NPE Assurance Model; (6) Section Source Tracking (V4G/V4P/V4C → V4U merger map)."
---

# V4U MASTER REFERENCE — All Drafted Sections Combined
# Generated: March 7, 2026
# Contains all 6 section files in document order

# ============================================================
# FILE 1 OF 6: Paradigm Shift and Federal Mandate Crosswalk
# Maps to: V4U Sections 3 + 4
# ============================================================


# SECTION: THE PARADIGM SHIFT — From Perimeter to Identity

---

> **Placement: V4U Section 3. Insert after the Four Core Conditions (Section 2) and before the Federal Mandate Crosswalk (Section 4).**

---

## 1. The Architecture Federal Agencies Actually Have

Most federal agencies — regardless of mission, size, or modernization rhetoric — are operating an architecture that was state-of-the-art in the late 1990s and has been incrementally patched ever since. The table below captures the actual operational state across eight architectural domains:

| Domain | Frozen State (What Agencies Actually Have) |
|--------|------------------------------------------|
| **Identity** | On-prem Active Directory forests, siloed per division. Identity is a login event, not a continuous signal. No unified identity graph. Service accounts with static passwords. PIV/CAC for physical + logical access but not integrated with cloud IAM. Contractors and citizens handled through separate, disconnected systems. |
| **Addressing** | Static IP addressing managed in spreadsheets or partially in InfoBlox. No identity-to-address binding. DHCP scopes configured per building/VLAN with no dynamic reconciliation. Cloud workloads get cloud-native IPs with no authoritative linkage back to enterprise IPAM. |
| **Network Security** | Perimeter firewalls (L3/L4 ACLs), VPN concentrators, and TIC 1.0/2.0 gateways. Trust is binary: inside the perimeter = trusted, outside = untrusted. No L5–L7 inspection at scale. No identity-aware segmentation. East-west traffic is largely unmonitored. |
| **Endpoint Management** | Mix of SCCM, Jamf, and manual imaging. No unified endpoint posture signal feeding access decisions. BYOD either banned or unmanaged. Mobile devices partially covered by MDM but not integrated into identity or network trust. |
| **Application Delivery** | Monolithic apps on physical or VMware infrastructure. Load balancers doing L4 distribution. No service mesh. No workload identity. Application teams manage their own authentication, often with local accounts. |
| **Telemetry** | SIEM (Splunk or equivalent) collecting logs but not correlating identity, network, and application signals into a unified conversation. Network monitoring is SNMP-based. No conversation-level tracing. No real-time closed-loop remediation. |
| **Governance** | Change management via email and ticketing. No automated policy enforcement. Entitlement reviews are annual checkbox exercises. No continuous compliance validation. ServiceNow used for tickets but not as a governance backbone. |
| **Data Protection** | Classification is manual (if it happens at all). DLP rules are broad and generate noise. No data-aware routing. No pseudonymization framework. Encryption at rest and in transit but no data-level access control tied to identity assurance. |

## 2. The Architecture Every Federal Mandate Now Demands

Every major federal cybersecurity mandate issued since 2021 converges on the same architectural requirements. The table below maps the mandated state across the same eight domains:

| Domain | Mandated State (What Every Directive Requires) |
|--------|----------------------------------------------|
| **Identity** | Centralized identity provider (cloud-hosted). Continuous authentication and authorization. Phishing-resistant MFA for all users. Identity as the primary security perimeter. Machine identity managed with the same rigor as human identity. Federation for cross-agency and citizen access. (OMB M-22-09 §1–3; CISA ZTMM Identity Pillar; NIST 800-63-4; EO 14028 §3) |
| **Addressing** | Authoritative IPAM as the single source of truth for all IP addressing. Dynamic reconciliation between on-prem and cloud. Identity-derived addressing enabling deterministic segmentation. (NIST 800-207 §2.1; CISA ZTMM Network Pillar) |
| **Network Security** | Identity-aware microsegmentation. East-west traffic inspection. Software-defined perimeters replacing hardware perimeters. L5–L7 policy enforcement. Encrypted DNS. Network traffic treated as untrusted regardless of location. (OMB M-22-09 §4; NIST 800-207 §2.1–2.6; TIC 3.0 Use Cases; CISA ZTMM Network Pillar) |
| **Endpoint Management** | Every device inventoried, compliant, and continuously assessed. Device identity and health as an input to every access decision. EDR/XDR on all endpoints. (OMB M-22-09 §5; CISA ZTMM Device Pillar; EO 14028 §7) |
| **Application Delivery** | Internet-accessible applications tested and secured. Workload identity for service-to-service authentication. Container and serverless security. Application-layer encryption (mTLS). (OMB M-22-09 §6; CISA ZTMM Application Pillar; FedRAMP Rev 5) |
| **Telemetry** | Centralized logging with identity, network, and application correlation. Automated threat detection and response. Shared telemetry with CISA (CDM/CLAW). Machine-speed incident response. (EO 14028 §6–8; CISA ZTMM Visibility & Analytics; OMB M-21-31) |
| **Governance** | Automated policy enforcement. Continuous compliance monitoring. Role-based access with least privilege. Entitlement governance with periodic recertification. (OMB M-22-09 §7; NIST 800-53r5 AC/IA families; FedRAMP continuous monitoring) |
| **Data Protection** | Data categorized and tagged. Data-level access controls. Automated DLP with identity-aware policies. Data encryption with agency-managed keys. Data-aware routing and residency enforcement. (OMB M-22-09 §8; CISA ZTMM Data Pillar; EO 14028 §3(d)) |

## 3. The Gap Is Structural — Not Incremental

The distance between the frozen state and the mandated state cannot be crossed by incremental upgrades to existing systems. Five structural reasons:

1. **The identity model is inverted.** The frozen architecture treats identity as a gate (authenticate once, access everything). The mandated architecture treats identity as a continuous signal that drives every trust decision. You cannot patch a gate into a signal — you must rebuild the trust model.

2. **The network trust model is backwards.** The frozen architecture trusts the network (inside = trusted). The mandated architecture trusts nothing and verifies everything. Adding ZTA features to a trusted-network architecture creates contradictions, not security.

3. **The telemetry model is disconnected.** The frozen architecture collects logs in silos (network logs here, identity logs there, application logs somewhere else). The mandated architecture requires conversation-level correlation across all signals. You cannot bolt correlation onto siloed collection — you must design the telemetry schema first and then instrument to it.

4. **The governance model is manual.** The frozen architecture relies on human review cycles (annual access reviews, manual change approval, periodic audits). The mandated architecture requires automated, continuous enforcement. Manual governance cannot scale to machine-speed threats.

5. **The data model has no control plane.** The frozen architecture protects data with network perimeters. The mandated architecture requires data-level controls that travel with the data regardless of network location. There is no incremental path from "data protected by firewall" to "data protected by identity-aware, classification-driven, location-enforced policy."

**This is why the architecture must be rebuilt from the identity layer outward** — not patched from the perimeter inward.

---

# SECTION: FEDERAL MANDATE CROSSWALK

---

> **Placement: V4U Section 4. Insert after the Paradigm Shift (Section 3) and before Federal Identity Fragmentation (Section 5).**

---

## OMB M-22-09: Federal Zero Trust Strategy

| OMB M-22-09 Requirement | Architecture Component | Implementation |
|------------------------|----------------------|----------------|
| 1. Enterprise identity system for agency staff | Entra ID (cloud-hosted, hybrid-synced) | Entra ID as the single enterprise IdP; bidirectional sync with on-prem AD; PIV/CAC CBA; Conditional Access |
| 2. Phishing-resistant MFA for all staff | PIV/CAC + FIDO2/WebAuthn | CAC/PIV for AAL3 staff access; FIDO2 passkeys for contractors/remote; no SMS/OTP fallback for privileged access |
| 3. Device inventory and compliance | Intune + ServiceNow CMDB + Defender | Every device enrolled, compliance state fed to Conditional Access; non-compliant = quarantine; NPE-AL2 minimum for production |
| 4. Network segmentation and encrypted DNS | NSX microsegmentation + SD-WAN + InfoBlox | Identity-aware microseg via NSX; encrypted DNS via InfoBlox/DoH; SD-WAN overlay replaces flat VLANs |
| 5. Encrypt all DNS, HTTP, and email traffic | mTLS + ACME automation + overlay encryption | ACME-issued certs for all services; mTLS for east-west; TLS 1.3 for north-south; encrypted DNS |
| 6. Application security testing | DevSecOps pipeline + SASE inspection | IaC scanning, container scanning, DAST/SAST in CI/CD; SASE SWG/CASB for runtime |
| 7. Immutable audit logs | Splunk/Sentinel + conversation schema | Conversation-level logging with ConversationID; tamper-evident log storage; CDM/CLAW export |
| 8. Data categorization and protection | DLP + classification + SASE + overlay metadata | Data tagged at creation; DLP policies identity-aware; classification propagates via overlay metadata |
| 9. Automate security responses | SOAR + ServiceNow + closed-loop telemetry | Detect → Capture → Correlate → Remediate → Report; machine-speed response; ServiceNow orchestration |

## CISA Zero Trust Maturity Model v2.0

| CISA ZTMM Pillar | Traditional (Frozen State) | Initial | Advanced | Optimal (Architecture Target) |
|-------------------|--------------------------|---------|----------|-------------------------------|
| **Identity** | On-prem AD; password + PIV; no cloud IdP | Entra ID deployed; MFA enabled; basic Conditional Access | Phishing-resistant MFA universal; ABAC policies; continuous authentication | Full identity graph; NPE-AL model; SPIFFE for workloads; identity-driven everything |
| **Device** | Partial inventory; SCCM imaging; no posture signal | Intune enrollment; basic compliance; Defender deployed | Device health in Conditional Access; TPM attestation; automated remediation | NPE-AL2/AL3 for all devices; continuous attestation; PACS integration; identity-bound device certs |
| **Network** | Perimeter firewalls; flat VLANs; VPN | SD-WAN deployed; basic segmentation; encrypted DNS | NSX microsegmentation; identity-aware routing; SASE enforcement | Full overlay fabric; conversation-level routing; ML path optimization; deterministic addressing |
| **Application** | Monolithic; local auth; no workload identity | Cloud migration started; SSO via Entra ID; basic API security | Service mesh; mTLS; ACME automation; container security | SPIFFE/SPIRE workload identity; OPA policy; conversation state machine; NPE-AL3 for production |
| **Data** | Manual classification; perimeter DLP; no data-aware routing | Basic DLP rules; some encryption; data inventory started | Classification automated; DLP identity-aware; data-level access controls | Data control plane; classification propagates in overlay metadata; pseudonymization framework; data residency enforcement |

## NIST SP 800-63-4: Digital Identity Guidelines

| 800-63-4 Requirement | Architecture Component | Notes |
|----------------------|----------------------|-------|
| IAL2/IAL3 identity proofing | Login.gov (IAL2), PIV enrollment (IAL3) | Citizens via Login.gov; staff via PIV enrollment with background investigation |
| AAL2/AAL3 authenticators | FIDO2/WebAuthn (AAL2), PIV/CAC (AAL3) | No passwords as single factor; phishing-resistant required for privileged |
| FAL2/FAL3 federation | SAML/OIDC federation to Entra ID | Login.gov, id.me, state partners federated; FPKI-anchored for cross-agency |
| Syncable authenticators (passkeys) | Entra ID + FIDO2 passkey support | New in 800-63-4; syncable passkeys acceptable at AAL2 |
| Digital identity risk management (DIRM) | Conditional Access + telemetry | Risk-based authentication decisions using identity graph signals |
| Presentation Attack Detection (PAD) | Login.gov biometric proofing | Required for remote IAL2 proofing with selfie match |
| Equity and inclusion requirements | Progressive authentication + fallback paths | No single technology dependency; in-person alternatives available |

## NIST SP 800-207: Zero Trust Architecture

| 800-207 Principle | Architecture Implementation |
|-------------------|---------------------------|
| All data sources and computing services are resources | Identity graph + ServiceNow CMDB: every resource registered, classified, and policy-governed |
| All communication is secured regardless of location | mTLS + overlay encryption + SASE: no implicit trust from network position |
| Access granted on per-session basis | Conversation state machine: every conversation is individually authenticated, authorized, and tracked |
| Access determined by dynamic policy | Conditional Access (Entra ID) + OPA + NPE-AL levels: continuous evaluation with identity, device, location, risk signals |
| Integrity and security posture of all assets monitored | Intune + Defender + SPIRE attestation + NAC: continuous posture assessment for people and machines |
| Authentication and authorization strictly enforced before access | Identity layer (Section 9): no access without verified identity at appropriate assurance level |

## EO 14028: Executive Order on Improving the Nation's Cybersecurity

| EO 14028 Requirement | Architecture Component |
|---------------------|----------------------|
| §3: Modernizing federal cybersecurity (cloud, ZTA) | Entire architecture: identity-forward, cloud-hosted IdP, overlay fabric |
| §4: Software supply chain security | DevSecOps pipeline + SPIFFE/SPIRE for CI/CD + NPE-AL3 for production deployment |
| §6: Standardized federal response playbook | Operational Playbooks (Section 17) + SOAR + ServiceNow runbooks |
| §7: Improving detection on federal networks | Telemetry layer (Section 13) + conversation schema + CDM/CLAW export |
| §8: Federal government cybersecurity response | Closed-loop evidence model + machine-speed remediation + inter-agency telemetry |
| §9: National security systems alignment | Architecture patterns applicable to NSS with classification-appropriate controls |

## TIC 3.0: Trusted Internet Connections

| TIC 3.0 Use Case | Architecture Implementation |
|-------------------|---------------------------|
| Traditional TIC | SD-WAN + SASE replaces physical TIC access points; telemetry maintained |
| Cloud TIC | SASE enforcement + Cloud OnRamp + Private Link/Service Connect; InfoBlox DNS coordination |
| Branch/Remote TIC | SD-WAN direct-to-cloud with SASE inspection; ZTNA replaces VPN; identity-driven access |

## FedRAMP Rev 5 / NIST 800-53r5

| Control Family | Architecture Component |
|---------------|----------------------|
| **AC (Access Control)** | Entra ID Conditional Access + RBAC/ABAC + NPE-AL model + least privilege + JIT elevation |
| **IA (Identification and Authentication)** | PIV/CAC (AAL3) + FIDO2 (AAL2) + ACME PKI + mTLS + SPIFFE/SPIRE + NPE-AL levels |
| **SC (System and Communications Protection)** | mTLS + overlay encryption + NSX microseg + encrypted DNS + FIPS 140-3 crypto |
| **AU (Audit and Accountability)** | Conversation schema + Splunk/Sentinel + tamper-evident logs + CDM/CLAW export |
| **CM (Configuration Management)** | IaC (Terraform/ARM) + Intune baselines + OPA/Gatekeeper + ServiceNow CMDB |
| **IR (Incident Response)** | SOAR + operational playbooks + ServiceNow orchestration + closed-loop evidence |
| **CA (Assessment, Authorization, and Monitoring)** | Continuous monitoring via telemetry + automated compliance dashboards + Power BI |
| **SI (System and Information Integrity)** | Defender XDR + NDR + UEBA + SPIRE attestation + conversation anomaly detection |

## Mandate Convergence Summary

All seven mandates converge on five non-negotiable architectural shifts:

| Shift | OMB M-22-09 | CISA ZTMM | 800-63-4 | 800-207 | EO 14028 | TIC 3.0 | FedRAMP |
|-------|-------------|-----------|----------|---------|----------|---------|---------|
| Identity as primary perimeter | ✓ §1–3 | ✓ Identity Pillar | ✓ IAL/AAL/FAL | ✓ Principle 4 | ✓ §3 | ✓ All use cases | ✓ IA family |
| Continuous verification (not one-time auth) | ✓ §1 | ✓ All pillars (Advanced+) | ✓ DIRM | ✓ Principle 3–4 | ✓ §7 | ✓ Cloud/Branch | ✓ CA family |
| Encrypted, identity-aware network | ✓ §4–5 | ✓ Network Pillar | — | ✓ Principle 2 | ✓ §3 | ✓ All use cases | ✓ SC family |
| Machine-speed telemetry and response | ✓ §7, 9 | ✓ Visibility & Analytics | — | ✓ Principle 5 | ✓ §6–8 | ✓ Telemetry reqs | ✓ AU/IR families |
| Data-level protection independent of network | ✓ §8 | ✓ Data Pillar | — | ✓ Principle 1 | ✓ §3(d) | — | ✓ SC family |


# ============================================================
# FILE 2 OF 6: Cost of Inaction Sidebar
# Maps to: V4U Section 3.4
# ============================================================


# SIDEBAR: THE COST OF INACTION

---

> **Placement: V4U Section 3.4. Insert within the Paradigm Shift section, after "The Gap Is Structural" and before "The Identity-Forward Modernization Context."**

---

## The Compliance Clock

The federal government is not offering agencies a choice about whether to modernize. The mandates have deadlines, and the enforcement mechanisms are real:

- **OMB M-22-09** required agencies to meet specific zero trust goals by the end of FY2024. Agencies that have not met these goals are now in remediation — with quarterly reporting to OMB and CISA on progress.
- **OMB M-21-31 (Logging)** required agencies to reach EL3 (advanced) logging maturity by August 2023. Most agencies have not achieved this. CISA CDM dashboards now surface non-compliance.
- **CISA Binding Operational Directives** (BOD 22-01, BOD 23-01, BOD 23-02, BOD 25-01) are mandatory and enforceable. Non-compliance is reported to the National Cyber Director and OMB.
- **DOJ Civil Cyber-Fraud Initiative** (launched 2021, expanded 2024) uses the False Claims Act to pursue contractors and agencies that misrepresent their cybersecurity compliance. This is not theoretical — settlements have exceeded $100M.
- **FISMA Modernization Act of 2023** updated reporting requirements and gave CISA explicit authority to issue emergency directives to federal civilian agencies.

**The compliance clock is not hypothetical. Agencies that cannot demonstrate progress against these mandates face budget consequences, audit findings, and legal exposure.**

## The Threat Landscape

While the compliance clock ticks, the threat landscape has accelerated beyond what legacy architectures can address:

- **Credential-based attacks account for 80%+ of initial access** in federal network compromises (CISA advisories, 2023–2025). The frozen architecture's reliance on passwords + network perimeter is the primary attack enabler.
- **Average cost of a federal data breach: $10.22M** (adjusted for federal sector, IBM/Ponemon 2024). This does not include mission disruption, public trust erosion, or Congressional inquiry costs.
- **Median dwell time for undetected compromises: 10+ days** in environments without conversation-level telemetry correlation. The frozen architecture's siloed logging enables this dwell time.
- **Supply chain attacks** (SolarWinds, MOVEit, Log4Shell) exploited exactly the gaps this architecture addresses: unmanaged NPE identities, no workload attestation, no mTLS, no conversation-level anomaly detection.
- **Nation-state actors (Volt Typhoon, Salt Typhoon)** have demonstrated persistent access to federal and critical infrastructure networks through credential theft and lateral movement — techniques that succeed specifically because of flat networks, static service accounts, and lack of east-west monitoring.

## Six Specific Consequences of Inaction

| Consequence | Mechanism | Timeline |
|------------|-----------|----------|
| **1. OMB budget scoring** | OMB uses FISMA metrics and CISA ZT assessments to score agency cybersecurity posture. Low scores affect budget requests and IT spending authority. | Ongoing — affects every budget cycle |
| **2. CISA emergency directive** | CISA can issue binding emergency directives requiring specific technical actions within days. Agencies without the architectural foundation to respond quickly are exposed. | Any time — triggered by emerging threats |
| **3. Inspector General audit findings** | OIG cyber audits benchmark against CISA ZTMM and OMB M-22-09. Agencies frozen at "Traditional" maturity receive material weakness findings. | Annual audit cycle |
| **4. DOJ Civil Cyber-Fraud exposure** | If the agency (or its contractors) has certified compliance with NIST 800-53, FedRAMP, or FISMA requirements that are not actually met, the False Claims Act applies. | Active enforcement — cases in progress |
| **5. Breach with mission impact** | A credential-based breach that disrupts citizen services (call center, benefits processing, case management) creates Congressional visibility and erodes public trust. | Unpredictable — but probability increases daily |
| **6. Inability to onboard state partners** | Agencies that cannot offer secure federation endpoints, pseudonymized telemetry, or overlay-enforced data residency will be unable to meet state partner security requirements — blocking mission-critical data sharing. | As state partners increase security requirements (accelerating) |

**The cost of inaction is not zero. It is the sum of these six consequences, compounding daily.**


# ============================================================
# FILE 3 OF 6: Source of Authority — Core Section
# Maps to: V4U Sections 8.1–8.4, 8.9–8.10
# ============================================================


# SECTION: SOURCE OF AUTHORITY — The Chain of Authoritative Truth

---

> **Placement: V4U Section 8 (first half: 8.1–8.4, 8.9–8.10). The second half (8.5–8.8) comes from Source_of_Authority_Location_InterAgency.md.**

---

## 1. Why "Source of Authority" Is Different from "Source of Truth"

Every V4 draft uses the term "Single Source of Truth" (SSOT) — InfoBlox is the SSOT for IP addressing, Entra ID is the SSOT for identity, ServiceNow is the SSOT for configuration. This is correct but incomplete.

**SSOT answers: "Where do I look things up?"**

**Source of Authority (SoA) answers: "Who is authorized to originate truth, and what process governs that origination?"**

Without SoA, your SSOT is just a database label. Anyone who can write to the database can change "truth." SoA defines the chain of custody for authoritative information — who creates it, who can modify it, what lifecycle events trigger changes, and what reconciliation mechanisms detect drift.

The architecture requires both:
- **SSOT** = the operational system where the current authoritative state is stored and queried (InfoBlox, Entra ID, ServiceNow)
- **SoA** = the upstream authority that creates, modifies, and revokes the data in the SSOT (HR, Contracting Officer, Application Owner, Data Owner, GSA)

If the SSOT and SoA are misaligned — for example, if an HR separation event does not propagate to Entra ID — then the SSOT is wrong, and every trust decision that depends on it is wrong.

## 2. The Six Authority Chains

The architecture defines six core Source of Authority domains. Each maps an upstream authority to an operational SSOT:

| Domain | Source of Authority | Operational SSOT | Reconciliation Mechanism |
|--------|--------------------|-----------------|-----------------------|
| **Human Identity** | HR System (EHRP/HRConnect) | Entra ID via JML workflows | HR → Identity Governance → Entra ID cascade; separation within 60 minutes |
| **Non-Person Entities** | Application/Service Owner (human sponsor required) | Entra ID + PKI/ACME | ServiceNow approval workflow; quarterly recertification; orphan detection |
| **Contractors** | Contracting Officer / COR (contract lifecycle = identity lifecycle) | Entra ID | Contract period-of-performance drives account lifecycle; auto-disable at expiration |
| **Citizens** | The citizen themselves (self-asserted, agency validates via Login.gov/id.me) | Federated to Entra ID via SAML/OIDC | Federated assertion validation; consent management; pseudonymized logging |
| **IP Addressing** | Enterprise Network Architecture team | InfoBlox DDI | API reconciliation with cloud IPAMs; conflict detection; subnet-to-identity binding |
| **Assets / Configuration** | Division IT / System Owner | ServiceNow CMDB → Intune → InfoBlox → Entra ID device identity | SAM lifecycle workflows; Intune enrollment; CMDB reconciliation |
| **Data Classification** | Data Owner (business decision) | DLP / SASE enforcement → overlay routing | Classification propagates via overlay metadata; DLP policies identity-aware |

## 3. HR-Driven Identity: The Most Critical Chain

The HR-to-identity chain is the most critical because every other trust decision depends on it. If identity is the root namespace (Core Model, Section 7.2), then the authority that creates identity is the root of the entire trust hierarchy.

### The Cascade

```
HR System (EHRP/HRConnect)
    ↓ Joiner event (new hire, new contractor, transfer)
Identity Governance (IGA / Lifecycle Workflows)
    ↓ Provisions account, assigns initial roles, triggers downstream
Entra ID (Cloud Identity Provider)
    ↓ Propagates to all consuming systems:
    ├── Conditional Access policies (evaluate identity + device + location + risk)
    ├── InfoBlox (identity-derived addressing / DNS registration)
    ├── SD-WAN / Overlay (identity-aware routing and segmentation)
    ├── PKI / ACME (certificate issuance with identity-bound SANs)
    ├── ServiceNow (asset/entitlement records linked to identity)
    ├── Splunk / Sentinel (identity context in telemetry correlation)
    ├── DLP / SASE (identity-aware data protection policies)
    └── NAC (identity-driven network admission)
```

### Operational Requirements

- **Separation (Leaver) must deactivate everything within 60 minutes.** For adverse action (termination for cause, security incident), deactivation must be immediate — within minutes. The architecture must support emergency kill-switch workflows that propagate from HR → Entra ID → all downstream systems in a single automated cascade.

- **Mover events** (role change, division transfer, promotion) trigger attribute updates in Entra ID + a 30-day recertification window for all existing entitlements. Stale entitlements from the previous role that are not recertified within 30 days are automatically revoked.

- **Contractor accounts auto-disable at period-of-performance expiration.** The Contracting Officer / COR is the SoA; the contract end date is the lifecycle trigger. No manual intervention required — the system enforces the contract boundary.

- **Orphan detection:** A scheduled reconciliation process compares the HR roster to Entra ID accounts. Any Entra ID account that does not have a corresponding active HR record is flagged as an orphan and investigated within 5 business days. Orphaned NPE accounts (service accounts without an active human sponsor) follow the same 5-day SLA.

### FICAM / OMB Alignment

This directly implements:
- **FICAM Architecture** requirement that identity information comes from "onboarding documents or HR systems" and is created in "the authoritative source"
- **FICAM Identity Lifecycle Management (ILM) Playbook** mapping of authoritative attribute sources to specific offices: HR for employment status, Security/Vetting for clearance, Training for certifications, Application Owners for entitlements
- **OMB M-19-17** directive to shift from managing credentials to managing identity lifecycles
- **OMB M-22-09** §1–3 requirements for enterprise identity management

## 4. Source of Authority for Databases and Application Data

Beyond identity and addressing, every agency database has (or should have) a named Source of Authority. The architecture extends the SoA model to data:

| Database Type | Source of Authority | Operational Pattern | Architecture Implication |
|--------------|--------------------|--------------------|------------------------|
| **HR / Personnel** | HR Office (CHCO) | HR system is authoritative; all other systems consume via API or batch | Identity governance must consume HR data in near-real-time; no manual identity provisioning |
| **Case Management** | Program Office / Case Owners | Case workers create and update case records; supervisors validate | Data classification (PII level) drives DLP policy; overlay routes case data per classification |
| **Financial** | CFO / Financial Management Office | Financial system of record (SAP, Oracle, etc.) is authoritative | Financial data tagged at highest sensitivity; audit logging mandatory; no bulk export without approval |
| **Citizen PII** | Privacy Office (SAOP) + Program Office | Citizen provides data; agency validates and stores per Privacy Act SORN | Pseudonymization mandatory in telemetry; consent management; per-jurisdiction handling rules |
| **CMDB / Asset Data** | Division IT / System Owners | ServiceNow CMDB fed by Intune, scanning tools, manual entry | CMDB reconciliation with Intune and InfoBlox; orphan asset detection mirrors orphan identity detection |
| **Telemetry / Log Data** | CISO / SOC | Generated by systems; ingested by Splunk/Sentinel | Retention per OMB M-21-31; tamper-evident storage; CDM/CLAW export; PII fields masked at ingestion |

**Key principle:** Every database has a named human or office authority. If you cannot name the SoA for a database, you cannot make trust decisions based on its data.

## 5. Mapping to Four Core Conditions

| Source of Authority Domain | Visibility | Verification | Validation | Control |
|---------------------------|-----------|-------------|-----------|---------|
| Human Identity | Identity graph shows all staff identities and their attributes | HR record validates identity is real and current | Entitlement reviews confirm access is appropriate | Separation cascade deactivates within 60 minutes |
| NPE Identity | NPE inventory shows all service accounts, managed identities, workloads | Human sponsor validates NPE purpose and scope | Quarterly recertification confirms NPE is still needed | Orphan detection + attestation failure triggers revocation |
| Contractor Identity | Contractor identities visible in identity graph with contract metadata | CO/COR validates contractor is authorized | Period-of-performance validation confirms active contract | Auto-disable at contract expiration |
| Citizen Identity | Federated citizen sessions visible in telemetry (pseudonymized) | Login.gov/id.me validates citizen identity at IAL2 | Consent validation confirms citizen authorized data use | Progressive authentication + data minimization |
| IP Addressing | InfoBlox shows all IP allocations with identity bindings | API reconciliation validates addresses match authoritative IPAM | Conflict detection validates no overlaps or orphans | Dynamic re-addressing on identity/policy change |
| Assets / Configuration | ServiceNow CMDB shows all assets with owner and compliance state | Intune validates device compliance continuously | CMDB reconciliation validates asset data accuracy | Non-compliant devices quarantined via NAC |
| Data Classification | DLP policies show what data exists and its classification | Data Owner validates classification is correct | Classification propagation validates tags travel with data | DLP enforcement blocks unauthorized access/export |

## 6. Mapping to Canon Points

| Canon Point | SoA Relevance |
|------------|--------------|
| **Point 5: Bureaucratic layer overlays** | SoA forces naming the *actual* authority for each domain — cutting through org chart ambiguity |
| **Point 10: IAM, IPAM, Asset Management** | Each of these is an SSOT; SoA defines *who feeds them* and *what makes them authoritative* |
| **Point 11: The Source-of-Truth Crisis** | SoA resolves the crisis by defining not just where truth lives but *who creates it and how it's validated* |
| **Point 12: AI as the Truth Engine** | AI can reconcile SSOTs only if SoA chains are defined — otherwise AI is reconciling garbage with garbage |
| **Point 13: Inter-Agency Truth Fabric** | Cross-agency truth requires knowing each agency's SoA per domain — federation, not centralization |


# ============================================================
# FILE 4 OF 6: Source of Authority — Location, Inter-Jurisdictional, Inter-Agency
# Maps to: V4U Sections 8.5–8.8
# ============================================================


# SOURCE OF AUTHORITY: LOCATION, INTER-JURISDICTIONAL, AND INTER-AGENCY AUTHORITY CHAINS

---

> **This section extends the Source of Authority model to cover three critical domains missing from all V4 drafts: (1) physical location and building/facility authority, (2) federal-to-state authority relationships, and (3) federal-to-federal authority relationships. Insert after the core Source of Authority section.**

---

## 1. Buildings and Facilities: The Location Source of Authority

### The Federal Real Property Profile Management System (FRPP MS)

Yes — every federal executive branch agency is **required by law** to maintain a buildings and facilities inventory. The Federal Real Property Profile Management System (FRPP MS), managed by GSA, is the government-wide centralized database of all real property under the custody and control of executive branch agencies. It was created under Executive Order 13327 and reinforced by the Federal Assets Sale and Transfer Act of 2016 (FASTA).

FRPP MS captures the following data elements for every building, land parcel, and structure:

**Location data elements (from the FY 2025 FRPP Data Dictionary):**
- Street Address
- Latitude / Longitude (preferred over street address; mandatory for buildings in the US/territories)
- City, County, State, Country, Zip Code
- Geographic Locator Code (GLC) — an alphanumeric code agencies must use for geographic reporting
- Asset Height, Elevation above Mean Sea Level, Asset Height above Mean Sea Level (added by MOBILE NOW Act)
- Real Property Unique Identifier
- Using Organization / Reporting Agency
- Real Property Type (Building, Land, Structure)
- Real Property Use (Office, Warehouse, Field Office, Headquarters Function, etc.)
- Structural Size, Year of Construction, Lease dates

**What FRPP MS provides:** Building-level location (lat/long, address, GLC) for every federally owned, leased, or controlled property.

**What FRPP MS does NOT provide:** Interior space data — room numbers, floor layouts, cubicle assignments, wiring closet locations, IDF/MDF locations, conference room identifiers, or sub-building location data needed for E911 dispatchable location, identity-to-location mapping, and physical access control.

### The Location Authority Gap

This creates a two-tier location authority problem:

| Location Tier | Source of Authority | Typical System | Status at Most Agencies |
|--------------|--------------------|--------------|-----------------------|
| **Tier 1: Building-level** | GSA (FRPP MS) + Agency Facilities Office | FRPP MS, agency real property systems, GSA Occupancy Agreements | Generally authoritative — legally mandated and audited |
| **Tier 2: Interior/sub-building** | Agency Facilities / Space Management Office | CAD/BIM systems, space management tools (Archibus, TRIRIGA, FM:Systems), spreadsheets, or nothing | **Almost never authoritative.** Fragmented, stale, or non-existent. Often maintained in disconnected CAD files or spreadsheets that are updated during renovations and forgotten. |

**Why this matters for the architecture:**

- **E911 dispatchable location** (required by Kari's Law and RAY BAUM's Act) demands sub-building accuracy — floor, wing, room. FRPP MS gives you the building; it does not give you the caller's location within the building. Without an authoritative interior location source, E911 compliance is best-effort, not deterministic.
- **Identity-to-location mapping** — the architecture derives trust from identity + device + location. If the location signal is unreliable or non-authoritative at the sub-building level, trust decisions that depend on "is this user in a secure area" or "is this device in the data center" are probabilistic, not deterministic.
- **Physical access control integration** — PACS (Physical Access Control Systems) know which badge swiped which door. PACS is often the most accurate real-time interior location signal, but it is rarely integrated with logical identity (Entra ID) or network addressing (InfoBlox). The architecture should consume PACS events as location enrichment signals in the identity graph.
- **Network infrastructure mapping** — IDF/MDF locations, switch port-to-room mappings, and wireless AP coverage maps are network-level location data that lives in DCIM tools, spreadsheets, or institutional knowledge. InfoBlox can map IP/subnet to building if someone builds and maintains that mapping — but it is rarely authoritative for sub-building granularity.

### Prescriptive Addition to the Architecture

Add **Location** as a seventh Source of Authority domain:

| Domain | Source of Authority | Operational SSOT | Reconciliation Mechanism |
|--------|--------------------|-----------------|-----------------------|
| **Location — Building-level** | GSA FRPP MS + Agency Facilities Office | Agency real property system (fed by FRPP data) | Annual FRPP submission + agency real property audit |
| **Location — Interior/sub-building** | Agency Space Management Office (or Facilities) | Space management system (Archibus/TRIRIGA/etc.) or, where absent, a purpose-built location SSOT integrated into ServiceNow | PACS events as validation signal; InfoBlox subnet-to-room mapping reconciliation; wireless AP location triangulation; E911 location validation testing |
| **Location — Network infrastructure** | Enterprise Network Architecture team | InfoBlox (subnet-to-building/floor/room mapping) + DCIM (rack/port mapping) | Switch port-to-room mapping maintained by network ops; validated during E911 dispatchable location testing |

**If the agency does not have an authoritative interior location system, the architecture must create one** — even if it starts as a structured ServiceNow CMDB extension that maps building → floor → wing → room → subnet → switch port → WAP. This is a prerequisite for E911 compliance, PACS-to-identity integration, and location-aware trust decisions.

---

## 2. Federal-to-State Source of Authority Relationships

Many federal agencies operate in deep partnership with state governments — SSA, CMS, USDA/FNS, DOL, HHS, ED, and others share data with state agencies as a core part of mission delivery. These relationships create **cross-jurisdictional Source of Authority chains** that the architecture must model.

### How Federal-State Authority Actually Works

There is no single federal-state authority model. Instead, there are established legal and procedural patterns:

| Pattern | How It Works | Federal Examples | Authority Source |
|---------|-------------|-----------------|-----------------|
| **Federal system as SoA, states consume** | Federal agency maintains the authoritative database. States query it via API or batch. Federal data is authoritative; state data is a cache or derivative. | **DHS SAVE** — states query federal citizenship/immigration status for benefit eligibility. SSA — states query for earnings/benefit verification. | Federal statute (e.g., Immigration and Nationality Act for SAVE; Social Security Act §1106 for SSA) |
| **State system as SoA, federal agency consumes** | State maintains the authoritative record (e.g., vital records, driver's licenses, Medicaid eligibility). Federal agency ingests state data for federal program administration. | **CMS/Medicaid** — states determine Medicaid eligibility; CMS consumes state eligibility data. **Census Bureau** — receives state administrative records (SNAP, TANF, WIC) under Title 13 §6. **USDA/FNS** — State Systems Office works with state agencies that administer SNAP, WIC at the state level. | State statute + federal authorizing statute + data sharing agreement |
| **Shared/federated authority** | Both federal and state systems contribute authoritative data elements. Neither is fully authoritative alone. A reconciliation process determines combined truth. | **Unemployment Insurance** — DOL sets policy, states administer and maintain claimant records. **IDEA (Disabilities Education)** — ED sets federal requirements, states maintain child-level data, share via MOU. | Federal-state MOU/ISA + statute |
| **Federal mandate, state implementation** | Federal agency mandates a standard or process; states implement it with their own systems. Federal agency validates/audits state compliance. | **FNS State Systems Office** — provides guidance and tools for states to automate SNAP/WIC program requirements. **REAL ID** — DHS sets standards, states issue compliant IDs from their own DMV systems. | Federal regulation + state implementation |

### The Legal Instruments

Every federal-state data relationship requires a formal agreement. The common instruments:

| Instrument | Purpose | Who Uses It |
|-----------|---------|------------|
| **Information Exchange Agreement (IEA)** | Governs PII disclosure between federal agency and another federal or state agency. Defines data elements, security requirements, permitted uses, and retention. | SSA (primary mechanism for all data exchanges); CMS; most HHS operating divisions |
| **Interconnection Security Agreement (ISA)** | Documents technical requirements for system-to-system connections across authorization boundaries. Required whenever a direct connection is implemented between federal and state systems. | SSA, CMS, any agency with direct state system connections |
| **Inter-Agency Agreement (IAA)** | Covers reimbursable costs and administrative terms. Usually accompanies an IEA. | SSA, DOL, CMS |
| **Computer Matching Agreement (CMA)** | Required by the Computer Matching and Privacy Protection Act of 1988 when federal records are matched against other federal or state records for benefit eligibility or payment verification. Requires Data Integrity Board approval. | SSA, CMS, DOL, HHS — any cross-system matching for eligibility |
| **Memorandum of Understanding (MOU)** | Broader framework agreement covering roles, responsibilities, and data governance. Often the umbrella under which IEAs and ISAs operate. | ED, USDA/FNS, DOJ/BJA (NIEM), DHS |

### What This Means for the Architecture

The architecture must model federal-state relationships as **federated Source of Authority chains**, not as simple data imports:

1. **Each state partner has its own Source of Authority** for data it owns (vital records, eligibility determinations, DMV records). The architecture cannot override state authority — it can only validate, consume, and reconcile.

2. **Legal agreements are the authority boundary.** The IEA/ISA/MOU defines what data can flow, in what direction, with what protections. The overlay fabric must enforce these constraints — per-jurisdiction telemetry filters, pseudonymization before data crosses boundaries, and data residency enforcement are not nice-to-haves; they are legally mandated by the agreements.

3. **State onboarding through the overlay** (described in V4P's Canon Point 13: Inter-Agency Truth Fabric) requires a formal legal attestation step before any data flows. The architecture should include a **State Partner Onboarding Workflow** in ServiceNow:
   - Legal review and IEA/ISA/MOU execution
   - Technical ISA documenting connection architecture
   - Identity federation configuration (federated Entra ID B2B or SAML/OIDC trust)
   - Per-jurisdiction telemetry filter configuration in Splunk/Sentinel
   - Pseudonymization rule deployment in the overlay
   - E2E validation test
   - ServiceNow records the entire chain as auditable evidence

4. **NIEM (National Information Exchange Model)** provides the semantic standard for cross-jurisdictional data exchange. If the agency exchanges structured data with states (especially in justice, emergency management, health, or human services domains), NIEM information exchange packages should be the format layer. NIEM is a partnership of DOJ, DHS, and HHS, and is designed to standardize data exchange across federal, state, tribal, and local governments.

---

## 3. Federal-to-Federal Source of Authority Relationships

### The Federal PKI Trust Fabric

The federal government already has one mature cross-agency Source of Authority model: **the Federal PKI (FPKI)**. Managed by the FPKI Policy Authority under the FICAM program:

- **Federal Common Policy CA (FCPCA)** — the trust anchor for the federal government. Authorized CAs issue certificates for exclusive use by the federal government (employees and contractors), including PIV credential certificates.
- **Federal Bridge CA (FBCA)** — enables PKI interoperability between federally operated and business partner PKIs through cross-certification.

This is a working federal-to-federal Source of Authority for **credential trust**. The architecture already depends on it (PKI/ACME, mTLS, cert-bound tokens). But credential trust is only one domain.

### Where Federal-to-Federal Authority Is Fragmented

| Domain | Current State | What's Needed |
|--------|-------------|--------------|
| **Identity** | Each agency operates its own Entra ID / AD. No cross-agency identity federation standard beyond PIV/FPKI. | Federated identity assertions via SAML/OIDC between agency Entra ID tenants, anchored by FPKI certificate trust. The FICAM ICAM Subcommittee (co-chaired by GSA, DOJ, and DHS/CISA) is the governance body but has no enforcement authority. |
| **Addressing (IPAM)** | Each agency manages its own IP space. No cross-agency IPAM reconciliation exists. | For agencies that interconnect (shared services, cross-agency applications, TIC shared connections), overlay addressing reconciliation via API between InfoBlox instances — or at minimum, documented non-overlapping address space allocation. |
| **Telemetry** | CISA CDM/CLAW is the closest thing to cross-agency telemetry. Agencies submit data to CDM dashboards, but there is no shared telemetry schema or conversation-level correlation across agencies. | The conversation schema defined in this architecture should be designed for CDM/CLAW compatibility. If two agencies share a conversation (e.g., a federated application session), the ConversationID should be correlatable across both agencies' telemetry without exposing PII. |
| **Data** | Each agency is the SoA for its own program data. Cross-agency data sharing governed by IEAs, CMAs, and statute. No common data authority model. | The architecture's data classification and DLP model must tag data with its originating agency SoA. When data crosses agency boundaries (via API, federation, or shared services), the originating agency's classification and handling rules travel with the data via overlay metadata. |
| **Facilities** | FRPP MS is the cross-agency standard for building-level location. No cross-agency standard for interior space. | For shared federal buildings (GSA-managed), GSA is the building-level SoA. Tenant agencies are the SoA for their occupied space within the building. This dual-authority model must be reflected in the location SSOT. |

### The Inter-Agency Truth Fabric (Canon Point 13) — Enhanced

The V4P document describes the Inter-Agency Truth Fabric as "overlay reconciliation mesh, not a new central system." This is correct. But the Source of Authority model adds specificity:

**Federation, not centralization.** Each agency remains the Source of Authority for its own domains. Cross-agency truth is achieved through:

1. **FPKI** for credential trust (already exists, already works)
2. **Federated identity assertions** (SAML/OIDC) for cross-agency authentication, anchored by FPKI cert trust
3. **Legal agreements** (IEA/ISA/MOU) for every data exchange — no data flows without a signed instrument
4. **NIEM** for semantic interoperability of exchanged data
5. **CDM/CLAW** for telemetry aggregation at the national level (CISA as the telemetry consumer, not the telemetry authority)
6. **Overlay metadata** carrying SoA tags — when data or a conversation crosses an agency boundary, the metadata declares which agency is authoritative for which data elements

The architecture does not need to build a new cross-agency authority system. It needs to **consume and enforce the existing authority instruments** (FPKI, IEAs, NIEM, CDM) through the overlay fabric, and **expose clean federation endpoints** that other agencies can connect to using the same patterns.

---

## 4. Updated Source of Authority Master Table

Combining the original SoA domains with the three new domains:

| Domain | Source of Authority | Operational SSOT | Reconciliation | Legal Instrument |
|--------|--------------------|-----------------|--------------|-----------------|
| Human Identity | HR System | Entra ID | JML workflows | Internal policy |
| NPE Identity | Application/Service Owner | Entra ID + PKI | ServiceNow workflows | Internal policy |
| Contractor Identity | CO/COR | Entra ID | Contract lifecycle automation | Contract + internal policy |
| Citizen Identity | Citizen (self-asserted, proofed) | Login.gov/id.me → Entra ID | Federated assertion validation | Privacy Act + consent |
| IP Addressing | Enterprise Network Architecture | InfoBlox DDI | API reconciliation | Internal policy |
| Assets / Configuration | Division IT / System Owner | ServiceNow CMDB + Intune | SAM lifecycle workflows | Internal policy |
| Data Classification | Data Owner | DLP / SASE policies | Classification propagation | Agency records policy + NARA |
| **Location — Building** | **GSA (FRPP MS) + Agency Facilities** | **Agency real property system** | **Annual FRPP submission** | **EO 13327 + FASTA** |
| **Location — Interior** | **Agency Space Management** | **Space mgmt system or ServiceNow CMDB** | **PACS + InfoBlox subnet mapping + E911 testing** | **Kari's Law + RAY BAUM's Act (for E911)** |
| **State Partner Data** | **State agency (per domain)** | **State system (federated access)** | **Per IEA/ISA/MOU terms** | **IEA + ISA + MOU + authorizing statute** |
| **Federal Partner Data** | **Originating federal agency** | **Originating agency's SSOT** | **CDM/CLAW + federated assertions + NIEM** | **IEA + ISA + MOU + FPKI MOA** |
| **Credential Trust (cross-agency)** | **FPKI Policy Authority** | **FCPCA + FBCA** | **FPKI audit + cross-certification** | **FPKI MOA + Certificate Policy** |

---

*This section completes the Source of Authority model by extending it beyond the agency boundary. It should be appended to the core Source of Authority section in the unified V4 document.*


# ============================================================
# FILE 5 OF 6: Federal Identity Fragmentation + NPE Assurance Model
# Maps to: V4U Sections 5 + 9.8
# ============================================================


# SECTION A: FEDERAL IDENTITY FRAGMENTATION — Five Disconnected Regimes, One Architecture

---

> **Placement: Insert in the Paradigm Shift section, after the "Mandate Convergence Summary" (Section 12) and before the 17-Point Canon. This sidebar visually demonstrates why identity-forward architecture is the reconciliation layer the federal government does not currently have.**

---

## The Problem: Five Identity Regimes, Zero Interoperability

The federal government operates five distinct identity regimes. Each was created by a different authority, for a different purpose, under a different legal framework. None were designed to interoperate with the others. Together, they create the illusion of a "federal identity strategy" while in practice producing fragmentation, redundancy, and gaps.

### The Five Regimes

| Regime | Governing Authority | Legal Basis | Credential Type | Identity Proofing | Scope | Assurance Level |
|--------|-------------------|------------|----------------|-------------------|-------|----------------|
| **REAL ID** | DHS / State DMVs | REAL ID Act of 2005 (P.L. 109-13); enforced May 7, 2025 | State-issued driver's license or ID card with star marking | In-person at DMV: identity document verification (birth certificate, SSN, 2 proofs of address) | Physical access only: TSA checkpoints, federal facilities, nuclear plants | No formal IAL — DHS minimum standards for document verification |
| **PIV / CAC** | OPM + GSA (PIV) / DoD (CAC) | HSPD-12; FIPS 201-3; NIST 800-73/76/78 | Smart card with X.509 certificates (authentication, digital signature, key management) | Adjudicated background investigation (NBIB/DCSA) + identity proofing at enrollment | Physical + logical access for federal employees and contractors | IAL3 / AAL3 (hardware-bound, phishing-resistant, identity-proofed) |
| **NIST 800-63-4** | NIST | NIST SP 800-63-4 (finalized August 2025) | Framework only — defines IAL/AAL/FAL levels; does not issue credentials | Defined at IAL1 (self-asserted), IAL2 (remote proofing), IAL3 (in-person or supervised remote with PAD) | Digital access to federal information systems | IAL1–3 / AAL1–3 / FAL1–3 |
| **Login.gov / id.me** | GSA (Login.gov) / VA + others (id.me) | E-Government Act; agency-specific authorizations | Username + MFA (FIDO2, SMS, TOTP); Login.gov adding passport verification and mDL acceptance by March 2026 | Remote identity proofing: document verification (driver's license photo) + selfie match; Login.gov adding passport via State Dept API and anti-fraud analytics | Digital access to federal services (SSA, VA, USDA, SBA, IRS, etc.) | Login.gov: IAL2 (certified); id.me: IAL2 (commercial proofing) |
| **U.S. Passport** | State Department | Immigration and Nationality Act; 22 CFR Part 51 | Physical booklet or card with MRZ; no digital credential (yet) | In-person or mail: citizenship evidence + identity document + photo | International travel; accepted as REAL ID alternative for domestic flights/federal facilities | De facto IAL3 (adjudicated citizenship determination) but not mapped to 800-63 |

### The Fragmentation Problem

**No single system connects these regimes.** A federal employee has a PIV card (HSPD-12), a REAL ID driver's license (state DMV), a passport (State Department), and possibly a Login.gov account (GSA) — all identity-proofed independently, all managed by different authorities, all with different lifecycle processes. If the employee separates from federal service:

- PIV is revoked (by the agency's credentialing office)
- REAL ID remains valid (state DMV has no knowledge of federal employment status)
- Passport remains valid (State Department has no knowledge of federal employment status)
- Login.gov account remains valid (GSA has no knowledge of federal employment status)

There is no cross-regime lifecycle event. There is no shared identity graph. There is no reconciliation.

### The Convergence Is Beginning — But Slowly

Login.gov's FY2026 roadmap includes significant interoperability steps:

- **Passport acceptance** for identity proofing — Login.gov will verify passport photos against State Department records via a privacy-preserving API
- **PIV/CAC reuse** — Login.gov will accept prior PIV/CAC proofing to establish Login.gov accounts without re-proofing
- **Mobile Driver's License (mDL) acceptance** by March 2026
- **Cross-agency threat modeling** and **anti-fraud signal sharing** APIs
- **Reusing proofing from other government systems** — checking authoritative government records rather than requiring re-proofing from scratch

This is directionally correct but still operates within Login.gov's scope (digital access to federal services). It does not create a unified identity graph that spans physical access (REAL ID/PIV), digital access (Login.gov), and credential lifecycle (HR-driven).

### How This Architecture Fills the Gap

The Unified Identity-Addressing-Overlay Architecture positions **Entra ID as the operational identity graph** that consumes assertions from all five regimes and correlates them into a single, queryable, policy-driving identity record:

| Identity Regime | Architecture Integration Point | Identity Graph Contribution |
|----------------|-------------------------------|---------------------------|
| **PIV/CAC** | Certificate-based authentication via Entra ID CBA (Certificate-Based Authentication); PIV cert attributes (SAN, EKU, issuer) ingested into identity graph | Highest-assurance staff identity; phishing-resistant AAL3; FPKI trust chain; physical + logical access correlation |
| **REAL ID** | In-person identity proofing evidence recorded during onboarding (HR-driven); not a digital credential but validates IAL for physical access | Physical identity proofing evidence for staff; does not provide a digital credential but confirms identity was proofed to DHS minimum standards |
| **Login.gov / id.me** | SAML/OIDC federation to Entra ID; federated session management; progressive authentication with inclusive fallbacks | Citizen identity at IAL2; authentication events logged and correlated; consent management and data minimization enforced |
| **Passport** | Indirect — as Login.gov adds passport-based proofing, the proofing event propagates via the Login.gov federation assertion to Entra ID | Higher-assurance citizen identity proofing (citizenship-verified); future: digital passport credentials via Login.gov |
| **NIST 800-63-4** | The framework that governs all of the above — IAL/AAL/FAL levels are the assurance metadata carried in the identity graph and used for Conditional Access policy decisions | Assurance-level metadata attached to every identity; drives risk-based access decisions |

**The architecture does not replace any of these regimes.** It provides the missing reconciliation layer — the identity graph that correlates credentials across regimes, enforces lifecycle events from the Source of Authority (HR for staff, CO/COR for contractors, citizen self-service for public users), and makes the combined identity state available as a real-time input to every trust decision in the fabric.

---

# SECTION B: NON-PERSON ENTITY ASSURANCE MODEL — Extending Identity-Forward to Machines

---

> **Placement: Insert in the Identity Layer section of the Layered Architecture, after "NAC and asset onboarding" and before the Addressing Layer. This section fills the gap that NIST 800-63-4 explicitly does not address.**

---

## 1. The NPE Identity Gap

NIST SP 800-63-4 (finalized August 2025) explicitly scopes itself to human users: "employees, contractors, or private individuals who interact with government information systems over networks." It does not cover machine identity, workload identity, service accounts, IoT devices, or any non-person entity (NPE). NIST 800-63-3 acknowledged this limitation and signaled intent to "support expanding the scope to include device identity, or machine-to-machine authentication in future revisions" — but 800-63-4 did not deliver that expansion.

This leaves the federal government with a critical asymmetry: **robust, standards-based assurance levels for human identity (IAL/AAL/FAL) and nothing equivalent for non-person entities** — despite the fact that NPEs now vastly outnumber human identities in every federal environment. Service accounts, managed identities, API keys, IoT devices, workload identities, and automated pipelines collectively represent the largest — and least governed — attack surface in any agency.

Academic research has proposed extending 800-63 to machines with constructs like Device Identity Assurance Level (DevIAL) and Device Authenticator Assurance Level (DevAAL), but NIST has not adopted these proposals.

The DoD's Zero Trust Implementation Guideline (January 2026) references "Non-Person Entity (NPE)" alongside "Person Entity (PE)" as requiring continuous authentication and authorization — signaling that the gap is recognized at the highest levels of federal cybersecurity policy.

---

## 2. NPE Taxonomy

Before defining assurance levels, the architecture must classify NPEs by type, because different NPE types require different identity proofing, credentialing, and lifecycle management approaches:

| NPE Type | Definition | Examples | Identity Authority (Source of Authority) | Credential Type |
|----------|-----------|---------|----------------------------------------|----------------|
| **Service Account** | A persistent identity used by an application or service to authenticate to other systems | AD service accounts, SQL Server service accounts, legacy batch job accounts | Application Owner (human sponsor) | Password (legacy), Kerberos ticket, managed identity token |
| **Managed Identity** | A cloud-native identity automatically provisioned and managed by the cloud platform | Azure Managed Identities, AWS IAM Roles for services, GCP Service Accounts | Application Owner + Cloud Platform | Platform-issued token (no credential to manage) |
| **Service Principal / App Registration** | An identity object representing an application in the identity provider | Entra ID App Registrations, Service Principals, OAuth client credentials | Application Owner (registered in Entra ID) | Client secret, client certificate, federated credential (SPIFFE) |
| **Workload Identity** | A cryptographically verifiable identity bound to a running workload at runtime | SPIFFE SVIDs (X.509 or JWT), Kubernetes ServiceAccount tokens, mTLS client certificates | Workload Orchestrator + Attestation Agent (SPIRE) | X.509 SVID, JWT SVID, or platform-issued token |
| **Device Identity** | An identity bound to a physical or virtual endpoint | Intune-enrolled device, TPM-attested machine, NAC-authenticated endpoint | Division IT / System Owner (procured and registered) | Device certificate (from ACME/PKI), TPM attestation, Intune compliance token |
| **IoT / OT Device** | A constrained or special-purpose device with limited identity capabilities | Sensors, cameras, HVAC controllers, building automation systems, medical devices | Facilities / OT Owner (human sponsor) | Manufacturer certificate (IDevID), locally significant certificate (LDevID), or NAC MAC-based authentication |
| **CI/CD Pipeline / Automated Process** | An ephemeral identity used during build, test, or deployment | GitHub Actions runners, Azure DevOps agents, Terraform execution contexts | DevSecOps team / Pipeline Owner | Short-lived token, SPIFFE SVID, OIDC federation token |

---

## 3. Non-Person Entity Assurance Levels (NPE-AL)

This model defines three assurance levels for NPEs, paralleling the human IAL/AAL framework but adapted for machine-specific identity proofing and credential binding:

### NPE-AL1: Self-Asserted / Unmanaged

| Dimension | Requirement |
|-----------|-------------|
| **Identity Proofing** | None. NPE identity is self-asserted or provisioned without verification against an authoritative source. |
| **Credential** | Shared secret, API key, static password, or bearer token. Credential is not bound to specific hardware or attested runtime. |
| **Lifecycle** | No formal lifecycle management. No human sponsor required. No automated deactivation. |
| **Trust Signal** | Identity cannot be independently verified. Trust is implicit (network location, firewall rule). |
| **Architecture Policy** | NPE-AL1 entities are permitted only in isolated dev/test environments with no access to production data, PII, or production identity systems. NPE-AL1 is NOT permitted in production. Any NPE-AL1 entity discovered in production triggers a ServiceNow incident and remediation workflow. |
| **Examples** | Legacy service accounts with shared passwords, hardcoded API keys, test environment bots |

### NPE-AL2: Validated / Managed

| Dimension | Requirement |
|-----------|-------------|
| **Identity Proofing** | NPE identity is registered in the authoritative identity system (Entra ID for service principals/managed identities; PKI for certificate-based identities). Registration includes: human sponsor identified and validated against HR/contractor authority chain; purpose and scope documented; ServiceNow asset/application record linked. |
| **Credential** | ACME-issued X.509 certificate with identity-bound SAN; managed identity platform token; or client certificate registered in Entra ID. No shared secrets. Credential is bound to a specific identity object and automatically rotated. |
| **Lifecycle** | Formal lifecycle: creation requires ServiceNow approval from human sponsor → Entra ID or PKI provisioning → periodic recertification (quarterly) → automatic deactivation if sponsor separates or recertification lapses. Orphan detection: any NPE without an active human sponsor is flagged within 5 business days. |
| **Trust Signal** | Identity is validated against CMDB/ServiceNow. Certificate attributes are ingested into the identity graph. Conditional Access policies evaluate NPE-AL2 entities with device compliance and network location signals. |
| **Architecture Policy** | NPE-AL2 is the **minimum for production workloads**. Required for: all service-to-service authentication, all API integrations, all managed endpoints, all agency-owned IoT/OT devices. mTLS required for all NPE-AL2 communications. |
| **Examples** | Production service accounts with managed identity credentials, Intune-enrolled devices with ACME certs, agency IoT devices with LDevID certificates |

### NPE-AL3: Hardware-Rooted / Attested

| Dimension | Requirement |
|-----------|-------------|
| **Identity Proofing** | All NPE-AL2 requirements PLUS: hardware attestation proving identity is bound to a specific physical or virtual trust anchor. For devices: TPM 2.0 attestation with endorsement key validation. For workloads: SPIFFE/SPIRE runtime attestation with verified selectors (kernel, Kubernetes namespace, container image hash). For HSMs/security appliances: manufacturer certificate (IDevID) validated against manufacturer trust anchor. |
| **Credential** | TPM-bound private key with ACME-issued certificate; SPIFFE X.509 SVID issued by SPIRE after workload attestation; or HSM-protected signing key with manufacturer provenance. Private key is non-exportable and hardware-protected. |
| **Lifecycle** | All NPE-AL2 lifecycle requirements PLUS: hardware attestation is continuous (not one-time). SPIRE re-attests workloads at SVID rotation (default: 1 hour). TPM health checks are continuous via Intune/Defender. Any attestation failure triggers immediate credential revocation and NAC quarantine. |
| **Trust Signal** | Hardware attestation provides cryptographic proof that the identity is running on approved hardware/software. SPIFFE trust domain is synchronized with the Entra ID identity graph — SPIFFE IDs are correlated to Entra ID service principals. Attestation status is a real-time input to Conditional Access and overlay routing decisions. |
| **Architecture Policy** | NPE-AL3 is **required for**: cross-agency service-to-service authentication; workloads handling PII or classified data; HSMs and root CA infrastructure; security appliances (firewalls, IDS/IPS, SIEM collectors); CI/CD pipelines deploying to production; any NPE participating in the overlay control plane (SD-WAN controllers, NSX managers, SPIRE servers). |
| **Examples** | TPM-attested endpoints accessing PII databases, SPIFFE-identified microservices in production Kubernetes clusters, HSMs protecting root CA keys, SD-WAN controller nodes with hardware-rooted identity |

---

## 4. NPE Assurance Level Comparison

| Dimension | NPE-AL1 | NPE-AL2 | NPE-AL3 |
|-----------|---------|---------|---------|
| Identity proofing | None | Registered + human sponsor | Registered + human sponsor + hardware attestation |
| Credential type | Shared secret / API key | ACME cert / managed identity | TPM-bound cert / SPIFFE SVID / HSM key |
| Credential binding | None (bearer) | Identity-bound (SAN) | Hardware-bound (non-exportable) |
| Rotation | Manual or never | Automated (ACME) | Automated + continuous attestation |
| Human sponsor | Not required | Required + recertified quarterly | Required + recertified quarterly |
| Orphan detection | None | 5-day flagging SLA | 5-day flagging SLA + immediate revocation on attestation failure |
| Production permitted | NO | YES (minimum) | YES (required for high-sensitivity) |
| mTLS required | No | Yes | Yes |
| Overlay trust | Not trusted | Trusted with Conditional Access | Trusted with hardware attestation signal |

---

## 5. SPIFFE/SPIRE Integration

SPIFFE (Secure Production Identity Framework for Everyone) is the emerging open standard for workload identity and is the recommended NPE-AL3 credential mechanism for cloud-native and containerized workloads in this architecture.

### How SPIFFE/SPIRE Fits the Architecture

| Architecture Component | SPIFFE/SPIRE Role |
|-----------------------|------------------|
| **Identity Layer** | SPIRE Server issues SPIFFE IDs (X.509 SVIDs) to workloads after runtime attestation. SPIFFE trust domain aligns with the agency's Entra ID tenant — every SPIFFE ID maps to an Entra ID service principal via a documented correlation table. |
| **PKI / ACME** | SPIRE can use the agency's ACME-managed CA as its upstream certificate authority, ensuring SPIFFE SVIDs chain to the same FPKI-anchored trust hierarchy as all other agency certificates. |
| **Overlay Layer** | SPIFFE SVIDs serve as the mTLS client certificate for workload-to-workload communication within the overlay. VXLAN/GENEVE encapsulations carry the SPIFFE ID as identity metadata alongside cert-bound conversation tokens. |
| **Conversation State Machine** | Workload conversations identified by SPIFFE ID maintain conversation continuity across container restarts, pod rescheduling, and horizontal scaling — the SPIFFE ID (not the ephemeral IP) is the stable identity anchor. |
| **Telemetry Layer** | SPIFFE IDs are logged in the conversation schema (replacing opaque service account names with cryptographically verifiable workload identities). Splunk/Sentinel correlation can trace a conversation from the human user's Entra ID identity through to the backend workload's SPIFFE ID. |
| **Policy / OPA** | Open Policy Agent (OPA) or Cedar policy engines evaluate SPIFFE IDs for fine-grained authorization — workload A (SPIFFE ID) can call workload B (SPIFFE ID) only if policy allows, with context from the identity graph. This replaces static network ACLs with identity-driven, policy-evaluated workload authorization. |

### SPIFFE/SPIRE Attestation Flow

```
1. Workload starts on compute (VM, container, serverless)
        ↓
2. SPIRE Agent on the node performs NODE ATTESTATION
   (validates the node's identity: AWS instance metadata, Azure IMDS,
    Kubernetes node token, TPM endorsement key)
        ↓
3. SPIRE Agent performs WORKLOAD ATTESTATION
   (validates the workload's identity: container image hash,
    Kubernetes namespace/service account, binary signature,
    kernel-level selectors)
        ↓
4. If attestation passes → SPIRE Server issues X.509 SVID
   (short-lived certificate, typically 1-hour TTL,
    automatically rotated before expiration)
        ↓
5. Workload uses SVID for mTLS authentication to other workloads
        ↓
6. Receiving workload validates SVID against SPIRE trust bundle
   (no shared secrets, no static credentials, no manual rotation)
        ↓
7. SVID attributes (SPIFFE ID, trust domain, expiry) logged
   in conversation schema → Splunk/Sentinel correlation
```

### Why SPIFFE/SPIRE Over Alternatives

| Approach | Limitation | SPIFFE/SPIRE Advantage |
|----------|-----------|----------------------|
| Static API keys / shared secrets | No identity proofing; no rotation; credential theft = full compromise | Runtime attestation; auto-rotation; non-exportable in hardware-backed mode |
| Kubernetes ServiceAccount tokens | Cluster-scoped only; no cross-cluster identity; JWT-based (not cert) | Cross-cluster, cross-cloud, cross-environment; X.509-based for mTLS |
| Cloud-native managed identities (Azure MI, AWS IAM Roles) | Cloud-specific; no cross-cloud interoperability; no workload attestation | Cloud-agnostic; works across Azure, AWS, GCP, on-prem, and hybrid; runtime attestation |
| Manual certificate management | Operationally unsustainable at scale; human error in rotation | Fully automated issuance, rotation, and revocation; no human in the loop |

---

## 6. NPE Assurance Model — Mapping to Architecture Layers

| Architecture Layer | NPE-AL1 Impact | NPE-AL2 Impact | NPE-AL3 Impact |
|-------------------|----------------|----------------|----------------|
| **Identity Layer** | Not registered in Entra ID | Registered in Entra ID with sponsor + ServiceNow record | Registered + attested + SPIFFE ID correlated |
| **Addressing Layer** | No identity-derived addressing | Identity-derived subnet/VLAN per workload classification | Identity-derived + attestation-derived micro-segmentation |
| **Overlay Layer** | Not permitted on overlay | mTLS with ACME cert; overlay carries NPE identity metadata | mTLS with SPIFFE SVID; overlay carries attestation status |
| **Telemetry Layer** | Unattributed traffic (blind spot) | All traffic attributed to named NPE identity | All traffic attributed + attestation-verified + SPIFFE ID in conversation schema |
| **Governance** | Compliance gap — unmanaged identity | ServiceNow lifecycle + quarterly recertification | ServiceNow lifecycle + continuous attestation + OPA policy enforcement |

---

## 7. Source of Authority Integration

The NPE Assurance Model extends the Source of Authority chain:

| NPE Type | Source of Authority | NPE-AL Requirement | Lifecycle Trigger |
|----------|--------------------|--------------------|------------------|
| Service Account (legacy) | Application Owner | Migrate to NPE-AL2 minimum; remediate to NPE-AL2 within 180 days of architecture deployment | Sponsor separation → deactivation; application decommission → deactivation |
| Managed Identity | Application Owner + Cloud Platform | NPE-AL2 (platform-managed credential) | Application lifecycle in ServiceNow |
| Service Principal | Application Owner | NPE-AL2 minimum; NPE-AL3 for cross-agency or PII-handling | Quarterly recertification; sponsor separation → deactivation |
| Workload (cloud-native) | Workload Owner + SPIRE Attestation | NPE-AL3 (SPIFFE SVID with runtime attestation) | Attestation failure → immediate revocation; workload decommission → SPIRE registration removal |
| Device (managed) | Division IT / System Owner | NPE-AL2 minimum (Intune + ACME cert); NPE-AL3 for sensitive environments (TPM attestation) | Device decommission → Intune wipe → cert revocation → InfoBlox address release |
| IoT / OT | Facilities / OT Owner | NPE-AL2 (LDevID + NAC); NPE-AL3 where hardware supports TPM | Device replacement → cert revocation; sponsor separation → access review |
| CI/CD Pipeline | DevSecOps Team / Pipeline Owner | NPE-AL3 (SPIFFE SVID for production deployment) | Pipeline decommission → SPIRE registration removal; deployment scope change → re-attestation |

---

## 8. Conditional Access Policy Integration

NPE assurance levels become a **Conditional Access signal** in Entra ID, just as IAL/AAL levels are for human identities:

| Policy Rule | Condition | Action |
|------------|-----------|--------|
| Production API access | NPE-AL < 2 | Block |
| PII database access | NPE-AL < 3 | Block |
| Cross-agency service call | NPE-AL < 3 | Block |
| Overlay control plane access | NPE-AL < 3 | Block |
| Dev/test environment access | NPE-AL = 1 | Allow (isolated environment only) |
| Standard production workload | NPE-AL ≥ 2 | Allow with mTLS required |
| High-sensitivity workload | NPE-AL = 3 + attestation = valid | Allow with mTLS + OPA policy evaluation |

---

*Section A should be inserted in the Paradigm Shift portion of the unified V4 document. Section B should be inserted in the Identity Layer of the Layered Architecture. Together, they close the two largest identity gaps in the current drafts: human identity fragmentation across federal regimes, and the complete absence of a non-person entity assurance framework.*


# ============================================================
# FILE 6 OF 6: V4U Unified Document Outline
# Maps to: Complete document blueprint
# ============================================================


# UNIFIED IDENTITY-ADDRESSING-OVERLAY ARCHITECTURE — V4U (Unified)
## Complete Document Outline with Section Sources and Placement Guide

---

# FRONT MATTER

## Document Control
- Version: V4U (Unified)
- Classification: CUI // FOUO (or as appropriate)
- Supersedes: V3 (Introduction to Unified Identity-Addressing-Overlay Architecture)
- Author / Sponsor
- Distribution list
- Revision history

## How to Read This Document
- Part I (Sections 1–5): WHY — Executive audience. Doctrine, diagnosis, mandates, business case. No technical prerequisites.
- Part II (Sections 6–8): WHAT — Architects and senior engineers. Canon, core model, authority chains.
- Part III (Sections 9–14): HOW — Implementation teams. Layered architecture, playbooks, telemetry, governance.
- Part IV (Sections 15–17): WHEN — Program managers. Roadmap, maturity model, reporting.
- Appendices: Reference material, crosswalks, glossary.

---

# PART I — STRATEGIC FRAME (Executive Audience)

---

## Section 1: Foreword and Core Thesis
**Source:** V4C (Copilot) Section 1–2 + V4P (Perplexity) Core Thesis
**Length target:** 2 pages

- 1.1 What this document is (cross-division modernization plan + engineering blueprint)
- 1.2 What this document supersedes (V3) and what changed (V3→V4 evolution from V4C Section 6)
- 1.3 Core Thesis: The federal government is structurally frozen at the Client/Server + L2–L4 perimeter era; identity-forward modernization is the only path forward
- 1.4 Public Interaction as the Agency's Core Mission (shared across all V4 drafts)
- 1.5 Design principle: "If it degrades the citizen interaction, it does not ship"

## Section 2: The Four Core Conditions
**Source:** V4C (Copilot) Sections 3, 7–11
**Length target:** 4 pages

- 2.1 The Modernization Reality (V4C Section 2)
- 2.2 The Missing Telemetry / Missing Location / Missing Dashboards Doctrine (V4C Section 3)
- 2.3 The Four Core Conditions defined:
  - Visibility (V4C Section 8: Identity, Asset, Workload, Boundary visibility)
  - Verification (V4C Section 9: Identity, Asset, Workload, Boundary verification)
  - Validation (V4C Section 10)
  - Control (V4C Section 11)
- 2.4 The Identity-Forward Frame (V4C Section 5) — identity as the organizing principle across all four conditions
- 2.5 Boundary Models (V4C Section 12) — Identity, Device, Workload, Data boundaries mapped to the four conditions

## Section 3: The Paradigm Shift — From Perimeter to Identity
**Source:** NEW (drafted in this conversation — Paradigm_Shift_and_Federal_Mandate_Crosswalk.md)
**Length target:** 6 pages

- 3.1 The Architecture Federal Agencies Actually Have (8-domain frozen state table)
- 3.2 The Architecture Every Federal Mandate Now Demands (8-domain mandated state table)
- 3.3 The Gap Is Structural — Not Incremental (5 reasons incremental patching fails)
- 3.4 **SIDEBAR: Cost of Inaction** (NEW — Cost_of_Inaction_Sidebar.md)
  - The Compliance Clock (OMB M-25-04, CISA BODs, DOJ Cyber-Fraud)
  - The Threat Landscape (credential breach statistics, $10.22M average cost)
  - Six Specific Consequences of Inaction
- 3.5 The Identity-Forward Modernization Context ("We are moving from 'the network tells us what to trust' to 'identity tells the network what to allow'")

## Section 4: Federal Mandate Crosswalk
**Source:** NEW (drafted in this conversation — Paradigm_Shift_and_Federal_Mandate_Crosswalk.md)
**Length target:** 8 pages

- 4.1 OMB M-22-09: Federal Zero Trust Strategy (9-requirement crosswalk table)
- 4.2 CISA Zero Trust Maturity Model v2.0 (all 5 pillars × 4 maturity stages, mapped to architecture)
- 4.3 NIST SP 800-63-4: Digital Identity Guidelines (7-requirement crosswalk)
- 4.4 NIST SP 800-207: Zero Trust Architecture (6-principle crosswalk)
- 4.5 EO 14028: Executive Order on Cybersecurity (6-requirement crosswalk)
- 4.6 TIC 3.0: Trusted Internet Connections (3 use cases mapped)
- 4.7 FedRAMP Rev 5 / NIST 800-53r5 (8 control families mapped)
- 4.8 Mandate Convergence Summary (5 non-negotiable shifts table)

## Section 5: Federal Identity Fragmentation
**Source:** NEW (drafted in this conversation — Federal_Identity_Fragmentation_and_NPE_Assurance_Model.md, Section A)
**Length target:** 3 pages

- 5.1 The Five Disconnected Identity Regimes (REAL ID, PIV/CAC, NIST 800-63-4, Login.gov/id.me, Passport — comparison table)
- 5.2 The Fragmentation Problem (no cross-regime lifecycle, no shared identity graph)
- 5.3 The Convergence Is Beginning (Login.gov passport/mDL/PIV acceptance roadmap)
- 5.4 How This Architecture Fills the Gap (Entra ID as the reconciliation layer consuming all five regimes)

## Section 5A: Private-Sector Comparison (2026 Reality Check)
**Source:** V4P (Perplexity) — Private-Sector Comparison section
**Length target:** 1 page

- 5A.1 Private sector executed multiple resets under market pressure
- 5A.2 Key gaps: 94%+ cloud vs. >50% federal legacy; full L5–L7 ZT vs. L2–L4; AI in production vs. pilots
- 5A.3 The 17-Point Canon is universal — market punishment forced the private sector to act; this architecture substitutes mission imperative

---

# PART II — ARCHITECTURAL FOUNDATIONS (Architect Audience)

---

## Section 6: The 17-Point Federal Modernization Canon
**Source:** V4P (Perplexity) — full Canon enumeration, all three tiers
**Enhancement:** Map each canon point to (a) which Core Condition it serves, (b) which mandate requires it
**Length target:** 10 pages

- 6.1 Canon overview and tier structure
- 6.2 **Tier 1 — Historical Foundations**
  - Point 1: Full history of compute (location of compute)
  - Point 2: Full history of networking
  - Point 3: Full history of cybersecurity
- 6.3 **Tier 2 — Federal Freeze and Structural Constraints**
  - Point 4: The Federal Freeze Point
  - Point 5: Bureaucratic layer overlays (org chart = architecture)
  - Point 6: Funding layer mismatch
  - Point 7: The L2–L4 vs. L5–L7 mismatch (core architectural failure)
- 6.4 **Tier 3 — Modern Requirements and Missing Control Planes**
  - Point 8: Telemetry and location as mandatory inputs
  - Point 9: Virtualized, application-driven networks (SASE/ZTNA)
  - Point 10: IAM, IPAM, Asset Management, Endpoint Management (new control planes)
  - Point 11: The Source-of-Truth Crisis
  - Point 12: AI as the Truth Engine
  - Point 13: Inter-Agency Truth Fabric
  - Point 14: The National Reset/Resync
  - Point 15: Legacy workload and application freeze
  - Point 16: Data as the new perimeter and data control plane
  - Point 17: The 1990s Risk-Model Event Horizon
- 6.5 **Canon-to-Conditions Mapping Table** (NEW — 17 rows × 4 columns: Visibility, Verification, Validation, Control)
- 6.6 **Canon-to-Mandate Mapping Table** (NEW — 17 rows × mandates: OMB, CISA ZTMM, 800-63-4, 800-207, EO 14028, TIC 3.0, FedRAMP)

## Section 7: Core Model — Fundamental Concepts
**Source:** V4G (Grok) + V4P (Perplexity) — merged, with V4P Canon point annotations
**Length target:** 4 pages

- 7.1 Conversation as the Atomic Unit (conversation = identity + certificate + addressing + overlay path + QoS + policy + telemetry)
- 7.2 Identity as Root Namespace (identity is not a lookup — it is the root of the entire namespace)
- 7.3 Deterministic Addressing (InfoBlox SSOT; addressing is a function of identity)
- 7.4 Certificate-Anchored Overlay (ACME PKI, mTLS, cert-bound tokens)
- 7.5 Telemetry as Control (not monitoring — active control input)
- 7.6 Governance and Automation (embedded in every workflow, not a layer above)
- 7.7 Public Service First (if it degrades the citizen interaction, it does not ship)

## Section 8: Source of Authority — The Chain of Authoritative Truth
**Source:** NEW (drafted in this conversation — Source_of_Authority_Section.md + Source_of_Authority_Location_InterAgency.md)
**Length target:** 10 pages

- 8.1 Why "Source of Authority" Is Different from "Source of Truth"
- 8.2 The Source of Authority Chain (6 original domains: Human Identity, NPE Identity, Contractor Identity, Citizen Identity, IP Addressing, Assets/Configuration, Data Classification)
- 8.3 HR-Driven Identity: The Most Critical Chain
  - HR → Identity Governance → Entra ID cascade diagram
  - JML workflow requirements (joiner-mover-leaver)
  - Separation SLA (60 minutes standard; immediate for adverse action)
  - Mover recertification (30-day window)
  - Contractor lifecycle bound to period of performance
  - Orphan detection (5-day resolution SLA)
  - FICAM and OMB alignment (M-19-17, M-22-09, FICAM ILM Playbook)
- 8.4 Source of Authority for Databases and Application Data
  - Authority chain per database type (HR, Case Management, Financial, Citizen PII, CMDB, Telemetry)
  - Key principle: every database has a named human/office authority
- 8.5 Buildings and Facilities: The Location Source of Authority
  - FRPP MS (GSA) — building-level authority (legally mandated)
  - Interior/sub-building gap — agency Space Management
  - Network infrastructure mapping — InfoBlox + DCIM
  - E911 dispatchable location dependency
  - PACS-to-identity integration opportunity
- 8.6 Federal-to-State Source of Authority Relationships
  - Four patterns (federal SoA/states consume; state SoA/federal consumes; shared authority; federal mandate/state implementation)
  - Legal instruments (IEA, ISA, CMA, IAA, MOU)
  - State Partner Onboarding Workflow (ServiceNow)
  - NIEM for semantic interoperability
- 8.7 Federal-to-Federal Source of Authority Relationships
  - FPKI Trust Fabric (FCPCA + FBCA — the one working cross-agency SoA)
  - Fragmentation in identity, addressing, telemetry, data, facilities
  - Enhanced Canon Point 13: Inter-Agency Truth Fabric grounded in legal instruments
- 8.8 Source of Authority Master Table (12 domains unified: Human, NPE, Contractor, Citizen, IP Addressing, Assets, Data Classification, Location-Building, Location-Interior, State Partner, Federal Partner, Credential Trust)
- 8.9 Mapping to Four Core Conditions
- 8.10 Mapping to Canon Points (5, 10, 11, 12, 13)

---

# PART III — LAYERED ARCHITECTURE AND OPERATIONS (Engineering Audience)

---

## Section 9: Identity Layer — Deterministic, Federated, Certificate-Anchored
**Source:** V4G (Grok) as skeleton + V4P Canon annotations + NEW NPE Assurance Model
**Length target:** 12 pages

- 9.1 FICAM / ICAM Alignment (V4G unique content)
  - Federal ICAM Architecture overview
  - Identity Assurance Level (IAL) 2/3 mapping
  - Authenticator Assurance Level (AAL) 2/3 mapping
  - Federation Assurance Level (FAL) 2/3 mapping
  - OMB M-19-17, CISA ZTMM Identity Pillar, GSA FICAM playbook alignment
  - NIST 800-63-4 updates (DIRM model, syncable passkeys, digital wallets, PAD for biometrics)
- 9.2 Entra ID and Directory Lineage
  - IAM, RBAC/ABAC, Conditional Access
  - Bidirectional sync with on-prem AD and vSphere SSO
  - Entra ID + InfoBlox alignment / separation of duties (V4G unique content)
- 9.3 PKI and ACME Automation
  - Automated issuance and rotation for user, machine, service, and overlay certs
  - Certificate attributes ingested into identity graph
  - FPKI trust chain alignment
- 9.4 mTLS and Cert-Bound Tokens
  - Mutual TLS for service-to-service and overlay authentication
  - Cert-bound conversation tokens for session continuity
- 9.5 MFA and Attestation
  - CAC/PIV for staff (AAL3)
  - FIDO2/WebAuthn for public portals and contractors (AAL2)
  - TPM attestation for devices
  - No exceptions policy
- 9.6 Citizen Identity Flows
  - Login.gov / id.me integration (SAML/OIDC federation to Entra ID)
  - RealID assertions (where lawful, with consent)
  - Passport-based proofing (Login.gov FY2026 roadmap)
  - Progressive authentication with inclusive fallbacks
  - Pseudonymized logging for CDM/CLAW
  - Consent management and data minimization
- 9.7 NAC and Asset Onboarding
  - NAC posture checks
  - ServiceNow asset registration and SAM handoffs
  - Intune replacing legacy HPAM
  - JIT privilege elevation
- 9.8 **Non-Person Entity Assurance Model (NEW)**
  - NPE taxonomy (7 types: service accounts, managed identities, service principals, workload identities, device identities, IoT/OT, CI/CD pipelines)
  - NPE-AL1 / NPE-AL2 / NPE-AL3 definitions and comparison
  - SPIFFE/SPIRE integration (architecture mapping, attestation flow, comparison to alternatives)
  - NPE-AL mapping to architecture layers
  - NPE Source of Authority integration (human sponsor chain)
  - Conditional Access policy integration for NPE-AL levels
  - Legacy service account remediation path (→ NPE-AL2 within 180 days)

## Section 10: Addressing Layer — InfoBlox SSOT Plus Native Cloud IPAMs
**Source:** V4G (Grok) + V4P Canon annotations
**Length target:** 3 pages

- 10.1 InfoBlox as SSOT (authoritative IPAM/DNS/DHCP; dynamic updates during VMotion/cloud bursting)
- 10.2 Native Cloud IPAM Reconciliation (Azure/AWS/GCP; API-driven reconciliation; conflict resolution; split-horizon DNS)
- 10.3 Public vs. Private Endpoints (MINR-aware SaaS routing; Private Link/Private Service Connect; InfoBlox coordination)
- 10.4 Identity-Derived Addressing (IP/subnet from identity attributes; deterministic segmentation)
- 10.5 Routing Hooks and QUIC (MINR telemetry, BGP/eBPF, ML path computation, TLS 1.3 resumption)

## Section 11: Overlay Layer — Certificate-Anchored Execution Substrate
**Source:** V4G (Grok) + V4P Canon annotations
**Length target:** 3 pages

- 11.1 SD-WAN / Catalyst (MINR ingestion, Cloud OnRamp, path diversity, FedRAMP deployment)
- 11.2 VMware NSX (identity-aware microsegmentation, VRF namespaces, legacy workload wrapping)
- 11.3 Encapsulation and Metadata (VXLAN/GENEVE carrying identity tokens, cert metadata, SPIFFE IDs)
- 11.4 Tunnel Authentication and Rotation (IPsec/IKEv2/TLS; ACME automation; sessionless rekeying)
- 11.5 SASE Enforcement (SWG, CASB, ZTNA, DLP at edge; data-as-the-new-perimeter implementation)
- 11.6 L7 Heuristics and ML (WebRTC/VoIP flow classification; AI truth engine meets overlay)

## Section 12: Conversation State Machine — Runtime Guarantees
**Source:** V4G (Grok) / V4P (Perplexity) — shared content
**Length target:** 2 pages

- 12.1 Atomic Unit definition (conversation = identity + cert + addressing + overlay + QoS + policy + telemetry)
- 12.2 Invariants (survive re-pathing, VMotion, cert rotation, policy updates without PII exposure or continuity break)
- 12.3 Mechanisms (cert-bound tokens, overlay checkpoints, identity graph reconciliation, telemetry-driven failover)
- 12.4 Legacy application continuity (NSX wrapping, VMotion tracking, split-horizon DNS fallback)

## Section 13: Telemetry, Observability, and Evidence Loop
**Source:** V4G (Grok) + V4P (Perplexity) — merged
**Length target:** 4 pages

- 13.1 Telemetry Sources (MINR, SD-WAN, Riverbed AppResponse, Riverbed NetProfiler, Microsoft Graph/CQD/Teams Admin Center, Defender, Azure Monitor, ThousandEyes, Splunk/Sentinel, ServiceNow)
- 13.2 Conversation Schema (normalized event model: ConversationID, Tenant, SourceIP, DestIP, OverlayPathID, MINRFrontDoorID, CQD_RTT_ms, PacketLoss_pct, AppResponseCaptureID, NetProfilerFlowID, SentinelIncidentID, ServiceNowTicketID, E911_DispatchableLocation, **SPIFFE_ID** [NEW])
- 13.3 Closed-Loop Evidence Model (Detect → Capture → Correlate → Remediate → Report)
  - Detailed from V4G evidence and reporting model (5-step)
  - Machine-speed response escaping the 1990s Risk-Model Event Horizon
- 13.4 Privacy and Sovereignty (pseudonymization, per-jurisdiction filters, PII field mapping, masking at ingestion)

## Section 14: Tools and Telemetry Inventory
**Source:** V4G (Grok) / V4P (Perplexity) — shared content
**Length target:** 2 pages

- 14.1 Network Observability (Riverbed AppResponse, NetProfiler, ThousandEyes)
- 14.2 Microsoft M365 Telemetry and Security (Graph, CQD, Teams Admin Center, Sentinel, Defender family, Azure Monitor, Power BI, Security Copilot)
- 14.3 Core Infrastructure (Entra ID, InfoBlox DDI, Catalyst SD-WAN, VMware NSX, ServiceNow, Splunk/Sentinel, Intune, ACME PKI, HSMs, **SPIRE** [NEW])
- 14.4 Security Stack (PAM, CASB, SWG, ZTNA, DLP, KMS, UEBA, NDR)
- 14.5 DevSecOps and Automation (Terraform/ARM/CloudFormation, OPA/Gatekeeper, CI/CD, IaC scanning, ServiceNow runbooks, SOAR playbooks)

---

# PART IV — IMPLEMENTATION AND MATURITY (Program Manager Audience)

---

## Section 15: Governance, Workflows, and Organizational Model
**Source:** V4G (Grok) — governance sections + V4P inter-agency federation governance
**Length target:** 4 pages

- 15.1 Cross-Division RACI (enterprise authority + division-scoped control) (Canon Point 5)
- 15.2 ServiceNow as Governance Backbone (IPAM/DNS, certs, IAM, NAC, SAM workflows)
- 15.3 Entitlement Governance (role mining, access certification, delegated admin, periodic reviews)
- 15.4 Legal and Privacy Controls (pseudonymization rules, RealID consent, per-jurisdiction filters, state onboarding attestation)
- 15.5 Dashboards and Reporting Tiers (division → enterprise → CISA/CDM → Congressional)
- 15.6 Inter-Agency Federation Governance (state onboarding workflow, peer agency federation, legal instruments)

## Section 16: Public Interaction Annex
**Source:** V4G (Grok) / V4P (Perplexity) — shared content
**Length target:** 3 pages

- 16.1 Purpose (citizen services as primary mission surface)
- 16.2 Public Interaction Dashboard (real-time SLAs, E911 accuracy, auth success rates, call center QoS, state-partner health)
- 16.3 Citizen Identity Flows (progressive auth, Login.gov/id.me, RealID opt-in, FIDO2, pseudonymized logging)
- 16.4 Public Endpoint Patterns (secure public + private default + split-horizon DNS)
- 16.5 Public Incident Playbook (containment, notification, PSAP coordination, state partner notification, post-incident audit)
- 16.6 Accessibility and Inclusion (fallback paths, assisted service, legal attestation)
- 16.7 E911 Dispatchable Location (FRPP + interior location SSOT + InfoBlox subnet mapping + PACS integration) [ENHANCED with Source of Authority location content]

## Section 17: Operational Playbooks
**Source:** V4G (Grok) — unique content (only V4G has these)
**Length target:** 4 pages

- 17.1 Controller Failover (automated detection, active/active failover, policy convergence, rollback, validation)
- 17.2 IPAM/DNS Failover (InfoBlox failover, cloud IPAM rollback, split-horizon validation, DNS TTL strategies)
- 17.3 Path Degradation / SLA Breach (MINR + SD-WAN re-pathing, ML path selection, AppResponse trigger, ServiceNow automation)
- 17.4 Identity Compromise (NAC containment, cert revocation, PAM JIT, identity graph reconciliation, post-incident audit)
- 17.5 NPE Attestation Failure (NEW — SPIRE attestation failure → SVID revocation → NAC quarantine → ServiceNow incident → sponsor notification → remediation)
- 17.6 State Partner Incident (NEW — cross-jurisdiction containment, per-IEA notification requirements, pseudonymized evidence sharing)

## Section 18: Implementation Roadmap — Prescriptive Phases
**Source:** V4P (Perplexity) Phase 0 + V4G (Grok) day-count phases
**Length target:** 4 pages

- 18.0 Phase 0: Canon Alignment (pre-pilot) [V4P unique] — Lock canon as strategic frame; brief leadership on freeze diagnosis + L2–L4 → L5–L7 gap; secure pilot authorization and funding
- 18.1 Phase 1: Discovery and Baseline (0–30 days) — Inventory all systems; run M365 Connectivity Tests; map current state to canon points; document freeze-point artifacts
- 18.2 Phase 2: Pilot Build (30–90 days) — Deploy AppResponse, NetProfiler, Catalyst SD-WAN edge, MINR, Graph/CQD, ServiceNow workflows, Splunk pipelines, Public-Interaction Dashboard, SPIRE pilot [NEW]
- 18.3 Phase 3: Validation and Resilience (90–120 days) — Conversation continuity tests, E911 simulations, VMotion/cloud bursting, chaos engineering, NPE-AL2 enforcement validation [NEW]
- 18.4 Phase 4: Scale and Harden (120–270 days) — ThousandEyes expansion, PAM rollout, SASE distribution, full IPAM/IAM reconciliation, SAM integration, ML tuning, SPIFFE/SPIRE production deployment [NEW]
- 18.5 Phase 5: Enterprise and Federate (270–540 days) — Multi-region controller fabric, federated state onboarding, Congressional reporting, legal review, NPE-AL3 enforcement for cross-agency services [NEW]

## Section 19: Rollout vs. Expansion Mapping
**Source:** V4G (Grok)
**Length target:** 1 page

- 19.1 Immediate Rollout Items (90–180 days) — Identity/PKI baseline, InfoBlox SSOT, SD-WAN/MINR, Riverbed pilot, telemetry, ServiceNow, Splunk/Sentinel, Public-Interaction Dashboard, runbooks, legal controls
- 19.2 Expansion Items (3–18 months) — ThousandEyes enterprise, full IPAM/IAM at scale, PAM/entitlement governance, SASE/ZTNA full, service mesh/container security, AIOps/ML, SAM + federated state onboarding, Congressional templates, SPIFFE/SPIRE at scale [NEW]

## Section 20: Evidence and Reporting Model
**Source:** V4G (Grok)
**Length target:** 1 page

- 20.1 Five-step model: Detect → Capture → Correlate → Remediate → Report
- 20.2 Mapping to ServiceNow, AppResponse, Splunk/Sentinel, Power BI, CLAW/CDM

## Section 21: Security, Privacy, and Compliance Guardrails
**Source:** V4G (Grok)
**Length target:** 2 pages

- 21.1 MFA for all access (people and machines)
- 21.2 PII sovereignty (per-jurisdiction pseudonymization, InfoBlox/overlay enforcement)
- 21.3 FIPS 140-3 validated crypto and HSMs
- 21.4 E911 proofs (InfoBlox + MINR + AppResponse → PSAP validation)
- 21.5 Auditability (every change ticketed in ServiceNow, correlated in Splunk)
- 21.6 NPE credential hygiene (no shared secrets in production, NPE-AL2 minimum) [NEW]

## Section 22: The Modernization Arc — Maturity Ladder
**Source:** V4C (Copilot) Sections 13–13.5
**Length target:** 3 pages

- 22.1 The Arc (not a project plan — a structural progression)
- 22.2 Five phases mapped to Core Conditions:
  - Discovery → establishes Visibility
  - Stabilization → establishes Verification
  - Alignment → establishes Validation
  - Transformation → establishes Control
  - Sustainment → continuous modernization
- 22.3 Mapping Arc phases to Implementation Roadmap phases (cross-reference to Section 18)
- 22.4 Mapping Arc phases to CISA ZTMM maturity stages (Traditional → Initial → Advanced → Optimal)

---

# APPENDICES

---

## Appendix A: Diagrams and Artifacts
- A.1 Unified Architecture Diagram (identity → addressing → overlay → conversation → governance/telemetry)
- A.2 Before-and-After Diagram (Client/Server + L2–L4 perimeter vs. Identity-Forward + L5–L7 fabric)
- A.3 Source of Authority Chain Diagram (HR → Identity Governance → Entra ID → all downstream systems)
- A.4 Conversation Data Flow (cert issuance → identity graph → overlay tokens → telemetry loop)
- A.5 SPIFFE/SPIRE Attestation Flow Diagram
- A.6 Federal Identity Regime Map (5 regimes → Entra ID reconciliation layer)
- A.7 Public Interaction Annex Visuals (dashboards, RealID flows, E911 mapping)
- A.8 90-Day Pilot Plan (call center cluster, AppResponse placements, ThousandEyes agents, Splunk ingestion, Microsoft license mapping)
- A.9 17-Point Canon Visual (Federal Glacier vs. Private Sector Rocket)

## Appendix B: Federal Mandate Crosswalk — Detailed Tables
- B.1 OMB M-22-09 full requirement crosswalk
- B.2 CISA ZTMM v2.0 full pillar × stage crosswalk
- B.3 NIST 800-63-4 full requirement crosswalk
- B.4 FedRAMP Rev 5 / 800-53r5 IA control family crosswalk
- B.5 EO 14028 requirement crosswalk
- B.6 TIC 3.0 use case crosswalk

## Appendix C: Source of Authority Master Reference
- C.1 Full 12-domain SoA table (from Section 8.8)
- C.2 HR-Driven Identity JML workflow specification
- C.3 State Partner Onboarding Workflow (ServiceNow)
- C.4 Federal Partner Federation Workflow
- C.5 NPE Lifecycle Management specification

## Appendix D: NPE Assurance Model Reference
- D.1 NPE-AL1 / AL2 / AL3 full specifications
- D.2 SPIFFE/SPIRE deployment guide
- D.3 Legacy service account remediation playbook
- D.4 NPE Conditional Access policy matrix

## Appendix E: Canon-to-Conditions Mapping Table
- 17 rows (canon points) × 4 columns (Visibility, Verification, Validation, Control) + mandate column

## Appendix F: Glossary (Canon-Locked)
**Source:** V4C (Copilot) glossary concept + all terms defined across V4G, V4P, V4C
- All architectural terms with precise definitions
- All acronyms
- Canon point cross-references

## Appendix G: Browser Context Metadata (Provenance)
**Source:** V4G (Grok) Appendix A / V3 Appendix A
- Reference provenance only

## Appendix H: Selected Verbatim Lines from Master Outline
**Source:** V4G (Grok) Appendix B / V3 Appendix B

---

# SECTION SOURCE TRACKING

| Section | Primary Source | Enriched By | New Content |
|---------|---------------|-------------|-------------|
| 1. Foreword | V4C + V4P | — | — |
| 2. Four Core Conditions | V4C | — | — |
| 3. Paradigm Shift | NEW | V4P freeze diagnosis | Cost of Inaction sidebar |
| 4. Mandate Crosswalk | NEW | — | Entire section |
| 5. Identity Fragmentation | NEW | — | Entire section |
| 5A. Private Sector Comparison | V4P | — | — |
| 6. 17-Point Canon | V4P | Canon mapping tables (NEW) | Mapping tables |
| 7. Core Model | V4G + V4P | Canon annotations | — |
| 8. Source of Authority | NEW | — | Entire section |
| 9. Identity Layer | V4G | V4P canon refs + FICAM 800-63-4 | NPE Assurance Model |
| 10. Addressing Layer | V4G | V4P canon refs | — |
| 11. Overlay Layer | V4G | V4P canon refs | SPIFFE in encapsulation |
| 12. Conversation State Machine | V4G / V4P | — | — |
| 13. Telemetry | V4G / V4P | — | SPIFFE_ID in schema |
| 14. Tools Inventory | V4G / V4P | — | SPIRE added |
| 15. Governance | V4G + V4P | — | — |
| 16. Public Interaction Annex | V4G / V4P | SoA location content | E911 enhancement |
| 17. Operational Playbooks | V4G | — | NPE + State Partner playbooks |
| 18. Implementation Roadmap | V4P Phase 0 + V4G phases | — | SPIFFE/NPE milestones |
| 19. Rollout vs. Expansion | V4G | — | SPIFFE at scale |
| 20. Evidence Model | V4G | — | — |
| 21. Security Guardrails | V4G | — | NPE credential hygiene |
| 22. Modernization Arc | V4C | — | ZTMM mapping |

---

# ESTIMATED DOCUMENT LENGTH

| Part | Sections | Estimated Pages |
|------|----------|----------------|
| Front Matter | Control + How to Read | 2 |
| Part I: Strategic Frame | 1–5A | 24 |
| Part II: Architectural Foundations | 6–8 | 24 |
| Part III: Layered Architecture + Operations | 9–14 | 26 |
| Part IV: Implementation + Maturity | 15–22 | 22 |
| Appendices | A–H | 20 |
| **TOTAL** | **22 sections + 8 appendices** | **~118 pages** |

---

*This outline is the complete blueprint for V4U. Every section has a named primary source, identified enrichments, and flagged new content. The Section Source Tracking table at the end ensures nothing from V4C, V4G, or V4P is lost, and every new section drafted in this conversation is placed.*
