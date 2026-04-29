---
document_id: UIAO_135
title: "Identity & Directory Transformation Inventory — AD to Entra ID"
version: "0.1"
status: Draft
classification: CANONICAL
owner: Michael Stratton
boundary: GCC-Moderate
created_at: "2026-04-28"
updated_at: "2026-04-28"
---

# Identity & Directory Transformation Inventory — AD → Entra ID

> **Purpose:** Comprehensive catalog of every Identity and Directory transformation defined within the UIAO canon, plus the systematic breakdown of all AD → Entra ID modernization domains required for full cloud-native identity posture.

---

## 1. UIAO-Defined Identity / Directory Transformations

The following transformations have been explicitly defined across UIAO canonical artifacts.

### 1.1 Structural Transformations — X.500 to Flat Attribute Model

| # | Transformation | Source (Legacy) | Target (Modern) | UIAO Source |
|---|---|---|---|---|
| 1 | **OrgPath — Deterministic Organizational Addressing** | AD X.500 OU tree (`OU=IT,OU=Baltimore,OU=East,DC=contoso`) | Canonical attribute path (`CORP/US/EAST/BALTIMORE/IT`) stamped on user/device objects via extensionAttributes or custom security attributes | Program Overview; Entra ID Org Hierarchy Guide |
| 2 | **OU → Dynamic Groups** | AD OUs as containers for user/device placement | Dynamic Entra ID security groups using attribute rules (`-eq`, `-startsWith` on OrgPath) | Entra ID Org Hierarchy Guide |
| 3 | **OU-Scoped Delegation → Administrative Units** | Delegated admin rights scoped to AD OUs | AUs with dynamic membership + scoped Entra ID role assignments (User Administrator, Helpdesk Administrator, etc.) | Entra ID Org Hierarchy Guide |

### 1.2 Identity Object Transformations

| # | Transformation | Source (Legacy) | Target (Modern) | UIAO Source |
|---|---|---|---|---|
| 4 | **Identity Translation — Human Identity Bridge** | AD user accounts, LDAP binds, local accounts | Entra ID users with certificate-based auth, passwordless, workload identity; durable legacy↔modern ImmutableId mapping | Program Overview |
| 5 | **Device Identity — Endpoints as First-Class Principals** | Domain-joined computer objects in AD (`CN=WORKSTATION01,OU=Computers,...`) | Entra ID joined/registered devices with device certificates, posture signals, OrgPath assignments; managed via Intune | Program Overview; Entra ID Org Hierarchy Guide |
| 6 | **Azure Arc Telemetry Projection — Hybrid Identity Bridge** | On-prem servers invisible to cloud governance | Arc-enabled servers with managed identities, Entra ID RDP auth (AADLoginForWindows extension), Azure RBAC, telemetry into Governance OS | Phase 2 GOS |
| 7 | **SQL Server Authentication — Service Identity** | Windows Auth (Kerberos/NTLM) + SQL Auth (sa accounts) | Entra ID auth for SQL 2022+ — MFA, Managed Identity, Service Principal, OAuth 2.0 tokens via Arc | Choosing EntraID vs AD for SQL |

### 1.3 Policy Transformations

| # | Transformation | Source (Legacy) | Target (Modern) | UIAO Source |
|---|---|---|---|---|
| 8 | **GPO → Intune Configuration Profiles** | Group Policy Objects linked to OUs | Intune Settings Catalog, Compliance Policies, App Protection Policies assigned to dynamic device groups | Entra ID Org Hierarchy Guide |
| 9 | **GPO Admin Scoping → Intune Scope Tags** | GPO filtering and OU-scoped admin visibility | Scope Tags restricting Intune admin visibility per organizational boundary | Entra ID Org Hierarchy Guide |
| 10 | **Group Policy Loopback → Device-Targeted Policy** | GPO loopback processing mode | Intune device group policy (device-targeted configuration profiles) | Entra ID Org Hierarchy Guide |
| 11 | **Security Filtering → Conditional Access** | GPO security group filtering (apply/deny) | Conditional Access policies with user group include/exclude + device compliance requirement | Entra ID Org Hierarchy Guide |
| 12 | **Policy Overlay — Continuous Enforcement** | Static firewall rules, one-time authentication events | Dynamic, identity-aware, telemetry-informed continuous policy evaluation based on identity assurance level, device posture, and OrgPath | Program Overview |

