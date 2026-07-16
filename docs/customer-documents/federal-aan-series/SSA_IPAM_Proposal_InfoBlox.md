---
title: "Executive Brief — Standardize DDI (DNS · DHCP · IPAM) on Infoblox"
subtitle: "Why authoritative DDI is a compliance requirement, not a networking preference — and why Infoblox is the deployable answer"
author: "CSI Team (Cloud Services Infrastructure)"
date: "2026-07-12 15:00 ET"
---

::: {.callout-warning}
**Draft proposal — CSI Team.** Not yet reviewed by the CIO Office, OIS, or leadership.
FedRAMP scope: **Moderate only** (GCC Moderate / FedRAMP Moderate). Vendor authorization
facts are stated at the level published on the FedRAMP Marketplace and **must be
re-verified at time of procurement**. **Date Code:** 2026-07-12 15:00 ET
:::

## Bottom line up front

**Recommendation: standardize the agency's DNS, DHCP, and IP Address Management (DDI)
on a single authoritative Infoblox platform, deployed inside our authorization
boundary.** This is not a tooling preference. A specific, enumerable set of federal
security controls **cannot be closed by any other mechanism**, and the authoritative
asset identity DDI produces is the join key on which our ServiceNow automation,
patch management, and continuous-monitoring evidence all depend. One Infoblox
deployment closes **16 NIST SP 800-53 Rev 5 controls** across our four environments
that would otherwise require manual, four-source evidence assembly at every assessment.

## 1. What federal compliance actually requires

Our authorization (FedRAMP Moderate, NIST 800-53 Rev 5) obligates us to *demonstrate*,
with evidence, that we operate:

- **Authoritative, secure name/address resolution** — SC-20, SC-20(1), SC-21, SC-22
  (DNSSEC-signed authoritative resolution, validating recursive resolution, protective
  DNS).
- **A complete, authoritative inventory of every system component, keyed to its
  address** — CM-8, reinforced by **CISA BOD 23-01** (enterprise asset visibility and
  vulnerability enumeration across exactly our multi-cloud heterogeneity).

These are *demonstrate-with-evidence* obligations, not best-effort ones.

## 2. Why this is required, not preferred — there is no alternate path

::: {.callout-important}
**A scanner measures drift *from* a source of truth. It cannot *author* one.** You
cannot attest authoritative name resolution without an authoritative resolver, and
you cannot inventory what you cannot enumerate. This is the whole argument in one line.
:::

The tempting objection is "we already have DNS in each cloud." We do — and that is the
problem, not the solution:

- **Native per-cloud DNS (Azure DNS, AWS Route 53) gives us *N* disconnected naming
  services, not one authoritative naming plane.** Each is a silo; none is the
  cross-environment source of truth SC-20/22 require, and none produces a unified,
  address-keyed component inventory for CM-8.
- **No scanner, no spreadsheet, and no policy document closes these controls.** They
  can only *measure* against a source of truth that something else must author. That
  "something" is an authoritative DDI/IPAM platform. There is no configuration setting
  that substitutes for it.

Result: SC-20, SC-20(1), SC-21, SC-22, and CM-8 have **no alternate closure path**.
Authoritative DDI is the mechanism; everything else is measurement of it.

## 3. The multiplier — DDI is the keystone of the whole program

This is the part that makes DDI a leadership decision rather than a networking one:

> **The address-keyed asset identity DDI produces (the CM-8 join key) is the single
> identity that lets our ServiceNow CMDB, our multi-cloud patch queue, and our
> continuous-monitoring evidence fabric reconcile into *one* compliance picture.**

Every downstream automation we are standing up — ServiceNow compliance coordination,
helpdesk and landing-zone provisioning, Entra/Azure/M365 control tracking — routes work
*to an asset*. Without one authoritative identity, the same server appears as three
records, a remediation closes against the wrong one, and the audit trail forks. **DDI is
upstream of the entire automation and ATO-evidence chain.** Defer it and every
downstream control loses its join key; the automation program is built on sand.

## 4. Why Infoblox

- **It is FedRAMP-authorized at our boundary level.** Infoblox DDI is one of a small
  number of FedRAMP **Moderate**-authorized DDI platforms — Marketplace listing
  *Infoblox Government Cloud*, **CSO FR2017257053**, authorized January 2023, hosted on
  AWS GovCloud. *(Re-verify current scope and authorization date on the FedRAMP
  Marketplace at procurement.)*
- **It closes the controls directly.** A single deployment spanning all four
  environments closes **16 NIST 800-53 Rev 5 controls** and produces a complete evidence
  package for annual assessment — no manual collection from four sources — and positions
  us ahead of the FedRAMP 20x KSI transition.
- **It already fits our stack.** Infoblox runs *on* AWS GovCloud; is a Microsoft Azure
  Technology Alliance Partner with native Sentinel, Defender Threat Intelligence, and
  **Entra ID** integrations (Grid admin auth governed by our Conditional Access); and is
  procurable via the **Azure Government Marketplace** against existing EA/ELA agreements
  — no separate IDIQ.
- **It can run inside our boundary.** For our topology the agency-operated path (Infoblox
  in our own authorization boundary) is the better fit; the SaaS portal stays outside the
  boundary and is gated by an explicit authorization review, so credentials and control
  never leave the boundary.

## 5. What we are not claiming

We claim only what our boundary targets: **FedRAMP Moderate.** Where an underlying
service holds a higher authorization we refer to it simply as *FedRAMP-authorized*. This
brief evaluates Infoblox as the deployed example; the load-bearing claim is the
*mechanism* (authoritative DDI/IPAM), and the vendor authorization is verified at
procurement.

## 6. The cost of doing nothing

- **Uncloseable controls.** SC-20/21/22 and CM-8 remain best-effort assertions no
  assessor can trace — a standing finding at every assessment.
- **A forked inventory.** Automation routes work into ambiguity; CMDB, patch, and
  evidence never reconcile into one picture (a CM-8 / BOD 23-01 gap).
- **Manual evidence forever.** Every annual assessment repeats four-source, hand-assembled
  evidence collection — the exact cost the FedRAMP 20x KSI model is meant to retire.

## 7. The ask

1. **Approve standardizing DDI on Infoblox**, deployed inside the authorization boundary.
2. Authorize a procurement-time FedRAMP Marketplace verification (CSO FR2017257053) and a
   right-sized capacity/cost estimate across the four environments.
3. Sequence DDI **first** in the automation roadmap — it is the join key the ServiceNow
   compliance, helpdesk, and landing-zone workstreams depend on.

## Sources & provenance

Vendor authorization and integration facts are drawn from the agency's own analysis and
must be re-verified at procurement:

- Landing-zone / IPAM analysis and the 16-control mapping: `docs/customer-documents/federal-aan-series/SSA_Landing_Zone_IPAM_FedRAMP.md` and `Vol_I_Book_01_FedAAN_SSA_Landing_Zone_IPAM_FedRAMP.qmd`.
- Control-closure necessity (SC-20/21/22, CM-8): the series compliance spine, `docs/customer-documents/federal-aan-series/aan-compliance-spine.yml`.
- Multi-cloud DDI realization: `infoblox-ddi-book/` (series Volume VIII).
- FedRAMP authorization: **FedRAMP Marketplace** — *Infoblox Government Cloud*, CSO FR2017257053 (verify at procurement). NIST SP 800-53 Rev 5 (Moderate baseline); CISA BOD 23-01.
