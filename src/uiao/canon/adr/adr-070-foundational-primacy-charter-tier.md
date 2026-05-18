---
id: ADR-070
title: "Foundational Primacy — Charter Tier and Amendment Process"
status: accepted
date: 2026-05-15
deciders:
  - architect
  - governance-steward
supersedes: []
related_adrs:
  - ADR-028
  - ADR-032
  - ADR-044
  - ADR-060
canon_refs:
  - CHARTER-001
  - UIAO-SSOT
governs:
  - src/uiao/canon/charter/
  - src/uiao/canon/charter-registry.yaml
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-070-foundational-primacy-charter-tier.html
---

# ADR-070: Foundational Primacy — Charter Tier and Amendment Process

## Status

Accepted

## Context

The substrate canon under `src/uiao/canon/` has, over the period
February through May 2026, accumulated a substantial body of governance,
compliance, transformation, and boundary work in correct response to
non-optional regulatory forcing functions: Microsoft vendor pressure
toward Entra ID / Intune / Azure Arc; mandatory federal regimes (EO
14028 / 14306, NIST 800-53 Rev 5, FedRAMP Rev 5, CISA SCuBA, BOD 25-01,
OMB memos); E911 federal law; and government-wide initiatives shipping
weekly (HRIT, FRPP MS). This work is operationally live and correct.

What that work lacks is the **architectural intent that scopes it**.
The pre-GitHub foundational canon — V3 (Feb 26 2026, original
whitepaper), V4 / V4U (Mar 7-9 2026, audience-variant unified merger),
and UIAO-V1 (Mar 9 2026, current authoritative charter) — was never
ingested into the substrate. Instead, that canon lives in OneDrive at
`Application_Aware_Networking_White_Paper_by_Mike/`, and the substrate
has operated against it implicitly. The result: substrate canon
correctly implements the compliance perimeter, but the charter that
defines what the substrate *is for* (identity-forward architecture,
conversation as atomic unit, public service first, source of authority
chains, citizen identity) has been visible only to the architect.

The Charter Restoration Plan ([`inbox/drafts/charter-restoration-plan.md`](../../../../inbox/drafts/charter-restoration-plan.md))
is the layered restoration that addresses this gap. The plan is
**additive only** — substrate work in flight is not touched. Charter
binding is layered above existing substrate canon as a foundational
tier. This ADR establishes the convention.

## Decision

1. **A new directory `src/uiao/canon/charter/`** holds foundational
   canon documents distinct from substrate canon. Charter docs are
   architectural authority FOR substrate work, not part of it.

2. **A distinct ID scheme `CHARTER-NNN`** is reserved for foundational
   docs. Charter IDs are not allocated from the `UIAO_NNN` range
   tracked by `document-registry.yaml`. Mixing the schemes would
   conflate substrate-scope canon with charter-scope canon and erode
   the tier distinction this ADR establishes.

3. **A separate registry `src/uiao/canon/charter-registry.yaml`**
   tracks charter doc allocations. Schema-distinct from
   `document-registry.yaml`; carries `tier`, `supersedable`,
   `load_order`, `source`, `source_date`, `ingested_at`, `ingested_by`
   fields for every entry.

4. **Charter docs carry mandatory frontmatter** beyond the substrate
   convention:
   - `tier: foundational`
   - `supersedable: false` (except for explicitly-superseded historical
     predecessors, e.g., `CHARTER-V3-LEGACY`)
   - `load_order: 0`
   - `charter_chain` — the documented supersession lineage
   - `provenance` — source path, ingestion date, editorial-pass scope

5. **The supersession chain is explicit and one-directional:**

   ```
   V3 (Feb 26)  →  V4 / V4U (Mar 7-9)  →  UIAO-V1 (Mar 9, CURRENT)
   ```

   - `CHARTER-V3-LEGACY` is the explicitly-superseded predecessor;
     retained for provenance, marked `supersedable: true` with
     `superseded_by: CHARTER-001`.
   - `CHARTER-002..005` are V4 / V4U feeder content (Core Canon
     Introduction, Master Reference, NPE Assurance Model, Source of
     Authority Location InterAgency) — complementary to CHARTER-001,
     not superseded by it.
   - `CHARTER-001` (UIAO-V1) is the current authoritative charter.

6. **Charter amendment requires an explicit ADR.** Routine substrate
   work does not modify charter content. A new charter version
   (e.g., a hypothetical `UIAO-V2`) requires:
   - A new `CHARTER-NNN` allocation (e.g., `CHARTER-006`),
   - An ADR documenting what changed and why,
   - Updates to `charter_chain` on affected docs,
   - Updates to `charter-registry.yaml` reflecting the supersession.

7. **Editorial pass on ingestion is light by design.** Permitted edits:
   pandoc-escape removal, list-bullet de-escape, table-row contiguity
   restoration, non-breaking-hyphen normalization, removal of
   metadata that duplicates frontmatter fields. **Not permitted**
   without a separate ADR: prose rewrites, section reorderings,
   content additions, content deletions beyond the editorial scope.
   Source content is preserved verbatim wherever possible. The
   `provenance.editorial_pass` field on each charter doc records
   exactly what was changed.

