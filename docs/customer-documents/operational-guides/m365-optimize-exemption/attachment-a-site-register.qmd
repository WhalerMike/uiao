---
title: "Attachment A — Pilot Site Register and Egress IP Ranges"
subtitle: "The SC-7(4) exception record: mission need, duration and review per site; egress ranges per circuit"
doc-type: operational-guide
audience: [Customer, Operator, Technical]
author: Michael Stratton
date: "September 2026"
status: Draft
canon-source: "inbox/M365-INR-GCC-Moderate/attachment-a-site-register.html"
derived-from: "NIST SP 800-53 Rev 5 SC-7(4)(c)-(d); Microsoft 365 informed network routing configuration guidance (egress IP ranges per office location); Vol I Book 05 Appendix A.4.4."
repo-path: docs/customer-documents/operational-guides/m365-optimize-exemption/attachment-a-site-register.qmd
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

# Attachment A — Pilot Site Register and Egress IP Ranges {.unnumbered}

::: {.callout-warning}
## Template — example rows use RFC 5737 documentation addresses

The example rows use `203.0.113.0/24`, `198.51.100.0/24` and `192.0.2.0/24`,
reserved for documentation under RFC 5737 and safe to publish. **Delete them
once real rows exist**, so no reader has to work out which is which.
:::

| Field | Value |
| --- | --- |
| **Attaches to** | SC-7(4) traffic-flow exception — [M365 Optimize endpoint set at branch DIA](sc7-4-exception-memo.qmd) |
| **Prepared by** | *[Name, title]* |
| **Version** | *[n]* — *[date]* |
| **Site count** | *[N]* sites, *[N]* circuits, approx. *[N]* users |

The sites listed here are the entire scope of the exemption. Adding a site is a
scope change and requires return to the Authorizing Official — so this register
is a controlled document, and its version is the thing the signed memo refers
to.

**This register is the SC-7(4) exception record itself, not a supporting annex
to it.** SC-7(4) requires each exception to the traffic-flow policy to be
documented with its supporting mission need and the duration of that need, and
requires those exceptions to be reviewed on a stated cadence and removed when
the need no longer holds. Table A1 carries those fields; A2 and A3 carry the
network and readiness detail beneath them. A register that lists circuits but
records no mission need and no expiry cannot evidence the control the memo
claims.

## Table A1 — Exception record

*Per site — the SC-7(4)(c) and (d) fields.*

| Site ID | Supporting mission need | In force from | Expiry, or the condition that ends it | Last review |
| --- | --- | --- | --- | --- |
| BR-001 | *[Mission need]* — **example** | *[date]* | *[date or condition]* | *[date]* |
| *[ID]* | *[Why this site needs the exemption — specific to the site, not the program]* | *[date]* | *[date or condition]* | *[date]* |
| *[ID]* | *[Why this site needs the exemption — specific to the site, not the program]* | *[date]* | *[date or condition]* | *[date]* |

One row per site, where A2 is one row per circuit: the mission need is a
property of the site, the egress range is a property of the circuit.

Two fields are worth writing carefully. **Mission need** restated from the
program justification is not a site-level need — if the same sentence would
serve every row, none of them is answering the question. **Expiry** may be a
date or a condition ("until the site is migrated to the SASE fabric"), but it
may not be blank: an exception with no end is a permanent change to the
traffic-flow policy, which is a different decision from the one the memo asks
for.

## Table A2 — Scope

*What the exemption covers.*

| Site ID | Location | Users | Circuit | Public egress range (post-NAT) | Egress model |
| --- | --- | --- | --- | --- | --- |
| BR-001 | *[City, ST]* — **example** | 140 | ISP-A primary | `203.0.113.16/28` | Local DIA |
| BR-001 | *[City, ST]* — **example** | — | ISP-B secondary | `198.51.100.64/28` | Local DIA |
| BR-002 | *[City, ST]* — **example** | 62 | ISP-A primary | `192.0.2.128/28` | Local DIA, gateway fallback |
| *[ID]* | *[Location]* | *[n]* | *[Circuit]* | *[a.b.c.d/nn]* | *[DIA / gateway]* |
| *[ID]* | *[Location]* | *[n]* | *[Circuit]* | *[a.b.c.d/nn]* | *[DIA / gateway]* |

One row per circuit, not per site. A site with two internet circuits occupies
two rows sharing a Site ID, because attribution and steering both operate per
circuit.

## Completion rules for egress ranges

*R1–R5, referenced by the admission checklist.*

These are the errors that actually occur, in the order they occur. Each one
produces a fabric that appears configured and attributes traffic to the wrong
place.

