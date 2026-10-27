---
title: "SOW as the Authority for Contractor Movers — Draft Pattern"
status: DRAFT
date: 2026-10-20
author: Michael Stratton
related:
  - src/uiao/canon/specs/Spec2-D3.1-APIDrivenInboundProvisioningArchitecture.md
  - src/uiao/canon/UIAO_151_OrgPath_Codebook.md
  - docs/customer-documents/whitepapers/snowflake-keypair-vs-uiao-orgpath.qmd
---

# SOW as the Authority for Contractor Movers

> **Draft, not canon.** This is an input to the open contractor-source question
> (HR contingent-worker record vs. NERM / PIV sponsorship). It proposes no ADR
> number and changes no existing spec.

## 1. Problem

HR-driven provisioning works when HR is the system that knows a change has
happened. For employees it usually is. For contractors and volunteers it
usually isn't.

The failure that matters in practice is the **mover**, not the joiner or the
leaver:

- A contracting team or volunteer group is re-chartered under the **next SOW**
  against a **different cost center**.
- The contract office knows this the day the new SOW is signed.
- HR either has no position record for these people, or updates it weeks
  late, or never.
- Entra keeps the old `CostCenter` value, and every downstream SCIM target
  (data platforms such as Snowflake, SaaS apps, license groups) keeps the
  old group-to-role mapping.

Nothing in the provisioning chain is broken. The engine faithfully
propagates **stale authority**. Joiners and leavers get noticed because
someone can't log in or someone still can. Movers fail silently: the person
keeps working, the wrong cost center pays, and access granted for the last
SOW outlives it.

Entra's own provisioning engine has the same weak spot. Joiner (create) and
leaver (`active:false`) are first-class operations. A mover is just an
attribute PATCH that happens only if the upstream value changes.

## 2. Principle

> **The authority for an attribute is the system that knows first when it
> changes.**

For a contractor's cost center, project, sponsor, and end date, that system
is the **contract instrument (the SOW / task order)**, not the HR position.
HR stays authoritative for things HR actually owns (legal name, employee
status, the person record where one exists). Attribute authority is split
**per facet**, not per person.

## 3. Pattern

```
 SOW / contract system          HR (where a record exists)
   cost center, project,          legal name, worker type,
   sponsor/COR, SOW start/end     employee status
            \                        /
             \                      /
          inbound provisioning middleware
          (per-facet source-of-authority table)
                       |
        Entra API-driven inbound provisioning
        (Spec2-D3.1: PATCH /Users/{externalId})
                       |
             Entra user + OrgPath facets
          (CostCenter = extensionAttribute5,
           Classification = extensionAttribute6)
                       |
        dynamic groups keyed on facets
                       |
     SCIM to downstream apps (group → role)
```

### 3.1 Per-facet source-of-authority table

| Facet / attribute | Employee source | Contractor / volunteer source |
|---|---|---|
| Legal name, person ID | HR | HR contingent-worker record if one exists; otherwise sponsor-entered at onboarding |
| `Classification` | HR | Contract system (`Contractor`) |
| `CostCenter` | HR position | **Active SOW** |
| Department / Division | HR position | **Active SOW** (performing organization) |
| Manager / approver | HR | **COR / sponsor named on the SOW** |
| End date | HR termination | **SOW period-of-performance end** (hard ceiling) |

The middleware resolves each facet from its row's source. It never falls
back to HR for a contractor facet the SOW owns, because the fallback is
exactly how stale values persist.

### 3.2 The SOW-transition event

The re-charter is modelled as one explicit event, not as an incidental edit:

1. **New SOW executed** → the contract system emits `sow.transition`
   naming the old SOW, the new SOW, and the people carried over.
2. Middleware computes facet deltas (cost center, department, sponsor, end
   date) per person.
3. Middleware sends **one PATCH per person** through API-driven inbound
   provisioning (Spec2-D3.1 mover row, `active` unchanged).
4. Dynamic groups re-evaluate on the new `CostCenter` / Department values.
   Downstream SCIM moves app roles on its next cycle. Old-SOW groups drop
   out without a manual removal.
5. **Anyone not carried over** reaches the old SOW's end date and goes
   through the leaver path (Spec2-D2.3), even if HR never acts.

### 3.3 The SOW end date is a dead-man's switch

Every contractor identity carries the active SOW's period-of-performance end
as its access ceiling. When no `sow.transition` or extension arrives by that
date, the identity is disabled. The default flips from "access persists
until someone notices" to "access expires unless the contract says
otherwise", which matches what the contract actually authorizes.

## 4. Why not just fix HR

