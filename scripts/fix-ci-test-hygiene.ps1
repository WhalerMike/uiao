#!/usr/bin/env pwsh
# fix-ci-test-hygiene.ps1
#
# Bundles three backlog items into one CI/test hygiene PR:
#
#   TST-001  Fix impl/.coveragerc — source/omit paths used old uiao_core
#            namespace (pre-ADR-031 rename); corrected to uiao/impl.
#
#   CI-010   Retire impl/.github/workflows/ci.yml — stale workflow checks
#            out the deleted WhalerMike/uiao-core repo; authoritative impl
#            pytest runs via .github/workflows/pytest.yml at repo root.
#
#   CI-001   Add .github/workflows/mypy.yml — mypy is declared in impl dev
#            deps but has never been wired into CI; this workflow runs on
#            every impl/**/*.py PR and push to main.
#
# Usage: pwsh scripts/fix-ci-test-hygiene.ps1

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (git rev-parse --show-toplevel)
Set-Location $RepoRoot

# Remove stale index.lock if present
$Lock = Join-Path $RepoRoot ".git/index.lock"
if (Test-Path $Lock) {
    Write-Host "Removing stale .git/index.lock ..."
    Remove-Item $Lock -Force
}

git checkout main
git pull origin main

$BranchName = "fix/ci-test-hygiene"
$branchExists = git branch --list $BranchName
if ($branchExists) {
    git branch -D $BranchName
}
git checkout -b $BranchName

# ------------------------------------------------------------------
# TST-001: fix impl/.coveragerc
# ------------------------------------------------------------------
$CoverageRc = @"
[run]
source = src/uiao/impl
omit =
    src/uiao/impl/generators/briefing.py
    src/uiao/impl/generators/rich_docx.py
    src/uiao/impl/generators/pptx.py
    src/uiao/impl/generators/sbom.py
    src/uiao/impl/generators/gemini_visuals.py
    src/uiao/impl/generators/plantuml.py
    src/uiao/impl/onboarding/wizard.py
    src/uiao/impl/onboarding/validator.py

[report]
exclude_lines =
    pragma: no cover
    if __name__ == .__main__.:
"@
Set-Content -Path "impl/.coveragerc" -Value $CoverageRc -NoNewline

# ------------------------------------------------------------------
# CI-010: delete stale impl/.github/workflows/ci.yml
# ------------------------------------------------------------------
git rm -f "impl/.github/workflows/ci.yml"

# ------------------------------------------------------------------
# CI-001: add .github/workflows/mypy.yml
# ------------------------------------------------------------------
$MypyYml = @"
name: Mypy

on:
  pull_request:
    paths:
      - 'impl/**/*.py'
      - 'impl/pyproject.toml'
      - '.github/workflows/mypy.yml'
  push:
    branches: [main]
    paths:
      - 'impl/**/*.py'
      - 'impl/pyproject.toml'

jobs:
  mypy:
    name: Type-check impl/ with mypy
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v6

      - name: Set up Python
        uses: actions/setup-python@v6
        with:
          python-version: '3.12'

      - name: Install impl package with dev extras
        run: pip install --quiet -e `"./impl[dev]`"

      - name: Run mypy
        working-directory: impl
        run: mypy src/uiao/impl --ignore-missing-imports
"@
Set-Content -Path ".github/workflows/mypy.yml" -Value $MypyYml -NoNewline

# ------------------------------------------------------------------
# Stage and commit
# ------------------------------------------------------------------
git add impl/.coveragerc
git add .github/workflows/mypy.yml

git commit -m "CI/test: coverage path fix, retire stale ci.yml, add mypy workflow

TST-001 impl/.coveragerc
  source and omit paths used the pre-ADR-031 namespace uiao_core.
  Updated every path to the current src/uiao/impl layout so that
  'coverage run -m pytest' reports against the correct tree.

CI-010 impl/.github/workflows/ci.yml (deleted)
  This workflow still checked out WhalerMike/uiao-core (the pre-split
  repo, now gone) as a sibling checkout and set UIAO_CANON_PATH to
  point there. The authoritative impl test workflow is
  .github/workflows/pytest.yml at the repo root; this in-folder file
  is a dead duplicate that would fail on every run.

CI-001 .github/workflows/mypy.yml (new)
  mypy is listed in impl/pyproject.toml [project.optional-dependencies]
  dev, but was never invoked in CI. The new workflow runs on every
  pull_request or push-to-main that touches impl/**/*.py or
  impl/pyproject.toml, matching the path-filter pattern already used
  by ruff.yml and pytest.yml."

git push --force-with-lease origin $BranchName

Write-Host ""
Write-Host "Done. Open PR at:"
Write-Host "  https://github.com/WhalerMike/uiao/pull/new/$BranchName"

git checkout main
