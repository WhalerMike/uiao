---
adr_id: adr-083
title: "Documentation Architecture Reorganization — Single URL Umbrella + Divio-Aligned Sections"
status: PROPOSED
decided: 2026-05-23
deciders: Michael Stratton
updated: 2026-05-23
next_review: 2026-11-23
review_trigger: A new top-level documentation surface is proposed outside /customer-documents/; the Divio quadrant mapping requires a sixth section; first agency reports broken bookmarks not caught by alias redirects; lifecycle scanner or publication-gap scanner discovers a path-hardcoding regression
impact: 'Collapses the dual documentation URL surface (`/modernization/` + `/customer-documents/`) into a single `/customer-documents/` umbrella with Divio-aligned subsections. The current `/modernization/` (canon specifications) becomes `/customer-documents/reference-architecture/`; the current `/customer-documents/modernization/` (operational how-to guides) becomes `/customer-documents/operational-guides/` to remove the section-name collision. All moves preserve external bookmarks via Quarto `aliases:` frontmatter. No content rewrites — the ADR moves files and renames sidebar sections only. Lifecycle semantics from ADR-076 (canon = aspirational, customer-doc = adopted Tier 1) are unchanged: they live in frontmatter, not URLs. Closes the recurring "are these duplicates?" cross-surface review pattern that ADRs 076, 078, 079, 080, 081 each addressed one conflict at a time.'
supersedes: null
superseded_by: null
classification: Controlled
boundary: GCC-Moderate
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-083-docs-architecture-reorganization.html
---

# ADR-083: Documentation Architecture Reorganization — Single URL Umbrella + Divio-Aligned Sections

## Status

**PROPOSED** — 2026-05-23.

## Context

A 2026-05-22 cross-surface site review found five doctrinal conflicts between `/modernization/` (canon) and `/customer-documents/` (customer-facing operational + narrative). Each conflict was resolved by its own ADR:

| Conflict | Resolved by |
|---|---|
| Status labels (canon "Aspirational" vs customer "v1.0 shipped") | [ADR-076](adr-076-tier-conformance-model.md) + [ADR-082](adr-082-status-label-lifecycle-policy.md) |
| Principle counts (canon 7 vs customer 3) | [ADR-079](adr-079-governance-principle-reconciliation.md) |
| "Intune-First" overloaded across three programs | [ADR-080](adr-080-intune-first-scope-disambiguation.md) |
| Directory Migration phase counts (canon 5 vs DNS 11 vs PKI 6) | [ADR-081](adr-081-directory-migration-phase-canonical-model.md) |
| OrgPath attribute model (Model A vs Model B vs Model C) | [ADR-078](adr-078-orgpath-attribute-schema-15-facet.md) |

A 2026-05-23 follow-up review surfaced the **meta-pattern** behind all five: every reconciliation found that *what looked like duplication was actually layered refinement* (canon spec + customer-doc operational guide + narrative explainer). The recurring "are these duplicates?" question is a **navigation symptom**, not a structural duplication. The dual URL surface keeps producing it because:

1. **Canon and customer-doc pages on the same topic live at sibling-level URLs**, so a federal reader cannot tell which is authoritative without reading both.
2. **The canon page rarely cross-links to its customer-doc companion** (the reverse direction is usually present). Reader landing on canon has no signal the operational guide exists.
3. **"Modernization" appears as a top-level section in BOTH surfaces** (`/modernization/` AND `/customer-documents/modernization/`), guaranteeing label collision in the sidebar.

### Industry comparison

