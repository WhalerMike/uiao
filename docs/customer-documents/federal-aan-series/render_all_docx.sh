#!/usr/bin/env bash
# Render every AAN book .qmd to .docx with AAN house-style callouts.
#
# Uses the bundled Pandoc (pypandoc-binary), the AAN reference doc
# (aan-reference.docx — carries the callout/banner paragraph styles) and the
# aan-callouts.lua filter (maps each callout/banner div class to its style).
# This is the FAST batch path, not a fallback: `quarto render <book>.qmd --to docx`
# also works locally and produces the same docx (since PR #1229/#1230 the front
# matter and this CLI agree, and the `.aan-*` classes keep both renderers on
# aan-callouts.lua). Pandoc is kept because it is ~6x faster across the ~56-book
# batch. See BUILD-DERIVATIVES.md §2.
#
# Usage:
#   ./render_all_docx.sh [OUTDIR]
# With no OUTDIR, renders each Vol_*_Book_*.docx next to its .qmd (in place).
# With OUTDIR, writes flat into OUTDIR (used by the zip rebuild, which then
# distributes into per-volume folders).
set -uo pipefail
cd "$(dirname "$0")"

# Prefer the bundled pypandoc binary (pinned, and what CI has); fall back to a
# pandoc on PATH so a local Windows/macOS checkout can render. The hardcoded
# Linux path does not exist off-CI, and every render fails without the fallback.
PANDOC="${PANDOC:-}"
if [ -z "$PANDOC" ]; then
  _bundled="/usr/local/lib/python3.11/dist-packages/pypandoc/files/pandoc"
  if [ -x "$_bundled" ]; then
    PANDOC="$_bundled"
  elif command -v pandoc >/dev/null 2>&1; then
    PANDOC="$(command -v pandoc)"
  else
    echo "FATAL: no pandoc found (set PANDOC=/path/to/pandoc)" >&2; exit 1
  fi
fi
REF="aan-reference.docx"
LUA="aan-callouts.lua"
OUTDIR="${1:-.}"
mkdir -p "$OUTDIR"

ok=0; fail=0
for qmd in Vol_*_Book_*.qmd; do
  base="${qmd%.qmd}"
  out="$OUTDIR/$base.docx"
  if "$PANDOC" "$qmd" -f markdown -o "$out" \
       --reference-doc="$REF" --lua-filter="$LUA" --resource-path=. 2>/tmp/pandoc-err.txt; then
    ok=$((ok+1))
    printf '  ok   %s\n' "$base"
  else
    fail=$((fail+1))
    printf '  FAIL %s\n' "$base"
    sed 's/^/       /' /tmp/pandoc-err.txt
  fi
done
printf 'rendered %d ok, %d failed\n' "$ok" "$fail"
[ "$fail" -eq 0 ]
