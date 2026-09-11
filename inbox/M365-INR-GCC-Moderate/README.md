# M365 Informed Network Routing — GCC Moderate briefing set

Source HTML for four published Claude Artifacts. These are the durable
copies; the artifacts themselves live outside the repo and the session
scratchpad that produced them is ephemeral.

| File | Artifact |
| --- | --- |
| `inr-gcc-briefing.html` | <https://claude.ai/code/artifact/e838b388-b500-4a62-b7e9-6983bfb9526c> |
| `ao-decision-memo.html` | <https://claude.ai/code/artifact/55276b46-12c5-471a-99f7-a380b6e46691> |
| `attachment-a-site-register.html` | <https://claude.ai/code/artifact/5a691d7b-1f59-4712-b82f-11c08af33188> |
| `attachment-b-architecture-review.html` | <https://claude.ai/code/artifact/85f62eaf-395d-43f9-9b8d-2caeac76b36f> |

Republishing an artifact means editing the file here and publishing it
from a session that holds the URL; publishing without the URL creates a
new artifact instead of updating the existing one.

## What they are

A technical briefing establishing that Microsoft 365 Informed Network
Routing is unavailable to GCC Moderate tenants, plus the decision
instruments for a Catalyst SD-WAN deployment that works around it. The
conclusion is correct and independently confirmed by the repo; the
reasoning carries three errors recorded below.

The briefing grades every claim documented / inferred / unsupported and
names the check that would settle the open ones.

The memo carries one bounded ask: a **documented SC-7(4) traffic-flow
exception** exempting the M365 Optimize endpoint set from TLS
break-and-inspect at branch DIA egress. Attachment A is the site and
egress-range register; Attachment B is the TIC 3.0 classification and PEP
capability transfer.

All three instruments are **templates with bracketed fields**, not
completed records.

## Overlap with existing canon and publications

This set was drafted from external sources without reference to the repo,
then reconciled against it. **Roughly four fifths of it re-derives material
the repo already owns**, at three levels of authority. An earlier version of
this section under-stated that: it named the canon row and two whitepapers
and missed the two closest pieces of prior art, both listed first below.

### Prior art, closest first

- **`docs/customer-documents/orgcomp-series/Vol_I_Book_05_OrgComp_Network_Modernization.qmd`,
  Appendix A** — "Cisco Catalyst SD-WAN and Microsoft 365 Informed Network
  Routing: Federal Implementation Reference", scoped in its own words to
  "FedRAMP Moderate civilian agencies using Microsoft 365 GCC". A.1–A.6
  already cover what the briefing's Sections 1, 5, 6 and 8 cover: the same
  Microsoft Learn quotation, Cloud OnRamp probe architecture and gateway
  selection, the Optimize/SC-8 reconciliation, TIC 3.0 alignment, NIST
  control satisfaction, KSI evidence contracts and an implementation
  sequence. **This appendix owns the subject.**
- **`tests/fixtures/contract/m365/informed-network-routing-unavailable-gcc-moderate.yaml`**
  — FINDING-001, a Tier-2 contract fixture that machine-enforces the
  unavailability: the m365 adapter must return `CapabilityUnavailable`
  rather than assume INR telemetry. The repo does not merely document this
  conclusion, it tests it. Boundary documentation should cite FINDING-001.
- `src/uiao/canon/data/gcc-moderate-telemetry-gaps.yaml`, row
  `inr-realtime-path-metrics` — records the gap as `documented: confirmed`
  (one of the eight vendor-confirmed rows of twenty-six), with rebuild path
  `SD-WAN / SASE / ThousandEyes (ADR-057)` and residual "agency-owned PEP
  telemetry, not Microsoft path intelligence". Authoritative over the matrix.
- `docs/customer-documents/whitepapers/fedramp-20x-and-the-commercial-feature-gap.qmd`
  — owns the framework and vendor-documentation argument, and carries the
  `MSO365MTA` Class D (High) in-process finding the briefing does not.