The dominant industry framework for technical documentation organization is the **Divio Documentation System** (https://docs.divio.com/documentation-system/), adopted by Django, GitLab, MDN, Anthropic, HashiCorp, Stripe, and many others. It defines four quadrants by reader intent:

| Quadrant | Purpose | Reader | UIAO instances today |
|---|---|---|---|
| **Tutorials** | Learning-oriented; hand-held | Beginner | (mostly absent — federal IT skips this) |
| **How-to guides** | Task-oriented; problem-solving | Working on a goal | DNS Modernization Guide, PKI Modernization Guide, GPO Sunset Program, end-user training |
| **Reference** | Information-oriented; lookup | Looking something up | OrgPath Codebook, JSON Schema, ADR catalog, adapter interfaces |
| **Explanation** | Understanding-oriented; the "why" | Curious about design | OrgPath Narrative, executive briefs, whitepapers |

Major-vendor documentation sites consistently implement this framework with a **single URL umbrella per program** plus a distinct **Reference Architecture** (or "Validated Designs", "Architecture Center") section as a sibling to operational guides:

| Vendor | URL umbrella | Reference / spec section | Operational section |
|---|---|---|---|
| **AWS** | `docs.aws.amazon.com/<service>/` | "API Reference", "Architecture Center" | "User Guide", "Developer Guide" |
| **Microsoft** | `learn.microsoft.com/<product>/` | "Reference", "Cloud Adoption Framework", "Well-Architected Framework" | "Tutorial", "How-to guide", "Concept" |
| **Google Cloud** | `cloud.google.com/<product>/` | "Reference", "Architecture Center" | "Guides", "Solutions" |
| **VMware** | `docs.vmware.com/<product>/` | "Validated Designs" (VVD) | "Installation Guide", "Administration Guide" |
| **Cisco** | `cisco.com/c/en/us/td/docs/` | "Reference Architectures" | "Configuration Guide", "Deployment Guide" |
| **HashiCorp** | `developer.hashicorp.com/<product>/` | "API Docs", "Plugin Reference" | "Tutorials", "Docs" |
| **Stripe** | `docs.stripe.com/` | "API Reference" | "Get started", "Products" |
| **Anthropic** | `docs.anthropic.com/` | "API Reference" | "Get started", "Build with Claude", "Resources" |
| **Red Hat** | `access.redhat.com/documentation/` | "Reference" | "Installation Guide", "Configuration Guide" |

Three observations carry forward:

1. **Reference (including Reference Architecture) is ALWAYS its own navigation section.** Never mixed in with operational guides. AWS Architecture Center, Google Architecture Center, Microsoft CAF/WAF, VMware VVD, Cisco Reference Architectures — all standalone.
2. **"Reference Architecture" is industry-standard terminology.** Federal-IT architects already recognize it. Cisco's "Reference Architectures", VMware's "Validated Designs", AWS's "Reference Architectures" library — same idea, slightly different brand names.
3. **One URL umbrella per program is the norm.** AWS does not split `aws.amazon.com/reference/` and `aws.amazon.com/customer-docs/`; both live under `docs.aws.amazon.com/<service>/`.

### Why ADR-076's lifecycle/authority semantics do not require dual URLs

[ADR-076](adr-076-tier-conformance-model.md) separates canon (aspirational) from customer-docs (adopted Tier 1) by **lifecycle and authority**, not by URL path. [ADR-072](adr-072-canon-publication-policy.md) governs *whether* (`publish_to_site`) and *how* (`publication_style: narrative | include | reference`) a page renders, not *where*. Both ADRs are about frontmatter semantics. Neither constrains the URL hierarchy.

A page at `/customer-documents/reference-architecture/orgtree.html` with `lifecycle: aspirational` still satisfies ADR-076 — the frontmatter carries the authority claim. The URL is just navigation. Therefore the dual URL surface is not load-bearing for the canon-vs-customer distinction; it is a presentation choice that happens to create the recurring navigation symptom.

## Decision

UIAO documentation collapses to a **single `/customer-documents/` URL umbrella** with **Divio-aligned subsections**. The current `/modernization/` and `/customer-documents/modernization/` are both renamed to remove the umbrella split and the section-name collision.

### URL moves

| Current URL | New URL | Rationale |
|---|---|---|
| `/modernization/<page>.html` | `/customer-documents/reference-architecture/<page>.html` | Canon specifications + architectural reference. Industry-standard name. |
| `/customer-documents/modernization/<page>.html` | `/customer-documents/operational-guides/<page>.html` | Operational how-to guides. Removes the "Modernization" sidebar-label collision. |
| All other `/customer-documents/<subsection>/<page>.html` | Unchanged | Existing subsections (executive-briefs, executive-governance-series, orgpath-narrative, platform-substrate, whitepapers, etc.) already fit the Divio quadrant grouping. |

### Repository moves

| Current path | New path |
|---|---|
| `docs/modernization/*.qmd` (12 files) | `docs/customer-documents/reference-architecture/*.qmd` |
| `docs/modernization/images/` | `docs/customer-documents/reference-architecture/images/` |
| `docs/modernization/intune-first-onboarding/*` (if present) | `docs/customer-documents/reference-architecture/intune-first-onboarding/*` |
| `docs/customer-documents/modernization/**/*.qmd` (all nested) | `docs/customer-documents/operational-guides/**/*.qmd` |

### Old-URL preservation

Every moved page MUST declare an `aliases:` frontmatter entry pointing to its old URL. Quarto generates redirect HTML at the old URL automatically. Example for the OrgTree page:

```yaml
---
title: "OrgTree — Identity Modernization"
aliases:
  - /modernization/orgtree.html
---
```

This preserves external bookmarks, internal soft links that were not caught by the sweep, and search-engine indexing during the transition window.

### Sidebar reorganization

The `docs/_quarto.yml` sidebar is reorganized so the eight customer-documents subsections present as Divio-aligned peer sections:

```
Customer Documentation
├── Reference Architecture          (← canon spec layer, was /modernization/)
├── Operational Guides              (← how-to guides, was /customer-documents/modernization/)
├── Executive Briefs                (unchanged)
├── Executive Governance Series     (unchanged)
├── OrgPath Narrative               (unchanged — explanation/narrative)
├── Whitepapers                     (unchanged)
├── Platform Substrate              (unchanged)
└── Other existing subsections      (unchanged)
```

### Lifecycle frontmatter is unchanged

This ADR moves files; it does **not** touch the `lifecycle`, `tiers_adopted`, or `lifecycle_review` fields per ADR-082. Pages in `reference-architecture/` keep `lifecycle: aspirational` (canon spec layer). Pages in `operational-guides/` keep `lifecycle: adopted, tiers_adopted: [1]` (shipped reality). The lifecycle banner ([ADR-082](adr-082-status-label-lifecycle-policy.md) Phase 2) renders the same regardless of the page's URL.

## Rationale

1. **Industry convention.** Every major enterprise-IT vendor docs site organizes this way: one URL umbrella per program, Reference Architecture as a peer to operational guides. The Divio Documentation System provides the framework; AWS, Microsoft, Google, VMware, Cisco, HashiCorp, Stripe, Anthropic, and Red Hat all implement it. UIAO has been the outlier with its dual umbrella.

2. **Closes the recurring "are these duplicates?" review pattern.** ADRs 076, 078, 079, 080, 081 each addressed one cross-surface conflict reactively. ADR-083 addresses the navigation symptom that keeps generating them. Future cross-surface reconciliations should be rare under the single umbrella because layered pages (spec + operational) sit in named peer sections rather than at sibling-level URLs.

3. **No doctrinal change to ADR-076 or ADR-072.** Lifecycle and authority semantics live in frontmatter. ADR-083 moves files and renames sections; it does not redefine what "aspirational" or "adopted" means, and it does not change how `publish_to_site` is interpreted.

4. **Alias redirects preserve every external bookmark.** Quarto's `aliases:` field generates redirect HTML at the old URL. Federal-IT readers with browser bookmarks, agency wiki cross-references, or vendor proposal PDFs citing the old URLs all continue to work transparently. The redirect can be removed in a future cleanup ADR (no earlier than 12 months from this ADR's acceptance) if traffic data shows the old paths are unused.

