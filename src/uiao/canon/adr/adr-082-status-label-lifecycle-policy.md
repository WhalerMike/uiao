---
adr_id: adr-082
title: "Status Label Lifecycle Policy — Page Lifecycle + Tier-Scoped Adoption"
status: ACCEPTED
decided: 2026-05-22
deciders: Michael Stratton
updated: 2026-05-22
next_review: 2026-11-22
review_trigger: A new lifecycle state is proposed; the per-page banner shortcode breaks under a Quarto upgrade; a CI gate over `lifecycle:` consistency reveals systematic drift; agencies request per-tier shipped-state filtering on the site
impact: 'Establishes a per-page `lifecycle:` frontmatter field (values: aspirational / adopted / superseded / deprecated) and a companion `tiers_adopted:` field (list of ADR-076 conformance tier numbers). Page status banners are rendered from these fields by a Quarto shortcode rather than hand-authored `callout-warning` blocks. Distinct from the existing ADR lifecycle (PROPOSED / ACCEPTED / SUPERSEDED / DEPRECATED per ADR-000), which governs ratification state and remains unchanged. Replaces the 12 hand-authored "Aspirational" callouts across canon `/modernization/` pages and the inconsistent customer-doc "Canonical — Authoritative Reference" / "Status: Active" markings with a single auditable frontmatter source. Adds CI gate validating field consistency (adopted implies non-empty tiers_adopted; superseded implies non-null superseded_by).'
supersedes: null
superseded_by: null
classification: Controlled
boundary: GCC-Moderate
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-082-status-label-lifecycle-policy.html
---

# ADR-082: Status Label Lifecycle Policy — Page Lifecycle + Tier-Scoped Adoption

## Status

**ACCEPTED** — 2026-05-24 (originally decided 2026-05-22).

## Context

The 2026-05-22 cross-surface review found status labels applied inconsistently across the corpus:

| Surface | Pattern | Mechanism |
|---|---|---|
| **Canon `/modernization/` pages (all 12)** | Hand-authored `::: {.callout-warning}` block with the text "Aspirational — canonically declared, not yet fully adopted" | Per-page Markdown, no metadata |
| **`_quarto.yml` footer** (L28) | Site-wide statement: "many components are not yet implemented…Pages describing capabilities that are canonically declared but not yet fully adopted carry an additional Aspirational callout at the top" | Site config; references the manual callout convention |
| **Customer-doc pages (e.g., `identity-modernization.qmd`)** | Header text "Status: Canonical — Authoritative Reference" / "Version: 1.0" | Per-page prose, no metadata |
| **ADRs** | Frontmatter `status:` field (PROPOSED/ACCEPTED/SUPERSEDED/DEPRECATED) per [ADR-000](adr-000-adr-process.md) | Frontmatter, validated by CI |

### Three problems

1. **Blanket vs per-page contradiction.** The canon side's blanket "Aspirational" banner says "nothing is adopted yet." Customer-side guides on the same subjects say "v1.0 shipped" with quantitative success criteria. Federal readers get opposite authority signals.
2. **Hand-authored banners drift.** 12 canon pages carry essentially the same callout block as Markdown prose. Any update to the wording requires touching 12 files. The wording IS subtly different across pages already (some say "canonically declared, not yet fully adopted"; others say "operational instantiation is under development").
3. **No machine-readable adoption state.** Tools that want to summarize "what is adopted at Tier N" or "which canon docs are aspirational" have nothing to query — the information lives only in callout prose.

[ADR-076](adr-076-tier-conformance-model.md) introduced the source-vs-release distinction (GitHub repo = pre-release / canon; Platform Server = released artifact at version X.Y.Z) but did not formalize per-page mechanics. [ADR-072](adr-072-canon-publication-policy.qmd) introduced the `publish_to_site:` frontmatter machinery and scanner — exactly the right pattern to extend for lifecycle.

### Code-is-SSOT direction

Per the `feedback_code_is_ssot` memory pattern, status should be expressed in frontmatter (machine-readable, validatable, auditable) — not prose. The ADR-000 ADR-lifecycle pattern proves this works (every ADR has a validated `status:` field). Extending the pattern to non-ADR pages with a page-level `lifecycle:` field follows the same discipline.

## Decision

UIAO declares a **two-dimensional lifecycle**:

### Dimension 1: ADR lifecycle (unchanged)

Per [ADR-000](adr-000-adr-process.md), ADRs declare ratification state in frontmatter:

```yaml
status: PROPOSED | ACCEPTED | SUPERSEDED | DEPRECATED
```

ADRs are governed by the existing process. This ADR does not modify ADR-000.

### Dimension 2: Page lifecycle (new)

Non-ADR canon and customer-doc pages declare adoption state in frontmatter:

```yaml
lifecycle: aspirational | adopted | superseded | deprecated
tiers_adopted: []                    # list of ADR-076 tier numbers; required if lifecycle=adopted
lifecycle_review: 2026-11-22         # ISO date; review trigger
superseded_by: null                  # path to successor page; required if lifecycle=superseded
deprecated_replacement: null         # path to replacement; optional if lifecycle=deprecated
```

**Lifecycle values:**

| Value | Meaning | Banner rendered |
|---|---|---|
| `aspirational` | Canon-declared intent; not yet operationally adopted at any tier. | Yellow `callout-warning`: "Aspirational — canonically declared, not yet fully adopted." Same wording as today's hand-authored block. |
| `adopted` | Operationally adopted at one or more ADR-076 tiers. `tiers_adopted:` list cites which. | Green `callout-note`: "Adopted at Tier N (Capability Name)." For multiple tiers, lists each. |
| `superseded` | Replaced by a successor page. `superseded_by:` cites the path. | Red `callout-important`: "Superseded by [link to successor]." Page kept for audit trail; ranking deprioritized in search/sidebar. |
| `deprecated` | Retiring without direct successor. `deprecated_replacement:` optional. | Yellow `callout-warning`: "Deprecated — see [replacement if any]." |

### Banner rendering: Quarto shortcode

A new Quarto shortcode renders the banner from frontmatter so authors never hand-write callout blocks for lifecycle status:

```markdown
{{< lifecycle-banner >}}
```

The shortcode reads `lifecycle:` and `tiers_adopted:` from page frontmatter and emits the appropriate callout. Hand-authored callouts for lifecycle are deprecated in favor of the shortcode. (Callouts for other purposes — `callout-important`, `callout-tip` for substantive content — remain valid.)

### CI gate (extends ADR-072 scanner)

`scripts/scan_publication_gaps.py` is extended to validate lifecycle consistency:

| Rule | Failure mode |
|---|---|
| `lifecycle: adopted` requires non-empty `tiers_adopted:` | CI fails: "adopted lifecycle requires at least one tier" |
| `lifecycle: superseded` requires non-null `superseded_by:` resolving to an existing page | CI fails: "superseded lifecycle requires successor link" |
| Tier values in `tiers_adopted:` must be in `[1, 2, 3, 4, 5]` per ADR-076 | CI fails: "invalid tier number" |
| `lifecycle_review:` date in the past produces a non-blocking advisory in the gap-report | Advisory only |

### Defaults when `lifecycle:` is absent

Defaults match the implicit convention today (no manual backfill required for already-correctly-flagged pages):

