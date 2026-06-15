# UIAO SVG Figure Style (ADR-093)

Figures are **committed SVG**, authored by Claude Code, rasterized to PNG by
`scripts/render_svg_images.py`. The SVG is the source of truth; the PNG is a
build artifact. No AI runs at render time, so **text is always exactly what the
SVG says** — this is the whole point (it retires the NanoBanana baked-in-text
defects).

> **Why PNG and not raw SVG?** The site builds `html`, `pdf`, and `docx`
> (the narratives ship downloadable Word bundles). Pandoc's docx/LaTeX writers
> need `rsvg-convert`/`inkscape` to embed SVG, which the build doesn't carry —
> so a raw `.svg` reference renders on the web but drops out of the Word/PDF
> bundle. The PNG (rendered at 2×, served `fig-format: retina`) is the portable
> artifact every format embeds. You author and review the **SVG**; the PNG is
> generated for you.

## Two registers (ADR-093 + ADR-095)

Every figure is in one of two registers, declared via the sidecar/registry
`visual_style` field:

- **`blueprint`** (default) — engineering schematics: flows, topologies,
  decision gates, architecture. The rules below are written for this register.
- **`illustrative`** ([ADR-095](../adr/adr-095-illustrative-svg-register.md)) —
  covers, openers, and figures whose job is to make an **abstract idea** land
  (a metaphor, a journey, a layer). Relaxes rules 1–2 only; see the
  *Illustrative register* section at the end.

Rule of thumb: **schematic → blueprint; abstract idea / cover / opener →
illustrative.** When in doubt, blueprint. Both registers use the same pipeline,
the same palette base, and the same absolute constraints (literal correctly
spelled text; no photographs; no vendor logos; no generative raster).

## Canvas
- **16:9 diagrams** → `viewBox="0 0 1280 720"`
- **1:1 cover/square** → `viewBox="0 0 1080 1080"`
- White background rectangle as the first child (`fill="#FFFFFF"`).

## Palette
See [`palette.json`](palette.json). Quick reference:

| Token | Hex | Use |
|---|---|---|
| navy | `#0D1B2E` | structural fills ("what AD had") |
| ice + navy border | `#EAF1FB` / `#0D1B2E` | cloud / Entra boxes |
| teal | `#1E8C8C` | good/native, connectors |
| red | `#C0392B` | loss / gap / "no native carrier" |
| amber | `#D4A017` | HIGH/CRITICAL severity ONLY |
| grey/muted/body | `#5A5A5A` / `#6B7A8D` / `#33414F` | labels / captions / body |

## Type
- Headers: `Georgia, serif`, bold.
- Body/labels: `Arial, sans-serif`.
- Code/identifiers: `Consolas, monospace`.

## Rules
1. White background; **no photographs and no vendor logos — ever, in either register.** Human figures: forbidden in `blueprint`; permitted as stylized (non-photographic) silhouettes in `illustrative` only (ADR-095).
2. **Blueprint look** (`blueprint` register): rectangles, rounded rectangles, arrows, node + edge labels; no artistic flourish. The `illustrative` register may use metaphor, scene composition, gradients, and iconography (see below).
3. **Spell everything correctly.** SVG `<text>` is literal — there is no excuse for a typo in a rendered figure. (Both registers.)
4. SVG `<text>` does not auto-wrap. Pre-wrap long lines into stacked `<tspan x=… dy=…>` lines, or center short labels with `text-anchor="middle"` + `dominant-baseline="central"`.
5. Keep it portable: prefer plain SVG (`<rect>`, `<text>`, `<line>`, `<path>`). Use `<foreignObject>` only when you must (it requires the Playwright/Chromium rasterizer, not cairosvg).
6. amber is reserved for severity/escalation — don't use it decoratively.

## Illustrative register (ADR-095)

Use when a figure's job is to make an **abstract idea** land rather than to
specify a structure — series covers, book/chapter openers, and inline concept
art (e.g. the silent NTLM fallback, the identity plane, the migration journey).