### 1.4 Governance & Lifecycle Transformations

| # | Transformation | Source (Legacy) | Target (Modern) | UIAO Source |
|---|---|---|---|---|
| 13 | **HR-Driven Provisioning — Lifecycle Automation** | Manual account creation; on-prem HR → MIM → AD | Cloud HR app → Entra ID Governance (Joiner-Mover-Leaver workflows); API-driven inbound provisioning | HR Driven EntraID |
| 14 | **Entra ID Identity Baselines — Governance Enforcement** | Manual CA/MFA/PIM policy management | Canonical OSCAL baselines with drift detection (UIAO_BL_001, BL_002) covering CA, MFA, PIM, guest access, app consent, cross-tenant settings | Phase 2 GOS |
| 15 | **Endpoint Compliance Baselines — Intune Governance** | Manual device configuration review | Canonical baselines (UIAO_BL_007, BL_008) for device compliance, configuration profiles, app protection, WUfB update rings | Phase 2 GOS |
| 16 | **AD Assessment Pipeline — Continuous State Capture** | Periodic manual AD audits | Automated PowerShell modules (UIAOADAssessment, UIAOIdentityAssessment) → JSON → Gitea → Quarto dashboard | Operations Runbook |
| 17 | **Governance Substrate — Provenance Chain** | Email/ticket governance, manual review cycles | Immutable SHA-256-linked provenance chain; automated drift detection, remediation orchestration, OSCAL output | Phase 2 GOS |

---

## 2. Federal HR System — Current State (April 2026)

### 2.1 OPM HR IT Consolidation Procurement

| Detail | Status |
|---|---|
| **Contract scope** | Single governmentwide HCM system, 10-year, $1B+ |
| **OMB target date** | All major agencies migrated by July 4, 2027 |
| **IBM** | Eliminated from competition; filed GAO protest Feb 25, 2026 |
| **EconSys** | Eliminated; filed GAO protest March 2, 2026 |
| **SAP** | Eliminated |
| **Remaining finalists** | Workday (Accenture) and Oracle (Deloitte) |
| **GAO protest decisions** | Expected early June 2026 |
| **Existing system** | OPM EHRI (Enterprise Human Resources Integration) + eOPF |

### 2.2 UIAO Architectural Implication

UIAO should define the HR-driven identity provisioning architecture as **HR-system-agnostic**, since Entra ID Governance supports all candidate paths:

1. **Cloud HR Connector** — Workday or Oracle direct (Microsoft-built connectors, GA)
2. **API-Driven Inbound Provisioning** — Any HR source → REST API → Entra ID (covers future-unknown systems)
3. **Legacy Bridge** — On-prem HR → MIM → AD → Entra Connect Sync (transition-state only)

The canonical UIAO artifact should define the provisioning **pattern** (attribute mapping, Joiner-Mover-Leaver rules, OrgPath population) independent of the HR source system.

---

## 3. Transformation Coverage Assessment

### 3.1 Well-Defined (✅)

| Domain | UIAO Coverage |
|---|---|
| X.500 OU Tree → OrgPath Attributes | adr-035 (orgpath-codebook-binding), adr-038 (device-plane-orgpath), adr-048 (orgpath-attribute-selection); Entra ID Org Hierarchy Guide for narrative |
| OU → Dynamic Groups | adr-036 (dynamic-group-provisioning); Org Hierarchy Guide |
| OU-Scoped Delegation → AUs + Scoped Roles + Scope Tags | adr-037 (admin-unit-provisioning); Org Hierarchy Guide §§4 & 8.4 |
| GPO → Intune Configuration Profiles + Compliance Policies | Org Hierarchy Guide §8; Phase 2 Intune baselines; intune.qmd / intune-policy-templates.qmd |
| Conditional Access Policy Targeting | adr-039 (policy-targeting); conditional-access-library.qmd |
| Computer Object → Entra Device + Arc | adr-001 (HAADJ deprecated → Entra Join only), adr-002 (Arc + Entra join, no domain join for servers), adr-034 (three-plane device model), adr-038 (device-plane OrgPath), adr-042 (AD computer conversion guide); UIAO_136 Spec 1 enumerates deliverables |
| HR-Driven Identity Lifecycle (HR-agnostic) | adr-003 (api-driven-inbound-provisioning) establishes the canonical HR-agnostic pattern; UIAO_136 Spec 2 enumerates deliverables |
| AD Service Accounts → Workload Identities | adr-004 (workload-identity-federation-default) establishes federation as default; UIAO_136 Spec 3 enumerates deliverables |
| DNS (AD-Integrated) → Azure DNS / Hybrid DNS | Covered in separate Hybrid DNS Orchestration Guides |