| Path pattern | Default |
|---|---|
| `src/uiao/canon/adr/adr-*.md` | n/a — ADRs use the `status:` field (Dimension 1), not `lifecycle:` |
| `src/uiao/canon/UIAO_*.md`, `docs/modernization/*.qmd` | `aspirational` (matches today's blanket callout convention) |
| `docs/customer-documents/**/*.qmd` | `adopted, tiers_adopted: [1]` (matches today's "Canonical" / "v1.0" framing — Tier 1 = Passive Observation is the minimum any customer-doc implies) |
| All other paths | Scanner reports as `lifecycle_unset` — author must declare |

### Relationship to `_quarto.yml` footer

The site-wide footer statement is rewritten to reference the lifecycle mechanism rather than describe a per-page convention. Footer becomes: "Page status is declared per page in frontmatter and rendered by the `{{< lifecycle-banner >}}` shortcode. See ADR-082 for the policy."

## Rationale

1. **Code-is-SSOT applied to status.** Status is metadata; metadata belongs in frontmatter; frontmatter is validatable in CI. The current hand-authored callout pattern is prose drift that has no enforcement mechanism — exactly the problem ADR-078/079/080/081 were designed to prevent in their respective domains.

2. **Two-dimensional separation honors existing machinery.** ADRs already have a working lifecycle (`status:`); this ADR doesn't touch it. Non-ADR pages get their own field with a vocabulary that fits their concern (adoption state, not ratification state). Conflating them (Option B in the asking) would force ADRs to declare `tiers_adopted:` (meaningless for an ADR) or force pages to use `ACCEPTED` (meaningless for an adoption claim).

3. **Tier integration honors ADR-076.** The whole point of ADR-076's five-tier conformance model is that adoption is per-tier, not binary. A page describing OrgPath drift can be `adopted, tiers_adopted: [1, 3]` (the discovery scanner ships at Tier 1; the auto-remediator ships at Tier 3) while still being aspirational at Tier 4 (no Platform Server enforcement yet). The `tiers_adopted:` field expresses this directly.

4. **Quarto shortcode eliminates banner drift.** 12 canon pages currently carry similar-but-not-identical hand-authored callouts. The shortcode means one banner template, rendered from authoritative metadata. Any wording change happens in one place.

5. **CI gate is the same pattern that worked for ADR-072.** The `scan_publication_gaps.py` scanner already walks frontmatter and gates merges. Extending it for lifecycle consistency is mechanical.

6. **Defaults match existing convention.** Pages without `lifecycle:` default to what they implicitly carry today — canon defaults to `aspirational`; customer-docs default to `adopted, [1]`. Backfill becomes incremental, not a flag day. New pages explicitly declare; existing pages get cleaned up as they're touched.

## Consequences

### Positive

- One source of truth for page status: frontmatter.
- 12 hand-authored "Aspirational" callouts replaced by a single shortcode that reads frontmatter.
- Page status becomes auditable in CI — drift is impossible to ship silently.
- Per-tier adoption is expressible directly, not via prose.
- Tools that want to render "what is adopted at Tier 3" can query the corpus.
- ADR machinery (ADR-000 lifecycle, ADR-072 scanner) extended naturally — no rewrite.

### Negative

- **Per-page backfill effort.** ~12 canon `/modernization/` pages + an unknown number of customer-doc pages need explicit `lifecycle:` and `tiers_adopted:` fields. Defaults cover the common case but explicit declarations are preferred. Backfill is Phase 4–5 work, incremental.
- **Quarto shortcode authoring.** New shortcode `{{< lifecycle-banner >}}` needs to be written (Phase 2). Modest engineering.
- **Scanner extension.** `scan_publication_gaps.py` gains lifecycle-consistency checks (Phase 1). Modest engineering.
- **Footer rewrite.** `_quarto.yml` footer statement (L28) needs updating to reference the new mechanism rather than the manual convention.

### Risks

- **`tiers_adopted:` drift.** A page may declare `adopted, [3]` but the Tier 3 implementation gets reverted, leaving the page falsely claiming adoption. Mitigation: lifecycle_review date triggers periodic re-validation; CI gate flags pages whose review date has passed.
- **Authors may overuse `adopted` to make pages look stronger.** Risk that "adopted" becomes the default puff. Mitigation: CI gate requires `tiers_adopted:` to cite specific tiers; reviewers can challenge tier claims in PR review. The default for new canon pages is `aspirational`, not `adopted`.
- **Shortcode rendering may break under Quarto upgrades.** Mitigation: review trigger flags it; shortcode is small and testable.
- **`lifecycle: superseded` link rot.** If `superseded_by:` points to a moved or deleted page, the page-level claim becomes false. Mitigation: CI gate validates `superseded_by:` resolves to an existing page; existing link-check workflow catches downstream cases.

## Implementation phases

| Phase | Branch | Scope |
|---|---|---|
| **0** | `charter/adr-082-status-lifecycle` (this PR) | Doctrine ADR. No schema or page edits. |
| **1** | `code/metadata-schema-lifecycle-fields` | Add `lifecycle`, `tiers_adopted`, `lifecycle_review`, `superseded_by`, `deprecated_replacement` to `src/uiao/schemas/metadata-schema.json`. Extend `scripts/scan_publication_gaps.py` with the validation rules in this ADR's Decision section. |
| **2** | `code/quarto-lifecycle-banner-shortcode` | Author the `{{< lifecycle-banner >}}` Quarto shortcode under `docs/_extensions/uiao-lifecycle/`. Renders the appropriate callout from frontmatter; unit-test against a fixture page. |
| **3** | `canon/quarto-footer-lifecycle-reference` | Update `_quarto.yml` page footer (L28) to reference the new mechanism rather than describing the manual callout convention. |
| **4** | `canon/modernization-pages-lifecycle-backfill` | Backfill the 12 canon `/modernization/` pages: add `lifecycle: aspirational` (or `adopted` where appropriate) frontmatter; replace the hand-authored "Aspirational" callout blocks with `{{< lifecycle-banner >}}` shortcode invocations. |
| **5** | `canon/customer-docs-lifecycle-backfill` | Backfill customer-docs pages with `lifecycle:` field. Most default to `adopted, tiers_adopted: [1]` per the defaults table; pages describing aspirational customer guidance get `aspirational`. ~50+ customer-doc pages — may be split into sub-PRs per pillar (compliance, modernization, substrate, etc.). |
| **6** | `canon/lifecycle-cross-ref-sweep` | Sweep ADRs and canon for references to "Aspirational" as a manual convention; update to cite ADR-082's frontmatter-driven mechanism. |

6 phases. Comparable scope to ADR-079/080/081; Phase 5 is the largest single chunk.

## Verification Sources

| Source | Reference | Last Verified |
|---|---|---|
| 12 canon `/modernization/` pages with hand-authored "Aspirational" callouts | Grep over `docs/modernization/` found 12 files with `callout-warning` patterns; e.g., `docs/modernization/index.qmd` L7–15, `codebook.qmd` L13–18, `adapters.qmd` L7–12 | 2026-05-22 |
| `_quarto.yml` footer convention | `docs/_quarto.yml` L28 page-footer statement | 2026-05-22 (line referenced; not directly re-read for this ADR) |
| Customer-doc status convention | `docs/customer-documents/modernization/identity-orgtree/identity-modernization.qmd` L39 ("Status: Canonical — Authoritative Reference") | 2026-05-22 |
| ADR lifecycle (unchanged) | [`adr-000-adr-process.md`](adr-000-adr-process.md) — PROPOSED/ACCEPTED/SUPERSEDED/DEPRECATED | 2026-05-22 |
| Frontmatter scanner pattern to extend | [`adr-072-canon-publication-policy.md`](adr-072-canon-publication-policy.md) + `scripts/scan_publication_gaps.py` | 2026-05-22 |
| Tier model for `tiers_adopted:` | [`adr-076-tier-conformance-model.md`](adr-076-tier-conformance-model.md) — 5 tiers, per-capability declarations | 2026-05-22 |

## Review Triggers

This ADR must be re-evaluated when any of the following occur:

- [ ] A new lifecycle state is proposed (e.g., `archived`, `experimental`)
- [ ] The Quarto shortcode breaks under a Quarto major-version upgrade
- [ ] The CI gate over `lifecycle:` consistency reveals systematic drift (e.g., >10% of `adopted` pages have stale `tiers_adopted:`)
- [ ] Agencies request per-tier filtering on the published site (e.g., "show me only Tier 4 adopted content") — would justify additional metadata or query tooling
- [ ] ADR-076 tier set changes (5 tiers becomes 4 or 6) — `tiers_adopted:` enum updates
- [ ] 2026-11-22 — scheduled six-month review

## Related Documents

- [ADR-000 — ADR Process and Lifecycle](adr-000-adr-process.md) — ADR lifecycle (Dimension 1) unchanged; this ADR adds page lifecycle (Dimension 2) without modifying ADR-000
- [ADR-072 — Canon Publication Policy](adr-072-canon-publication-policy.md) — provides the frontmatter scanner machinery that Phase 1 extends
- [ADR-076 — Five-Tier Capability Conformance Model](adr-076-tier-conformance-model.md) — defines the 5 tiers that populate `tiers_adopted:`
- [ADR-078 — OrgPath Attribute Schema — 15-Facet](adr-078-orgpath-attribute-schema-15-facet.md) — same pattern: code-is-SSOT discipline applied to a doctrinal-conflict surface
- [ADR-079 — Governance Principle Reconciliation](adr-079-governance-principle-reconciliation.md) — same pattern: canon vs customer-doc reconciliation via metadata, not prose
- [ADR-080 — Intune-First Scope Disambiguation](adr-080-intune-first-scope-disambiguation.md) — same pattern: doctrinal disambiguation via naming + cross-reference
- [ADR-081 — Directory Migration Phase Canonical Model](adr-081-directory-migration-phase-canonical-model.md) — same pattern: universal scaffold + adapter-specific refinement
- [`src/uiao/schemas/metadata-schema.json`](../../schemas/metadata-schema.json) — Phase 1 extends with new `lifecycle:` fields
- [`scripts/scan_publication_gaps.py`](../../../../scripts/scan_publication_gaps.py) — Phase 1 extends with consistency rules
- [`docs/_quarto.yml`](../../../../docs/_quarto.yml) — Phase 3 rewrites the page-footer convention statement