**Permitted here (and only here):**
- **Stylized human silhouettes** — simple shapes (a circle head + a rounded
  body/`<path>`), never photographic. Use the `figure` / `figure_muted` tokens.
- **Conceptual metaphor & scene** — horizons, paths, doors, layers, roots —
  each carrying one specific, nameable idea.
- **Gradients** — `<linearGradient>` / `<radialGradient>` for sky, depth, glow.
  cairosvg renders these deterministically; keep stops to the palette tokens.
- **Iconography** beyond rectangles and arrows.

**Still absolute (inherited, do not break):**
- No photographs, no vendor logos. Literal, correctly spelled `<text>`.
- `amber` stays reserved for HIGH/CRITICAL severity — never decorative. `red`
  keeps loss/gap semantics (an illustration *of* a loss may use it).
- Portable SVG; `<foreignObject>` only when unavoidable.
- **Carry an idea, not decoration.** A merely-pretty figure is out of register —
  cut it or replace it with a blueprint that conveys information.

**Illustrative palette** — see the `illustrative` group in
[`palette.json`](palette.json): `figure` / `figure_muted` for silhouettes,
`sky_top` → `sky_low` for horizon gradients, `glow` for luminous accents. Base
structural tokens (navy, teal, ice, mid_blue, greys) carry the same meaning as
in blueprint.

**Naming:** illustrative figures use the `-image-NN-` infix (e.g.
`book01-image-01-the-inheritance.svg`, `index-image-01-…`), reserving
`-diagram-NN-` for blueprints.

## Generated illustrative raster (ADR-103)

Per [ADR-103](../adr/adr-103-generated-illustrative-raster.md) the
illustrative register has **two permitted production methods**; everything
above in the illustrative section describes the *vector* method, which
remains valid. The second method is **generated raster**: illustrative
images may be produced by any tool — including generative models — and
committed directly as PNG/JPEG with no SVG sibling.

**This applies to `-image-NN-` figures only. `-diagram-NN-` blueprints are
untouched: committed hand-authored SVG, the render pipeline, and every rule
above remain mandatory for diagrams. Mermaid stays prohibited everywhere.**

For generated images the rules above reduce to four absolutes; the rest
(palette tokens, silhouette conventions, element restrictions) becomes
advisory prompt guidance:

1. **White background.**
2. **No vendor logos/trademarks; no identifiable real individuals.**
3. **No baked text — none.** The generator must be instructed to render no
   words or letterforms; labels live in the figure caption or a
   deterministic SVG/text overlay composited by tooling. (This is the
   structural fix for the typo failure mode that retired the pre-ADR-093
   pipeline — never rely on a generator to spell.)
4. **Portability:** PNG (or baseline JPEG for photographic content) — never
   WebP/AVIF (DOCX embedding breaks); long edge ≥ 2400 px (16:9 → 2400×1350,
   1:1 → 2160×2160) for retina/mobile crispness; ≤ 1.5 MB per image;
   16:9 or 1:1 aspect; embedded via standard Quarto figure syntax with
   `width="85%"` and a complete `fig-alt`.

**Provenance:** the generation prompt is the source of record — store it in
`fig-alt` (the fig-alt-as-prompt convention) or the `<name>.png.json`
sidecar (`generator`, `prompt_sha256`, `sha256`). The render script ignores
rasters without SVG siblings, so no pipeline change is involved.

## Authoring → render loop
```bash
# author docs/.../images/<name>.svg, then:
python scripts/render_svg_images.py docs/.../images/<name>.svg   # one file
python scripts/render_svg_images.py                              # all changed SVGs
python scripts/render_svg_images.py --force                      # ignore cache
```
The filename convention `<...>-(diagram|image|figure)-NN-<slug>.svg` lets the
renderer derive the sidecar `placeholder_id` (`IMAGE-NN`) and `slug`. The PNG
keeps the doc's existing reference, so `.qmd` files need no edits when a
NanoBanana PNG is replaced by its SVG-sourced version.

## Base templates
- [`template-16x9.svg`](template-16x9.svg)
- [`template-1x1.svg`](template-1x1.svg)