### 3.2 Partially Defined — Needs Canonical Specification (⚠️)

| Domain | Current State | Gap |
|---|---|---|
| AD Security Group Rationalization | adr-036 covers dynamic-group provisioning; adr-039 covers policy targeting | Distribution lists, mail-enabled groups, and nested-group flattening still need explicit transformation pattern |
| Kerberos/NTLM → Modern Auth Protocols | SQL Server path covered (Spec3-D1.8 discovery script); broader auth modernization not yet ADR-scoped | NTLM elimination timeline, Cloud Kerberos trust posture, and certificate-based auth rollout still need a canonical spec |
| LDAP-Dependent Applications → Entra ID App Proxy + SAML/OIDC | Discovery script exists (Spec3-D1.9-Get-LDAPBindAccountInventory.ps1); no transformation ADR | Migration pattern per app class (App Proxy, SAML federation, OIDC migration) still needs a canonical spec |

### 3.3 Not Yet Defined — Gaps (❌)

| Domain | Description |
|---|---|
| AD Sites & Subnets → Named Locations + Conditional Access | Discovery scripted in UIAO_136 Spec 1 D1.8 (not yet implemented). Network topology addressing model has no Entra ID equivalent transformation spec yet. |
| AD Certificate Services → Entra ID Certificate-Based Auth + Cloud PKI | Discovery script exists (Spec3-D1.10-Get-CertBasedAuthAudit.ps1). No transformation spec linking ADCS to Entra CBA and Microsoft Cloud PKI. |

---

## 4. Systematic Specification Roadmap

### Priority 1 — Structural Completeness

The three Priority 1 specs are realized in **UIAO_136** (Phase 1 discovery scripts ~62% landed; Phases 2–5 awaiting drafts):

1. **Computer Object Transformation Spec** — UIAO_136 Spec 1; foundational ADRs: adr-001, adr-002, adr-034, adr-038, adr-042
2. **HR-Agnostic Provisioning Architecture** — UIAO_136 Spec 2; foundational ADR: adr-003
3. **Service Account → Workload Identity Mapping** — UIAO_136 Spec 3; foundational ADR: adr-004

### Priority 2 — Protocol & Infrastructure

4. **Kerberos/NTLM Elimination Spec** — Cloud Kerberos trust, CBA rollout, NTLM audit and deprecation
5. **AD Sites & Subnets → Named Locations** — Map network topology model to Conditional Access targeting
6. **ADCS → Cloud PKI + CBA** — Certificate authority transformation path

### Priority 3 — Application Layer

7. **AD Security Group Rationalization** — Explicit mapping of all group types to Entra ID equivalents
8. **LDAP-Dependent Application Migration Pattern** — Discovery, classification, and migration path per app type

---

## 5. Refinement Notes

> **Items flagged for further refinement before promoting from DRAFT:**
>
> - [ ] Confirm document_id assignment (UIAO_135 assigned 2026-04-28)
> - [x] **Doc-ID scheme reconciliation** — Resolved 2026-04-29: standardized on the `UIAO_NNN` registry scheme. adr-001/002/003/004 cross-references updated from `UIAO_IDT_001`/`UIAO_IDT_002` to `UIAO_135`/`UIAO_136`.
> - [ ] Cross-reference each transformation against the canonical UIAO Article series to ensure no transformations defined in articles are missing from this inventory
> - [ ] Validate OrgPath attribute implementation — extensionAttributes vs. custom security attributes vs. directory extensions — and lock the canonical approach
> - [ ] Define whether the HR provisioning architecture should be a standalone UIAO artifact or a section within an existing document
> - [ ] Add boundary impact annotations (compute, storage, licensing, compliance) per transformation domain
> - [ ] Determine if AD Sites & Subnets mapping should include Azure Virtual Network integration or remain scoped to Conditional Access Named Locations only
> - [ ] Cross-reference against the 30 modernization articles to capture any transformation concepts defined in the narrative series but not yet formalized here
> - [ ] Add OSCAL control mapping per transformation where applicable
