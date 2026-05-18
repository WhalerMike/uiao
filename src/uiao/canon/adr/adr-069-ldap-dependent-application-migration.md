---
adr_id: adr-069
title: "LDAP-Dependent Application Migration — Four-Class Migration Pattern (App Proxy, SAML, OIDC, Domain Services)"
status: ACCEPTED
decided: 2026-05-13
deciders: Michael Stratton
updated: 2026-05-13
next_review: 2026-11-01
review_trigger: Microsoft Ignite 2026; any Entra ID App Proxy or Entra Domain Services posture change
impact: UIAO_135 §3.2 (Partially Defined gap closure); consumes Spec3-D1.9 (Get-LDAPBindAccountInventory.ps1) discovery output as input
supersedes: null
superseded_by: null
classification: Controlled
boundary: GCC-Moderate
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-069-ldap-dependent-application-migration.html
---

# ADR-069: LDAP-Dependent Application Migration — Four-Class Migration Pattern

## Status

**ACCEPTED** — May 13, 2026

## Context

Spec3-D1.9 (`Get-LDAPBindAccountInventory.ps1`) discovers every LDAP-bind account in the on-premises Active Directory environment. Discovery is the prerequisite; the **transformation pattern** for the discovered apps remains without an explicit canonical pattern in canon as of UIAO_135 §3.2.

LDAP-dependent applications fall into several categories with materially different migration paths. Without a canonical classification, every engagement re-derives the per-app decision tree, and the migration audit cannot certify that every app has a documented migration target before the on-premises AD is retired.

The decision question is two-part:

1. **What are the canonical migration classes?** — i.e., what are the legitimate target states an LDAP-bound app can land in after migration.
2. **How is an app assigned to a class?** — i.e., what observable property of the source app determines its target.

UIAO_135 §3.2 explicitly flags this as a gap.

## Decision

**Every LDAP-dependent application is classified into exactly one of four canonical migration classes, with a per-class transformation pattern:**

### Class 1 — Entra ID App Proxy (legacy on-prem web apps)

**Applies to:** On-premises web applications that authenticate users via HTTP-header injection from an upstream LDAP-aware reverse proxy, or via Windows Integrated Authentication backed by Kerberos / LDAP. Examples: legacy LOB intranet sites, internal SharePoint on-premises farms, OWA-pre-cloud, internal wiki/portal applications.

**Target state:** Entra ID Application Proxy fronts the app; users authenticate to Entra ID; the proxy forwards the request to the on-prem app with the appropriate identity context (header injection or KCD). The app itself remains on-premises until separately modernized.

**Why this class:** Cloud-side authentication for an app that cannot accept cloud-side authentication directly. Preserves the legacy app surface while modernizing its authentication ingress.

### Class 2 — SAML Federation (third-party SaaS with SAML 2.0 support)

**Applies to:** SaaS applications that natively support SAML 2.0 federated authentication. Examples: Salesforce, Workday, ServiceNow, most modern SaaS-vendor catalogs.

**Target state:** Entra ID is the SAML 2.0 IdP; the SaaS app is the SAML SP; user attributes (UPN, OrgPath, group membership) flow via SAML assertion claims. No more direct LDAP binds against on-prem AD; the federation trust anchor is the SAML trust anchor (ADR-051).

**Why this class:** SAML is the mature federation standard for SaaS, well-supported by both Entra ID and by every modern SaaS vendor's identity tier. The on-prem LDAP dependency is replaced wholesale.

### Class 3 — OIDC Migration (OAuth-capable apps and modern web/mobile clients)

**Applies to:** Applications whose identity model supports OpenID Connect (OIDC) — most modern web apps (React/Vue SPAs, modern server-side web apps), most mobile apps, all apps built against the Microsoft identity platform after ~2018.

**Target state:** Entra ID is the OIDC OP; the app uses authorization code flow (web/mobile) or client credentials flow (workload-to-workload) per ADR-004. App-side identity claims come from the ID token; access tokens carry the OAuth 2.0 scope grants. No more LDAP binds.

**Why this class:** OIDC is the modern application-authentication standard. Apps that already speak OAuth 2.0 can speak OIDC with minimal effort; new apps built on the Microsoft identity platform are OIDC-native.

### Class 4 — Entra Domain Services (unmigrate-able legacy apps)

**Applies to:** Legacy applications that hard-code LDAP binds against an on-prem AD domain controller and cannot be modified, replatformed, or fronted by App Proxy. Examples: vendor appliances with hard-coded LDAP queries, end-of-life COTS applications whose vendor no longer supports modernization, certain financial / clinical applications under regulatory freeze.

**Target state:** Entra Domain Services (managed AD-compatible LDAP) hosts a synthetic domain that the app binds against; the synthetic domain is sync'd from Entra ID. The on-prem AD can be retired; the app continues to issue LDAP binds against the managed surface.

**Why this class:** Acceptable carve-out for the long-tail residual that cannot be modernized by the migration deadline. Preserves the LDAP semantic without preserving the on-prem AD trust.