5. **"Reference Architecture" is recognized federal-IT terminology.** Cisco's "Reference Architectures" library, VMware's "Validated Designs", AWS's "Reference Architectures" — federal architects already know the term and the artifact class it implies (vetted, normative, deployment-blueprint-grade). Federal proposal language frequently asks for "the reference architecture" as a deliverable.

6. **"Operational Guides" rather than "Modernization Guides" for the renamed section.** The current `/customer-documents/modernization/` subsection contains a broader scope than its name implies — operational runbooks, end-user training, exec-brief-style program management material, technical narratives, and customer-facing modernization guides. "Operational Guides" honors the Divio "How-to" quadrant while accommodating the breadth. "Modernization" as a section label survives in the page titles and the umbrella program name; this rename is about navigation hygiene, not program scope.

## Consequences

### Positive

- Single navigation umbrella matching industry convention; no more "which surface is authoritative for X?" reader confusion.
- "Modernization" no longer collides as a sidebar label.
- "Reference Architecture" replaces the less-descriptive "Modernization" label for canon specs — clearer signal of what readers are looking at.
- Closes the cross-surface reconciliation backlog (ADRs 076-082 series) at its structural root, not symptomatically.
- Cleaner mental model for new contributors: pages live where their Divio quadrant says they live.

### Negative

