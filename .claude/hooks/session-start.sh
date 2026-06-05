#!/usr/bin/env bash
# UIAO SessionStart hook — prepare a fresh checkout for Claude Code on the web.
#
# Builds an isolated project virtualenv (.venv) and installs the package
# editable with the `dev` and `visuals` extras, so the three things a web
# session typically needs all work with no manual setup:
#   - pytest        (run the test suite under tests/)
#   - ruff / mypy   (lint + format gates, see `make lint`)
#   - cairosvg      (the SVG -> PNG rasterizer used by
#                    scripts/render_svg_images.py per ADR-093)
#
# Why a venv: the base image's Python is distro-managed, so installing the
# project's pinned runtime deps directly fails (pip cannot uninstall
# debian-owned packages like cryptography). A clean .venv sidesteps that and
# matches how the repo already ignores .venv/ and ships a uv.lock.
#
# Notes:
#   - Web-sessions only (guarded on $CLAUDE_CODE_REMOTE); local/devcontainer
#     setups keep using scripts/bootstrap.sh / the devcontainer postCreate.
#   - Synchronous (no async marker): the session waits until deps are ready,
#     so Claude never races ahead of the install.
#   - Idempotent: re-running reuses the existing .venv; container state is
#     cached after the hook completes.
set -euo pipefail

# Only run in the remote (Claude Code on the web) environment.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

REPO_ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
cd "$REPO_ROOT"
VENV="$REPO_ROOT/.venv"

# Create the venv with uv (fast, the repo's own tool); fall back to stdlib venv.
if command -v uv >/dev/null 2>&1; then
  uv venv "$VENV" >/dev/null
  uv pip install --python "$VENV/bin/python" --quiet -e ".[api,dev,visuals]"
else
  python3 -m venv "$VENV"
  "$VENV/bin/python" -m pip install --quiet --upgrade pip 2>/dev/null || true
  "$VENV/bin/python" -m pip install --quiet -e ".[api,dev,visuals]"
fi

# Make the venv and the workspace root active for the rest of the session.
if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  {
    echo "export VIRTUAL_ENV=\"$VENV\""
    echo "export PATH=\"$VENV/bin:\$PATH\""
    echo "export UIAO_WORKSPACE_ROOT=\"$REPO_ROOT\""
  } >> "$CLAUDE_ENV_FILE"
fi

echo "UIAO session-start: .venv ready with uiao (editable) + [api,dev,visuals] — pytest, ruff, and cairosvg are on PATH."
