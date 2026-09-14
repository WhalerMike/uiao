---
title: "Attachment B — Architecture Review Determination"
subtitle: "TIC 3.0 classification and PEP capability transfer for M365 Optimize local egress, verified against Security Capabilities Catalog v3.3"
doc-type: operational-guide
audience: [Customer, Architect, Technical-Lead]
author: Michael Stratton
date: "September 2026"
status: Draft
canon-source: "inbox/M365-INR-GCC-Moderate/attachment-b-architecture-review.html"
derived-from: "CISA TIC 3.0 Security Capabilities Catalog Volume 3 v3.3 (July 2025), read from source — Tables 3 through 15; TIC 3.0 Branch Office Use Case; NIST SP 800-53 Rev 5; the SD-WAN vs. DIA whitepaper section 5.5."
repo-path: docs/customer-documents/operational-guides/m365-optimize-exemption/attachment-b-architecture-review.qmd
created-at: 2026-09-14
updated-at: 2026-09-14
version: "1.0"
format:
  html:
    toc: true
    toc-depth: 2
  docx:
    toc: true
lifecycle: draft
tiers_adopted: []
lifecycle_review: 2027-03-14
---

# Attachment B — Architecture Review Determination {.unnumbered}

::: {.callout-warning}
## Template — complete against the current SCC and Reference Architecture before the review convenes
:::

| Field | Value |
| --- | --- |
| **Attaches to** | SC-7(4) traffic-flow exception — [M365 Optimize endpoint set at branch DIA](sc7-4-exception-memo.qmd) |
| **Scope** | Sites listed at [Attachment A](attachment-a-site-register.qmd), version *[n]* |
| **Prepared by** | *[Name, title]* |
| **Reviewed by** | *[Architecture review board / date convened]* |
| **Guidance used** | TIC 3.0 Security Capabilities Catalog **v3.3 (July 2025)**; Reference Architecture *[version]*; Branch Office Use Case |

::: {.callout-note}
## Sourcing of the catalog facts in this document

The catalog **has been read from source**: *CISA TIC 3.0 Security Capabilities
Catalog, Volume 3, v3.3, July 2025*. The twelve PEP capability groups below are
Tables 4 through 15 of that document and match its own bulleted list in §4.2.
The Universal Security Capabilities in the separate table are Table 3, §4.1,
with their capability identifiers. Group names, ordering and the
universal-versus-PEP distinction are verified, not inferred.

The catalog states that *"the PEP security capability groups listing is not
exhaustive"* and that additional groups may be developed for new use cases, so
the count remains a property of the revision. Confirm the revision in the
header against the current one before the review convenes.

**The NIST control references at B2 remain this document's own proposal and
carry no external authority.** The catalog maps PEP capabilities to NIST CSF
categories, not to SP 800-53 controls. That column is the review board's work
product and still needs confirming.
:::

::: {.callout-important}
## What this determination is, and is not

This document records the architecture review's finding that the design is TIC
3.0 conformant and that campus policy enforcement point capabilities have been
accounted for at the branch. **It does not accept risk.** The single item
requiring the Authorizing Official's decision — the Optimize-category
inspection exemption, sought as a documented **SC-7(4)** traffic-flow
exception — is referred to them in the covering memo. Keeping those two
decisions separate is what allows each signer to answer a question that is
actually theirs.
:::

## B1 — Security pattern classification

The Branch Office Use Case defines three patterns. An agency may implement a
subset. Classification is not bookkeeping: it determines which policy
enforcement point capabilities apply, and a misclassification here propagates
into every row of B2.

- ☐ **Branch Office to Cloud Service Provider** — *proposed.* Branch users
  reaching an agency-sanctioned CSP. Microsoft 365 is a sanctioned service
  under *[reference]*, which places locally egressing Optimize traffic in this
  pattern.
- ☐ **Branch Office to Web** — generic internet destinations. Selecting this
  pattern for Microsoft 365 pulls in a general web-proxy capability set whose
  inspection expectations are incompatible with the Optimize category's
  purpose.
- ☐ **Branch Office to Agency Campus** — branch access to internal resources.
  Applies to the site's other traffic and is unchanged by this design; recorded
  here for completeness.

**Board rationale where the determination differs from the proposal:**
*[record here]*

### Trust zone and enforcement point

TIC 3.0 permits policy enforcement points to sit between, before, or within a
trust zone. Record the definition this design adopts:

| Field | Value |
| --- | --- |
| **Trust zone** | *[Branch site as defined — scope and boundary]* |
| **PEP location** | *[Device and position relative to the zone]* |
| **Prior state** | Enforcement at the campus PEP, reached by backhaul |
| **Reversion** | Returns enforcement to the campus PEP — the prior posture is restored, not degraded |

