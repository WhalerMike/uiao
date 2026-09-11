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
2. **The AO memo omits a structural incompatibility an assessor will
   construct.** Per tic3-sdwan-vs-dia §5.5, Microsoft's **tenant restrictions
   v2** enforcement requires header injection at a proxy in the traffic path.
   A flow that bypasses the proxy cannot have tenant restrictions enforced on
   it, and tenant-to-tenant exfiltration over an Optimize-categorized path is
   named there as exactly the case an assessor will build. The memo's
   compensating-controls list does not mention this.
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

### Rebuild status

- **Items 1–4 folded** into Book 05 Appendix A (PR #1513).
- **`ao-decision-memo.html` rebuilt** on the control vocabulary. It now
  opens on SC-7(4) rather than generic risk acceptance, cites FINDING-001
  in the background clause, names SI-3, SI-4(10), AC-4 and AU-12 as the
  punctured controls, states that **SC-8 is not a gap** to forestall the
  obvious challenge, carries tenant restrictions v2 as its own clause — a
  structural incompatibility rather than a gap awaiting a compensating
  control — and groups compensating controls by plane with the rule that a
  control listed without a reference is not yet a compensating control. The
  retracted commercial-Azure inference is gone: the memo now says Microsoft
  publishes no rationale and none is required for this decision. Corrections
  1–3 above are all discharged in the memo.
- **Still open:** Attachment B's Web row still reads "content inspection
  forgone" and should carry SI-3, SI-4(10), AC-4 and AU-12 instead; item 5
  (terminology) is not yet folded into feature-gap §6; Attachment B's twelve
  PEP capability group names are unverified against SCC v3.3 from source.

## Research limitation

cisco.com, cisa.gov, docs.thousandeyes.com and fedramp.gov were all
blocked by the session's network egress policy. Cisco, CISA and
ThousandEyes content was assembled from search summaries rather than
read from source. Microsoft Learn was reachable directly and its
citations are firsthand. Each document carries its own verification-limit
block saying which of its content is affected.