- `docs/customer-documents/whitepapers/tic3-sdwan-vs-dia.qmd` — owns the
  transport-versus-control argument. §5.5 and §5.6 supersede the briefing's
  Sections 6 and 8 on the control questions.
- `docs/customer-documents/whitepapers/infoblox-hybrid-dns-unified-ddi.qmd`
  and `infoblox-dns-reference.qmd` — own the Infoblox DDI material the
  briefing's Section 6 note touches on.

### Corrections the repo makes to the briefing

Three of these are load-bearing. Fix them before any of this is reused.

1. **Section 2's inferred explanation is contradicted and should be
   retracted, not softened.** The briefing infers that INR is absent from
   GCC because its exchanged data rests in commercial Azure regions, which a
   sovereign-cloud service description cannot absorb. The feature-gap paper
   documents that **GCC pairs with Azure Commercial** — GCC High and DoD pair
   with Azure Government. GCC already rides Azure Commercial, so commercial
   Azure storage cannot by itself explain exclusion from GCC Moderate. What
   survives of the inference is the third-party SaaS handoff to the SD-WAN
   vendor; the sovereign-storage premise does not.
2. **The AO memo omits the tenant-restrictions question an assessor will
   construct.** Per tic3-sdwan-vs-dia §5.5, tenant-to-tenant exfiltration over
   an Optimize-categorized path is exactly the case an assessor will build, and
   the memo's compensating-controls list did not mention it. **§5.5's stated
   reason is itself wrong** — see *Correction the briefing makes to the repo*
   below. The gap in the memo was real; the explanation offered for it was not.
   **§5.5 has since been corrected** and no longer carries either the
   tenant-restrictions overstatement or the AU-12/AU-3 imprecision.
3. **The exemption is framed too loosely.** The repo's compliant shape is
   **SC-7(4) documented traffic-flow exception discipline** — a named
   exception with its mission need, a review cadence, and the steering log as
   *enforcement evidence* — with the explicit warning that documentation
   alone is not a compensating control. The memo frames it as a generic risk
   acceptance. §5.5 also names the controls the carve-out punctures —
   **SI-3, SI-4(10), AC-4, AU-12** — which Attachment B's Web row should
   carry instead of "content inspection forgone".

### What this set adds that the repo does not already hold

Fold these into their existing owners rather than promoting the briefing.

1. **The local-DNS performance trap** (briefing §6). Front-door selection
   follows the resolver's apparent location, so branches resolving centrally
   reach a datacentre-proximate front door while egressing locally — and
   Cloud OnRamp probes report that path healthy, because it is. §5.6 covers
   DNS as a control flow (Protective DNS, RPZ, split-horizon); this failure
   mode is not covered. Belongs in Book 05 Appendix A.
2. **The ThousandEyes government-instance registration step** (briefing §7).
   A Linux-package agent needs `-m advanced` set to `FEDRAMP`; without it the
   agent registers to the commercial platform, putting agency network
   telemetry outside the authorized boundary. Not found elsewhere in the repo.
3. **Attachment A's egress-range completion rules** — post-NAT public address
   not the interface address, unique per circuit, static and agency-assigned,
   verified from the branch, IPv6 listed where enabled. A.3 describes probe
   architecture but not register discipline.
4. **The five-minute tenant check** — Health → Network connectivity →
   Settings, where absence of the SD-WAN solution pane is first-party
   confirmation.
5. **A terminology data point for feature-gap §6**, which states that "GCC
   Moderate" is not a Microsoft product name. The INR page uses exactly that
   phrase, as both this briefing and Book 05 Appendix A quote. The claim is
   right in substance and slightly overstated as written.

### Disposition