- HR has no business process for a cost-center change on a non-employee, and
  often no record to change. Asking HR to own it adds a step to a
  department that has no reason to do it promptly.
- The contract office already performs this action as part of executing the
  SOW. Capturing the event there costs a feed, not a new business process.
- Fixing timeliness at the wrong source still leaves a lag between the
  contract decision and the HR keystroke. Moving authority to the SOW
  removes the lag.

## 5. Handshake hygiene (downstream SCIM)

The pattern only fixes the data. Downstream SCIM connections still need care:

- **Two trusts, not one.** SSO (SAML) and provisioning (SCIM) are separate
  protocols with separate trust material: an X.509 signing certificate for
  SAML and a target-issued bearer token for SCIM. SSO alone does not
  deprovision. The service provider isn't told about changes between SAML
  requests, so a removed user can keep access until the session or token
  lapses. Mover and leaver correctness depends on the SCIM leg.
- **Token expiry.** Some targets issue bearer tokens with a fixed life.
  Snowflake's SCIM access token is valid for six months (two independent
  sources, §8). When it lapses, provisioning stops silently while the Entra
  side keeps "succeeding" at nothing. Each SCIM target should have its
  token-expiry date tracked and renewed before it lapses. Provisioning-log
  quarantine is the backstop signal, not the plan.
- **Sync is scheduled, not real-time.** Entra's SCIM cycle to Snowflake runs
  roughly every 20–40 minutes. A `sow.transition` therefore lands in
  downstream roles within one cycle, not instantly. That is fine for cost
  center, but the SOW-end ceiling (§3.3) should disable in Entra first
  (sign-in blocked at the IdP immediately), with SCIM `active:false`
  following on the next cycle.
- **Ownership of pre-existing users.** Targets such as Snowflake reject
  updates to users the provisioner role doesn't own. Users created before
  SCIM need an ownership transfer, or movers on them fail.
- **Group → role mapping stays in the target.** Keep the business logic
  (which cost center gets which role) in Entra facets and dynamic groups.
  The target only maps a group to a role, so a cost-center change needs no
  change in the target.

## 6. Open questions

1. **Which system holds the SOW roster?** A contract-writing system, a
   procurement module, or the COR spreadsheets that exist today? If only the
   spreadsheets, step one is a structured roster (person ↔ SOW ↔ cost
   center ↔ end date), however modest.
2. **Contractor person record:** HR contingent-worker record or NERM? This
   pattern works with either, since it only needs a stable `externalId`, but
   it pushes toward whichever can take the SOW feed natively.
3. **Volunteers** usually have no SOW. Is the equivalent instrument a
   sponsorship or agreement with a term date, handled the same way?
4. **Overlap periods.** When a person works under two SOWs at once, which
   cost center wins? The likely rule is primary SOW = the one with the later
   end date, with the other carried as a secondary facet for chargeback only.
5. Does `sow.transition` deserve its own event type next to
   `provisioning.user.mover` (Spec2-D3.1 §event schema), or is it a mover
   with a reason code?

## 7. Possible next steps (if pursued)

- Add the per-facet authority table (§3.1) as an appendix to the HRIT
  inbound-provisioning spec family.
- Add an SOW-end-date ceiling to the leaver workflow spec (Spec2-D2.3).
- Add a "SCIM target token-expiry register" to the operational guides.

## 8. Sources

- InterWorks, [An Overview on SSO with AD and SCIM for Snowflake](https://interworks.com/blog/2022/09/27/an-overview-on-sso-with-ad-and-scim-for-snowflake/)
  (2022-09-27): SAML vs SCIM trust separation, six-month SCIM token, 20–40 min
  sync cycle, SSO-alone deprovisioning gap.
- InterWorks, [SCIM and User Management for Snowflake with Azure AD](https://interworks.com/blog/2022/10/03/scim-and-user-management-for-snowflake-with-azure-ad/)
  (2022-10-03): step-by-step follow-up.
- phData, [How to Connect Azure AD SCIM to Snowflake](https://www.phdata.io/blog/how-to-connect-azure-ad-scim-to-snowflake/)
  (2023-05-16): six-month token, provisioner-role ownership of pre-existing
  users, regex group-to-role mapping.
- Microsoft Learn, [Entra governance: employee lifecycle](https://learn.microsoft.com/en-us/entra/architecture/governance-deployment-employee-lifecycle).
- Snowflake docs (cited in the source SQL, not yet re-verified here):
  `docs.snowflake.com/en/user-guide/scim-azure`,
  `docs.snowflake.com/en/sql-reference/sql/create-security-integration-scim`.
