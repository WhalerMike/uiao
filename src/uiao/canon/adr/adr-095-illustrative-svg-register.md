---
adr_id: adr-095
title: "Illustrative SVG register — expanding the figure house style beyond the engineering-blueprint boundary"
status: PROPOSED
decided: 2026-06-06
deciders: Michael Stratton
updated: 2026-06-06
next_review: 2026-12-06
review_trigger: A document adopts illustrative figures at scale and the register needs tier-specific guidance; illustration begins drifting into decoration (figures that carry no idea); a need re-emerges for photographic/raster art that vector SVG cannot serve; the rasterizer or the svg-style palette/canvas conventions change
impact: "Adds a second visual register — 'illustrative' — alongside the default 'blueprint' register established by ADR-093, governed by the identical committed-SVG → deterministic-raster pipeline. Relaxes STYLE.md rules 1–2 for the illustrative register only (permits stylized human silhouettes, conceptual metaphor and scene composition, gradients, iconography) while preserving every hard constraint that made ADR-093 work: SVG is the source of truth, PNG is a build artifact, no generative AI runs at render time, text is literal and spelled correctly, no photographs, no vendor logos. Extends src/uiao/canon/svg-style/ (STYLE.md + palette.json). Pilots the register on the SQL Server narrative (series cover, book openers, inline concept illustrations). Does not supersede ADR-093 — blueprint remains the default for schematic and architecture diagrams."
supersedes: null
superseded_by: null
classification: Controlled
boundary: GCC-Moderate
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-095-illustrative-svg-register.html
---

# ADR-095: Illustrative SVG register (expanding beyond the blueprint boundary)

## Status

**PROPOSED** — June 6, 2026

## Context

[ADR-093](adr-093-image-generation-svg.md) put every figure on a committed-SVG
footing: each figure is hand-authored SVG, rasterized deterministically to PNG
in CI (`scripts/render_svg_images.py`, `cairosvg`-first), with **no generative
step at render time**. That decision retired the Gemini "NanoBanana" raster
generator specifically because it baked spelling errors into pixels
(`MICROSFT CLOUD STACK`, `policy inherts`, `travseral`). The anti-typo guarantee
— "the text is always exactly what the source says" — is the whole point of the
regime, and it is non-negotiable.

ADR-093 also fixed the **house style** in `src/uiao/canon/svg-style/STYLE.md`.
Two of its rules draw a deliberately narrow boundary — call it the **blueprint
boundary**:

> 1. White background; **no photos, no people, no vendor logos**.
> 2. **Engineering-blueprint look**: rectangles, rounded rectangles, arrows,
>    node + edge labels.

That boundary serves *schematic* figures very well — flows, topologies,
decision gates, architecture. It serves *explanatory* figures poorly. A series
cover, a book opener, or a figure whose job is to make an **abstract idea**
land — the silent NTLM fallback, the identity plane that Conditional Access
sits on, the migration from a domain keep to the Entra identity plane — reads
better as **illustration** than as boxes-and-arrows. Forcing every such figure
through the blueprint boundary either flattens the idea or produces a diagram
that is technically a schematic but communicates nothing a paragraph didn't.

We want to widen the visual vocabulary **without** reopening the defect class
ADR-093 closed. The constraint that caused the typos was *generative raster*,
not *vector authoring*. Illustration authored as committed vector SVG keeps the
anti-typo guarantee intact — the text is still literal `<text>` — while
unlocking metaphor, scene, figure, and gradient.

## Decision

**1. Introduce a second visual register: `illustrative`, alongside the default
`blueprint`.**
Both registers are authored as committed SVG and rendered by the same
deterministic pipeline. `blueprint` remains the default and the correct choice
for schematic/architecture diagrams. `illustrative` is **additive** — it is the
right choice for covers, openers, and conceptual/metaphor figures.

**2. The illustrative register relaxes STYLE.md rules 1–2 — and nothing else.**
In the illustrative register the following are now permitted:
- **Stylized human silhouettes / figures** (abstract shapes — never photographs
  of people).