Do not promote the briefing as a standalone whitepaper; Book 05 Appendix A
owns the subject. Fold items 1–4 above into that appendix and item 5 into
feature-gap §6. The three instruments (memo, Attachment A, Attachment B) are
the genuinely new artifacts and are worth keeping, but should be rebuilt on
the repo's own control vocabulary and cite FINDING-001.

### Correction the briefing makes to the repo

**`tic3-sdwan-vs-dia` §5.5 overstates the tenant-restrictions-v2
constraint, and Book 05 Appendix A should not inherit it.** §5.5 says
enforcement requires header injection at a proxy in the traffic path, so a
proxy-bypassed flow cannot have tenant restrictions enforced on it. Microsoft
Learn's *Set up tenant restrictions v2* page documents otherwise. A single
cross-tenant access policy has **three** enforcement paths:

| Path | Proxy required | Authentication plane | Data plane |
| --- | --- | --- | --- |
| Windows Group Policy on corporate-owned devices | No | Yes | **Yes** |
| Universal tenant restrictions (Global Secure Access) | No | Yes, all platforms | Graph only |
| Corporate proxy header injection | Yes | Yes | **No** |

The v1-versus-v2 comparison table on the same page is explicit that proxy
enforcement is the **v1** model, and that v2's Windows device-management path
"provides both authentication plane and data plane protection… A corporate
proxy isn't required for policy enforcement." The proxy path is not merely
optional under v2 — it is the *weakest* of the three, being the only one that
does not reach the data plane.

So the constraint is real in a narrower form: the agency loses the proxy
signaling path and must re-signal from the endpoint. It is not a structural
incompatibility and not uncompensable. Two genuine limits survive: the Group
Policy path covers Office apps, UWP .NET apps and Microsoft Edge, so non-Edge
browsers and non-Windows devices are uncovered; and Global Secure Access
availability in the government cloud is unconfirmed.

Source: <https://learn.microsoft.com/en-us/entra/external-id/tenant-restrictions-v2>.
**This correction has been applied to §5.5**, along with the same document's
Part 7 ledger row and references entry. §5.5 additionally now records that
`entra-security-baseline-federal-crosswalk` lists Global Secure Access as
non-FIPS in GCC Moderate and unavailable in GCC High and DoD — which makes
the Windows Group Policy path the only one a FedRAMP Moderate agency can
actually rely on, a sharper conclusion than "three paths exist".

### Rebuild status

