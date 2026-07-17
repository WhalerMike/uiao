#!/usr/bin/env bash
# Block accidental commits of files that should be gitignored but got
# force-added. Mirrors the pre-commit block-tracked-build-artifacts hook.
set -euo pipefail

# Deletions are always fine — only additions/modifications are gated.
staged="$(git diff --cached --name-only --diff-filter=d)"

if grep -E 'docs/_site/|docs/exports/.+\.(pptx|docx)$' <<<"$staged" >/dev/null; then
    echo "ERROR: staged a file that should be gitignored" >&2
    exit 1
fi

# ADR-093: a committed SVG is the source of truth for a figure; the sibling
# <name>.png (+ <name>.png.json sidecar) is a build artifact rendered by
# scripts/render_svg_images.py — in CI before every Quarto render, or
# locally while authoring. Block staging a PNG/sidecar whose sibling SVG is
# tracked or staged. Grandfathered exceptions (matched against the base
# path, extension stripped): scripts/svg-derived-png-allowlist.txt.
# CI enforces the same invariant tree-wide via
# scripts/check_no_tracked_derived_pngs.sh.
repo_root="$(git rev-parse --show-toplevel)"
allow_file="$repo_root/scripts/svg-derived-png-allowlist.txt"
allow_patterns="$(grep -Ev '^[[:space:]]*(#|$)' "$allow_file" 2>/dev/null || true)"

fail=0
while IFS= read -r f; do
    case "$f" in
        *.png)      base="${f%.png}" ;;
        *.png.json) base="${f%.png.json}" ;;
        *)          continue ;;
    esac
    svg="${base}.svg"
    if git ls-files --error-unmatch "$svg" >/dev/null 2>&1 || grep -qxF "$svg" <<<"$staged"; then
        if [ -n "$allow_patterns" ] && grep -Eq -f <(printf '%s\n' "$allow_patterns") <<<"$base"; then
            continue
        fi
        echo "ERROR: $f is derived from committed $svg (ADR-093) — do not commit it." >&2
        echo "       CI renders it before every Quarto build; locally run:" >&2
        echo "       python scripts/render_svg_images.py" >&2
        fail=1
    fi
done <<<"$staged"

exit $fail
