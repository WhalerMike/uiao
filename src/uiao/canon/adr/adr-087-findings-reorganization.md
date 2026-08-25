---
adr_id: adr-087
title: "Findings Reorganization — Move docs/findings/ Under /customer-documents/"
status: PROPOSED
decided: 2026-05-25
deciders: Michael Stratton
updated: 2026-05-25
next_review: 2026-11-25
review_trigger: A new artifact class is proposed at top-level outside `/customer-documents/`; the sidebar/index synchronization gap recurs after enumeration; a federal reader reports broken bookmarks not caught by alias redirects; ADR-030 is rebaselined or superseded
impact: 'Relocates the governance-findings artifact class from `docs/findings/` to `docs/customer-documents/findings/`, completing the single-URL-umbrella collapse begun in ADR-083 (which absorbed `/modernization/` into `/customer-documents/reference-architecture/` and renamed `/customer-documents/modernization/` to `/customer-documents/operational-guides/`). Preserves the §5.2 artifact-class semantics in full: findings remain distinct from canon (they document conditions the substrate does not control) and distinct from customer-document Tier 1 (they carry status lifecycle Open / Awaiting-External-Remediation / Resolved / Withdrawn, not the canon Aspirational / Adopted lifecycle from ADR-076). Only the URL path moves. Updates ADR-030 §5.2 in-place to point at the new path; supersedes that subsection only, not the ADR. Adds Quarto `aliases:` frontmatter to each moved page so the 12 existing `/uiao/findings/*.html` URLs continue to resolve. Adds the section to the `format-links: [docx]` scope so findings get the same per-page Word render and section bundle as the rest of customer-documents (current state: zero findings rendered to .docx).'
supersedes: null
superseded_by: null
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-087-findings-reorganization.html
---

# ADR-087: Findings Reorganization — Move docs/findings/ Under /customer-documents/

## Status

**PROPOSED** — 2026-05-25.

## Context

[ADR-030 §5.2](adr-030-pre-uiao-terminology-reconciliation.md) (2026, "Pre-UIAO Terminology Reconciliation") established the **governance findings** artifact class and pinned its location to `docs/findings/`:

> *Governance findings → `docs/findings/`. Findings are reader-facing operational artifacts that document … (a) the constraint, (b) primary-source evidence, (c) the capability gap, (d) proposed remedy, (e) the ownership trail. Findings live under `docs/findings/` with frontmatter marking them as governance findings. They are **not** canon — they document conditions the substrate does not control — but they …* — [adr-030 §5.2](adr-030-pre-uiao-terminology-reconciliation.md)

At the time, `/findings/` as a top-level URL sibling of `/customer-documents/` and `/modernization/` was consistent with the surrounding URL surface — every documentation class had its own top-level umbrella.

Three subsequent decisions changed the surrounding context:

1. **[ADR-076](adr-076-tier-conformance-model.md) (Tier Conformance Model)** clarified that the canon-vs-customer-doc distinction is carried by **frontmatter lifecycle**, not URL path.
2. **[ADR-072](adr-072-canon-publication-policy.md) (Canon Publication Policy)** established that whether and how a canon page renders to the published site is a **frontmatter decision** (`publish_to_site`, `publication_style`), not a URL placement decision.
3. **[ADR-083](adr-083-docs-architecture-reorganization.md) (Documentation Architecture Reorganization)** collapsed the dual `/modernization/` + `/customer-documents/` URL surface into a single `/customer-documents/` umbrella with Divio-aligned subsections, on the principle that **one URL umbrella per program is the industry norm** (AWS, Microsoft Learn, Google Cloud, VMware, HashiCorp, Stripe, Anthropic, Red Hat — all single-umbrella).

After ADR-083, `/customer-documents/` is no longer "the customer-facing surface as distinct from canon" — it is **the documentation surface**, with frontmatter carrying lifecycle and authority. Top-level `/findings/` is now the only remaining top-level documentation subsection outside that umbrella. It is the same "sibling-of-umbrella" navigation pattern ADR-083 explicitly removed for `/modernization/`.

### Current symptoms

A 2026-05-25 audit surfaced three concrete navigation defects rooted in the `/findings/` placement:

1. **Sidebar exposes 1 of 11 findings.** [`docs/_quarto.yml:77-85`](docs/_quarto.yml) defines a hand-written sidebar with a single entry pointing at `findings/index.qmd`. The other 10 deployed finding pages (FedRAMP CAE-realtime, CQD-EUII 28-day cliff, endpoint-analytics, Entra Identity Protection, Purview audit 180-day, ThousandEyes coverage scope, WUFB reporting, adoption-score, 20x-moderate-pilot, RFCs substrate assessment) are not reachable from the sidebar.
2. **The `Current findings` table in [findings/index.qmd:31-33](docs/findings/index.qmd) lists only FINDING-001.** A reader landing on the section's index sees one of 11 findings.
3. **Zero findings render to DOCX.** The `format-links: [docx]` directive is scoped to [`docs/customer-documents/_metadata.yml`](docs/customer-documents/_metadata.yml). Findings get no per-page Word download, no section bundle. This is inconsistent with the rest of the customer-facing documentation surface, which produces both.

Symptoms (1) and (2) are not strictly URL-placement bugs — they can be fixed in place by switching to a `registry.yaml`-driven enumeration. Symptom (3) is a URL-placement consequence: the DOCX-render scope is `customer-documents/`, so any artifact outside that tree skips the render. Fixing (3) in place would require extending `format-links: [docx]` to a second top-level surface, multiplying the "remember to add the new section" failure mode each time a new top-level surface is introduced. Single-umbrella collapses that surface to one.

### Why the §5.2 artifact class remains intact

ADR-030 §5.2 makes two separable claims:

| Claim | Status under this ADR |
|---|---|
| (A) Findings are a **distinct artifact class** — not canon, not pure narrative — with a five-section contract (constraint / evidence / capability gap / proposed remedy / ownership trail) and a four-state lifecycle (Open / Awaiting-External-Remediation / Resolved / Withdrawn) | **Preserved unchanged.** Frontmatter contract, contract sections, lifecycle, and ownership-trail requirement all carry over verbatim. |
| (B) Findings **live under `docs/findings/`** | **Revised.** New location is `docs/customer-documents/findings/`. |

Claim (A) is the load-bearing doctrinal decision in §5.2 — it establishes that findings are not canon, not narrative, and not a customer-document Tier 1 specification. Nothing in this ADR weakens that. Claim (B) is the URL/filesystem placement decision; under ADR-083's single-umbrella principle it now reads as incidental rather than load-bearing.

The artifact class remains visually and frontmatter-distinct under the new path: `customer-documents/findings/<slug>.qmd` with frontmatter `artifact_class: governance-finding` (existing field) is unambiguous in any reader, sidebar, or grep.

## Decision

**Move `docs/findings/` → `docs/customer-documents/findings/`.** Update ADR-030 §5.2 in-place to reference the new path and cite this ADR. Add Quarto `aliases:` frontmatter to each moved page to preserve every existing `/uiao/findings/*.html` URL via 302 redirect. Extend `format-links: [docx]` coverage to the new location automatically (no change needed — it already covers everything under `customer-documents/`). Replace the hand-written single-entry sidebar with an enumeration driven by `docs/customer-documents/findings/registry.yaml`.

### Repository moves

