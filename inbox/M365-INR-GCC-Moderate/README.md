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

A corrected technical briefing establishing that Microsoft 365 Informed
Network Routing is unavailable to GCC Moderate tenants, plus the
decision instruments for a Catalyst SD-WAN deployment that works around
it. The briefing grades every claim documented / inferred / unsupported
and names the check that would settle the open ones.

The memo carries one bounded ask: risk acceptance for exempting the
M365 Optimize endpoint set from TLS break-and-inspect at branch DIA
egress. Attachment A is the site and egress-range register; Attachment B
is the TIC 3.0 classification and PEP capability transfer.

All three instruments are **templates with bracketed fields**, not
completed records.

## Overlap with existing canon and publications

This set was drafted from external sources without reference to the
repo, and then found to re-derive material the repo already owns. Before
promoting any of it, reconcile against:

- `src/uiao/canon/data/gcc-moderate-telemetry-gaps.yaml`, row
  `inr-realtime-path-metrics` — already records the gap as
  `documented: confirmed`, with rebuild path
  `SD-WAN / SASE / ThousandEyes (ADR-057)` and residual
  "agency-owned PEP telemetry, not Microsoft path intelligence".
  The briefing reaches the same conclusions independently.
- `docs/customer-documents/whitepapers/fedramp-20x-and-the-commercial-feature-gap.qmd`
  — owns the FedRAMP-20x-versus-Microsoft-feature-gap argument, and
  asserts GCC High certification activity the briefing does not cover.
- `docs/customer-documents/whitepapers/tic3-sdwan-vs-dia.qmd` — owns the
  TIC 3.0 transport-versus-control argument. The briefing's Section 8
  covers adjacent ground and should defer to it rather than compete.
- `docs/customer-documents/whitepapers/infoblox-hybrid-dns-unified-ddi.qmd`
  and `infoblox-dns-reference.qmd` — own the Infoblox DDI material the
  briefing's Section 6 note touches on.

## Research limitation

cisco.com, cisa.gov, docs.thousandeyes.com and fedramp.gov were all
blocked by the session's network egress policy. Cisco, CISA and
ThousandEyes content was assembled from search summaries rather than
read from source. Microsoft Learn was reachable directly and its
citations are firsthand. Each document carries its own verification-limit
block saying which of its content is affected.
