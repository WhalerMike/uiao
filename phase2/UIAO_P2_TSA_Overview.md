# UIAO Phase 2 Target State Architecture

Id: UIAO_P2_TSA_001
Version: 0.1.0
Owner: UIAO Architecture
Phase: 2

## Description
Canonical target state architecture outline for UIAO Phase 2.

## Source Specifications
- UIAO_136
- Program Overview
- Entra ID Org Hierarchy Guide
- Phase 2 GOS
- HR Driven EntraID
- Choosing EntraID vs AD for SQL
- Operations Runbook

## Planes
### Identity and Directory Plane ($(System.Collections.Hashtable.Id))
Human, device, and workload identities; directory services; lifecycle and assurance.

### Endpoint and Server Plane ($(System.Collections.Hashtable.Id))
Client endpoints, servers, and hybrid assets including Arc-enabled resources.

### Access and Policy Plane ($(System.Collections.Hashtable.Id))
Conditional Access, Zero Trust policy overlay, and enforcement surfaces.

### Governance and Provenance Plane ($(System.Collections.Hashtable.Id))
Baselines, drift detection, provenance chain, and compliance evidence.

### Application and Integration Plane ($(System.Collections.Hashtable.Id))
Line-of-business apps, SaaS, LDAP-dependent apps, and modern auth integration.

### Network and Name Resolution Plane ($(System.Collections.Hashtable.Id))
DNS, named locations, and network-aware policy constructs.

## Lifecycles
### Human Identity Lifecycle ($(System.Collections.Hashtable.Id))
Joiner-Mover-Leaver lifecycle for human users driven by HR systems.

**Drivers**
- HR System
- Entra ID Governance
- Access Packages

**Key Flows**
- HR event -> Entra ID account provisioning
- Role or OrgPath change -> access re-evaluation
- Termination -> deprovisioning and access revocation

### Device Lifecycle ($(System.Collections.Hashtable.Id))
Enrollment, configuration, compliance, and retirement for endpoints and servers.

**Drivers**
- Intune
- Azure Arc
- OrgPath
- Compliance Policies

**Key Flows**
- Device enrollment -> OrgPath assignment -> policy targeting
- Compliance drift -> Conditional Access impact
- Server onboarding -> Arc enablement -> RBAC and telemetry

### Workload Identity Lifecycle ($(System.Collections.Hashtable.Id))
Service accounts, managed identities, and service principals.

**Drivers**
- Entra Workload Identities
- Managed Identity
- Service Principal

**Key Flows**
- Legacy service account -> workload identity mapping
- Credential rotation and secretless auth
- Decommissioning workloads and identities

### Policy and Baseline Lifecycle ($(System.Collections.Hashtable.Id))
Definition, rollout, monitoring, and adjustment of identity and device baselines.

**Drivers**
- OSCAL Baselines
- Governance Substrate
- Drift Detection

**Key Flows**
- Baseline definition -> deployment -> drift monitoring
- Drift detection -> remediation orchestration
- Baseline versioning and evidence capture

## Domains
### Identity and Directory ($(System.Collections.Hashtable.Id))
**Plane:** Identity and Directory Plane
Human identity, directory services, and identity assurance.

**Source State**
- Active Directory domains and forests
- X.500 OU trees
- AD security groups and distribution lists
- Kerberos/NTLM authentication
- LDAP-dependent applications

**Target State**
- Entra ID as primary identity provider
- OrgPath attributes and dynamic groups
- Administrative Units and scoped roles
- Modern auth (OAuth2/OIDC, SAML, CBA)
- Entra ID App Proxy and app registrations

**Key Transformations**
- X.500 OU Tree -> OrgPath Attributes + Dynamic Groups
- AD Security Groups -> Entra ID Groups
- OU-Scoped Delegation -> Administrative Units + Scoped Roles
- Kerberos/NTLM -> Modern Auth Protocols
- LDAP-Dependent Applications -> Entra ID App Proxy + SAML/OIDC

**Dependencies**
- LC_HUMAN
- LC_WORKLOAD
- LC_POLICY

### HR-Driven Provisioning ($(System.Collections.Hashtable.Id))
**Plane:** Identity and Directory Plane
HR-agnostic provisioning architecture for human identities.

**Source State**
- On-prem HR -> MIM -> AD
- Manual account creation
- Ticket-driven lifecycle changes