- **Items 1–4 folded** into Book 05 Appendix A (PR #1513).
- **`ao-decision-memo.html` rebuilt** on the control vocabulary. It now
  opens on SC-7(4) rather than generic risk acceptance, cites FINDING-001
  in the background clause, names SI-3, SI-4(10), AC-4 and AU-12 as the
  punctured controls, states that **SC-8 is not a gap** to forestall the
  obvious challenge, carries tenant restrictions v2 as its own clause, and
  groups compensating controls by plane with the rule that a control listed
  without a reference is not yet a compensating control. The retracted
  commercial-Azure inference is gone: the memo now says Microsoft publishes
  no rationale and none is required for this decision. Corrections 1–3 above
  are all discharged in the memo.
- **Memo clause 4 corrected after first draft.** The rebuild initially wrote
  tenant restrictions v2 as a structural incompatibility, following §5.5. The
  Microsoft Learn check above contradicted it. The clause now reads as a
  control that moves from the network plane to the endpoint, names all three
  enforcement paths, makes device-side signaling a precondition to cutover and
  a return trigger, and states what the Group Policy path does not cover.
- **Control mapping verified.** SI-3, SI-4(10), AC-4, SC-7(4) and SC-8 are
  each used against their NIST SP 800-53 Rev 5 definitions; SC-7(4)(c)-(d)
  is the exception-documentation and review-cadence discipline the memo
  claims it is. One refinement: §5.5 and the first draft cited **AU-12** for
  thin audit content, but records are still generated — what degrades is
  their content, which is **AU-3**'s requirement, incorporated by AU-12.
  The memo now names AU-3 with AU-12 by reference. §5.5 could take the same
  refinement.
- **`attachment-b-architecture-review.html` rebuilt.** The Web row now names
  SI-3, SI-4(10), AC-4 and AU-3 and says SC-8 is not punctured, instead of
  "inspection of that set is forgone". Every PEP row carries a proposed
  NIST SP 800-53 mapping, with the column labelled as the board's own work
  product — the catalog maps PEP capabilities to NIST CSF, not to 800-53, so
  presenting that column as a catalog citation would be wrong. The Enterprise
  row carries the tenant-restrictions-v2 move to endpoint signaling from memo
  clause 4, and device-side signaling becomes a re-assessment trigger.
- **Two structural defects fixed in Attachment B.** The capability table had a
  **duplicate Enterprise row** while claiming twelve groups, and it carried
  **"Universal capabilities" as a thirteenth row inside a table headed "PEP
  capability group"**. Universal Security Capabilities are a separate catalog
  category — enterprise-level and expected in every use case, where PEP
  capabilities apply according to use-case scope. They now have their own
  table covering the three this design actually changes: Central Log
  Management with Analysis, Auditing and Accounting, and **Policy Enforcement
  Parity**, the capability the design is most in tension with.
- **`attachment-a-site-register.html` rebuilt.** The register asserted the
  memo's SC-7(4) discipline without carrying the fields the control requires.
  SC-7(4)(c) wants each exception documented with its **supporting mission
  need and the duration of that need**; (d) wants the exceptions **reviewed
  on a cadence and removed when the need lapses**. The register had site IDs,
  circuits and egress ranges and none of that. New **Table A1 — Exception
  record** carries mission need, in-force date, expiry-or-ending-condition
  and last review, one row per site (where the scope table is one row per
  circuit, because mission need is a site property and an egress range is a
  circuit property). The change log now records SC-7(4) reviews including the
  ones that change nothing, since a register showing no reviews evidences no
  reviews. Expiry may be a condition rather than a date but may not be blank:
  an exception with no end is a permanent traffic-flow policy change, which
  is a different decision from the one the memo asks for.
- **The cutover gate now matches the memo.** The memo and Attachment B both
  make device-side tenant restrictions signaling a precondition to cutover,
  but Attachment A — the document that actually gates a site — had no such
  check. Added as a readiness column and an admission-checklist line, with
  the uncovered device and browser population to be enumerated rather than
  assumed empty.
- **Rule-label collision fixed.** The completion rules render as `A1`–`A5`
  badges, which collided with the table numbering once Table A1 existed. They
  are now `R1`–`R5` and the checklist references them by that name.
- **Item 5 folded into feature-gap §6.** The section said "GCC Moderate" is
  not a Microsoft product name. Right in substance, overstated as written:
  Microsoft's own informed network routing page says the feature "supports
  tenants in WW Commercial cloud but not the **GCC Moderate**, GCC High, DoD,
  Germany, or China clouds", read firsthand from
  <https://learn.microsoft.com/en-us/microsoft-365/enterprise/office-365-network-mac-perf-cpe>
  on 11 September 2026. §6 now distinguishes the two: "GCC Moderate" is not an
  *offering* name — the offering is Government Community Cloud and the listing
  is `MSO365MT` — but it is Microsoft's own usage for the *cloud environment*.
  An agency writing it for the environment is following Microsoft; what it
  cannot do is treat the phrase as naming a distinct product or a distinct
  FedRAMP authorization.
- **The GSA question is closed, and the answer narrows the design.** The memo
  and Attachment B recorded Global Secure Access availability in the
  government cloud as unconfirmed.
  `entra-security-baseline-federal-crosswalk` answers it: **non-FIPS in GCC
  Moderate, unavailable in GCC High and DoD**. Both documents now say so. The
  consequence is not cosmetic — with the proxy path given up by the exemption
  and GSA unavailable, **Windows Group Policy signaling is not the preferred
  tenant-restrictions path but the only one**, which raises the stakes on the
  population it does not cover (non-Edge browsers, non-Windows devices).
- **Memo's sourcing disclosure tightened.** It said engineering detail came
  from "vendor and CISA documentation accessed indirectly". Microsoft
  documentation has since been read firsthand twice and cited directly; CISA
  and Cisco remain indirect. The bullet now says which is which and names
  Attachment B's capability-group list as the weakest-sourced claim in the set.

### All README items are now closed

The reconciliation's three corrections are discharged, its five additive items
are folded into their owners, all three instruments are rebuilt, and the §5.5
error the set inherited is fixed at source. **One thing remains unverified
rather than open:** Attachment B's twelve PEP capability group names have not
been read from the catalog, and cannot be from this environment — cisa.gov is
refused at the egress proxy. A verification attempt on 11 September 2026
confirmed the block and failed to establish the list by any other allowed
means. See *Catalog sourcing* above for what is and is not known, and note
that the earlier claim of "two independent derivations" was itself overstated.
It closes when someone on an unrestricted network opens the v3.3 catalog and
counts the capability-group tables.

### Catalog sourcing — the group list is NOT verified

cisa.gov is blocked by this environment's egress policy. The block is at the
proxy, not the tool: `curl` fails at the CONNECT tunnel with **403**, for the
core-guidance page and the catalog PDFs alike. The proxy's own guidance is to
report blocked hosts rather than route around them, so no mirror of the
document was sought.

**Attachment B's PEP capability group list has not been checked against the
catalog, and cannot be from this environment.** An earlier version of this
section described the twelve-group figure as resting on "two independent
derivations". *That was overstated, and the overstatement is the point worth
recording.* Both derivations — the ten groups named in the 2023 catalog, and
Services and Identity added in v3.3 — came from the same search tool
summarizing the same corpus of cisa.gov PDFs that it can read and this
environment cannot. Two claims through one intermediary is not two sources.

What is known, at the confidence it is actually known:

| Claim | Status |
| --- | --- |
| v3.3 exists, filed under `2025-07` | **Solid** — an artifact-level fact from a returned URL path |
| No revision later than v3.3 as of September 2026 | Absence of evidence from one search tool |
| Twelve PEP capability groups, and their names | **Unverified** — one intermediary, no primary read |
| Services and Identity are new in v3.3 | **Unverified** — same intermediary |
| Universal Security Capabilities are a separate category from PEP groups | Consistent across every source seen, including the structure of the 2023 catalog |

A later attempt to pin the v3.3 table of contents by search produced a result
that **echoed the query back** — returning "Enterprise Services" as a group
name, which is two of the names in the query run together — and simultaneously
denied that v3.3 exists, contradicting the search that surfaced its path. That
is what this class of evidence looks like when pushed, and it is why the table
above stops where it does.

The **"eight groups"** phrasing that recurs in search results is stale body
text from earlier revisions. Whatever the true current count, a table copied
forward from an old revision reads as complete while being short, so the
version must be named wherever the list is used.

**How this closes:** open
[the v3.3 catalog](https://www.cisa.gov/sites/default/files/2025-07/CISA%20TIC%203.0%20Security%20Capabilities%20Catalog%20v3.3%20(Volume%203).pdf)
and count the PEP capability group tables, or allowlist cisa.gov for this
environment. Until one of those happens, Attachment B's list is a working
assumption that is disclosed as one — in its own note and here — and not a
verified enumeration.

## Research limitation

cisco.com, cisa.gov, docs.thousandeyes.com and fedramp.gov were all
blocked by the session's network egress policy. Cisco, CISA and
ThousandEyes content was assembled from search summaries rather than
read from source. Microsoft Learn was reachable directly and its
citations are firsthand. Each document carries its own verification-limit
block saying which of its content is affected.