- **~12 page moves + git renames in `docs/modernization/`** (12 .qmd files + images directory + possibly `intune-first-onboarding/` subtree if present).
- **~25-30 page moves** in `docs/customer-documents/modernization/` and its nested subdirectories (`network-transformation/`, `target-surface/`, `client-server-to-hybrid-cloud/`, etc.). Git history is preserved via `git mv`.
- **~100+ internal cross-link updates.** Internal links using `./modernization/...`, `/modernization/...`, or `../modernization/...` need a corpus sweep. Mostly mechanical (regex replace), but every replacement must preserve the link target's anchor and any query string.
- **`docs/_quarto.yml` sidebar restructure** — modest but visible change.
- **Scanner audits.** `scripts/scan_lifecycle_consistency.py` and `scripts/scan_publication_gaps.py` may hardcode the old paths in their scan roots, default exclusions, or path-pattern publish-default rules. Both must be audited and updated.
- **ADR cross-references.** ADRs 076, 078, 079, 080, 081 reference `docs/modernization/...` paths in their Verification Sources tables. These citations remain historically correct (the path was correct at the time the ADR was written) but new ADRs should cite the new paths.

### Risks

- **Alias redirects can be silently broken.** A typo in the `aliases:` frontmatter, an interaction with `_quarto.yml`'s `site-url`, or a path-prefix issue can produce a 404 instead of a redirect. Mitigation: every moved page's old URL must be tested in CI (a small alias-presence test in the publication-gap scanner) and visually spot-checked on the deployed site after the move.
- **Lifecycle scanner path-hardcoding regression.** If the scanner expects `src/uiao/canon/` and `docs/modernization/` as its scan roots, the rename will silently exclude the moved pages from validation. Mitigation: scanner audit is a required Phase 5 of the implementation; CI must show the same number of pages validated before and after the move.
- **Stale customer assumption that `/modernization/` is the canon URL.** Federal proposal documents and agency wikis often cite the canonical URL as the "long-term stable" identifier. The alias redirect keeps the old URL functional, but new external citations should use the new URL. Mitigation: explicit cite in the redirect HTML (Quarto-default) and a Release Notes line in the next version cut.
- **Sidebar restructure may surface lifecycle-banner placement bugs.** The `{{< lifecycle-banner >}}` shortcode (ADR-082) renders the same regardless of URL, but reader expectation of banner placement may shift when pages move sections. Mitigation: visual spot-checks on the deployed site for the first wave of moved pages.
- **The current customer-docs sidebar already has eight subsections.** Adding two more (or renaming two existing) may push the sidebar past comfortable navigation length. Mitigation: implementation Phase 3 must include a sidebar usability check; consider collapsible groups if subsection count exceeds ~10 visible.

## Implementation phases

| Phase | Branch | Scope |
|---|---|---|
| **0** | `charter/adr-083-docs-architecture-reorganization` (this PR) | Doctrine ADR. No file moves. |
| **1** | `restructure/move-modernization-to-reference-architecture` | `git mv docs/modernization/ → docs/customer-documents/reference-architecture/`. Add `aliases:` frontmatter to every moved page citing its old URL. Move images directory alongside. |
| **2** | `restructure/move-customer-modernization-to-operational-guides` | `git mv docs/customer-documents/modernization/ → docs/customer-documents/operational-guides/`. Add `aliases:` frontmatter to every moved page. Preserve nested subdirectory structure. |
| **3** | `restructure/quarto-sidebar-reorg` | Update `docs/_quarto.yml` sidebar: rename "Modernization" section, add "Reference Architecture" as peer section, reorganize subsection ordering for Divio-quadrant grouping. |
| **4** | `restructure/internal-cross-link-sweep` | Corpus sweep for `./modernization/`, `/modernization/`, `../modernization/`, and `docs/modernization/` references. Mostly regex; spot-check tricky cases (e.g., links inside code blocks). |
| **5** | `restructure/scanner-path-audit` | Audit `scripts/scan_lifecycle_consistency.py` + `scripts/scan_publication_gaps.py` for path-hardcoding. Update scan roots if needed. CI must show same page count validated before/after the move. |
| **6** | `restructure/render-check-and-remediation` | Build site locally + on CI; visually spot-check the deployed site; fix any broken `aliases:` redirects, missing images, or sidebar regressions. |

