---
document_id: UIAO_136
title: "Priority 1 Transformation Specs — Project Plans and Deliverable Inventories"
version: "0.2"
status: Draft
classification: CANONICAL
owner: Michael Stratton
boundary: GCC-Moderate
created_at: "2026-04-28"
updated_at: "2026-04-30"
parent: UIAO_135
---

# Priority 1 Transformation Specs — Project Plans & Deliverable Inventories

> **Purpose:** Full project plans, phased execution roadmaps, and comprehensive deliverable inventories for the three Priority 1 identity transformation domains identified in UIAO_135.

---

# SPEC 1: Computer Object Transformation — Domain-Joined → Cloud-Native Identity

## 1.1 Scope Statement

Transform all AD computer objects — workstations, laptops, kiosks, and servers — from domain-joined Active Directory identities to cloud-native Entra ID device identities with appropriate management plane (Intune for endpoints, Azure Arc for servers). Eliminate the dependency on AD computer object containers, machine Kerberos authentication, and GPO-based device policy.

### Object Classes In Scope

| Object Class | Current State | Target State | Management Plane |
|---|---|---|---|
| Windows Workstations | Domain-joined, GPO-managed | Entra ID joined, Intune-managed | Intune + Autopilot |
| Windows Laptops | Domain-joined or HAADJ | Entra ID joined, Intune-managed | Intune + Autopilot |
| Shared/Kiosk Devices | Domain-joined, shared login | Entra ID joined, shared device mode | Intune + Shared Device Config |
| Windows Servers (application) | Domain-joined, GPO-managed | Arc-enabled, Entra ID auth, RBAC | Azure Arc + Defender for Servers |
| Windows Servers (infrastructure — DC, ADFS, PKI) | Domain-joined, forest-critical | Retained in AD during coexistence; decommissioned last | AD (retained) → eventual decommission |
| Linux Servers | Standalone or LDAP-bound | Arc-enabled, Entra ID SSH auth | Azure Arc + SSH for Arc |
| Virtual Desktop (AVD/W365) | Domain-joined or HAADJ | Entra ID joined, Intune-managed | Intune + AVD/W365 service |

## 1.2 Phased Execution Plan

### Phase 1: Discovery & Assessment (Weeks 1–4)

**Objective:** Complete inventory of all computer objects, their dependencies, authentication patterns, and migration readiness.

| Deliverable | Description | Format |
|---|---|---|
| D1.1 — AD Computer Object Inventory | Full export of all computer objects from all AD domains/forests — DN, OS, OS version, last logon timestamp, OU path, managed-by, SPN list, BitLocker recovery keys present, LAPS password age | PowerShell script + JSON output |
| D1.2 — Device State Classification Matrix | Classify every device into: Active (logged in <90 days), Stale (90–180 days), Abandoned (>180 days), Infrastructure-Critical | Spreadsheet + Quarto dashboard |
| D1.3 — GPO-to-Device Dependency Map | For every GPO linked to computer OUs: which settings are device-targeted, which are user-targeted, which use loopback processing | CSV export from GPMC + analysis doc |
| D1.4 — Authentication Protocol Audit | Identify all computer objects using Kerberos constrained delegation, resource-based constrained delegation, NTLM fallback, or certificate-based machine auth | Defender for Identity report + PowerShell audit |
| D1.5 — Kerberos SPN Inventory (Computer Objects) | Every SPN registered on computer accounts — HTTP, MSSQLSvc, HOST, etc. — mapped to dependent services | PowerShell script + JSON |
| D1.6 — BitLocker & LAPS State Assessment | Current BitLocker key escrow location (AD vs. Entra), LAPS deployment state, LAPS password age, Windows LAPS vs. legacy LAPS | PowerShell audit + remediation checklist |
| D1.7 — Server Workload Dependency Matrix | For every server: services running, inbound/outbound auth dependencies, scheduled tasks with domain credentials, certificate bindings | Server inventory script + dependency graph |
| D1.8 — Network Topology & Site Mapping | AD Sites & Services export — map all subnets, site links, DC placement to inform Named Location strategy | ADSS export + network diagram |
| D1.9 — Migration Readiness Scorecard | Per-device readiness score based on: OS version, HAADJ capability, Intune enrollment state, GPO complexity, app dependencies | Quarto dashboard |

### Phase 2: Architecture & Pattern Definition (Weeks 3–6, overlaps Phase 1)

**Objective:** Define canonical migration patterns, coexistence rules, and target-state architecture.

| Deliverable | Description | Format |
|---|---|---|
| D2.1 — Device Identity Target State Architecture | Canonical diagram: Entra ID joined devices → Intune → Compliance → Conditional Access → OrgPath assignment → Dynamic Groups. Include all device types. | Architecture document + PlantUML diagram |
| D2.2 — Migration Pattern Catalog | Standardized patterns for each transition path: (a) Domain-joined → HAADJ → Entra joined (staged), (b) Domain-joined → Entra joined (wipe & re-provision via Autopilot), (c) Domain-joined server → Arc-enabled (in-place), (d) New device → Autopilot (greenfield) | Pattern specification document |
| D2.3 — OrgPath Device Assignment Specification | How OrgPath is stamped on device objects in Entra ID — which attribute (extensionAttribute, custom security attribute), population method (Intune compliance script, Autopilot profile, dynamic rule), inheritance from primary user vs. explicit assignment | Technical specification |
| D2.4 — GPO → Intune Policy Migration Map | Per-GPO mapping to Intune equivalent: Settings Catalog profile, Compliance Policy, Endpoint Security policy, or App Protection Policy. Flag GPOs with no Intune equivalent. | Migration matrix spreadsheet |
| D2.5 — Conditional Access Device Policy Framework | CA policies replacing domain-join trust: require compliant device, require Entra joined device, device filters for server vs. workstation, Named Locations replacing AD Sites | CA policy specification document |
| D2.6 — LAPS Migration Specification | Transition from legacy LAPS (AD-escrowed) to Windows LAPS (Entra ID-escrowed). Include: policy configuration, password rotation schedule, emergency access procedure, audit logging | Technical specification |
| D2.7 — BitLocker Key Escrow Migration Plan | Move BitLocker recovery key storage from AD to Entra ID. Validation procedure. Key rotation post-migration. | Migration runbook |
| D2.8 — Server Management Transition Architecture | Arc-enabled server management model: Entra ID RBAC roles (Virtual Machine Administrator Login, Virtual Machine User Login), Conditional Access for RDP/SSH, managed identity for Azure resource access, Defender for Servers integration | Architecture document + PlantUML |
| D2.9 — Coexistence Rules Document | Rules for the hybrid period: which devices can be HAADJ, when HAADJ → Entra join cutover happens, Entra Connect device sync scope, stale device cleanup cadence | Governance specification |
| D2.10 — Device Compliance Baseline (UIAO_BL_DVC_001) | Canonical Intune compliance policy baseline aligned to UIAO governance: OS version requirements, encryption required, firewall required, antivirus required, disk encryption, secure boot, TPM attestation | OSCAL-aligned baseline definition |

