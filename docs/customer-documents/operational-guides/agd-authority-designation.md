---
title: "AGD — OrgPath Authority Designation"
subtitle: "Policy stub designating the Active Governance Directory as authoritative for organizational placement"
document_id: UIAO_199
status: DRAFT
classification: UNCLASSIFIED
boundary: GCC-Moderate
publish_to_site: false
---

# OrgPath Authority Designation

> **Step 1D of the AGD in-path program.** This document is a policy stub —
> the structural shell that makes consulting the AGD an *obligation* rather
> than an option. Sections marked `[TO BE COMPLETED BY AGENCY]` require
> organizational sign-off and system-specific configuration. Until completed,
> the AGD is optional enrichment. Once signed, querying it is a governance
> requirement auditable against this document.
>
> **Completion gate for the baseline skeptical review:** Until this document
> is signed and the three named systems are configured, OrgPath cannot pass
> the "name one thing that fails if UIAO goes offline" test. This document
> is what makes that answer possible.

---

## 1. Declaration

`[TO BE COMPLETED BY AGENCY]`

> **[Agency Name]** hereby designates the UIAO Active Governance Directory
> (AGD) as the authoritative source for organizational placement data for
> all identity objects — human, device, and non-human — within the
> `[Agency Entra Tenant ID]` identity boundary.
>
> Effective date: `[DATE]`
> Authorizing official: `[Name, Title]`
> Review date: `[DATE + 1 year]`

**What "authoritative" means in this context:**

OrgPath canonical facets — Region, Department, Division, Role, Cost Center,
Classification, Clearance Level, and Account Type — are the governed
definitions for those attributes across all identity systems. Where a
downstream system (SailPoint ISC, ServiceNow, Entra) holds a copy of these
attributes, the AGD projection is the source those copies are reconciled
against. Divergence is a drift finding, not an acceptable variant.

---

## 2. Systems required to consult the AGD

The following systems must query the AGD for organizational placement data
before completing the named governance workflows. Each system's connector
configuration is the enforcement mechanism for this declaration.

### 2.1 SailPoint Identity Security Cloud

| Workflow | AGD query required before | Fallback if AGD offline |
|---|---|---|
| Access review campaign routing | Reviewer assignment | **Halt** — do not assign to unverified manager |
| Joiner provisioning | Role and division entitlement grant | **Halt** — do not grant without placement |
| Leaver deprovisioning | Confirmation of term_date | **Halt** — do not skip; flag for manual review |
| Contractor expiry review | term_date lookup | **Halt** — escalate to identity team |

Connector reference: [AGD SailPoint ISC connector guide](agd-sailpoint-connector.md)

`[TO BE COMPLETED BY AGENCY]`
> ISC Source name: `[UIAO Active Governance Directory — configured per connector guide]`
> Configured by: `[Name]` on `[DATE]`
> Test connection result: `[PASS / date of last successful aggregation]`

### 2.2 ServiceNow (CMDB / ITSM)

| Workflow | AGD query required before | Fallback if AGD offline |
|---|---|---|
| Incident routing | Manager lookup for approval | **Halt** — do not auto-route to unverified owner |
| Change request approval | Division-owner lookup | **Halt** — escalate to ISSO |
| CMDB CI ownership assignment | Department and cost_center lookup | **Halt** — mark CI as unowned |

`[TO BE COMPLETED BY AGENCY]`
> ServiceNow LDAP Data Source name: `[AGD — UIAO OrgPath]`
> Configured by: `[Name]` on `[DATE]`
> Scheduled import set: `[daily / weekly]` at `[TIME]`
> Last successful import: `[DATE]`

### 2.3 Entra Administrative Unit scoping

Entra Administrative Units (AUs) are already driven by OrgPath facets via
the `OrgTreeAdminUnitsAdapter` (ADR-037). This is the most mature AGD
dependency — AU membership is computed from the same codebook the AGD
projects. The AGD reinforces this by providing LDAP-queryable confirmation
of placement for tools that cannot call Graph directly.

`[TO BE COMPLETED BY AGENCY]`
> AU sync cadence: `[daily / on-change]`
> Governing adapter: `OrgTreeAdminUnitsAdapter` (ADR-037, plan/apply)
> Last apply run: `[DATE]`
> Drift findings since last run: `[COUNT or NONE]`

