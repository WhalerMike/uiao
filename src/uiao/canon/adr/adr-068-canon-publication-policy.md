---
adr_id: adr-068
title: "Canon Publication Policy — `publish_to_site` Frontmatter Field and Publication-Gap Scanner"
status: ACCEPTED
decided: 2026-05-14
deciders: Michael Stratton
updated: 2026-05-14
next_review: 2026-11-01
review_trigger: Substantive change to the published-site Quarto pipeline; introduction of an auto-include publication mode; first publication-gap scanner CI gate promotion
impact: Adds optional `publish_to_site` and `publication_style` frontmatter fields recognized by `src/uiao/schemas/metadata-schema.json`; introduces `scripts/scan_publication_gaps.py` as advisory tooling; declares default publication intent per content class
supersedes: null
superseded_by: null
classification: Controlled
boundary: GCC-Moderate
---

# ADR-068: Canon Publication Policy — `publish_to_site` Frontmatter Field and Publication-Gap Scanner

## Status

**ACCEPTED** — 2026-05-14

## Context

UIAO's published documentation site at <https://whalermike.github.io/uiao/>
is a Quarto site built from `docs/` (Quarto `.qmd` narratives explicitly
listed in `docs/_quarto.yml`). The site is the customer- and developer-
facing surface of the canon. It is curated by hand: a `.qmd` page
narrates the canon for its audience and links back to the canonical
source under `src/uiao/`.

This pattern produces high-quality public-facing pages but has three
structural weaknesses:

1. **No declared publication intent.** Canon docs do not record whether
   they are intended for public consumption. New canon (e.g., the
   `intune-first-onboarding` module added in ADR-067) lands in the repo
   and must be remembered, manually, for the site backlog.

2. **No drift detection.** A canon doc that *should* be published but
   has no corresponding `.qmd` page is invisible to CI. The gap is
   discovered only when someone notices the missing page.

3. **No content-class policy.** ADRs, UIAO_NNN specs, modernization
   modules, and JSON schemas have different audiences and warrant
   different publication treatments. The repo currently has no policy
   declaring which classes are publishable, in what style, or under
   what default.