**R1.** Record the **post-NAT public address** the branch presents to the
internet — not the WAN interface address, and not the inside pool.
*The address Microsoft and your probe endpoints observe is the one that
identifies the circuit. An interface address recorded here silently
mis-attributes every measurement from that site.*

**R2.** Give each circuit a **unique** range. If two circuits at a site share a
NAT pool, per-circuit attribution is not possible.
*Fix the NAT design before listing the site, or accept that path comparison at
that site is meaningless and record why.*

**R3.** Ranges must be **static and assigned to the agency** for the life of
the exemption. Dynamically assigned or ISP-rotated addresses do not qualify.
*A changed egress address moves the site outside the approved scope without
anyone making a decision to move it.*

**R4.** Verify each range **from the branch itself** before listing it, not
from documentation or the ISP order.
*Recorded ranges and deployed ranges diverge over time. The site is the
authority; the record is not.*

**R5.** Where IPv6 is enabled on the circuit, **list the IPv6 range too**.
*An IPv6-capable client egressing on an unlisted range is outside the recorded
scope even though the site is listed.*

## Table A3 — Readiness

*Per site, before cutover.*

| Site ID | Router / DRAM | UTD co-resident | TE agent | Gov instance confirmed | TRv2 device signaling | Baseline captured | Probe verified | Cutover | Revert owner |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| BR-001 | *[Platform]* / 16 GB | Yes | Embedded | *[date]* | *[date]* | *[date]* | *[date]* | *[date]* | *[team]* |
| *[ID]* | *[Platform]* / *[n]* GB | *[Y/N]* | *[Embedded / standalone]* | *[date]* | *[date]* | *[date]* | *[date]* | *[date]* | *[team]* |

Dates rather than ticks throughout. A tick records an intention; a date records
an event, and a reviewer can check it.

**TRv2 device signaling** is the date tenant restrictions v2 was confirmed in
force at the site *from the endpoint* rather than the proxy. Bypassing the
proxy removes the header-injection path, so unless the device-side path is
configured and verified, the site is cut over with tenant restrictions silently
unenforced. Record alongside it the device and browser population the Group
Policy path does not cover — it reaches Office applications, Universal Windows
Platform .NET applications and Microsoft Edge, and nothing else.

## Admission checklist

All of the following must be true before a site is listed in Table A2. A site
that fails any line is not ready to be in scope, and adding it later is a scope
change.

- ☐ Egress ranges verified **from the site** and satisfying completion rules
  **R1–R5**.
- ☐ Table A1 complete for this site: a **site-specific mission need**, a start
  date, and an **expiry or ending condition** that is not blank.
- ☐ Endpoint feed confirmed as **Worldwide (+GCC)** — not the DoD or GCC High
  instance.
- ☐ Probe endpoint resolves and responds **from this branch**, not only from
  the datacenter.
- ☐ Name resolution for Microsoft 365 occurs **local to this branch's egress** —
  no conditional forwarder returns these queries to a core resolver. Central
  resolution defeats local egress silently and the probes will not report it.
- ☐ ThousandEyes agent registered to the **government instance**, and absent
  from the commercial console.
- ☐ **Tenant restrictions v2 signaled from the endpoint** and verified in
  force, since the proxy path goes with the bypass — with the device and
  browser population it does not cover enumerated rather than assumed empty.
- ☐ Pre-cutover baseline captured and retained — the one step that cannot be
  recovered afterward.
- ☐ Branch telemetry reaching CLAW under the reporting pattern named in the
  memo.
- ☐ Router sized for the finished architecture, including UTD if the capability
  transfer places it here.
- ☐ Revert owner named, reachable, and able to act within one shift without an
  approval cycle.

::: {.callout-important}
## Handling

Completed, this register is a map of the agency's branch egress: public
addresses, circuit topology, per-site user counts and which sites have reduced
inline inspection — and, with Table A1, why each one was granted it. Handle and
mark it under the agency's own rules for network architecture information, and
check before circulating it more widely than the signature chain.
:::

## Change log

Record every scope change here with its date and the AO decision that
authorized it. The register version cited in the signed memo is the
authoritative scope; a later version without a corresponding decision is a
finding, not an update.

Record the **SC-7(4) reviews** here too, on the cadence the memo states,
including the reviews that change nothing. The control requires exceptions to
be reviewed and removed when the supporting need lapses; a register showing no
reviews evidences no reviews, whatever happened in practice.

> *[v1 — date — initial scope, N sites — approved DD MMM YYYY]*
