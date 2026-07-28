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

**Recommendation: commission a discovery-only DDI/IPAM assessment now, and standardize
on a single authoritative platform once that assessment gives us numbers, not a
category.** "Federal compliance" does not name a vendor, and no BOD, OMB memo, or
800-53 control obligates any specific commercial DDI product — a category argument
alone will not survive a CIO or budget review. What will survive it: three measured
gaps (unreconciled address ranges across our environments, stale/orphaned DNS
records, and assets absent from our CMDB), bound explicitly to **OMB M-21-07** (we
cannot execute the IPv6-only mandate without an authoritative address inventory) and
**CISA BOD 23-01** (enterprise asset visibility). This brief lays out why DDI
consolidation is the mechanism that closes those gaps once measured, evaluates
Infoblox as the deployable example, and asks for the assessment and an ownership
decision before it asks for a platform. A single authoritative DDI platform, once
justified by that evidence, would close up to **16 NIST SP 800-53 Rev 5 controls**
across our four environments that would otherwise require manual, four-source
evidence assembly at every assessment.

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

## 2. This is a reconciliation problem, not a "we need DNS security" problem

The honest starting point: **we are not DNS-blind today.** We run Windows DNS/DHCP
tied to Active Directory, cloud-native IPAM in each CSP we operate in, and CISA
Protective DNS is available to us at no cost. Anyone reviewing this brief will ask
why that isn't enough — and "we need DNS security" is the wrong answer, because
PDNS already covers a meaningful slice of that ask. The right answer is narrower and
harder to wave away:

::: {.callout-important}
**None of our existing tools reconciles across the other three.** Windows DNS/DHCP,
each CSP's native IPAM, and PDNS each answer for their own slice of the estate. **No
one of them — and no scanner reading any one of them — can tell us whether the same
address means the same thing in two of those systems at once.** That reconciliation
is what SC-20/SC-22 (authoritative, consistently-provisioned resolution) and CM-8
(one inventory, not four) actually require, and it is the argument this brief rests
on, not "DNS security" in the abstract.
:::

- **Four systems of record, not one.** Windows DNS/DHCP-on-AD, per-CSP IPAM, and PDNS
  policy each have their own view of what exists. Where they disagree — a decommissioned
  host still resolving, an address reused across two environments, a record neither
  AD nor the CSP knows about — nothing today catches it, because nothing today compares
  them to each other.
- **A scanner measures drift *from* a source of truth; it cannot *author* one.** PDNS
  and per-CSP IPAM are each a source of truth for their own slice. Closing SC-20/22
  and CM-8 agency-wide requires one source of truth that spans all four environments —
  the thing none of our current tools is positioned to be, because none was deployed
  to reconcile across the other three.

This is the argument the discovery assessment (§8) is meant to make concrete: name the
unreconciled ranges, the orphaned records, and the CMDB gap, and the reconciliation
case makes itself.

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

## 4. Ownership — the decision this brief cannot make for itself

This brief is authored by the CSI Team (Cloud Services Infrastructure). At most
agencies, DDI — DNS, DHCP, and IP address management — is owned by the network
organization, not by a cloud/systems-operations function. **If ownership of DDI is
contested, the technical merit of this brief is irrelevant until that is resolved** —
a compliance argument does not settle an org-chart question, and a platform decision
made by the wrong owner will not stick. Before this goes to the CIO Office or OIS,
CSI should confirm with the network organization (and, if applicable, Systems
Operations and Hardware Engineering) who owns DDI standardization, and bring this
brief forward jointly or explicitly as input to whoever does.

## 5. Why Infoblox

- **It is FedRAMP-authorized at our boundary level — as of six days ago, specifically
  for DDI.** CSO FR2017257053 has a two-stage history that this brief must state
  precisely: it was originally authorized **December 15, 2022** (Census/Commerce
  sponsored) for **BloxOne Threat Defense Federal Cloud** — a DNS-security/threat-intel
  service (Cloud Services Portal, TIDE, Dossier), not DDI/IPAM. On **July 22, 2026**,
  the same CSO — rebranded *Infoblox Government Cloud*, hosted on AWS GovCloud —
  was recertified FedRAMP **Moderate** with an expanded boundary adding **Universal
  DDI Management, NIOS-X Servers, and Universal Asset Insights**. The DDI authorization
  this brief relies on is six days old, not three years old. *(Re-verify current scope,
  sponsoring agency, and package status on the FedRAMP Marketplace at procurement —
  this is a freshly expanded boundary, not a settled one.)*
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

