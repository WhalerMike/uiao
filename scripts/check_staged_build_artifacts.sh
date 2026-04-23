#!/usr/bin/env bash
# Block accidental commits of files that should be gitignored but got
# force-added. Mirrors the pre-commit block-tracked-build-artifacts hook.
set -euo pipefail

if git diff --cached --name-only | grep -E 'docs/_site/|docs/exports/.+\.(pptx|docx)$' >/dev/null; then
    echo "ERROR: staged a file that should be gitignored" >&2
    exit 1
fi
exit 0