## B2 — Capability transfer register

One row per PEP capability group in the catalog — **twelve in v3.3**. Complete
every row: a blank row is a gap, not an omission, and is treated as such by
this review.

The **control reference** column is the agency's own NIST SP 800-53 mapping.
The catalog itself maps PEP capabilities to NIST CSF categories, not to 800-53
controls, so this column is the review board's work product rather than a
catalog citation. The entries shown are proposed; confirm or replace them.

| PEP capability group | What branch DIA changes | Where enforcement now sits | Control reference | Status |
| --- | --- | --- | --- | --- |
| **Files** | SharePoint and OneDrive transfers bypass campus file inspection when steered locally. | *[Defender for Office 365 safe attachments; Purview DLP; endpoint DLP]* | SI-3, AC-4 | Enforced tenant-side |
| **Email** | Exchange Online traffic steered locally no longer passes campus email inspection on that path. | *[Exchange Online Protection; Defender for Office 365 policies in force]* | SI-3, SI-8, AC-4 | Enforced tenant-side |
| **Web** | Optimize-category traffic no longer traverses the campus web PEP. What that punctures, named rather than described as inspection forgone: no SWG inline malicious-code inspection (**SI-3**), no visibility into the content of encrypted communications (**SI-4(10)**), no CASB information-flow enforcement (**AC-4**), and audit records whose content is five-tuple plus steering metadata rather than user, device, application, action and data type (**AU-3**). **SC-8 is not punctured** — Optimize flows carry TLS and SRTP, and the overlay encrypts the rest. | *[Identity, service and endpoint controls per memo clause 6]* | SI-3, SI-4(10), AC-4, AU-3/AU-12; sought under SC-7(4) | **Referred to AO** |
| **Networking** | Enforcement moves to the branch edge — DIA NAT, ACLs, and the SD-WAN policy governing local egress. The steering log is the SC-7(4) enforcement evidence for the exception above. | *[Branch device and policy; steering log retention and location]* | SC-7, SC-7(4), AC-4 | Enforced at branch |
| **Resiliency** | Microsoft 365 reachability at the site now depends on the local circuit. Failure behavior must be defined, not incidental. | *[Failback to backhaul on DIA loss — state trigger and timing]* | SC-5, SC-6, CP-8 | *[status]* |
| **Domain Name System** | Resolution moves local. DNS security enforcement that sat on the campus path does not follow automatically, and resolver location also determines which Microsoft front door the site reaches. | *[Protective DNS / branch resolver policy; FedRAMP-authorized DNS security service]* | SC-20, SC-21, SC-22 | *[status]* |
| **Intrusion Detection** | Branch egress is not observed by the sensors covering campus egress. | *[Branch UTD or equivalent — or state the coverage gap plainly]* | SI-4, SI-4(4) | *[status]* |
| **Enterprise** | Identity enforcement is unchanged by routing but becomes the primary control on a less-inspected path. **Tenant restrictions v2 signaling moves here**: proxy header injection is lost with the bypass, so the cross-tenant access policy must be signaled from the endpoint. **Windows Group Policy is the only available path** — it alone reaches the data plane, and Global Secure Access, which would otherwise serve, is non-FIPS in GCC Moderate and unavailable in GCC High and DoD. See memo clause 4. | *[Conditional Access policies; cross-tenant access policy; device-side TRv2 configuration and the population it does not cover]* | IA-2, AC-2, AC-6, AC-4 | Enforced tenant-side |
| **Unified Communications and Collaboration** | Teams media egresses locally — one of the workloads this design exists to improve, and squarely in scope. | *[UCC controls applying to Teams media at branch]* | SC-8, SC-8(1), AC-4 | *[status]* |
| **Data Protection** | Content leaving via branch egress is outside campus data-protection enforcement on that path. | *[Purview DLP coverage; sensitivity labeling; endpoint DLP]* | SC-28, SC-8, AC-4 | *[status]* |
| **Services** | Catalog Table 14: Active Content Mitigation, Data Loss Prevention, Protocol Compliance Enforcement, Malicious Content Filtering, Access Control. Several restate at the service layer what the Web row gives up at the network layer, so this row is where the exemption is answered rather than repeated. | *[Assess each against the design]* | *[map from catalog]* | *[status]* |
| **Identity** | Catalog Table 15: Adaptive Authentication, Service Identity, Entitlement Inventory, Secrets Management, Behavioral Baselining. Overlaps Enterprise, so record the split your agency uses. | *[Assess each; note which carry the tenant-restrictions signaling from the Enterprise row]* | *[map from catalog]* | *[status]* |