## Per-Class Detection Signals

| Source signal (from Spec3-D1.9 output) | Target class |
|---|---|
| Web app behind on-prem reverse proxy with header injection | Class 1 — App Proxy |
| App's identity config supports SAML 2.0 IdP federation | Class 2 — SAML |
| App's identity config supports OIDC or OAuth 2.0 with `id_token` claim | Class 3 — OIDC |
| App's LDAP bind is hard-coded in vendor-supplied binary; no auth-config surface; vendor will not modernize | Class 4 — Entra Domain Services |

When multiple classes apply, **prefer in order: Class 3 → Class 2 → Class 1 → Class 4**. OIDC is the cleanest end-state; Class 4 is a deliberate carve-out for the residual.

## Rationale

1. **Four classes cover the discoverable surface.** Empirically, every LDAP-dependent application observed in federal-modernization engagements falls into one of these four classes. The four-class taxonomy is exhaustive without being aspirational.

2. **The ordering preference reflects end-state quality.** OIDC apps have the cleanest identity story (modern protocol, token-based, scope-bound); SAML apps are mature but legacy-flavored; App Proxy apps preserve the legacy app surface with a modernized ingress; Entra Domain Services apps preserve the legacy LDAP semantic entirely. The migration pipeline should push each app to the highest-quality class it supports.

3. **Class 4 prevents the spec from being aspirational.** A small number of applications genuinely cannot be migrated by any reasonable timeline. Class 4 acknowledges this and provides a documented carve-out path that does **not** preserve the on-prem AD trust as the authoritative directory.

4. **Per-class transformation is well-bounded.** Each class has a documented vendor implementation (Microsoft's Entra ID App Proxy, Entra SAML SSO, Entra OIDC, Entra Domain Services). The migration team executes the per-class pattern; the pattern itself is not invented per engagement.

5. **The taxonomy enables migration-audit certification.** Every discovered LDAP-bind app gets a classification; every classification has a target state; the post-migration audit can certify that every app is in its target state (or in the documented Class 4 carve-out) before the on-prem AD is retired.

## Implementation Plan

| Phase | Deliverable | Owner | Input |
|---|---|---|---|
| **Discovery** | Run `Spec3-D1.9-Get-LDAPBindAccountInventory.ps1` | Identity team | On-prem AD |
| **Classification** | Tag each discovered app with its canonical class per the detection signals above | Identity team + App owner | Discovery output |
| **Class 1 execution** | Configure Entra ID Application Proxy for each App Proxy-class app | Identity team | Tagged inventory |
| **Class 2 execution** | Configure Entra SAML SSO for each SAML-class app; coordinate with SaaS vendor on metadata exchange | Identity team + App owner | Tagged inventory |
| **Class 3 execution** | Reconfigure each OIDC-class app to use Entra OIDC; update app-side identity client | App owner | Tagged inventory |
| **Class 4 execution** | Provision Entra Domain Services; re-point each Class 4 app's LDAP bind to the managed surface | Identity team | Tagged inventory |
| **Audit** | Per-app sign-off that the target state is operational; on-prem AD retirement gated on 100% sign-off + Class 4 carve-out documented | Migration program | Per-class execution outputs |

## Consequences

**Positive:**
- Every LDAP-dependent app gets a documented migration target before on-prem AD retirement.
- The four-class taxonomy is exhaustive; engagements stop re-deriving the decision tree.
- Class 4 prevents the residual from blocking AD retirement while honestly accepting the long-tail.
- Per-class patterns are well-bounded; execution is repeatable across engagements.

**Negative:**
- Class 1 (App Proxy) preserves the legacy app surface, which means those apps remain a modernization debt even after their authentication is modernized.
- Class 4 (Entra Domain Services) is a non-trivial Azure cost and adds an operational surface that has to be governed in its own right. Acceptable as a carve-out but not as the default.
- Classification disagreements (e.g., an app whose vendor claims OIDC support but whose deployment is hard-bound to LDAP) require per-app investigation; the four-class assignment cannot be fully automated.

**Operationally accepted:** the migration audit must enumerate every discovered LDAP-bind app, its assigned class, its target-state validation timestamp, and (for Class 4) the per-app ADR documenting why no higher-quality class applies.

## References

- ADR-004 — Workload identity federation as default (overlaps with Class 3 for workload identity)
- ADR-051 — SAML federation trust anchor (consumed by Class 2)
- UIAO_135 §3.2 — Partially Defined transformation gaps
- Spec3-D1.9 — `Get-LDAPBindAccountInventory.ps1` (provides the input inventory)
- Microsoft Learn: "Entra ID Application Proxy" — Class 1 reference architecture
- Microsoft Learn: "Entra SAML SSO" — Class 2 reference architecture
- Microsoft Learn: "Entra OIDC and OAuth 2.0" — Class 3 reference architecture
- Microsoft Learn: "Microsoft Entra Domain Services" — Class 4 reference architecture