The intune-first-onboarding promotion (PR #502) surfaced all three
weaknesses concretely: a 9-document operational module landed in
`src/uiao/modernization/` with zero corresponding `.qmd` pages and zero
CI signal that the gap exists.

## Decision

**This ADR establishes the Canon Publication Policy: every canon-class
document declares its publication intent in frontmatter via a
`publish_to_site` field and (optionally) a `publication_style` field.
A scanner under `scripts/scan_publication_gaps.py` walks the repository
and emits a gap report. The scanner runs as advisory tooling now and is
positioned to become a CI gate after the publication backlog closes.**

### The `publish_to_site` field

```yaml
publish_to_site: true | false
```

| Value | Meaning |
|---|---|
| `true` | Document is intended for the published site. The scanner expects a corresponding `.qmd` entry in `docs/_quarto.yml` and will report a gap if absent. |
| `false` | Document is repo-internal. Drafts, fixtures, transitional content, contributor-facing notes. The scanner does not expect a published page. |

**Defaults when the field is absent:**

| Path pattern | Default |
|---|---|
| `src/uiao/canon/UIAO_*.md` | `true` |
| `src/uiao/canon/adr/adr-*.md` | `true` (excluding `adr-000-adr-process.md`, which is process-internal) |
| `src/uiao/modernization/**/*.md` (excluding `README.md`) | `true` |
| `src/uiao/schemas/**/*.json` | `true` (style: `reference`) |
| `inbox/**` | `false` |
| `tests/**`, `scripts/**`, `tools/**` | `false` |
| All other paths | Scanner reports as `unclassified`; governance disposition required |

### The `publication_style` field

```yaml
publication_style: narrative | include | reference
```

| Style | Meaning | Typical content class |
|---|---|---|
| `narrative` | A hand-authored `.qmd` page summarizes the canon for the audience. The canonical source is linked, not embedded. | Marquee canon docs (UIAO_007, the modernization track narratives) |
| `include` | A small `.qmd` wrapper supplies title and one-paragraph intro, then `{{< include >}}`s the canon markdown body verbatim. | Most ADRs, modernization-module READMEs, doctrine docs that read well as-is |
| `reference` | A generated `.qmd` page renders the file as developer reference (e.g., schema rendered as a property table; YAML registry rendered as a sortable table). | JSON schemas, YAML registries, OpenAPI specs |

**Default when absent:** `include` for canon docs without an existing
`narrative`-style `.qmd` page; `narrative` if a hand-authored `.qmd`
page already exists at the expected path; `reference` for JSON
schemas and YAML registries.

### The publication-gap scanner

`scripts/scan_publication_gaps.py` walks the repository, reads
frontmatter for every candidate document, applies the defaults above,
checks the published-site sidebar in `docs/_quarto.yml`, and emits:

- **stdout** — a human-readable summary table with gap counts per class
- **`tools/publication-gaps/report.md`** — the full markdown gap report
- **`tools/publication-gaps/report.json`** — the machine-readable
  equivalent for CI consumption

The scanner exits 0 in advisory mode (default). A `--strict` flag
makes it exit 1 if any gap is detected.

## Rationale

1. **Declared intent is more honest than inferred intent.** Today, "is
   this canon meant for the public site?" is answered by trial and
   error or by tribal knowledge. Frontmatter makes the answer
   inspectable and audit-able. New contributors do not have to guess.

2. **Gap detection prevents publication backlog from accumulating
   silently.** ADR-067's promotion produced 9 publishable canon
   documents and zero corresponding site pages. Without a scanner,
   the gap is invisible until someone notices. With the scanner, the
   gap appears on every CI run.

3. **Content-class policy aligns publication treatment with audience.**
   ADRs typically read well as direct includes; UIAO marquee specs
   benefit from hand-authored summaries; schemas are best rendered as
   property tables. A single one-size-fits-all approach degrades the
   site for some classes. The `publication_style` field captures the
   variation.

4. **`additionalProperties: true` in the metadata schema means this
   policy is non-breaking.** Existing canon docs without the new
   fields continue to validate. The scanner falls back to defaults.
   Backfill happens incrementally as new canon docs are authored or
   touched, not as a forced flag day.

5. **Advisory mode before blocking mode.** Going straight to a CI
   gate would block the next several PRs until the publication
   backlog closes. Advisory-then-blocking is the conservative path:
   measure first, close the backlog, then enforce.

## Consequences

### Positive

- Every canon doc carries inspectable publication intent.
- Publication backlog is measured, not invisible.
- New canon authors know what is expected of them at authoring time
  (a frontmatter field and a corresponding `.qmd` plan).
- Future automation (auto-include via `{{< include >}}`, schema-
  rendered reference pages) has a declared signal to act on.
- Foundation for a future "publish" CLI subcommand that scaffolds the
  expected `.qmd` page from canon frontmatter.

### Negative

- **Frontmatter backfill effort.** ~108 existing canon documents
  (36 UIAO_NNN + 72 ADRs) eventually need explicit `publish_to_site`
  fields. Defaults cover the common case, but explicit declarations
  are preferred for auditability. Backfill is a follow-up work item,
  not a precondition.
- **Scanner false positives are possible during defaults rollout.**
  The default-true rule for `src/uiao/canon/UIAO_*.md` will surface
  every UIAO doc without a corresponding `.qmd` as a gap. Some of
  these may be legitimately not-for-publication (internal-process
  docs that happen to live under canon/). The first scanner run will
  produce a triage list, not a verdict.
- **`publication_style` adds complexity.** A simple `publish_to_site:
  true|false` would be sufficient for the gap-detection use case.
  Adding `publication_style` is forward-looking — it makes the
  publication mode explicit so future automation can act on it
  without ambiguity. Cost is one extra optional field.

### Risks

- **Default mis-classification.** The defaults table assumes most
  things under `src/uiao/canon/` are publishable. If a class of
  canon doc is genuinely not for public consumption, those docs will
  surface as gaps until the field is explicitly set to `false`.
  Mitigation: the scanner emits `unclassified` and `default-applied`
  separately so explicit declarations can be prioritized.
- **`docs/_quarto.yml` parsing fragility.** The scanner parses the
  sidebar to determine "what is published." If the YAML structure
  changes (new section types, includes from external files), the
  scanner needs corresponding updates. Mitigation: the scanner
  treats unrecognized YAML structures as opaque and warns rather
  than failing.
- **Scanner becomes shelfware.** Advisory tools that no one runs do
  not change behavior. The promotion path to CI gate must be
  followed within a defined window (target: scanner promoted to CI
  advisory within 30 days of this ADR; promoted to blocking gate
  after publication backlog closes, target ≤ 90 days).

## Verification Sources

| Source | Reference | Last Verified |
|---|---|---|
| Metadata schema | [`src/uiao/schemas/metadata-schema.json`](../../schemas/metadata-schema.json) — `additionalProperties: true` permits new fields | 2026-05-14 |
| Frontmatter validator | [`scripts/validate_canon_frontmatter.py`](../../../../scripts/validate_canon_frontmatter.py) — runs the schema against `src/uiao/canon/*.md` | 2026-05-14 |
| Published-site sidebar source | [`docs/_quarto.yml`](../../../../docs/_quarto.yml) — single source of truth for what is on the site | 2026-05-14 |
| ADR-067 — first promotion that exposed the gap | [`adr-067-intune-first-asset-onboarding.md`](adr-067-intune-first-asset-onboarding.md) | 2026-05-14 |

## Review Triggers

This ADR must be re-evaluated when any of the following occur:

- [ ] The Quarto pipeline gains an auto-include capability that
      removes the need for hand-maintained `_quarto.yml` sidebar
      entries
- [ ] The metadata schema validator switches to schema-driven
      validation (the schema already has `additionalProperties: true`,
      but a stricter mode might be introduced for the new field)
- [ ] The publication-gap scanner is promoted from advisory to
      blocking CI gate
- [ ] The scanner's default-true rule for `src/uiao/canon/UIAO_*.md`
      proves to mis-classify a substantial fraction (≥ 20%) of canon
      docs, suggesting the default should be flipped or the path
      patterns refined
- [ ] Microsoft Ignite 2026 (November) — scheduled review

## Related Documents

- [ADR-000 — ADR Process and Lifecycle](adr-000-adr-process.md)
- [ADR-067 — Intune-First Asset Onboarding](adr-067-intune-first-asset-onboarding.md) (the promotion that exposed the gap this ADR closes)
- [`src/uiao/schemas/metadata-schema.json`](../../schemas/metadata-schema.json) — schema updated by this ADR to document the new fields
- [`scripts/scan_publication_gaps.py`](../../../../scripts/scan_publication_gaps.py) — the scanner introduced by this ADR
- [`docs/_quarto.yml`](../../../../docs/_quarto.yml) — the publication sidebar the scanner reads