::: {.callout-warning}
## The group list is a property of the catalog version, not of TIC 3.0

**The list has grown, and not in the revision you might assume.** Per the
catalog's own revision history, **Services and Identity were added as groups in
v3.0 (April 2023)**, bringing the total to twelve. **v3.3 (July 2025) added no
groups at all** — its sole recorded change is the removal of an NCPS reference
in Appendix A. A table copied forward from a pre-v3.0 revision will be short by
two groups and will read as complete, which is why the revision must be named
wherever the list is used.
:::

### Universal Security Capabilities

**These are not PEP capability groups and do not belong in the table above.**
The catalog treats universal capabilities as enterprise-level and expected in
every use case, whereas PEP capabilities apply or not according to the use case
scope. Conflating the two is a common way for a capability-transfer register to
look complete while leaving the enterprise layer unexamined.

Most are unchanged by a routing decision. Three are not, and this review should
record them:

| Universal capability | What branch DIA changes | Where enforcement now sits | Status |
| --- | --- | --- | --- |
| **Central Log Management with Analysis** (`3.UNI.CLMAN`) | Branch egress does not traverse the sensors that observed campus egress, so the log sources feeding central analysis change. | *[Branch PEP log sources; collection path; retention]* | *[status]* |
| **Auditing and Accounting** (`3.UNI.AACCO`) | Audit record content thins on the bypassed flows, as recorded in the Web row above. | *[AU-3 content actually captured at the branch; CLAW reporting pattern reference]* | *[status]* |
| **Policy Enforcement Parity** (`3.UNI.PEPAR`) | **The capability this design is most in tension with.** The catalog defines it as *"consistently applying security protections and other policies, independent of the communication mechanism, forwarding path, or endpoints used"* — and a per-category exemption at one set of sites is, on its face, a departure from that. The SC-7(4) exception is the mechanism for recording the departure rather than denying it. | *[Statement of how parity is maintained, or the bounded departure and its review cadence]* | *[status]* |

Enumerate the remaining universal capabilities from the catalog and confirm
each is genuinely unaffected before signing. *"Unchanged by routing"* is an
assertion this review makes, not a default.

### Status values

| Status | Meaning |
| --- | --- |
| **Enforced at branch** | The capability is delivered by a device or policy at the branch trust zone boundary. |
| **Enforced tenant-side** | Delivered by a service-side or endpoint control rather than a network device. A legitimate answer where the control is named and verifiable. |
| **Referred to AO** | Not transferred; a decision is sought in the covering memo. Permitted only for the item the memo actually covers. |
| **Gap** | Neither transferred nor referred. **A gap blocks sign-off.** Resolve it or convert it to an explicit referral before this determination is signed. |

## B3 — Telemetry

| Field | Value |
| --- | --- |
| **Reporting pattern** | *[NCPS Cloud Interface RA pattern reference]* |
| **Sources** | *[Branch PEP log sources feeding the pattern]* |
| **Verified** | *[Date telemetry confirmed arriving, per site or per pattern]* |
| **Gap during pilot** | *[If any — state it, do not leave blank]* |

Telemetry reaching CISA is a condition of fleet rollout, not of pilot cutover —
but a pilot that runs without it should say so here rather than leave the
reviewer to infer it.

## Architecture review determination

- ☐ **Conformant** — classification at B1 confirmed; capability transfer at B2
  complete with no gaps.
- ☐ **Conformant with conditions** — conditions stated below; each must close
  before the site enters scope.
- ☐ **Not conformant** — basis stated below. Design returns for rework before
  AO routing.

**Conditions or basis**

> *[Record here]*

By signing, the review asserts that the classification at B1 is correct for
this traffic; that every PEP capability group in the catalog revision named in
the header has been assessed and recorded at B2, and the universal capabilities
with it; that the control references at B2 are the agency's considered mapping
rather than placeholders; and that the only capability forgone is the one
referred to the Authorizing Official as an SC-7(4) exception. It asserts
nothing about whether that exception should be granted.

| Signature block | |
| --- | --- |
| Architecture review chair — signature | |
| Date | |
| Concurrence — ISSO | |
| Next review or re-assessment trigger | |

::: {.callout-note}
## Re-assessment triggers

This determination is bound to Attachment A at the version cited above.
Re-assess if: sites are added; the exemption scope widens beyond the Optimize
category; a control named at B2 changes or lapses — including device-side
tenant restrictions signaling, or the arrival of a device or browser population
it does not cover; the catalog is revised in a way that alters the group list;
or the telemetry pattern at B3 changes.
:::