8. **Ingestion is sliced.** Charter Restoration PR-A is broken into
   PR-A1 through PR-A6 to keep each PR independently reviewable:
   - **PR-A1 (this PR):** CHARTER-001 + this ADR + charter-registry.yaml
   - PR-A2: CHARTER-001-APPENDICES (AtoBZ_clean.md after preprocessing)
   - PR-A3: CHARTER-002 + CHARTER-003 (V4U feeders)
   - PR-A4: CHARTER-004-NPE + CHARTER-005-SOA
   - PR-A5: CHARTER-V3-LEGACY
   - PR-A6: CHARTER-EVIDENCE-TELEMETRY

## Consequences

**Positive**

- Charter intent is visible inside the substrate, not implicit. Any
  contributor reading canon can find the architectural authority
  scoping their work without consulting OneDrive.
- The supersession chain is documented, so future readers understand
  why V3 references appear in some contexts and UIAO-V1 in others —
  and which one is authoritative when they conflict.
- Substrate canon work continues unchanged. PR-A* lands additively;
  no UIAO_NNN doc, ADR, schema, or data file is modified by this ADR
  or by the charter ingestion sequence.
- `foundational-trace` (Charter Restoration Plan PR-E, future) will
  let UIAO_NNN docs cite their charter ancestry, closing the loop
  between intent and implementation.

**Negative / deferred**

- Two separate document registries (`document-registry.yaml` and
  `charter-registry.yaml`) increase the number of canonical-list
  files. Mitigated by their semantic distinction — they answer
  different questions ("what substrate canon exists?" vs. "what
  charter authority exists?").
- Charter ingestion does not retroactively validate that existing
  substrate canon is consistent with charter intent. The
  `foundational-trace` backfill (PR-E/F) is the mechanism that
  surfaces gaps between charter and substrate. Until PR-E/F lands,
  consistency is enforced only at PR review for new substrate work.
- The 928KB AtoBZ_clean.md master appendix is not ingested in PR-A1.
  Appendix references in CHARTER-001 point to OneDrive until PR-A2
  lands the cleaned in-repo version. Operators reading CHARTER-001
  must understand that "See Appendix X" cross-references resolve to
  OneDrive content for the duration of PR-A1's lifetime.

## Alternatives considered

- **Mix CHARTER-NNN into the UIAO_NNN range** (e.g., reserve UIAO_300+
  for charter docs). Rejected — semantic distinction matters. Charter
  is authority FOR substrate canon, not part of it. Mixing the IDs
  would erode the tier distinction and force operators reading the
  registry to mentally separate two semantically distinct categories.

- **Skip charter ingestion entirely; cite OneDrive paths from substrate
  canon and AGENTS.md.** Rejected — the architect (2026-05-04 session)
  explicitly identified the orphan-charter problem as a narrative gap
  worth closing. Substrate-internal authority is also necessary for
  contributors who do not have OneDrive access.

- **Single-PR ingestion of all charter material** (PR-A as originally
  scoped). Rejected — at ~10 separate ingests including the 928KB
  AtoBZ master appendix that requires audit-mandated preprocessing,
  one PR is too large for meaningful review. The PR-A1..A6 slicing
  preserves the architect-blessed PR-A scope while making each slice
  independently reviewable.

## Related work

- [Charter Restoration Plan](../../../../inbox/drafts/charter-restoration-plan.md) — the architect-blessed roadmap this ADR implements (PR-A through PR-L).
- [ADR-028: Monorepo Consolidation + GOS Integration](adr-028-monorepo-consolidation-gos-integration.md) — substrate consolidation that preceded the charter binding work.
- [ADR-032: Single-Package Consolidation](adr-032-single-package-consolidation.md) — the topology this ADR adds the charter tier above.
- [ADR-044: Substrate Governance Realignment](adr-044-substrate-governance-realignment.md) — most recent topology ADR; charter sits above the substrate it realigned.
- [ADR-060: MOD Namespace Flatten into UIAO Canon](adr-060-mod-namespace-flatten-into-uiao-canon.md) — set precedent that canon-tier ADRs flatten lower tiers into the canonical namespace; this ADR adds the charter tier above the canonical namespace.

## Pending decisions deferred to later ADRs

- **`foundational-trace` schema and required-field cutover** — Charter
  Restoration Plan PR-E/F. Schema-only PR adds the optional field;
  backfill PR makes it required. ADR forthcoming when PR-E is drafted.
- **`ADR-MS (Microsoft-Forced Transition Rationale)`** — records why
  OrgPath / Three-plane device model / Entra adapter / Intune / Azure
  Arc layers exist, the vendor-pressure forcing function, and how they
  satisfy V4U Identity-plane intent. Lands in PR-A2..A6 timeframe.
- **Charter amendment for UIAO-V2 and beyond** — out of scope for this
  ADR. When the architect produces a successor charter, a new ADR will
  document the supersession.