### Phase 3: Pilot Execution (Weeks 5–10)

**Objective:** Validate all patterns with controlled pilot groups before wave migration.

| Deliverable | Description | Format |
|---|---|---|
| D3.1 — Pilot Ring Definition | Define pilot groups: Ring 0 (IT staff, 10 devices), Ring 1 (early adopters, 50 devices), Ring 2 (business unit pilot, 200 devices). Include at least one server per ring. | Pilot plan document |
| D3.2 — Autopilot Profile Configuration | Autopilot deployment profiles for each device type: user-driven, self-deploying (kiosk), pre-provisioned (white glove). Include OrgPath tagging in ESP. | Intune configuration export |
| D3.3 — Intune Configuration Profile Package | All Settings Catalog profiles migrated from GPO, assigned to pilot dynamic groups, validated against D2.4 mapping | Intune configuration export + validation report |
| D3.4 — Arc Onboarding Automation | PowerShell/Azure Policy for Arc agent deployment to pilot servers. Include AADLoginForWindows extension deployment. Validate Entra ID RDP auth. | PowerShell scripts + Azure Policy definitions |
| D3.5 — Pilot Validation Test Plan | Test matrix: user login, app access, Conditional Access enforcement, compliance evaluation, BitLocker key escrow, LAPS password retrieval, VPN/network access, printer access, file share access | Test plan spreadsheet |
| D3.6 — Pilot Results Report | Findings from each ring: pass/fail per test case, issues encountered, workarounds applied, pattern modifications required | Assessment report |
| D3.7 — Application Compatibility Report | Applications that broke or degraded during device migration — root cause, remediation path, timeline | Compatibility matrix |

### Phase 4: Wave Migration & Cutover (Weeks 8–20+)

**Objective:** Execute migration in controlled waves; decommission AD computer objects post-validation.

| Deliverable | Description | Format |
|---|---|---|
| D4.1 — Wave Migration Schedule | Device migration waves by OrgPath segment, business unit, or location. Include rollback criteria per wave. | Project schedule |
| D4.2 — User Communication Package | Migration notifications, self-service instructions (Autopilot enrollment), FAQ, helpdesk escalation path | Communication templates |
| D4.3 — Stale Device Cleanup Runbook | Automated identification and disablement of stale AD computer objects (>180 days inactive). 30-day disable → 90-day delete. | PowerShell automation + runbook |
| D4.4 — AD Computer Object Decommission Procedure | Post-migration: disable AD computer account, move to Decommissioned OU, remove from all security groups, delete after retention period | Standard operating procedure |
| D4.5 — Server Migration Runbook (Per Server Type) | Step-by-step migration procedure for each server class: file server, print server, application server, database server, web server. Include pre/post validation checks. | Runbook per server type |
| D4.6 — Post-Migration Validation Dashboard | Continuous monitoring: device compliance %, Entra join success rate, Intune enrollment %, stale device count, LAPS coverage, BitLocker escrow coverage | Quarto dashboard |
| D4.7 — Domain Controller Dependency Tracker | Track remaining dependencies on domain controllers — DNS, LDAP, Kerberos, NTLM — as devices migrate. Target: zero workstation dependencies. | Dependency tracker spreadsheet |
| D4.8 — Migration Completion Certificate | Per-wave sign-off: all devices migrated, all GPOs deprecated, all computer objects decommissioned, validation tests passed | Sign-off document |

### Phase 5: Steady State & Governance (Ongoing)

| Deliverable | Description | Format |
|---|---|---|
| D5.1 — Device Lifecycle Governance Specification | Canonical rules: how new devices are provisioned (Autopilot only), how devices are retired (Intune wipe + Entra ID delete), OrgPath reassignment on user transfer | Governance specification |
| D5.2 — Device Drift Detection Rules | OSCAL-aligned rules for detecting device configuration drift: non-compliant devices, unenrolled devices, stale registrations, missing LAPS | Drift detection rule set |
| D5.3 — Quarterly Device Posture Report Template | Template for ongoing reporting: compliance %, enrollment %, OS currency, security baseline adherence | Report template |

**Total Deliverables: 30**

---

# SPEC 2: HR-Agnostic Provisioning Architecture — Canonical Identity Lifecycle Pattern

## 2.1 Scope Statement

Define the UIAO canonical pattern for HR-driven identity provisioning that operates independently of the HR source system (Workday, Oracle, SAP, or any future system selected by OPM). The architecture must support the full Joiner-Mover-Leaver (JML) lifecycle, populate OrgPath from HR organizational data, and work across both cloud-only and hybrid (AD coexistence) environments.

### Design Constraints

| Constraint | Rationale |
|---|---|
| HR-system-agnostic | OPM procurement decision pending (Workday vs. Oracle); architecture must not depend on either |
| API-driven inbound provisioning as canonical path | Microsoft Graph API is the universal interface; native connectors are optimizations, not requirements |
| OrgPath as mandatory output | Every provisioned identity must have OrgPath populated from HR organizational hierarchy |
| Coexistence-aware | Must support provisioning to both Entra ID (cloud) and on-prem AD (via provisioning agent) during transition |
| Governance-integrated | All provisioning events must produce auditable provenance records for UIAO Governance OS |

