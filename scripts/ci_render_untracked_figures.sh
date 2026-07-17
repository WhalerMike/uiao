#!/usr/bin/env bash
# Render exactly the build-artifact figure set: every committed .svg under
# the image-pipeline scan roots (docs/, src/uiao/canon/) whose sibling
# .png is NOT tracked. Used by the quarto.yml render jobs (before every
# Quarto render) and the derived-binary-gate.yml render canary.
#
# Tracked sibling PNGs are the grandfathered exceptions from
# scripts/svg-derived-png-allowlist.txt — kept committed because their
# SVGs cannot go through cairosvg (foreignObject, cairosvg parse bugs) and
# CI does not install the Playwright fallback. Re-rendering those here
# would either fail the build or silently change published figures, so
# they are excluded: what ships for them is the committed PNG.
#
# render_svg_images.py exits nonzero if any figure fails, so a bad SVG
# breaks the build loudly instead of deploying broken figures.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT

comm -23 \
    <(git ls-files -- '*.svg' | grep -E '^(docs|src/uiao/canon)/' | sed 's/\.svg$//' | sort -u) \
    <(git ls-files -- '*.png' | sed 's/\.png$//' | sort -u) \
    | sed 's/$/.svg/' > "$tmp"

count="$(wc -l < "$tmp")"
echo "Rendering ${count} figure(s) whose PNG is an untracked build artifact"
if [ "$count" -eq 0 ]; then
    exit 0
fi
xargs -a "$tmp" -d '\n' python scripts/render_svg_images.py