| Current path | New path |
|---|---|
| `docs/findings/index.qmd` | `docs/customer-documents/findings/index.qmd` |
| `docs/findings/README.qmd` | `docs/customer-documents/findings/README.qmd` |
| `docs/findings/registry.yaml` | `docs/customer-documents/findings/registry.yaml` |
| `docs/findings/fedramp-gcc-moderate-informed-network-routing.qmd` | `docs/customer-documents/findings/fedramp-gcc-moderate-informed-network-routing.qmd` |
| `docs/findings/fedramp-gcc-moderate-adoption-score-unavailable.qmd` | `docs/customer-documents/findings/fedramp-gcc-moderate-adoption-score-unavailable.qmd` |
| `docs/findings/fedramp-gcc-moderate-cae-realtime-degraded.qmd` | `docs/customer-documents/findings/fedramp-gcc-moderate-cae-realtime-degraded.qmd` |
| `docs/findings/fedramp-gcc-moderate-cqd-euii-28day-cliff.qmd` | `docs/customer-documents/findings/fedramp-gcc-moderate-cqd-euii-28day-cliff.qmd` |
| `docs/findings/fedramp-gcc-moderate-endpoint-analytics-advanced-inferred-blocked.qmd` | `docs/customer-documents/findings/fedramp-gcc-moderate-endpoint-analytics-advanced-inferred-blocked.qmd` |
| `docs/findings/fedramp-gcc-moderate-entra-identity-protection-inferred-blocked.qmd` | `docs/customer-documents/findings/fedramp-gcc-moderate-entra-identity-protection-inferred-blocked.qmd` |
| `docs/findings/fedramp-gcc-moderate-purview-audit-180day-cliff.qmd` | `docs/customer-documents/findings/fedramp-gcc-moderate-purview-audit-180day-cliff.qmd` |
| `docs/findings/fedramp-gcc-moderate-thousandeyes-coverage-scope.qmd` | `docs/customer-documents/findings/fedramp-gcc-moderate-thousandeyes-coverage-scope.qmd` |
| `docs/findings/fedramp-gcc-moderate-wufb-reporting-inferred-blocked.qmd` | `docs/customer-documents/findings/fedramp-gcc-moderate-wufb-reporting-inferred-blocked.qmd` |
| `docs/findings/fedramp-20x-moderate-pilot.qmd` | `docs/customer-documents/findings/fedramp-20x-moderate-pilot.qmd` |
| `docs/findings/fedramp-rfcs-substrate-assessment.qmd` | `docs/customer-documents/findings/fedramp-rfcs-substrate-assessment.qmd` |

13 files total.

### URL moves and redirects

| Current published URL | New published URL |
|---|---|
| `https://whalermike.github.io/uiao/findings/index.html` | `https://whalermike.github.io/uiao/customer-documents/findings/index.html` |
| `https://whalermike.github.io/uiao/findings/<slug>.html` (×11) | `https://whalermike.github.io/uiao/customer-documents/findings/<slug>.html` |

Each moved `.qmd` gets `aliases: [/findings/<basename>/]` in its frontmatter. Quarto generates a stub HTML page at the old URL that 302-redirects to the new location. The 12 existing URLs remain resolvable for any external bookmark, agency citation, ADR back-reference, or search-engine link that already points at the old path.

### DOCX rendering

No explicit change required. `docs/customer-documents/_metadata.yml` carries `format-links: [docx]` and applies to every nested page, so the moved findings inherit it automatically. Per-page `.docx` will appear at `https://whalermike.github.io/uiao/customer-documents/findings/<slug>.docx`. The [`scripts/bundle_section_docx.py`](scripts/bundle_section_docx.py) `--all` mode picks up the new section automatically (it iterates direct children of `_site/customer-documents/`), producing `findings-bundle.docx`.

### Sidebar enumeration

Replace the hand-written entry in [`docs/_quarto.yml:77-85`](docs/_quarto.yml) with an entry that enumerates all `customer-documents/findings/*.qmd`. Two acceptable forms:

```yaml
- id: findings
  title: "Governance Findings"
  style: "docked"
  contents:
    - section: "Governance Findings"
      contents:
        - customer-documents/findings/index.qmd
        - customer-documents/findings/fedramp-gcc-moderate-informed-network-routing.qmd
        - customer-documents/findings/fedramp-gcc-moderate-adoption-score-unavailable.qmd
        # … all 11 individual finding pages …
```

Or, equivalently, an `auto:` pattern (`auto: customer-documents/findings/*.qmd`) that Quarto expands at build time. Phase 2 implementation may choose either; the explicit form is preferred because the order of FedRAMP findings is editorially meaningful (severity / chronology).

Also: rename the sidebar `title:` from `"Findings"` (and the section heading from `"Security Findings"`) to `"Governance Findings"` — the page itself titles the artifact class "UIAO Governance Findings" (per the existing [findings/index.qmd:2](docs/findings/index.qmd) frontmatter) and ADR-030 §5.2 calls them "governance findings", not "security findings". The current sidebar label is the only place the class is misnamed.

### Index regeneration

Replace the hand-maintained `Current findings` table in `index.qmd` with one generated from `registry.yaml`. The registry is already the single source of truth for finding ID / title / status / severity / owner; the table can be rendered via a small Quarto inline-code block at build time, or by a `scripts/render_findings_index.py` step in the publish workflow. Phase 2 picks one mechanism. This closes symptom (2) from the Context.

