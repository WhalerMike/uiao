# HRIT-IAM-Findings — How Federal HRIT Requires & Integrates with IAM

> **Status:** DRAFT — inbox content, not canon. Promote to `src/uiao/canon/specs/` only via the four ADRs proposed alongside this document (see `proposed-canon-additions/`).
>
> **Source materials** (all in this directory):
> - `Solicitation+24322626R0007+Amd+4+-+Federal+HRIT+Modernization.pdf` (latest authoritative PWS)
> - `Solicitation+24322626R0007+Amd+2/3/...pdf` (prior amendments, retained for diff context)
> - `ATTACHMENT+0001+-+Appendix+A+Requirements+Checklist+-+Amd+2.xlsx` (244 functional requirements)
> - `Questions+and+Answers+-+Solicitation+No+24322626R0007.pdf` and `+2+...pdf` (clarifications)
>
> **Scope:** Identity & Access Management mandates only. Performance management, payroll, and learning-management requirements are out of scope for this analysis except where they touch IAM boundaries.
>
> **Created:** 2026-05-04 by analysis of OPM Federal HRIT Modernization Solicitation 24322626R0007.

---

## 1. Executive summary

The OPM Federal HRIT Modernization Solicitation 24322626R0007 mandates a deeply prescriptive IAM contract — far more specific than UIAO canon currently captures. The headline elements:

1. **OPM Microsoft Entra ID is the federal IdP.** Not optional, not vendor-substitutable.
2. **SAML federation with OPM IdP is bid-window evidence.** Per Clause 1752.224-71, offerors must include SAML-integration proof in their proposal.
3. **SCIM 2.0 user provisioning, ≤ 15-minute sync, with audit logs on every event.**
4. **PIV-based authentication for OPM users; phishing-resistant MFA for everyone else** (NIST SP 800-53-5 IA-02 (01,02)).
5. **OAuth 2.0 + OpenID Connect at the API perimeter,** with mTLS and automated certificate rotation.
6. **All persistent integrations through OPM-hosted Azure APIM gateway.**
7. **One OPM ATO covers every onboarded agency** (reciprocity model).
8. **Identity is one of four explicit segmentation layers** (data, application, identity, logging).
9. **OMB M-22-09 + NIST SP 800-207 Zero Trust mandated by reference.**
10. **Platform must be a single code line** — agency differences are configuration, never forks (Q&A #47-48).

Eight of the ten land cleanly on existing UIAO canon. **Four exposed gaps** are the basis of the proposed canon additions documented in `proposed-canon-additions/`.

---

## 2. The keystone mandate — OPM Entra is the IdP

**PWS §5.1.1, item #3 (Amd 4 p. 26):**

> *"Integrate and implement OPM approved identity management solution using **OPM MS Entra-based solution**."*

This single sentence is the load-bearing IAM constraint of the entire solicitation. Every Core HCM platform serving any of the ~24 CFO-Act agencies federates to **OPM's Entra tenant**. Vendor IdPs are not acceptable substitutes.

**Implication for UIAO:** The `entra-id` modernization adapter ([modernization-registry.yaml:32](../../src/uiao/canon/modernization-registry.yaml)) is already the right shape — but the canon does not yet model the case where **OPM's tenant is the authority for all downstream agency tenants**. This is a multi-tenant IdP-of-record pattern that warrants explicit canon.

---

## 3. Contractual IAM clauses (Section H)

These are bid-evaluated; non-conformance is a non-responsive proposal.

### 3.1 Clause 1752.224-70 — Identification and Authentication (Dec 2023) (Amd 4 p. 99)

| § | Mandate |
|---|---|
| (a) | All accounts uniquely identified (e.g., `firstname.lastname`); **no default or generic accounts**; system-process accounts also uniquely identified |
| (b) | **OPM users**: PIV-based authentication, federated SSO, or other phishing-resistant mechanism |
| (c) | **Non-OPM (public) users**: phishing-resistant MFA "to the greatest degree possible." Per **NIST SP 800-53-5 IA-02 (01, 02)**, the solution shall, **at the time of award**, integrate directly with OPM's IdP via **SAML** assertions from third-party software. MFA for **all access**. Phishing-resistant MFA enforced for OPM users and made available to public users. Passphrases per OPM cybersecurity policy. |
| (d) | **SCIM 2.0** automated user provisioning (full text reproduced from Appendix A Req #5) |

### 3.2 Clause 1752.224-71 — Identification and Authentication Certification (Dec 2023) (Amd 4 p. 100)

> *"Offerors must include in their offer/quotation **evidence, artifacts, or proof** of the ability to integrate directly with the OPM's identity provider and SSO mechanism; having the built-in ability to accept a SAML assertion from a third-party software."*

This is **bid-time evidence**. Vendors without working SAML federation to OPM Entra at proposal submission are non-responsive.

### 3.3 Other security-frame clauses

| Clause | Subject | Page |
|---|---|---|
| 1752.224-72 | Protecting CUI / IT system authorization | 100 |
| 1752.224-73 | Information Protection Policies (FIPS 140-3 encryption / masking / redaction) | 101 |
| 1752.224-74 | Information Security Incident reporting (≤ 30 minutes to OPM SOC) | 101 |
| 1752.239-74 | OPM ATO process — single ATO for the platform | 107 |
| 1752.239-75 | Cloud Computing — CSP must meet all cybersecurity requirements | 108 |
| 1752.239-82 | Supply Chain Risk Management — SBOM in SPDX or CycloneDX | 112 |

---

## 4. Functional IAM requirements (Appendix A — 244 total, ~17 IAM-core)

Source: `ATTACHMENT+0001+-+Appendix+A+Requirements+Checklist+-+Amd+2.xlsx` (Sheet1, 563 rows = 244 numbered requirements).

### 4.1 Core IAM requirements

| Req # | Functional Area | Requirement (verbatim or paraphrased) |
|---|---|---|
| **#1** | Core HCM Admin | FedRAMP Moderate or higher certified platform |
| **#4** | Core HCM Admin | Single Sign-On (SSO) + APIs for automated data extraction |
| **#5** | Core HCM Admin | **SCIM 2.0** automated provisioning from Government IdP. Sync **near real-time / ≤ 15 minutes**. Logs and audit on every provisioning event. Compliant with NIST/OMB references including **OMB M-25-21**. |
| **#7** | Core HCM Admin | Tenant/agency-specific access controls; granular RBAC by user role and responsibility |
| **#8** | Core HCM Admin | Secure multi-tenancy with isolated administrative spaces; **role-based landing pages** |
| **#9** | Core HCM Admin | OPM has Administrator-level access across **all tenants** |
| **#11** | Core HCM Admin | Role-based access for notifications, actions, alerts, data, analytics, views, permissions; org-scoped visibility |
| **#12** | Core HCM Admin | RBAC enforcing **least privilege**; **dynamic provisioning/deprovisioning of roles based on employment status, organizational changes, or business rules** |
| **#19** | Core HCM Admin | Audit logs of all access control changes — **who, when, what** |
| **#24** | Core HCM Admin | Delegation: assign approver proxies for time-bounded periods |
| **#26** | Core HCM Admin | Data exchange supporting integration with **IAM systems, Phishing-Resistant MFA, SSO** |
| **#27** | Core HCM Admin | Bulk user upload, provisioning, role assignment; delegated administration |
| **#28** | Core HCM Admin | Role-based security profiles binding **role × function × data** with least privilege |
| **#75** | LMS module | FISMA, FedRAMP, encryption at rest + in transit, regular audits |
| **#185** | HC Analytics | Audit logs for workflow approvals, **user role changes**, and system integrations |
| **#186** | HC Analytics | Role-based dashboard reporting |
| **#240** | PAR Processing | Privileged users execute mass change transactions |

### 4.2 IAM-adjacent requirements (auth-context, authority gating)

The Appendix carries 26 additional requirements that mention "authorized users" as a gating predicate (e.g., Reqs #40, #45, #51, #65, #109, #117, #142, #151, #152, #191, and the X1 PAR Processing series #225–#243). These are not standalone IAM mandates but *consume* the RBAC model defined by #7/#11/#12/#28.

---

## 5. Integration architecture — IAM at the API perimeter

Source: Appendix B (Amd 4 pp. 82–85).

### 5.1 OPM-hosted Azure APIM gateway (p. 82)

All **persistent OPM-side integrations** flow through an OPM-hosted Azure API Management (APIM) gateway. The contractor must:

- Securely expose APIs across agency boundaries via APIM
- **Enforce OAuth 2.0**, rate limiting, IP filtering at the gateway
- Support data format transformation (XML ↔ JSON)
- Provide developer-portal API documentation
- Enable monitoring, logging, analytics for all API traffic
- Comply with FedRAMP Moderate+, FISMA, NIST SP 800-53

### 5.2 Core-HCM API boundary (p. 84)

The contractor publishes the Core HCM APIs and:

- **Implements OAuth 2.0 and OpenID Connect** for authentication and authorization, enforcing **least-privilege scopes**
- **Supports mutual TLS (mTLS) with automated certificate rotation** where required
- Publishes **OpenAPI 3.0** specs for all REST/JSON endpoints
- Provides webhooks + batch interfaces for async/scheduled exchange
- Furnishes a non-production sandbox + developer portal
- Maintains **99.7% monthly uptime SLA**
- Delivers structured logs, metrics, **correlation IDs** for end-to-end traceability
- **Operates nothing beyond the Core-HCM boundary** — OPM and other agencies operate their own API managers and consume Core-HCM APIs as published

### 5.3 Outside OPM — agency-direct integrations (p. 84)

- REST/JSON or analogous standards-based interop
- **FIPS 140-2/3 validated encryption** in transit and at rest
- RBAC + strict data segmentation
- Full unrestricted Government API access for integration, modification, extension
- Agencies may use their existing FedRAMP-certified integration platforms

### 5.4 Federal HR systems referenced

| System | Role | Citation |
|---|---|---|
| OPM Microsoft Entra ID | Federal IdP for Core HCM | PWS §5.1.1 #3 (p. 26) |
| OPM Azure APIM | Centralized API gateway; OAuth 2.0 enforcement | Appendix B (p. 82) |
| USA Staffing | Request Processing Interconnection (RPI), SOAP | Req #66 |
| USA Performance | Performance evaluation API | Req #96 |
| EHRI | Enterprise HR Integration — governmentwide HR/payroll/training feed | Appendix B (p. 85) |
| eOPF | Centralized digital personnel folder | Appendix B (p. 85) |
| Payroll providers | DFAS, NFC, IBC, HHS, Treasury, NASA — direct integration points | Q&A #128 |

---

## 6. Identity-layer segmentation & Zero Trust posture

### 6.1 Tenant segmentation (PWS §6.9.2, p. 51)

> *"Segmentation is enforced at the **data, application, identity, and logging layers**. Tenant/Agency-aware APIs and query guards scope data access to the appropriate boundaries. **Least-privilege authorization (role based and/or attribute based)** governs user and service access, **with periodic access recertification**. Per-tenant/agency encryption and key management isolate data at rest even within shared infrastructure."*

Identity is **explicitly named as one of four segmentation layers** — not derived, not implied.

### 6.2 Zero Trust mandate (PWS p. 112)

> *"The platform aligns with **OMB Memorandum M-22-09** (Federal Zero Trust Strategy) and **NIST SP 800-207** (Zero Trust Architecture), emphasizing strong identity controls; **phishing-resistant multifactor authentication (e.g., PIV/CAC)**; granular authorization; encryption; continuous monitoring; and controls that minimize lateral movement risks across tenant(s)."*

PIV/CAC is named explicitly. The federal Zero Trust pillar of identity is mandated by reference, not implication.

### 6.3 Federal compliance frame (PWS §6.3.1, p. 47)

The contractor shall ensure full compliance with:
1. The Privacy Act of 1974
2. Executive Order 14028
3. Federal Information Security Modernization Act (FISMA)
4. NIST SP 800-53 Rev. 5 controls for Moderate-impact systems
5. FedRAMP
6. OMB M-21-31
7. Federal Records Retention requirements and schedules
8. POA&M maintenance
9. Guide to Processing Personnel Actions (GPPA)
10. Guide to Data Standards
11. Enterprise Human Resources Integration (EHRI) standards
12. OPM Cyber & Security guidelines/policies/procedures
13. **OMB M-22-09**
14. **NIST SP 800-207 (Zero Trust Architecture)**
15. OMB M-22-18

---

## 7. Single-ATO reciprocity model

| Element | Mandate | Source |
|---|---|---|
| One ATO covers all agencies | "OPM's ATO covers any agency's use of the platform" | PWS §5.1.1 #5 (p. 26) |
| Bid-window | Draft SSP within 30 days of award; final within 45 days | Q&A #44 |
| Authority | OPM Authorizing Officials issue the ATO; OPM CIO is the final authority | Clause 1752.239-74 (p. 107) |
| FedRAMP path | A 3PAO assesses; existing FedRAMP package may be leveraged but is **not a substitute** for an explicit OPM ATO decision | p. 108 |
| Code line | **Single code base** required; agency differences via configuration only — no per-agency forks | Q&A #47-48 |

This concentrates the IAM trust boundary at OPM's CISO and creates **single-decision reciprocity** for every onboarded agency — exactly the inverse of the legacy "every agency does its own ATO of every system" pattern.

---

## 8. Q&A clarifications that materially changed the IAM contract

| Q# | Question | Answer |
|---|---|---|
| **#336** | Which data domains require near-real-time replication? | **Identity provisioning must synchronize in near real-time or within 15 minutes** (cites Appendix A Req #5) |
| **#335** | Required masking method? | **FIPS 140-3 compliant** masking/redaction; synthetic data only with OPM approval |
| **#43-44** | Per-agency ATO required? | No — single OPM ATO covers all agencies under reciprocity |
| **#47** | Is RBAC config or customization? | **Configuration** — security settings live in the delivered platform |
| **#48** | Single code base required? | **Yes** — agency differences are handled via configuration and data settings, not code forks |
| **#147-148** | OPM on-prem connectivity? | OPM systems remain on-prem; **ExpressRoute will not be required** |

---

## 9. Mapping to UIAO canon

| HRIT mandate | UIAO canon location | Status |
|---|---|---|
| OPM Entra as mandated IdP | `entra-id` modernization adapter, [UIAO_129 §2 binding #3](../../src/uiao/canon/specs/application-identity-model.md) | ✅ aligned |
| SCIM 2.0 ≤ 15 min provisioning | [Spec2-D3.1 §11.1](../../src/uiao/canon/specs/Spec2-D3.1-APIDrivenInboundProvisioningArchitecture.md) (claims < 30 s median target) | ✅ aligned (UIAO target tighter than HRIT requirement) |
| **SAML federation (1752.224-71)** | UIAO_129 binding #4 (Trust anchor) — *currently OIDC/JWT or mTLS only* | ⚠️ **Gap → ADR-A** |
| **PIV/CAC phishing-resistant MFA** | NIST SP 800-63 referenced in `docs/governance/VISION.md`; no PIV adapter | ⚠️ **Gap → ADR-B** |
| **OPM Azure APIM OAuth 2.0 gateway** | Implied by `entra-id`; not an explicit canon entity | ⚠️ **Gap → ADR-C** |
| mTLS with automated cert rotation | VISION.md Concept #5; `cyberark` modernization adapter | ✅ aligned |
| RBAC dynamic to employment status | UIAO_136 Spec 2 D2.2 (Mover) | ✅ aligned |
| Per-tenant identity-layer segmentation | UIAO_112 Multi-Tenant Isolation | ✅ aligned |
| Audit log of access-control changes | UIAO_113 Evidence Graph | ✅ aligned |
| **Single OPM ATO with reciprocity** | OSCAL-native single-ATO model — implicit, not canonized | ⚠️ **Gap → ADR-D** |
| OMB M-22-09 / NIST SP 800-207 | UIAO_120 Zero-Trust Integration Layer | ✅ aligned |
| 15-min sync SLA | Spec2-D3.1 §3.2 push-driven | ✅ aligned |

---

## 10. Proposed canon additions

Four ADR drafts under `proposed-canon-additions/` close the four gaps above. Each ADR is independently mergeable; the bundle is the closure of the HRIT IAM gap analysis.

| ADR draft | Closes gap | Files touched on merge |
|---|---|---|
| `ADR-A-saml-trust-anchor.md` | SAML as third trust-anchor type | `src/uiao/canon/specs/application-identity-model.md` (UIAO_129 §2 binding #4) |
| `ADR-B-piv-usaccess-adapter.md` | PIV/CAC issuance authority | `src/uiao/canon/adapter-registry.yaml` (new conformance slot); paired modernization slot deferred |
| `ADR-C-opm-azure-apim-adapter.md` | OPM-hosted APIM as named Authority | `src/uiao/canon/modernization-registry.yaml` (new integration slot) |
| `ADR-D-single-ato-reciprocity.md` | Multi-tenant single-ATO model | New spec under `src/uiao/canon/specs/` + `document-registry.yaml` UIAO_NNN allocation |

Each draft is self-contained with the standard ADR sections (Context, Decision, Consequences, Alternatives, References). They have **not** been allocated UIAO_NNN or ADR-NNN identifiers — that allocation happens at canon-merge time per repo invariant I5.

---

## 11. Open questions and follow-ups

1. **OMB M-25-21** is referenced in Req #5 but not yet incorporated into UIAO governance canon. Pull and review when the memo is published.
2. **ExpressRoute is not required** (Q#148) — but the OPM on-prem boundary still consumes USA Staffing, USA Performance, EHRI, eOPF over IP. The transport story for those needs explicit canon (likely a follow-up ADR).
3. **Workday vs. Oracle** — the Spec2-D3.1 architecture is HR-system-agnostic by design. No canon work needed until OPM resolves the procurement.
4. **Federal HRIT Integration Runbook (Spec2-D6.x candidate)** would name USAccess, NFC EmpowHR, Treasury HR Connect, DCPDS, USA Staffing, GRB, eOPF as instances of the D3.1 pattern. Out of scope for this gap analysis but worth filing.

---

*End of findings document. The four ADR drafts in `proposed-canon-additions/` are the actionable output.*