## 2.2 Phased Execution Plan

### Phase 1: HR Data Model Analysis & Mapping (Weeks 1–4)

**Objective:** Define the canonical HR-to-Identity attribute mapping regardless of HR source system.

| Deliverable | Description | Format |
|---|---|---|
| D1.1 — Canonical HR Attribute Schema | Define the minimum set of HR attributes required for identity provisioning: Employee ID, First Name, Last Name, Display Name, Email, Department, Division, Job Title, Manager Employee ID, Hire Date, Termination Date, Worker Type (employee/contractor/intern), Location Code, Cost Center, Organization Code (for OrgPath derivation) | Schema specification (YAML/JSON Schema) |
| D1.2 — HR-to-OrgPath Translation Rules | Define how HR organizational hierarchy fields (Department, Division, Location, Cost Center) map to the canonical OrgPath format (CORP/REGION/STATE/CITY/DEPT). Include rules for multi-level hierarchy flattening. | Mapping rules specification |
| D1.3 — Attribute Mapping Matrix (HR → Entra ID) | Complete mapping of HR attributes to Entra ID user properties: userPrincipalName, mail, displayName, department, jobTitle, manager, employeeId, extensionAttributes (OrgPath), employeeType, accountEnabled, usageLocation | Mapping matrix spreadsheet |
| D1.4 — Attribute Mapping Matrix (HR → On-Prem AD) | Complete mapping of HR attributes to AD user properties for coexistence period: sAMAccountName, distinguishedName (OU placement), userPrincipalName, displayName, department, title, manager (DN), employeeID, extensionAttributes | Mapping matrix spreadsheet |
| D1.5 — UPN Generation Rules | Canonical rules for generating userPrincipalName from HR data: first.last@domain.com, conflict resolution (append number), name change handling (legal name change, marriage), preferred name vs. legal name | Business rules specification |
| D1.6 — Worker Type Classification Taxonomy | Define all worker types and their provisioning implications: Full-Time Employee, Part-Time Employee, Contractor, Intern, Volunteer, Vendor, External Collaborator. Map each to: license assignment, group membership, access scope, retention period | Classification document |
| D1.7 — HR Source System Connector Comparison | Technical comparison of Workday connector, Oracle HCM connector, SAP SuccessFactors connector, and API-driven inbound provisioning. Feature parity matrix. Identify any capabilities unique to native connectors vs. API-driven. | Comparison matrix |
| D1.8 — HR Data Quality Requirements | Define minimum data quality standards for HR feed: required fields, validation rules, allowed values, referential integrity (manager must exist before direct report), data freshness SLA | Data quality specification |

### Phase 2: Lifecycle Workflow Design (Weeks 3–8)

**Objective:** Define the complete Joiner-Mover-Leaver workflow with all branching logic, error handling, and governance integration.

| Deliverable | Description | Format |
|---|---|---|
| D2.1 — Joiner Workflow Specification | Complete joiner workflow: trigger conditions (hire date = today or pre-hire window), attribute population sequence, UPN generation, OrgPath assignment, OU placement (AD coexistence), group membership assignment, license assignment, manager link, welcome notification trigger. Include pre-hire vs. day-of-hire vs. post-hire timing. | Workflow specification + PlantUML sequence diagram |
| D2.2 — Mover Workflow Specification | Complete mover workflow: trigger conditions (department change, title change, location change, manager change, worker type change), attribute update sequence, OrgPath recalculation, dynamic group membership cascade, access review trigger, license reassignment (if tier changes), notification to old/new manager | Workflow specification + PlantUML sequence diagram |
| D2.3 — Leaver Workflow Specification | Complete leaver workflow: trigger conditions (termination date = today or pre-term window), account disable sequence (disable → sign out all sessions → revoke refresh tokens → remove from groups → archive mailbox → convert to shared mailbox → retain for litigation hold → delete after retention), OrgPath preservation for audit trail, manager reassignment of direct reports, delegated access cleanup | Workflow specification + PlantUML sequence diagram |
| D2.4 — Rehire Workflow Specification | Rehire handling: match on Employee ID, reactivate vs. create new, attribute refresh, OrgPath reassignment, license reassignment, access review, manager notification | Workflow specification |
| D2.5 — Conversion Workflow Specification | Contractor-to-employee conversion (and reverse): worker type change trigger, attribute remapping, license tier change, group membership overhaul, access scope change, OrgPath recalculation | Workflow specification |
| D2.6 — Error Handling & Quarantine Specification | Error scenarios: missing required attributes, UPN conflict, manager not found, invalid department code, HR data integrity failure. Quarantine queue design. Manual remediation workflow. Escalation paths. SLA for quarantine resolution. | Error handling specification |
| D2.7 — Pre-Hire Provisioning Window Specification | Define timing: how many days before start date should account be created? Which attributes are populated at pre-hire vs. day-of-hire? When does the account become enabled? When does license assignment occur? | Timing specification |
| D2.8 — Provisioning Scope Filter Rules | Define which HR records are in scope for provisioning: include/exclude by worker type, location, department, employment status. Handle edge cases: LOA (leave of absence), sabbatical, secondment, internship end dates | Scoping rules specification |

### Phase 3: Technical Architecture (Weeks 5–10)

**Objective:** Define the technical implementation architecture for the HR-agnostic provisioning pipeline.

