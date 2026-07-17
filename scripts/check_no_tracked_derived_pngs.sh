#!/usr/bin/env bash
# Closed-world gate for ADR-093 figure sources.
#
# The committed SVG is the source of truth for a figure; the sibling
# <name>.png (+ <name>.png.json sidecar) is a build artifact rendered by
# scripts/render_svg_images.py — in CI before every Quarto render, or
# locally while authoring. This script asserts the repo-wide invariant:
#
#   no tracked *.png / *.png.json may have a tracked sibling *.svg,
#
# except for the grandfathered entries in
# scripts/svg-derived-png-allowlist.txt. Run by
# .github/workflows/derived-binary-gate.yml; safe to run locally from
# anywhere inside the repo.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

git ls-files -- '*.png' '*.png.json' | sed -E 's/\.png(\.json)?$//' | sort -u > "$tmp/png_bases"
git ls-files -- '*.svg' | sed 's/\.svg$//' | sort -u > "$tmp/svg_bases"
comm -12 "$tmp/png_bases" "$tmp/svg_bases" > "$tmp/derived_bases"

grep -Ev '^[[:space:]]*(#|$)' scripts/svg-derived-png-allowlist.txt > "$tmp/allow" || true

violations="$(grep -Evf "$tmp/allow" "$tmp/derived_bases" || true)"

if [ -n "$violations" ]; then
    echo "ERROR: tracked PNG(s) whose sibling SVG is also tracked (ADR-093):" >&2
    echo "$violations" | sed 's/$/.png/' >&2
    echo "" >&2
    echo "The SVG is the committed source; the PNG is a build artifact." >&2
    echo "Untrack the PNG (+ .png.json sidecar): git rm --cached <file>" >&2
    echo "CI and local authoring regenerate it: python scripts/render_svg_images.py" >&2
    exit 1
fi

echo "OK: no tracked SVG-derived PNGs outside the allowlist ($(wc -l < "$tmp/derived_bases") allowlisted base(s) checked)."
