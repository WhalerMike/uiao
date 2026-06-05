# UIAO SVG Figure Style (ADR-093)

Figures are **committed SVG**, authored by Claude Code, rasterized to PNG by
`scripts/render_svg_images.py`. The SVG is the source of truth; the PNG is a
build artifact. No AI runs at render time, so **text is always exactly what the
SVG says** — this is the whole point (it retires the NanoBanana baked-in-text
defects).

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
1. White background; no photos, no people, no vendor logos.
2. Engineering-blueprint look: rectangles, rounded rectangles, arrows, node + edge labels.
3. **Spell everything correctly.** SVG `<text>` is literal — there is no excuse for a typo in a rendered figure.
4. SVG `<text>` does not auto-wrap. Pre-wrap long lines into stacked `<tspan x=… dy=…>` lines, or center short labels with `text-anchor="middle"` + `dominant-baseline="central"`.
5. Keep it portable: prefer plain SVG (`<rect>`, `<text>`, `<line>`, `<path>`). Use `<foreignObject>` only when you must (it requires the Playwright/Chromium rasterizer, not cairosvg).
6. amber is reserved for severity/escalation — don't use it decoratively.

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