## 6. What we are not claiming

We claim only what our boundary targets: **FedRAMP Moderate.** Where an underlying
service holds a higher authorization we refer to it simply as *FedRAMP-authorized*. This
brief evaluates Infoblox as the deployed example; the load-bearing claim is the
*mechanism* (authoritative DDI/IPAM), and the vendor authorization is verified at
procurement.

## 7. The cost of doing nothing

- **Uncloseable controls.** SC-20/21/22 and CM-8 remain best-effort assertions no
  assessor can trace — a standing finding at every assessment.
- **A forked inventory.** Automation routes work into ambiguity; CMDB, patch, and
  evidence never reconcile into one picture (a CM-8 / BOD 23-01 gap).
- **Manual evidence forever.** Every annual assessment repeats four-source, hand-assembled
  evidence collection — the exact cost the FedRAMP 20x KSI model is meant to retire.

## 8. The ask

1. **Commission a discovery-only DDI/IPAM assessment** (no procurement decision implied)
   across the four environments, reporting three numbers: unreconciled address ranges
   between systems of record, stale/orphaned DNS records, and assets present in the
   estate but absent from the CMDB. Bind the findings to **OMB M-21-07** (IPv6-only
   transition milestones cannot be executed without an authoritative address inventory)
   and **CISA BOD 23-01** (asset visibility).
2. **Resolve ownership** (§4) — confirm with the network organization who owns DDI
   standardization before this goes to the CIO Office or OIS.
3. Contingent on the assessment findings and ownership resolution, **approve
   standardizing DDI on a single authoritative platform**, deployed inside the
   authorization boundary, and authorize a procurement-time FedRAMP Marketplace
   verification (CSO FR2017257053) plus a right-sized capacity/cost estimate.
4. If approved, sequence DDI **first** in the automation roadmap — it is the join key
   the ServiceNow compliance, helpdesk, and landing-zone workstreams depend on.

## 9. Independent checks before this brief goes anywhere

This brief has not yet done the following, and should not be sent to the CIO Office,
OIS, or leadership until it has:

- **Check the FedRAMP Marketplace listing directly** (not the vendor press release) —
  confirm the current impact level, package/component boundary, and whether the DDI
  scope carries an **agency-specific ATO** or only a **JAB/P-ATO designation**. These
  imply different inheritance postures for us.
- **Pull our own open FISMA/IG findings** touching asset inventory and DNS. If no open
  finding maps to this brief's argument, the case is weaker than §1–3 suggest and should
  say so plainly rather than argue from a compliance category in the abstract.
- **Check our actual M-21-07 IPv6 transition plan status** against OMB's milestones —
  this brief's IPv6 tie-in is only as strong as our own transition timeline.
- **A reference call is not a slam dunk here.** The obvious ask would be Census — but
  Census sponsored the **2022/2023 BloxOne Threat Defense** authorization, not the DDI
  scope; nothing in that sponsorship establishes that Census (or anyone) is running
  production DDI under this ATO, since the DDI scope on CSO FR2017257053 is six days
  old as of this writing. If a reference is required, find an agency actually operating
  Infoblox Government Cloud's Universal DDI Management under the July 2026 boundary —
  not one running BloxOne Threat Defense.

## Sources & provenance

Vendor authorization and integration facts are drawn from the agency's own analysis and
must be re-verified at procurement:

- Landing-zone / IPAM analysis and the 16-control mapping: `docs/customer-documents/orgcomp-series/SSA_Landing_Zone_IPAM_FedRAMP.md` and `Vol_I_Book_01_OrgComp_SSA_Landing_Zone_IPAM_FedRAMP.qmd`.
- Control-closure necessity (SC-20/21/22, CM-8): the series compliance spine, `docs/customer-documents/orgcomp-series/orgcomp-compliance-spine.yml`.
- Multi-cloud DDI realization: `infoblox-ddi-book/` (series Volume VIII).
- FedRAMP authorization: **FedRAMP Marketplace** — *Infoblox Government Cloud*, CSO
  FR2017257053, DDI scope added July 22, 2026 (verify at procurement; original Dec
  15, 2022 authorization under this CSO covered BloxOne Threat Defense Federal
  Cloud only, per Infoblox's Jan 26, 2023 press release). NIST SP 800-53 Rev 5
  (Moderate baseline); CISA BOD 23-01.
