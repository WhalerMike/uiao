#!/usr/bin/env bash
# UIAO monorepo bootstrap
#
# Sets up a fresh checkout for development:
#   - Exports UIAO_WORKSPACE_ROOT for the current shell
#   - Installs impl/ as an editable package
#   - Installs dev tools (ruff, pre-commit, pytest)
#   - Runs the substrate walker to verify the tree is intact
#
# Idempotent — safe to re-run.

set -eu -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "==> UIAO bootstrap — repo root: $REPO_ROOT"

# 1. Environment ----------------------------------------------------------
export UIAO_WORKSPACE_ROOT="$REPO_ROOT"
echo "    UIAO_WORKSPACE_ROOT=$UIAO_WORKSPACE_ROOT"

# 2. Python package install (editable) ------------------------------------
if ! command -v python3 >/dev/null 2>&1; then
  echo "    ERROR: python3 not found; install Python >=3.10 first" >&2
  exit 1
fi

echo "==> Installing impl/ as editable package"
python3 -m pip install --quiet --upgrade pip
python3 -m pip install --quiet -e "$REPO_ROOT/impl" \
  || { echo "    WARN: impl editable install had warnings (OK if trestle deps are heavy)" >&2; }

# 3. Dev tools ------------------------------------------------------------
echo "==> Installing dev tools (ruff, pre-commit, pytest)"
python3 -m pip install --quiet ruff pre-commit pytest pyyaml jsonschema typer rich pydantic

# 4. Pre-commit hooks -----------------------------------------------------
if [ -f "$REPO_ROOT/.pre-commit-config.yaml" ]; then
  echo "==> Installing pre-commit hooks"
  (cd "$REPO_ROOT" && pre-commit install --install-hooks) \
    || echo "    WARN: pre-commit install failed; continuing" >&2
fi

# 5. Substrate walker -----------------------------------------------------
echo "==> Running substrate walker"
if PYTHONPATH="$REPO_ROOT/impl/src" python3 -c "
from uiao_impl.substrate.walker import walk_substrate
from pathlib import Path
r = walk_substrate(workspace_root=Path('$REPO_ROOT'))
print('    modules:   %d' % r.modules_checked)
print('    documents: %d' % r.documents_checked)
print('    findings:  %d' % len(r.findings))
import sys
sys.exit(0 if r.ok else 1)
"; then
  echo "==> Substrate OK — tree is intact"
else
  echo "==> Substrate findings present — inspect with 'uiao substrate walk'"
fi

# 6. Summary --------------------------------------------------------------
cat <<EOF

UIAO bootstrap complete.

Quick commands:
  uiao substrate walk              # full substrate report
  uiao substrate drift             # exit-code-only gate
  cd impl && pytest -q             # run tests
  cd impl && ruff check .          # lint
  (cd docs && quarto render)       # render docs site

Canon reference:
  core/canon/substrate-manifest.yaml      (UIAO_200)
  core/canon/workspace-contract.yaml      (UIAO_201)
  core/canon/document-registry.yaml

Rules loaded:
  impl/.claude/rules/canon-consumer.md    (no hardcoded canon paths)
  impl/.claude/rules/test-coverage.md     (every CLI command has a test)

See CONTRIBUTING.md for the full workflow.
EOF