---

## 3. Governance SLA — what "offline" means

The AGD is a governance dependency. When it is unreachable, the workflows
in Section 2 **halt** — they do not fall back to cached, unverified, or
manually entered data. This is intentional.

**Why no fallback:** A fallback to unverified data defeats the purpose of
the authority designation. If SailPoint falls back to Entra
`onPremisesExtensionAttributes` when the AGD is offline, the AGD is not
authoritative — it is optional enrichment. The halt behavior is what makes
the dependency real.

| Condition | Required response | SLA |
|---|---|---|
| AGD unreachable < 15 min | Identity team notified; workflows queue | 15 minutes |
| AGD unreachable 15 min – 4 hr | Incident opened; ISSO notified | 4 hours |
| AGD unreachable > 4 hr | Emergency restart; root cause documented | Same business day |
| AGD data stale > refresh cadence | Drift finding raised; refresh triggered | Next scheduled window |

`[TO BE COMPLETED BY AGENCY]`
> AGD monitoring: `[Tool / dashboard / alert name]`
> On-call contact: `[Name / team]`
> Restart runbook: `[Link or location]`

---

## 4. Audit hooks — verifying the AGD is actually consulted

A future audit verifies compliance with this designation by checking the
following evidence artifacts:

| Audit check | Evidence source | Pass condition |
|---|---|---|
| ISC aggregation from AGD | ISC Admin → Sources → UIAO AGD → Aggregation history | Successful aggregation within cadence window |
| ISC access review routing | ISC certification campaign logs | Reviewer assignments reference OrgPath attributes |
| ServiceNow import set | ServiceNow → System Import Sets → AGD import | Import completed within cadence window |
| Entra AU membership | `uiao orgtree govern --check` output | Zero drift findings on AU membership |
| AGD uptime | Monitoring dashboard | < 4 hr cumulative downtime per quarter |

`[TO BE COMPLETED BY AGENCY]`
> Audit frequency: `[quarterly / annual]`
> Auditor: `[Name / team]`
> Evidence retained in: `[SharePoint / ServiceNow / UIAO evidence bundle]`

---

## 5. What this designation does NOT cover

This document designates the AGD as authoritative for **organizational
placement** only. It does not:

- **Replace Entra as the authentication authority** — credentials, MFA,
  and conditional access policy remain with Entra. The AGD does not
  issue tokens or validate passwords.
- **Replace SailPoint as the provisioning authority** — entitlement grants
  and revocations are executed by SailPoint against Entra. The AGD
  provides the placement data SailPoint uses to make those decisions.
- **Govern network admission** — device compliance and network policy
  enforcement remain with Intune and Entra Conditional Access, informed
  by OrgPath but not driven by the AGD directly.
- **Cover non-managed identities** — shared accounts, local admin accounts,
  and identities outside the Entra tenant boundary are out of scope until
  a separate designation covers them.

---

## 6. Completion checklist

- [ ] Section 1 — Declaration signed by authorizing official
- [ ] Section 2.1 — SailPoint ISC source configured and test connection passing
- [ ] Section 2.2 — ServiceNow LDAP data source configured and import set running
- [ ] Section 2.3 — Entra AU adapter confirmed running with zero drift
- [ ] Section 3 — Monitoring and on-call contacts populated
- [ ] Section 4 — Audit cadence and evidence location documented
- [ ] AGD running in production with restart runbook in place
- [ ] This document filed in the agency's governance record system

**When this checklist is complete:** the answer to "name one thing that
fails if UIAO goes offline" is: SailPoint ISC access review routing,
ServiceNow incident routing, and Entra AU scoping all halt. OrgPath is
load-bearing.

---

## Related

- [AGD SailPoint ISC connector guide](agd-sailpoint-connector.md)
- [ADR-100 — AGD LDAPv3 read projection](../../../adr/adr-100-active-governance-directory-ldap.html)
- [ADR-092 — Active Governance](../../../adr/adr-092-active-governance.html)
- [OrgPath codebook (UIAO_151)](../../../specs/OrgPath-Codebook.html)
- [Baseline skeptical evaluation](../../../inbox/startup-assessment/uiao-startup-assessment-2026-06-09.md)