- **Conceptual metaphor and scene composition** — horizons, paths, doors,
  layers, roots — used to carry one specific idea.
- **Gradients and richer fills** (`<linearGradient>`, `<radialGradient>`) for
  depth, sky, glow.
- **Iconography** beyond rectangles and arrows.

**3. Every hard constraint from ADR-093 is preserved unchanged.**
- SVG is the source of truth; PNG is the build artifact.
- **No generative AI / no API key at render time** — `cairosvg`-first, literal text.
- **Spell everything correctly.** SVG `<text>` is literal; a typo is
  inexcusable in either register.
- **No photographs, no vendor logos**, in *either* register.
- Portable SVG; `<foreignObject>` only when unavoidable (it forces the
  Playwright/Chromium rasterizer).
- `amber` remains reserved for HIGH/CRITICAL severity — it is not an
  illustrative/decorative colour. `red` keeps its loss/gap semantics; an
  illustration of a loss (e.g. the silent fallback door) may use it because the
  semantics still hold.

**4. The register is declared, not guessed.**
Canonical figures declare the register through the `visual_style` field in
`image-registry.yaml` (`illustrative`; default `blueprint`), reusing the same
field ADR-093 reserved for the out-of-scope `cover-art` value. Document-local
figures — like the SQL Server narrative pilots — declare it through the
`-image-NN-` filename infix, reserving `-diagram-NN-` for blueprints. House
style for the new register is centralized in `svg-style/STYLE.md` (a new "Two
registers" section) and `palette.json` (an `illustrative` token group + gradient
guidance).

**5. Illustration must carry an idea, not decorate.**
The standing guard against the obvious failure mode: every illustrative figure
must make one specific, nameable point that the prose around it is making. A
figure that is merely pretty is out of register and should be cut or replaced
with a blueprint that does carry information.

## Consequences

**Positive**
- Explanatory range the blueprint boundary could not reach: covers, openers,
  and metaphors for abstract authentication concepts.
- The anti-typo guarantee is fully preserved — illustration is still literal
  vector text, not generative raster.
- Figures remain diff-reviewable, deterministic, versioned source.
- No new build dependency, no API key, no per-figure cost.

**Costs / trade-offs**
- Authoring an illustration is more judgment-heavy than a schematic; the
  payoff is only real when the idea genuinely reads better as illustration.
- Risk of drift into decoration — mitigated by decision #5 and review.
- Two registers mean authors must choose; STYLE.md gives the rule of thumb
  (schematic → blueprint; abstract idea / cover / opener → illustrative).

**Rollout**
- The **SQL Server narrative** is the pilot: a series cover, a Book 01 opener,
  and two inline concept illustrations (silent NTLM fallback; the identity
  plane / zero-trust boundary). Blueprint diagrams already in that series are
  untouched.
- Other documents adopt illustrative figures incrementally; there is no
  back-fill mandate.

## Alternatives considered

- **Keep the strict blueprint boundary only.** Rejected: it forces covers and
  conceptual figures into a schematic idiom that communicates poorly.
- **Re-introduce a generative raster backend for artistic figures.** Rejected:
  it reopens exactly the baked-in-text defect class ADR-093 was written to
  eliminate. Vector illustration gets most of the expressive range with none of
  the risk.
- **Licensed stock photography for openers/covers.** Rejected for now: it
  introduces license-provenance tracking and the "binary committed into the
  source tree" question (a repo invariant), with no anti-typo benefit over
  authored vector. Left open as a future register behind its own ADR if a
  photographic need emerges.

## References

- [ADR-093](adr-093-image-generation-svg.md) — committed-SVG pipeline this extends
- `src/uiao/canon/svg-style/STYLE.md` — house style (now two registers)
- `src/uiao/canon/svg-style/palette.json` — palette + illustrative tokens
- `scripts/render_svg_images.py` — the deterministic rasterizer (unchanged)
- SQL Server narrative — pilot document for the illustrative register
- AGENTS.md §7 — diagram source-of-truth principle (updated to note both registers)
