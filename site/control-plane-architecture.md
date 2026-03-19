# Unified Identity-Addressing-Overlay Architecture - Control Plane Architecture

Canonical definitions for the six control planes that form the unified modernization architecture.

---

## Identity Control Plane

**Entra ID + ICAM + Zero Trust**

The authoritative identity control plane for the Unified Modernization Program

### Components


- **Microsoft Entra ID** — Primary Identity Provider


  - Conditional Access (CA)

  - MFA / SSPR

  - Identity Protection

  - Authentication Strength



- **ICAM Governance** — Identity governance and compliance


  - NIST 800-63 Alignment

  - OMB M-19-17 Compliance

  - Credentialing

  - Access Reviews

  - Privileged Identity Management (PIM)

  - Joiner/Mover/Leaver Automation



- **Zero Trust Policy Engine** — Continuous access evaluation


  - Identity + Device + Location + Risk

  - Continuous Access Evaluation (CAE)

  - Policy decisions exported to SD-WAN + Telemetry





### Core Responsibilities


### Integrations

Integrates with: network, addressing, telemetry


### Notes


- Identity is the first control plane in the modernization program

- All other planes consume identity signals

- Aligned to Zero Trust, TIC 3.0, and INR requirements



---

## Addressing Control Plane

**InfoBlox IPAM**

The authoritative source of truth for identity-anchored addressing, DNS, DHCP, and cross-cloud reconciliation

### Components


- **InfoBlox IPAM** — Authoritative Source of Truth


  - IP address allocation and tracking

  - Subnet creation and lifecycle management

  - DNS zone management and record authority

  - DHCP scope governance and lease evidence



- **DNS Management** — Authoritative DNS zones


  - Internal zones managed by InfoBlox

  - Split-horizon DNS

  - DNS evidence tied to identity/subnet/location



- **DHCP Management** — Scope governance


  - Scopes defined and owned by IPAM

  - Lease durations aligned with device identity

  - Automatic DNS record creation from DHCP leases



- **Cloud IPAM Reconciliation** — Multi-cloud addressing truth




### Core Responsibilities


- IP lifecycle: allocation > assignment > reclamation

- Authoritative DNS and DHCP services

- Cloud-native IPAM reconciliation

- Deterministic addressing for devices/workloads/apps

- Subnet ownership and segmentation alignment

- Emit addressing evidence to Telemetry Plane



### Integrations

Integrates with: identity, network, telemetry


### Notes


- InfoBlox is the single source of truth; cloud IPAMs are reconciled, not authoritative

- DNS and DHCP are identity and location evidence systems

- IP-to-location inference is foundational for Zero Trust, INR, and compliance



---

## Network Control Plane

**Cisco Catalyst SD-WAN (Viptela/vManage)**

A governed, identity-anchored, telemetry-driven routing and segmentation system

### Components


- **vManage** — Centralized policy engine


  - Pushes routing/segmentation/security policies to WAN edges

  - Integrates with identity and telemetry for INR



- **vSmart** — Control-plane orchestrator


  - OMP route distribution

  - Security and segmentation policy distribution



- **vBond** — Secure orchestration


  - Secure control-plane connections

  - WAN edge device authentication



- **WAN Edge Devices** — Enforcement points


  - Segmentation and routing enforcement

  - IPSEC/GRE overlay maintenance

  - Telemetry emission





### Core Responsibilities


### Integrations

Integrates with: identity, addressing, telemetry


### Notes


- SD-WAN is the orchestration substrate, not the source of truth

- INR is the convergence point where identity, telemetry, and routing unify

- TIC 3.0 compliance through identity-anchored routing and telemetry-driven governance



---

## Telemetry Control Plane

**Detection, diagnosis, governance, and automation**

The substrate of truth for detection, diagnosis, governance, and automation

### Components


- **Splunk / Sentinel** — Aggregation, correlation, compliance


- **Azure Monitor / CloudWatch** — Cloud-native telemetry


- **ThousandEyes / Riverbed** — Network path truth


- **InfoBlox** — DNS/DHCP/IPAM evidence


- **Defender / MINR** — Endpoint truth




### Core Responsibilities


- Collect, normalize, and correlate telemetry across all domains

- Tamper-proof storage for audit and compliance

- Real-time signals to Identity, Network, and Addressing planes

- Detect anomalies, drift, and misconfigurations

- Enable closed-loop automation and remediation

- Dashboards that express operational truth



### Integrations

Integrates with: identity, network, addressing, endpoint


### Notes


- Telemetry is the control plane that validates all other planes

- No signal is trusted unless correlated across identity, addressing, and network context

- Dashboards must express truth, not noise



---

## Endpoint Control Plane

**Identity-anchored, telemetry-driven device governance**

The identity-anchored, telemetry-driven governance layer for all devices

### Components


- **Defender / MINR** — Endpoint detection and response


- **Intune** — Configuration and compliance management


- **Entra ID Device Objects** — Device identity anchoring




### Core Responsibilities


- Device identity and compliance posture

- Configuration baselines and OS hardening

- Application control, patching, vulnerability remediation

- Emit endpoint telemetry to Telemetry Plane

- Provide device evidence to Identity and Network planes

- Support Zero Trust segmentation and INR



### Integrations

Integrates with: identity, network, addressing, telemetry


### Notes


- Endpoint identity is the foundation of Zero Trust

- No device is trusted unless identity-anchored, telemetry-visible, and policy-compliant



---

## Security Control Plane

**Zero Trust enforcement, validation, and assurance**

The enforcement, validation, and assurance substrate for Zero Trust across all systems, identities, networks, and workloads

### Components


### Core Responsibilities


- Authentication, authorization, and access control

- Zero Trust segmentation across identity, network, and endpoint

- Continuous risk evaluation and adaptive policy enforcement

- Threat detection and response using correlated telemetry

- Vulnerability management and attack-surface reduction

- Audit-ready evidence for compliance and governance



### Integrations

Integrates with: identity, network, addressing, telemetry, endpoint


### Notes


- Security Plane is the enforcement substrate that ties all other planes together

- All access, routing, and system behavior must be identity-anchored, policy-validated, and telemetry-verified



---


## Cross-Plane Integration Matrix

**Identity**: User identity | Device identity | App identity | Conditional Access posture | Risk signals

**Addressing**: IP-to-identity mapping | DNS evidence | Subnet classification | Location inference

**Network**: Routing decisions | Segmentation enforcement | Tunnel health | Path performance

**Telemetry**: Correlated evidence | Anomaly detection | Drift detection | Behavioral analysis

**Endpoint**: Device compliance | Health posture | Authentication evidence | Process metrics

**Security**: Zero Trust enforcement | Threat detection | Access control | Audit evidence