**Target State**
- Cloud HR connector (Workday or Oracle) -> Entra ID
- API-driven inbound provisioning
- Joiner-Mover-Leaver workflows in Entra ID Governance
- Attribute writeback to HR where required

**Key Transformations**
- On-prem HR -> MIM -> AD -> Entra Connect Sync -> Entra ID
- Cloud HR Connector -> Entra ID (Workday/Oracle)
- API-driven inbound provisioning for non-standard HR sources

**Dependencies**
- LC_HUMAN
- DOM_ID_DIR

### Device Identity and Compliance ($(System.Collections.Hashtable.Id))
**Plane:** Endpoint and Server Plane
Device identity, configuration, and compliance baselines.

**Source State**
- Domain-joined Windows clients
- GPO-based configuration and loopback processing
- On-prem servers without cloud projection

**Target State**
- Entra ID-joined or hybrid-joined devices
- Intune configuration profiles and compliance policies
- Azure Arc-enabled servers with managed identities
- Device posture integrated into Conditional Access

**Key Transformations**
- Computer Objects -> Entra ID Device Identity + Arc
- GPO -> Intune Configuration Profiles + Compliance Policies
- GPO Loopback -> Device-Targeted Policy
- GPO Admin Scoping -> Intune Scope Tags

**Dependencies**
- LC_DEVICE
- LC_POLICY
- DOM_ID_DIR

### Access and Conditional Policy ($(System.Collections.Hashtable.Id))
**Plane:** Access and Policy Plane
Conditional Access, Zero Trust enforcement, and policy overlay.

**Source State**
- Static firewall rules
- GPO security filtering
- One-time authentication decisions

**Target State**
- Conditional Access policies with device compliance requirements
- Policy Overlay with continuous evaluation
- Named locations and risk-based controls

**Key Transformations**
- Security Filtering -> Conditional Access
- Policy Overlay -> Continuous enforcement layer
- AD Sites & Subnets -> Named Locations + Conditional Access

**Dependencies**
- DOM_ID_DIR
- DOM_DEVICE
- DOM_NETWORK
- LC_POLICY

### Governance and Provenance ($(System.Collections.Hashtable.Id))
**Plane:** Governance and Provenance Plane
Baselines, provenance, and governance substrate.

**Source State**
- Manual CA/MFA/PIM policy management
- Email/ticket-based governance
- Manual device config review

**Target State**
- Entra ID Identity Baselines (UIAO_BL_001, BL_002)
- Endpoint Compliance Baselines (UIAO_BL_007, BL_008)
- Governance Substrate with SHA-256-linked provenance chain
- Automated drift detection and remediation orchestration

**Key Transformations**
- Identity Baselines -> Canonical OSCAL baselines with drift detection
- Endpoint Compliance Baselines -> Intune governance
- Governance Substrate -> Provenance chain and evidence generation

**Dependencies**
- LC_POLICY
- DOM_ID_DIR
- DOM_DEVICE

### Network and Name Resolution ($(System.Collections.Hashtable.Id))
**Plane:** Network and Name Resolution Plane
DNS, named locations, and hybrid network constructs.

**Source State**
- AD-integrated DNS
- On-prem-only name resolution
- AD Sites and Subnets

**Target State**
- Azure DNS / Hybrid DNS
- Named locations feeding Conditional Access
- Hybrid DNS orchestration

**Key Transformations**
- DNS (AD-Integrated) -> Azure DNS / Hybrid DNS
- AD Sites & Subnets -> Named Locations + Conditional Access

**Dependencies**
- DOM_ACCESS

### Application and Integration ($(System.Collections.Hashtable.Id))
**Plane:** Application and Integration Plane
Application identity, auth, and integration patterns.

**Source State**
- LDAP-bound applications
- SQL Server using Windows Auth and SQL Auth
- Apps bound to AD groups and OUs

**Target State**
- Entra ID app registrations and enterprise apps
- Entra ID auth for SQL Server 2022+
- Workload identity federation
- App Proxy for on-prem apps

**Key Transformations**
- SQL Server Authentication -> Entra ID Auth
- LDAP-Dependent Applications -> Entra ID App Proxy + SAML/OIDC
- AD Service Accounts -> Entra Workload Identities

**Dependencies**
- LC_WORKLOAD
- DOM_ID_DIR
- DOM_DEVICE
