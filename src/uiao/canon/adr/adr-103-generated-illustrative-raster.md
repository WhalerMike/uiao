---
adr_id: adr-103
title: "Generated Illustrative Raster — Unblocking Images While Diagrams Stay Committed SVG"
status: PROPOSED
decided: 2026-06-12
deciders: Michael Stratton
updated: 2026-06-12
next_review: 2026-12-12
review_trigger: A generated image ships with baked-in text and the overlay rule failed to catch it; a DOCX or mobile rendering defect traces to a generated raster; a third figure register is proposed; ADR-093 or ADR-095 is revised.
impact: 'Partially amends ADR-093 and ADR-095 for the illustrative register only: images (`-image-NN-` figures — covers, openers, concept art) may now be produced by any method, including generative raster, with the committed PNG as the source artifact. Blueprint diagrams (`-diagram-NN-` figures) are untouched — committed hand-authored SVG remains their single source of truth with the full ADR-093 pipeline and STYLE.md rules. The typo failure mode that retired the NanoBanana pipeline is engineered out structurally: generated images carry no text at all; every label lives in the figure caption or a deterministic overlay. Portability is a hard requirement: PNG (or JPEG for photographic content), minimum resolution for retina/mobile, file-size budget, and the standard aspect ratios, so every image embeds identically in HTML, the DOCX bundles, and small-screen renderings. Provenance moves from SVG-as-source to prompt-as-source: the generation prompt is recorded in fig-alt and the image sidecar.'
supersedes: null
superseded_by: null
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-103-generated-illustrative-raster.html
---

# ADR-103: Generated Illustrative Raster — Images Unblocked, Diagrams Unchanged

## Status

**PROPOSED** — 2026-06-12.

This ADR amends the figure doctrine for one register. It does not supersede [ADR-093](adr-093-image-generation-svg.md) or [ADR-095](adr-095-illustrative-svg-register.md) wholesale: both remain in force for blueprint diagrams, and ADR-095's register taxonomy (blueprint vs illustrative) is retained. What changes is *how illustrative images may be produced*.

## Context

[ADR-093](adr-093-image-generation-svg.md) retired the generative raster pipeline ("NanoBanana") because the generator baked misspelled text into figures, and replaced it with committed Claude-authored SVG rasterized deterministically. [ADR-095](adr-095-illustrative-svg-register.md) then split figures into two registers — **blueprint** (schematics) and **illustrative** (covers, openers, concept art) — but kept both inside the hand-authored-SVG pipeline.

Operating experience with the illustrative register (Book_19, 2026-06-11/12) exposed the cost of that uniformity: hand-authored vector art has a hard fidelity ceiling. A maximum-effort vector pass produces competent flat illustration, but it cannot reach the texture, depth, and finish of contemporary professional technical-book art — which is the standard the repository owner requires for reader-facing narrative documents. Reference images generated from the same scene briefs demonstrated both the achievable quality *and*, instructively, the original failure mode: one reference rendered its in-image label as garbled text. The conclusion is not that generation is unsafe — it is that **text inside generated pixels is unsafe**, and that constraint can be enforced structurally rather than by abandoning generation.

The two registers have fundamentally different relationships to text. A blueprint diagram *is* its labels — facet names, attribute values, error codes — so ADR-093's literal-SVG-text guarantee is load-bearing there. An illustrative image carries an idea through composition; its few labels are incidental and can live outside the pixels entirely.

## Decision

### D1. The illustrative register is unblocked: any production method, PNG as source artifact

Figures in the **illustrative register** (`-image-NN-` naming per ADR-095) may be produced by any method — generative raster models, digital painting, hand-authored SVG, or hybrids. The committed raster file is the source artifact for generated images; no SVG sibling is required. The ADR-093 rule "no generative raster" is **lifted for this register only**.

### D2. The blueprint register is unchanged

Figures in the **blueprint register** (`-diagram-NN-` naming) remain exactly as ADR-093 specifies: committed hand-authored SVG as single source of truth, deterministic rasterization via `scripts/render_svg_images.py`, full STYLE.md rules, literal spelled `<text>`. Nothing in this ADR applies to diagrams. Mermaid remains prohibited everywhere.