Phases 1 and 2 are independent (different file trees) and can ship in parallel. Phase 3 can begin after either Phase 1 or Phase 2 lands (incremental sidebar updates per moved subsection). Phases 4-6 follow once both 1 and 2 are merged.

Estimated total: **1 week** for a focused execution; **2 weeks** if interleaved with other work.

## Verification Sources

| Source | Reference | Last Verified |
|---|---|---|
| Recurring cross-surface duplication symptom | ADRs [076](adr-076-tier-conformance-model.md), [078](adr-078-orgpath-attribute-schema-15-facet.md), [079](adr-079-governance-principle-reconciliation.md), [080](adr-080-intune-first-scope-disambiguation.md), [081](adr-081-directory-migration-phase-canonical-model.md) | 2026-05-23 |
| Specific cross-surface conflict noted but not yet ADR'd (OrgTree canon vs OrgPath Narrative companion) | `docs/modernization/orgtree.qmd` (27-doc canon index) + `docs/customer-documents/orgpath-narrative/index.qmd` (15-chapter narrative paraphrase) | 2026-05-23 |
| Divio Documentation System | https://documentation.divio.com | 2026-05-23 |
| ADR-076 lifecycle/authority separation by frontmatter (not URL) | [`adr-076-tier-conformance-model.md`](adr-076-tier-conformance-model.md) | 2026-05-23 |
| ADR-072 publication policy by frontmatter (`publish_to_site`, `publication_style`) | [`adr-072-canon-publication-policy.md`](adr-072-canon-publication-policy.md) | 2026-05-23 |
| ADR-082 lifecycle banner renders from frontmatter, not URL | [`adr-082-status-label-lifecycle-policy.md`](adr-082-status-label-lifecycle-policy.md) | 2026-05-23 |

## Review Triggers

This ADR must be re-evaluated when any of the following occur:

- [ ] A new top-level documentation surface is proposed outside `/customer-documents/` — review whether the umbrella discipline holds
- [ ] The Divio quadrant mapping requires a sixth section that does not fit "Tutorials / How-to / Reference / Explanation" — review whether a custom UIAO quadrant is justified
- [ ] First agency reports a broken bookmark that the alias redirects did not catch — review the alias-presence CI gate's coverage
- [ ] `scripts/scan_lifecycle_consistency.py` or `scripts/scan_publication_gaps.py` discovers a path-hardcoding regression after the move — review the scanner audit's completeness
- [ ] Sidebar visible subsection count grows past ~10 — review whether collapsible grouping is needed
- [ ] An ADR proposes restoring the dual URL surface (e.g., separating a new product line) — review whether the reorganization should be partially reversed or extended with a third surface
- [ ] 2026-11-23 — scheduled six-month review

## Related Documents

- [ADR-000 — ADR Process and Lifecycle](adr-000-adr-process.md)
- [ADR-072 — Canon Publication Policy](adr-072-canon-publication-policy.md) — establishes the `publish_to_site` and `publication_style` frontmatter machinery; ADR-083 leaves both unchanged
- [ADR-076 — Five-Tier Capability Conformance Model](adr-076-tier-conformance-model.md) — establishes the canon-vs-customer lifecycle and authority separation that this ADR preserves in frontmatter while collapsing the URL umbrella
- [ADR-078 — OrgPath Attribute Schema — 15-Facet](adr-078-orgpath-attribute-schema-15-facet.md) — same cross-surface review pattern; resolved one of the five 2026-05-22 conflicts
- [ADR-079 — Governance Principle Reconciliation](adr-079-governance-principle-reconciliation.md) — same pattern
- [ADR-080 — Intune-First Scope Disambiguation](adr-080-intune-first-scope-disambiguation.md) — same pattern
- [ADR-081 — Directory Migration Phase Canonical Model](adr-081-directory-migration-phase-canonical-model.md) — same pattern
- [ADR-082 — Status Label Lifecycle Policy](adr-082-status-label-lifecycle-policy.md) — the `{{< lifecycle-banner >}}` shortcode renders from frontmatter independent of URL; this ADR leaves the banner mechanism unchanged
- [`docs/_quarto.yml`](../../../../docs/_quarto.yml) — sidebar configuration restructured in Phase 3
- [`scripts/scan_lifecycle_consistency.py`](../../../../scripts/scan_lifecycle_consistency.py) — Phase 5 audit target
- [`scripts/scan_publication_gaps.py`](../../../../scripts/scan_publication_gaps.py) — Phase 5 audit target