### ADR-030 §5.2 update

A single in-place patch to [`src/uiao/canon/adr/adr-030-pre-uiao-terminology-reconciliation.md`](src/uiao/canon/adr/adr-030-pre-uiao-terminology-reconciliation.md) at the §5.2 paragraph:

```diff
-**5.2 — Governance findings → `docs/findings/`.** The FedRAMP
+**5.2 — Governance findings → `docs/customer-documents/findings/`.** The FedRAMP
 GCC-Moderate telemetry constraint (Appendix A §A.2 of the inbox
 drop) is a **governance finding**, not advocacy. …
@@
-Findings live under `docs/findings/` with frontmatter marking
+Findings live under `docs/customer-documents/findings/` (per
+[ADR-087](adr-087-findings-reorganization.md)) with frontmatter marking
 them as governance findings.
```

The §5.2 artifact-class definition (the five-section contract and ownership-trail principle) is unchanged. Only the path is updated, with an explicit ADR-087 back-reference so the change is auditable from the ADR-030 page.

## Cross-reference sweep

44 files in the repository reference `findings/` in path-bearing contexts. Phase 2 includes a mechanical sweep to update every reference. The set spans:

| Surface | Count | Examples |
|---|---|---|
| Canon ADRs | 4 | [adr-030](src/uiao/canon/adr/adr-030-pre-uiao-terminology-reconciliation.md), [adr-047](src/uiao/canon/adr/adr-106-fedramp-20x-integration.md), [adr-058](src/uiao/canon/adr/adr-058-microsoft-purview-conformance-adapter-coverage.md), [adr-061](src/uiao/canon/adr/adr-061-fedramp-cr26-catalog-vendoring.md) |
| Canon specs | 5 | fedramp-20x-integration, application-identity-onboarding-runbook, adapter-test-strategy, GCC-Moderate capabilities + README |
| Customer-documents pages | 6 | operational-guides (3 phase pages), validation-suites, compliance boundary-authorization, adapter-specs (purview-audit, infoblox, bluecat) |
| Academy pages | 4 | entra-id, operator-track, document-generation-guide, contributor-tier-1-setup |
| Narrative pages | 2 | UIAO-Narrative-Layer, 2026-04-fedramp narrative |
| Registries | 2 | modernization-registry.yaml, adapter-registry.yaml |
| Scripts + tooling | 2 | scripts/cleanup_live_doc_links.py, tools/lifecycle-consistency/report.json |
| Test fixtures | 2 | contract/m365 INR fixture + contract/README |
| CHANGELOG + diagram recs | 2 | CHANGELOG.md, qmd-diagram-recommendations.md |
| Findings files themselves | ~13 | self-references inside the moved directory |
| Inbox drafts (historical, not published) | 3 | drafts/aspirational-candidates-* (2 dates), drafts/relative-link-audit-* |

The sweep is regex-driven: `findings/<basename>` → `customer-documents/findings/<basename>` across the path-bearing contexts above. The single canonical sweep pattern means no judgment calls per file.

## What this ADR does NOT do

1. **Does not promote findings to customer-document Tier 1.** The lifecycle remains Open / Awaiting-External-Remediation / Resolved / Withdrawn — distinct from canon Aspirational / Adopted (ADR-076). Frontmatter `artifact_class: governance-finding` (existing) carries the distinction. URL co-location is not class merger.
2. **Does not change the five-section contract.** Constraint / evidence / capability gap / proposed remedy / ownership trail remains the per-finding requirement. The contract is enforced by the same scanner currently watching `docs/findings/`; the scanner gets a path update only.
3. **Does not change ownership semantics.** The CIO principle *"Everyone owns all problems they identify"* (ADR-030 §5.2 closing paragraph) carries over unchanged.
4. **Does not merge findings with FedRAMP narrative pages.** [`docs/narrative/2026-04-fedramp-gcc-moderate-three-assessments.qmd`](docs/narrative/2026-04-fedramp-gcc-moderate-three-assessments.qmd) and similar narrative pages remain in `docs/narrative/` (Phase 2 may revisit the narrative surface separately; out of scope here).
5. **Does not change the publication mechanism for ADR-030 itself.** ADR-030 is updated in-place under its existing publish-to-site wrapper; no ADR-030 wrapper changes.
6. **Does not introduce a new lifecycle scanner or governance mechanism.** All checks (frontmatter completeness, registry/index consistency, alias resolution) are existing scanners with path inputs updated.
7. **Does not change DOCX-render scope by extending `format-links: [docx]` to additional top-level surfaces.** The single-umbrella principle removes that motivation; nothing else needs the extension.