### D3. No baked text — the structural fix for the ADR-093 failure mode

A generated illustrative image must contain **no text whatsoever in its pixels**: no labels, no words, no letterforms requested from the generator. Every label belongs outside the image:

- in the figure **caption** (the markdown alt/caption text), or
- as a **deterministic overlay** — an SVG or text layer composited over the raster by repository tooling, where spelling is literal by construction.

Prompts must explicitly instruct the generator to render no text. An image that arrives with incidental text-like artifacts is rejected at review. This rule is what makes generation safe: the typo failure mode cannot recur in pixels that were never asked to spell anything.

### D4. Remaining absolutes (everything else becomes guidance)

The restrictions on illustrative images reduce to four absolutes:

1. **White background** — the page is white; images sit on it without seams.
2. **No vendor logos or trademarks**, and no identifiable real individuals.
3. **No baked text** (D3).
4. **Portability requirements** (D5).

Everything else that STYLE.md previously mandated for illustrative SVGs — palette tokens, silhouette conventions, element restrictions — becomes **advisory style guidance** for prompts: the navy/teal family and red-means-loss semantics keep the corpus coherent, but they no longer gate an image.

### D5. Portability: HTML, DOCX, and mobile are hard requirements

Every illustrative image, generated or vector-rendered, must satisfy:

| Requirement | Rule | Why |
|---|---|---|
| **Format** | PNG (flat/graphic content) or baseline JPEG (photographic content). **No WebP/AVIF/SVG-only.** | Pandoc embeds PNG/JPEG into DOCX reliably; WebP breaks Word embedding — the bundles are a first-class output |
| **Resolution** | Long edge ≥ 2400 px (16:9 → 2400×1350; 1:1 → 2160×2160) | Serves as 2× retina at the site's full-column (100%-width) layout; stays crisp on high-DPI mobile |
| **File size** | ≤ 1.5 MB per image | Mobile bandwidth; the orgpath-narrative section alone serves dozens of figures per book |
| **Aspect** | 16:9 or 1:1, matching the established canvases | Layouts hold across desktop, mobile, and DOCX page flow without per-image CSS |
| **Embedding** | Standard Quarto figure syntax with `width="100%"` (full text-column width, margin to margin) and a complete `fig-alt` | HTML responsiveness (max-width scaling) and accessibility come from the figure machinery, not the file; full-column width maximizes legibility of dense diagrams in the DOCX bundles |

### D6. Provenance: the prompt is the source of record

For a generated image the prompt replaces the SVG as the reproducible source. Each committed raster carries:

- the **generation prompt** recorded in the figure's `fig-alt` (the established fig-alt-as-prompt convention) or, when the fig-alt is written as a reader-facing description, in the sidecar;
- a **sidecar** `<name>.png.json` in the existing sidecar schema, with `generator` naming the producing model/tool, `prompt_sha256` over the prompt text, and `sha256` over the committed bytes.

`scripts/render_svg_images.py` ignores rasters without SVG siblings by construction; no pipeline change is required. CI image checks remain advisory for this register.

## Consequences

**Positive.** Reader-facing narrative documents can carry professional-grade illustration. The typo failure mode is eliminated structurally rather than by prohibition. Diagrams — where text is the content — keep every guarantee ADR-093 established. DOCX bundles and mobile renderings are protected by explicit format/resolution/size rules instead of incidental pipeline properties.

**Trade-offs.** Generated images are not regenerable from the repository alone (the generator is external); the prompt-as-provenance plus committed bytes is the auditable record. Visual coherence across the corpus now depends on prompt discipline rather than enforced palette tokens. Review gains a step: checking arriving images for accidental text-like artifacts.

**Neutral.** ADR-095's register taxonomy and `-image-NN-` / `-diagram-NN-` naming are unchanged. Existing illustrative SVGs remain valid — vector stays a permitted production method.

## Next actions

1. Amend `src/uiao/canon/svg-style/STYLE.md`: scope the existing illustrative-register rules as the *vector method* and add the generated-raster method under this ADR's absolutes — same PR.
2. Retrofit Book_19's eleven illustrative figures with generated raster art from revised no-text scene briefs — follow-on PR.

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