| Deliverable | Description | Format |
|---|---|---|
| D3.1 — API-Driven Inbound Provisioning Architecture | Canonical architecture diagram: HR System → Middleware/Integration Layer → Microsoft Graph bulkUpload API → Entra ID Provisioning Service → Entra ID (cloud) + Provisioning Agent → On-Prem AD (coexistence). Include: authentication flow, retry logic, rate limiting, payload format. | Architecture document + PlantUML |
| D3.2 — Integration Middleware Specification | Define the middleware layer that normalizes HR data from any source into the canonical schema (D1.1). Options: Azure Logic Apps, Azure Functions, Power Automate, custom microservice. Include: input validation, schema transformation, error handling, logging. | Technical specification |
| D3.3 — Provisioning Agent Deployment Architecture | On-prem provisioning agent deployment for AD writeback: HA configuration (2+ agents), network requirements, service account (gMSA), AD permissions required (Create/Delete/Modify user objects in designated OUs), monitoring | Deployment architecture |
| D3.4 — Attribute Mapping Engine Configuration | Entra ID provisioning app attribute mapping configuration: expression-based mappings, constant values, direct mappings, function-based transformations (Switch, Join, Replace, ToUpper). Include OrgPath calculation expression. | Configuration specification + export |
| D3.5 — OrgPath Population Pipeline | End-to-end specification: HR org hierarchy → middleware → OrgPath calculation → extensionAttribute/custom security attribute write → dynamic group membership cascade → policy assignment cascade | Pipeline specification |
| D3.6 — Writeback Specification | Attributes written back from Entra ID to HR system (if supported): email address, UPN, phone number. Attributes written from Entra ID to on-prem AD: all mapped attributes during coexistence. | Writeback specification |
| D3.7 — Monitoring & Alerting Configuration | Provisioning logs → Azure Monitor → alerts for: provisioning failures, quarantine threshold exceeded, sync cycle failures, agent offline, attribute mapping errors. Dashboard for provisioning health. | Monitoring specification + dashboard design |
| D3.8 — Data Flow Security Assessment | Security review: data in transit (TLS 1.2+), data at rest (HR PII handling), least-privilege API permissions (User.ReadWrite.All scope), conditional access for provisioning service principal, audit logging | Security assessment document |

### Phase 4: Testing & Validation (Weeks 8–14)

| Deliverable | Description | Format |
|---|---|---|
| D4.1 — Test HR Data Set | Synthetic HR data set covering all scenarios: new hire, termination, department transfer, manager change, name change, rehire, contractor conversion, LOA, multiple positions. Minimum 500 records. | JSON/CSV test data |
| D4.2 — Integration Test Plan | Test matrix: every JML scenario × every worker type × cloud-only and hybrid target. Include negative tests: bad data, duplicate employee IDs, circular manager references. | Test plan spreadsheet |
| D4.3 — Performance & Scale Test Plan | Load testing: bulk provisioning (1,000+ records), incremental sync cycle time, provisioning agent throughput, API rate limit behavior, recovery after agent outage | Performance test plan |
| D4.4 — UAT Acceptance Criteria | User acceptance test criteria per scenario: correct UPN, correct OrgPath, correct group membership, correct license, correct manager link, account enabled on correct date, account disabled on correct date | Acceptance criteria document |
| D4.5 — Validation Report | Results from all test phases: pass/fail per scenario, defects found, remediations applied, performance metrics | Test results report |

### Phase 5: Cutover & Steady State (Weeks 12–20+)

| Deliverable | Description | Format |
|---|---|---|
| D5.1 — Production Cutover Runbook | Step-by-step production deployment: middleware deployment, provisioning app configuration, agent deployment, initial full sync, incremental sync enablement, legacy provisioning decommission | Cutover runbook |
| D5.2 — Legacy Provisioning Decommission Plan | Plan to shut down existing manual/MIM/FIM provisioning after API-driven pipeline is validated. Include: parallel run period, comparison reconciliation, final cutover, decommission sign-off | Decommission plan |
| D5.3 — Provisioning Governance Specification | Ongoing governance: provisioning log retention (7 years for compliance), quarterly access review of provisioning service principal permissions, annual attribute mapping review, OrgPath hierarchy change management | Governance specification |
| D5.4 — HR System Onboarding Playbook | Playbook for connecting a new HR system (when OPM selects Workday or Oracle): steps to configure native connector or middleware adapter, attribute mapping validation, test cycle, parallel run, cutover | Onboarding playbook |
| D5.5 — Provisioning Drift Detection Rules | OSCAL-aligned rules: orphaned accounts (no matching HR record), zombie accounts (terminated in HR but active in Entra), attribute drift (Entra values != HR values), OrgPath staleness | Drift detection rule set |
| D5.6 — Provisioning Health Dashboard | Ongoing monitoring dashboard: provisioning success rate, quarantine count, sync cycle duration, attribute drift count, orphaned account count | Quarto dashboard |

**Total Deliverables: 33**

---

# SPEC 3: Service Account → Workload Identity Mapping — The Hidden Landmine

## 3.1 Scope Statement

Discover, classify, and systematically migrate every Active Directory service account to the appropriate Entra ID workload identity type. This is the most risk-laden transformation in the AD modernization program because service accounts have invisible dependency chains, embedded credentials, and undocumented trust relationships that, if disrupted, cause silent application failures.

### Risk Statement

Service accounts are the hidden load-bearing walls of AD infrastructure. Unlike user accounts, they:
- Have no human owner who notices when they break
- Often have credentials embedded in scripts, config files, scheduled tasks, and application databases
- Frequently have elevated privileges accumulated over years with no access review
- May use Kerberos constrained delegation chains that span multiple services
- Are rarely documented and often outlive the person who created them

### Target Identity Types

| Source (AD) | Target (Entra ID) | When to Use |
|---|---|---|
| User account running as service (password never expires, SPN set) | Managed Identity (system-assigned) | Workload runs in Azure (VM, App Service, Function, AKS) |
| User account running as service | Managed Identity (user-assigned) | Workload in Azure, shared identity across multiple resources |
| gMSA (Group Managed Service Account) | Managed Identity or retain gMSA | Azure-hosted → Managed Identity; on-prem Windows service → retain gMSA |
| sMSA (Standalone Managed Service Account) | gMSA (interim) → Managed Identity (final) | Upgrade to gMSA first for password management, then migrate to MI when workload moves to cloud |
| Service account for external platform (GitHub Actions, Jenkins, Terraform) | Workload Identity Federation | External platform with OIDC issuer — eliminates all secrets |
| Service account for application auth (API calls, Graph API) | App Registration + Service Principal (certificate auth) | Application needing programmatic access to Entra ID / Microsoft Graph |
| Service account for SQL Server | Entra ID authentication (Managed Identity via Arc) | SQL Server 2022+ with Entra ID auth support |
| Scheduled Task credentials | Managed Identity (Azure Automation) or gMSA (on-prem) | Scheduled tasks → Azure Automation runbooks (cloud) or gMSA (on-prem during coexistence) |