## Rollout

Three phases, each shippable independently.

### Phase 1 (this ADR)

- Land this ADR file at `src/uiao/canon/adr/adr-087-findings-reorganization.md`.
- Add the entry to [`docs/adr/adr-index.qmd`](docs/adr/adr-index.qmd).
- Generate the wrapper at `docs/adr/adr-087-findings-reorganization.qmd` via [`scripts/generate_adr_qmd_wrappers.py`](scripts/generate_adr_qmd_wrappers.py).
- No file moves, no cross-reference updates, no `_quarto.yml` changes.

Status flips to ACCEPTED in a separate doctrine batch PR (matching the ADRs 076/078/079/080/081/082/083 batch promotion pattern in [#651](https://github.com/WhalerMike/uiao/pull/651)).

### Phase 2 — Move + redirects + cross-ref sweep

Single PR:

1. `git mv docs/findings/ docs/customer-documents/findings/` (preserves history).
2. Add `aliases: [/findings/<basename>/]` frontmatter to each moved `.qmd`.
3. Update [`docs/_quarto.yml:44`](docs/_quarto.yml) navbar entry (`findings/index.qmd` → `customer-documents/findings/index.qmd`) and the sidebar block at lines 77-85 (enumerate all 11 findings, rename to "Governance Findings").
4. Sweep 44 cross-referencing files per the regex pattern above.
5. Update ADR-030 §5.2 in-place per the diff above.
6. Update `docs/findings/index.qmd`'s "Current findings" table to render from `registry.yaml` (or pre-populate with all 11 entries as a fallback if the registry render is deferred to Phase 3).

Verify: after deploy, all 12 old `/uiao/findings/*.html` URLs return 302→new location; all 12 new `/uiao/customer-documents/findings/*.html` URLs return 200; new `.docx` per-page renders appear; `findings-bundle.docx` builds.

### Phase 3 — Registry-driven index render (optional, deferrable)

If the index table was pre-populated in Phase 2: add the small Quarto inline-code block (or scripts step) that generates the table from `registry.yaml`. Removes the hand-maintenance failure mode that produced the symptom (2) gap (1 of 11 listed).

Can ship independently any time after Phase 2 lands.

## Relation to other ADRs

- **[ADR-030 §5.2](adr-030-pre-uiao-terminology-reconciliation.md)** — Revised in-place by Phase 2. The §5.2 artifact-class semantics are preserved; only the path is updated. ADR-030 is not superseded.
- **[ADR-083](adr-083-docs-architecture-reorganization.md)** — Direct precedent. ADR-083 collapsed `/modernization/` and `/customer-documents/modernization/` into `/customer-documents/reference-architecture/` and `/customer-documents/operational-guides/` on the same single-umbrella principle. This ADR extends that principle to the last remaining top-level documentation surface.
- **[ADR-076](adr-076-tier-conformance-model.md)** — The frontmatter-carries-authority principle that makes URL co-location safe. Findings retain their distinct artifact class via `artifact_class: governance-finding`, not via URL path.
- **[ADR-072](adr-072-canon-publication-policy.md)** — Publication mechanism (publish_to_site / publication_style) is unchanged; this ADR is a path move, not a publication-policy change.

## Provenance

- 2026-05-25 — Drafted in response to a site-walk observation that the Findings navbar entry surfaces 1 of 11 actual findings, the section label is misnamed ("Security" vs "Governance"), and findings render zero `.docx` despite the post-PR #671 fix landing for the rest of the site.
- 2026-05-25 — Verified via sitemap.xml that all 12 finding pages render and are reachable by direct URL; only the navigation pathway and DOCX scope are deficient. Verified ADR-030 §5.2 explicitly pins the location and is therefore the load-bearing doctrinal reference that must be revised in-place.