## 3.2 Phased Execution Plan

### Phase 1: Discovery & Inventory (Weeks 1–6)

**Objective:** Find every service account, every credential, every dependency. This phase is intentionally longer because undiscovered accounts are the primary risk.

| Deliverable | Description | Format |
|---|---|---|
| D1.1 — Automated Service Account Discovery Scan | Deploy Defender for Identity service account discovery. Supplement with PowerShell: query all accounts with SPN set, password never expires, or "service" in name/description. Query all gMSAs and sMSAs. | PowerShell scripts + JSON inventory |
| D1.2 — Scheduled Task Credential Audit | Scan all servers for scheduled tasks running under domain accounts: task name, run-as account, last run time, trigger schedule, action (script path, executable). Include SCCM task sequences. | PowerShell script + CSV output |
| D1.3 — Windows Service Credential Audit | Scan all servers for Windows services running under domain accounts (not LocalSystem/NetworkService/LocalService): service name, display name, run-as account, startup type, binary path. | PowerShell script + CSV output |
| D1.4 — IIS Application Pool Identity Audit | Scan all IIS servers for app pools running under domain accounts: app pool name, identity type, domain account, associated websites, authentication configuration (Windows/Anonymous/Forms) | PowerShell script + CSV output |
| D1.5 — COM+/DCOM Application Identity Audit | Scan for COM+ applications and DCOM configurations with explicit domain account identities | PowerShell script + CSV output |
| D1.6 — Kerberos Delegation Chain Map | Map all constrained delegation (KCD) and resource-based constrained delegation (RBCD) configurations: source SPN → target SPN → delegated service. Build full delegation chain graph. | PowerShell audit + graph visualization (Graphviz) |
| D1.7 — SPN Collision & Duplication Report | Identify duplicate SPNs, orphaned SPNs (SPN registered but service doesn't exist), SPNs on wrong accounts | PowerShell script + remediation checklist |
| D1.8 — Embedded Credential Scan | Scan for credentials embedded in: PowerShell scripts (.ps1), batch files (.bat/.cmd), config files (.config, .xml, .json, .ini), connection strings, registry values. Flag files containing plaintext passwords or encoded credentials. | Credential scanner script + findings report |
| D1.9 — Service Account Privilege Audit | For every discovered service account: group memberships (especially Domain Admins, Enterprise Admins, local Administrators), ACL permissions on file shares/registry/AD objects, SQL Server roles | Privilege audit report |
| D1.10 — Service Account Owner Assignment | Attempt to assign an owner to every service account: check description field, creation date/creator, managed-by attribute, associated application team. Flag unowned accounts as critical risk. | Owner assignment matrix |
| D1.11 — Service Account Authentication Pattern Analysis | For each account: authentication frequency (last 30/90/180 days from DC security logs), source IPs, target resources, authentication protocol (Kerberos/NTLM), success/failure ratio | Authentication analytics report |
| D1.12 — Service Account Risk Classification | Classify every account: Critical (domain admin or delegation chain, no owner), High (elevated privileges, owner known), Medium (standard privileges, documented), Low (read-only, documented, gMSA) | Risk-classified inventory spreadsheet |

### Phase 2: Migration Target Architecture (Weeks 4–8)

**Objective:** Define the migration target for each service account class and the canonical patterns for each target type.

| Deliverable | Description | Format |
|---|---|---|
| D2.1 — Workload Identity Decision Tree | Flowchart: Is workload in Azure? → Managed Identity. External platform with OIDC? → Workload Identity Federation. Needs Graph/M365 API? → App Registration + cert. On-prem Windows service? → gMSA (retain). On-prem scheduled task? → gMSA or Azure Automation. | Decision tree document + PlantUML |
| D2.2 — Managed Identity Pattern Specification | Canonical pattern: system-assigned MI (lifecycle tied to resource) vs. user-assigned MI (shared across resources). When to use each. RBAC role assignment. Conditional Access for workload identities. Token lifetime. | Pattern specification |
| D2.3 — Service Principal + Certificate Auth Pattern | Canonical pattern: App Registration → certificate credential (not secret) → RBAC assignment → Conditional Access workload identity policy. Certificate rotation procedure. Monitoring for expiring certificates. | Pattern specification |
| D2.4 — Workload Identity Federation Pattern | Canonical pattern for each external platform: GitHub Actions (OIDC issuer config, subject claim mapping), Terraform Cloud, Jenkins, Kubernetes (non-AKS). Eliminates all stored secrets. | Pattern specification per platform |
| D2.5 — gMSA Retention & Hardening Specification | For accounts remaining as gMSA during coexistence: password rotation policy (default 30 days), KDS root key management, gMSA security group scope, monitoring for gMSA password retrieval | Hardening specification |
| D2.6 — Kerberos Delegation Replacement Architecture | Replace KCD chains with: App Proxy (for web apps), Entra ID authentication (for SQL), Managed Identity token exchange (for Azure resources). Map each existing delegation chain to replacement pattern. | Architecture document + migration matrix |
| D2.7 — Scheduled Task Migration Architecture | Migration patterns: (a) Azure Automation Runbook (cloud execution), (b) Azure Functions Timer Trigger (lightweight cloud), (c) gMSA-backed task (on-prem retention), (d) Intune remediation script (endpoint tasks). Decision criteria for each. | Architecture document |
| D2.8 — Secret Elimination Roadmap | Phased plan to eliminate all stored secrets: Phase A — inventory all secrets, Phase B — migrate to certificate auth, Phase C — migrate to Managed Identity, Phase D — migrate to Workload Identity Federation. Target: zero stored passwords. | Roadmap document |
| D2.9 — Workload Conditional Access Policy Framework | CA policies for workload identities: restrict token issuance to known IP ranges, require compliant network location, block from untrusted locations. Apply to service principals and managed identities. | CA policy specification |
| D2.10 — Workload Identity Monitoring Specification | Monitoring requirements: anomalous sign-in detection for service principals, token usage patterns, credential expiry alerts, unused workload identity detection, privilege escalation detection | Monitoring specification |

### Phase 3: Migration Execution (Weeks 6–20)

**Objective:** Systematically migrate service accounts from lowest to highest risk.

| Deliverable | Description | Format |
|---|---|---|
| D3.1 — Migration Wave Plan | Waves ordered by risk: Wave 0 (new/greenfield — use MI from start), Wave 1 (Low risk — documented, gMSA, read-only), Wave 2 (Medium — standard privileges, owner known), Wave 3 (High — elevated, complex dependencies), Wave 4 (Critical — domain admin, delegation chains, unknown owners) | Wave plan document |
| D3.2 — Per-Account Migration Runbook Template | Template for each migration: pre-migration validation, credential swap procedure, parallel-run validation, rollback procedure, post-migration monitoring, AD account disable, AD account delete | Runbook template |
| D3.3 — Parallel Run Validation Framework | Framework for running old (AD service account) and new (workload identity) simultaneously: how to validate both are working, how to switch traffic, how to detect failures, how long to parallel-run per risk tier | Validation framework |
| D3.4 — Credential Rotation Automation | Automation for certificate rotation on service principals: Azure Key Vault integration, certificate auto-renewal, notification pipeline for expiring credentials, emergency rotation procedure | PowerShell/Azure Automation scripts |
| D3.5 — Delegation Chain Migration Runbooks | Specific runbooks for each identified Kerberos delegation chain: document the chain, identify replacement pattern, implement replacement, validate, remove old delegation, decommission old SPN | Per-chain runbooks |
| D3.6 — Embedded Credential Remediation Tracker | Track remediation of every embedded credential found in D1.8: file path, credential type, remediation action (replace with MI, move to Key Vault, use certificate), remediation status, verification | Tracker spreadsheet |
| D3.7 — Application Team Coordination Package | Communication package for each application team whose service account is being migrated: what's changing, what they need to do, timeline, testing requirements, escalation path | Communication templates |
| D3.8 — Migration Validation Test Suite | Automated test suite per migration: can the workload authenticate? Can it access all required resources? Are all dependent services still functional? Are audit logs recording correctly? | Test scripts + results |
| D3.9 — Emergency Rollback Procedures | Per-account rollback: re-enable AD service account, restore SPN, revert application configuration. Include RTO/RPO targets per risk tier. | Rollback runbook |

### Phase 4: Decommission & Governance (Weeks 16–24+)

| Deliverable | Description | Format |
|---|---|---|
| D4.1 — Service Account Decommission Procedure | Standard procedure: disable AD account → 30-day monitoring → remove from all groups → 60-day hold → delete. Preserve audit trail. | Decommission SOP |
| D4.2 — Workload Identity Governance Specification | Ongoing governance: quarterly access review of all service principals, annual certificate rotation verification, unused workload identity detection and cleanup, privilege creep detection | Governance specification |
| D4.3 — Workload Identity Drift Detection Rules | OSCAL-aligned rules: service principal with secret (should be certificate), managed identity with excessive RBAC, expired certificate, unused workload identity (>90 days no sign-in), workload identity with no owner | Drift detection rule set |
| D4.4 — Workload Identity Inventory Dashboard | Ongoing dashboard: total workload identities by type, certificate expiry timeline, sign-in activity heatmap, privilege distribution, owner coverage percentage | Quarto dashboard |
| D4.5 — Zero Standing Privilege Assessment | Assessment of remaining standing privileges after migration: which workload identities still have permanent admin roles? Can any be converted to PIM-eligible or JIT? | Assessment report |
| D4.6 — Service Account Elimination Certificate | Final sign-off per wave: all service accounts migrated, all embedded credentials remediated, all delegation chains replaced, all AD accounts decommissioned | Sign-off document |
| D4.7 — Lessons Learned & Pattern Library | Documented patterns that worked, anti-patterns that failed, edge cases encountered, recommendations for future migrations | Lessons learned document |

**Total Deliverables: 38**

---

# Cross-Cutting Deliverables (All Three Specs)

| # | Deliverable | Description | Applies To |
|---|---|---|---|
| X1 | UIAO OrgPath Attribute Implementation Decision | Lock the canonical attribute: extensionAttribute vs. custom security attribute vs. directory extension. This decision is a prerequisite for all three specs. | All |
| X2 | Entra Connect Sync Scope Configuration | Define what syncs during coexistence: which user attributes, which device attributes, which OUs, which object types. Directly impacts all three migration paths. | All |
| X3 | Entra ID Governance License Requirement | Map license requirements (Entra ID P1/P2, Entra ID Governance, Intune P1/P2, Defender for Identity) across all three specs. Calculate total licensing impact. | All |
| X4 | UIAO Governance OS Integration Specification | How provisioning events, device migrations, and service account changes feed into the UIAO provenance chain. Event schema. Drift detection rule format. | All |
| X5 | Master Test Environment Specification | Shared test environment requirements: test Entra ID tenant, test AD domain, test HR data source, test Intune environment, test Arc-enabled servers | All |
| X6 | Training & Knowledge Transfer Plan | Training for: IT operations (new management tools), helpdesk (new device support procedures), application teams (workload identity migration), security team (new monitoring patterns) | All |

**Cross-Cutting Deliverables: 6**

---

# Summary

| Spec | Deliverable Count | Estimated Duration |
|---|---|---|
| Spec 1: Computer Object Transformation | 30 | 20+ weeks |
| Spec 2: HR-Agnostic Provisioning Architecture | 33 | 20+ weeks |
| Spec 3: Service Account → Workload Identity | 38 | 24+ weeks |
| Cross-Cutting | 6 | Parallel with all specs |
| **TOTAL** | **107** | **24+ weeks (parallel execution)** |

---

# Next Implementation Tracks (2026-04-30)

This section names the next high-leverage tracks beyond the discovery-script
work that has been landing. It is editorial — every deliverable referenced is
already enumerated above. Order reflects dependency, not necessarily duration.

## Track A — Land D1.7 Connector Comparison (Spec 2, Phase 1, in progress)

The HR Source System Connector Comparison (D1.7) is the last Spec 2 Phase 1
deliverable that does not yet have a canonical Markdown form. The
PowerShell generator at `tools/discovery/Spec2-D1.7-New-HRConnectorComparisonMatrix.ps1`
builds structured outputs (JSON, CSVs, per-run Markdown report) but the
hand-curated canonical comparison matrix is the deliverable referenced
in §SPEC 2 → Phase 1 → D1.7. Closes the connector-evaluation evidence
gap that ADR-003 currently cites only by reference.

## Track B — Spec 2 Phase 3 (Technical Architecture, D3.1–D3.8)

Once D1.7 is in, the next strategic track is **Spec 2 Phase 3** — the
technical architecture deliverables (D3.1 through D3.8). This is where
SCIM and the Microsoft Graph `bulkUpload` API "become real" in the
codebase rather than living only in canon prose. The lead deliverable
is **D3.1 — API-Driven Inbound Provisioning Architecture**, the canonical
SCIM/bulkUpload architecture document.

Track B also creates the integration point for the proposed
`entra-id-governance` and `entra-workload-identity` adapters
(ADR-049, PROPOSED) — Access Reviews, Entitlement Management, Lifecycle
Workflows, and workload identity federation all consume the HR-driven
provisioning output. Without Track B, those adapters have no canonical
upstream to reference.

Track B is **premature** until D1.7 (Track A) is complete: the connector
comparison evidence is what allows D3.1 to make defensible
build-vs.-buy decisions per HR vendor scenario.

### Track B status (2026-05-01)

D3.1 landed at v1.0 on 2026-04-30 (PRs #272 / #274 / #276 / #277 with
ADRs #270 / #271 / #275). The remaining 7 D3.x deliverables landed as
v0.1 (Draft) on 2026-05-01 in a single batch, mirroring the Track C
v0.1 pattern.

| Deliverable | Path | Status |
|---|---|---|
| D3.1 — API-Driven Inbound Provisioning Architecture | [`specs/Spec2-D3.1-APIDrivenInboundProvisioningArchitecture.md`](./specs/Spec2-D3.1-APIDrivenInboundProvisioningArchitecture.md) | v1.0 Final (2026-04-30) |
| D3.2 — Integration Middleware Specification | [`specs/Spec2-D3.2-IntegrationMiddlewareSpecification.md`](./specs/Spec2-D3.2-IntegrationMiddlewareSpecification.md) | v0.1 Draft |
| D3.3 — Provisioning Agent Deployment Architecture | [`specs/Spec2-D3.3-ProvisioningAgentDeploymentArchitecture.md`](./specs/Spec2-D3.3-ProvisioningAgentDeploymentArchitecture.md) | v0.1 Draft |
| D3.4 — Attribute Mapping Engine Configuration | [`specs/Spec2-D3.4-AttributeMappingEngineConfiguration.md`](./specs/Spec2-D3.4-AttributeMappingEngineConfiguration.md) | v0.1 Draft |
| D3.5 — OrgPath Population Pipeline | [`specs/Spec2-D3.5-OrgPathPopulationPipeline.md`](./specs/Spec2-D3.5-OrgPathPopulationPipeline.md) | v0.1 Draft |
| D3.6 — Writeback Specification | [`specs/Spec2-D3.6-WritebackSpecification.md`](./specs/Spec2-D3.6-WritebackSpecification.md) | v0.1 Draft |
| D3.7 — Monitoring & Alerting Configuration | [`specs/Spec2-D3.7-MonitoringAlertingConfiguration.md`](./specs/Spec2-D3.7-MonitoringAlertingConfiguration.md) | v0.1 Draft |
| D3.8 — Data Flow Security Assessment | [`specs/Spec2-D3.8-DataFlowSecurityAssessment.md`](./specs/Spec2-D3.8-DataFlowSecurityAssessment.md) | v0.1 Draft |

**Cross-spec architecture:**

- D3.2 is the load-bearing one — the canonical middleware contract.
  ADR-050 names the chosen reference implementation; D3.2 specifies
  the contract any conformant middleware MUST satisfy.
- D3.3 binds the Microsoft-verified prerequisites (D3.1 v1.0
  verification) to the UIAO deployment posture (gMSA naming,
  OU-scope rules, AD permission model, decommission runbook).
- D3.4 codifies the two-layer mapping (middleware-side per
  D3.2 §3 + Entra-side per the synchronization-job export); the
  two layers MUST agree.
- D3.5 traces the OrgPath cascade end-to-end across stages 0–8,
  binding latency planning values and drift-detection contracts.
- D3.6 names two writeback directions (Entra → AD during
  coexistence; optional Entra → HR) with sunset paths.
- D3.7 binds D3.2/D3.3/D3.5/D3.6 telemetry into a 3-tier alert
  model that integrates with the D2.6 escalation framework.
- D3.8 is the FedRAMP Moderate security-posture statement; cites
  every NIST 800-53 Rev 5 control implemented across the
  substrate.

**Outstanding for v0.2 (per per-spec verification blocks):**

- D3.2: Azure Functions Python developer guide; Logic Apps Standard;
  managed identities for Microsoft Graph.
- D3.3: Microsoft Entra Cloud Sync prerequisites delta (2025-server
  support); Cloud Sync agent installation; gMSA management.
- D3.4: Provisioning attribute-mappings expression-language reference;
  how attribute mappings work for app provisioning.
- D3.5: Dynamic group rule-evaluation latency; AU membership-rule
  semantics; Intune assignment evaluation timing.
- D3.6: Cloud Sync attribute writeback; group writeback in Cloud
  Sync.
- D3.7: Microsoft Entra ID provisioning logs; Azure Monitor metric
  naming conventions; Application Insights KQL reference.
- D3.8: Microsoft Graph permissions reference; TLS 1.2+ enforcement;
  Conditional Access for service principals.

## Track C — Spec 2 Phase 2 (JML Workflow Design)

Phase 2 (D2.1–D2.8) — Joiner / Mover / Leaver / Rehire / Conversion /
error-handling / pre-hire / scope-filter — runs in parallel with Track B
once D1.7 is in. Phase 2 is workflow specification work; Phase 3 is
architecture work. They share the canonical attribute schema (D1.1) and
attribute mapping matrices (D1.3, D1.4) as inputs but do not block
each other.

### Track C status (2026-04-30)

All 8 Phase 2 deliverables landed as v0.1 (Draft) on 2026-04-30 in a
single batch following the D3.1 pattern (initial draft → MS-Learn
verification → v1.0 closure).

| Deliverable | Path | Sequence diagram | Status |
|---|---|---|---|
| D2.1 — Joiner | [`specs/Spec2-D2.1-JoinerWorkflowSpecification.md`](./specs/Spec2-D2.1-JoinerWorkflowSpecification.md) | yes | v0.2 Draft |
| D2.2 — Mover | [`specs/Spec2-D2.2-MoverWorkflowSpecification.md`](./specs/Spec2-D2.2-MoverWorkflowSpecification.md) | yes | v0.2 Draft |
| D2.3 — Leaver | [`specs/Spec2-D2.3-LeaverWorkflowSpecification.md`](./specs/Spec2-D2.3-LeaverWorkflowSpecification.md) | yes | v0.2 Draft (corrected) |
| D2.4 — Rehire | [`specs/Spec2-D2.4-RehireWorkflowSpecification.md`](./specs/Spec2-D2.4-RehireWorkflowSpecification.md) | (workflow only) | v0.2 Draft |
| D2.5 — Conversion | [`specs/Spec2-D2.5-ConversionWorkflowSpecification.md`](./specs/Spec2-D2.5-ConversionWorkflowSpecification.md) | (workflow only) | v0.2 Draft |
| D2.6 — Error Handling & Quarantine | [`specs/Spec2-D2.6-ErrorHandlingQuarantineSpecification.md`](./specs/Spec2-D2.6-ErrorHandlingQuarantineSpecification.md) | n/a (policy) | v0.2 Draft (sync) |
| D2.7 — Pre-Hire Provisioning Window | [`specs/Spec2-D2.7-PreHireProvisioningWindowSpecification.md`](./specs/Spec2-D2.7-PreHireProvisioningWindowSpecification.md) | n/a (timing) | v0.2 Draft |
| D2.8 — Provisioning Scope Filter Rules | [`specs/Spec2-D2.8-ProvisioningScopeFilterRules.md`](./specs/Spec2-D2.8-ProvisioningScopeFilterRules.md) | n/a (rules) | v0.2 Draft (corrected) |

D2.6 is the canonical failure-routing sister; D2.1–D2.5 + D2.7 + D2.8
all delegate failure handling there. D3.1 §6.3 (retry / quarantine
manager) and D2.6 §3 (queue contract) MUST stay wire-compatible.

### Track C v0.2 verification pass (2026-05-01)

All 8 Phase 2 specs verified against Microsoft Learn and bumped to
v0.2 on 2026-05-01. The authoritative `verification_history` block in
each spec's frontmatter is the load-bearing record; the summary:

**Material corrections landed (architecturally significant):**

- **D2.3 §4 step 3** — Microsoft Graph user property name
  `refreshTokensValidFromDateTime` (incorrect) → `signInSessions
  ValidFromDateTime`. v0.1 also prescribed step 3 as a writable
  PATCH; the property is read-only per Microsoft Graph, so the
  step is reframed as a verification read-back of step 2's
  effect. Implementations following v0.1 would have failed with
  read-only-property errors.
- **D2.8 §5** — `IN(...) AND ... IN(...)` SQL-style filter syntax
  (incorrect) → Microsoft's actual Clause/Group authoring shape
  with `EQUALS`, `ENDS_WITH`, `&`, `!&` operators. Prose-only
  correction (no implementation impact since v0.1 explicitly
  flagged the syntax as illustrative).

**Substantive confirmations (v0.1 architectural posture validated):**

- **D2.1 / D2.2 / D2.4** — LCW joiner / mover trigger categories
  exist; Attribute-changes trigger type substrate-aligns with
  delta-detection model. LCW per-user license requirement
  (Entra ID Governance / Entra Suite). LCW does NOT expose a
  separate 'rehire' trigger — confirms D2.4's rehire-as-
  derived-event posture.
- **D2.3** — `revokeSignInSessions` invalidates BOTH refresh
  tokens AND session cookies; permissions matrix
  (`User.RevokeSessions.All` least-privileged) confirmed.
- **D2.5** — Group-based-licensing change-on-group is the
  canonical mechanism with "over time" propagation; validates
  §5.1 transition-window framing.
- **D2.7** — `user.accountEnabled -eq true` confirmed as the
  canonical dynamic-group filter. Disabled users are NOT
  auto-blocked from manual group assignments (relevant to
  Posture-A vs. Posture-B license-cost analysis).
- **D2.8** — Clause/Group AND/OR structure and operator set
  (`EQUALS`, `ENDS_WITH`, `&`, `!&`) confirmed.

**Items still unverified (deferred to future passes):**

- Workday inbound provisioning attribute mapping table
  (referenced but not extracted in this pass).
- Access Reviews trigger event wire format / API endpoint.
- LCW built-in joiner/leaver task names.
- Microsoft Purview litigation-hold policy reference (D2.3 step 9).
- Exchange shared-mailbox conversion API contract (D2.3 step 8).
- CAE propagation latency for `revokeSignInSessions`.
- Group-based-licensing tier-change SLA bound.
- `bulkUpload` payload-rejection per-class HTTP response codes.

The authoritative source surface for v0.2 was Microsoft Learn search
results (the `learn.microsoft.com` HTML responded 403 to direct
WebFetch during this pass; WebSearch surfaced the canonical
excerpts). Items where direct page extraction was needed have been
listed under each spec's `remaining_unverified` block for a
follow-on pass.

## Sequencing summary

```
D1.x discovery scripts (in flight)  ──▶  D1.7 canonical matrix (Track A)
                                              │
                                              ├──▶  D3.1 SCIM/bulkUpload arch (Track B)
                                              │     ├──▶  D3.2..D3.8
                                              │     └──▶  ADR-049 adapter integration
                                              │
                                              └──▶  D2.1..D2.8 JML workflows (Track C)
```
