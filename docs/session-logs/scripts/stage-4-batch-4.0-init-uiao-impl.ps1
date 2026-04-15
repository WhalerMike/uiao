# =============================================================================
# stage-4-batch-4.0-init-uiao-impl.ps1
# Phase D Stage 4, Batch 4.0 — Initialize WhalerMike/uiao-impl
# -----------------------------------------------------------------------------
# Prereqs:
#   - WhalerMike/uiao-impl already created on GitHub (done — empty repo).
#   - gh auth status is clean; git is configured for WhalerMike.
#   - Repo root for sibling clones: C:\Users\whale\
# What this does:
#   - Clones uiao-impl locally.
#   - Seeds pyproject.toml, README.md, CLAUDE.md, .gitignore, LICENSE,
#     src/uiao_impl/__init__.py, tests/__init__.py, .github/workflows/ci.yml.
#   - Commits a single chore(init) commit on main.
#   - STOPS before pushing — user must review and push manually.
# Idempotent: if files already exist, Set-Content overwrites them (no-op diff).
# =============================================================================

$ErrorActionPreference = 'Stop'
$RepoRoot              = 'C:\Users\whale'
$ImplDir               = Join-Path $RepoRoot 'uiao-impl'
$RepoUrl               = 'https://github.com/WhalerMike/uiao-impl.git'

function Write-Step($msg) { Write-Host "`n>>> $msg" -ForegroundColor Cyan }
function Confirm-Or-Exit($prompt) {
    $ans = Read-Host "$prompt [y/N]"
    if ($ans -ne 'y' -and $ans -ne 'Y') { Write-Host 'Aborted.' -ForegroundColor Yellow; exit 1 }
}

# --- 1. Clone or locate --------------------------------------------------------
Write-Step 'Locating uiao-impl clone'
if (-not (Test-Path $ImplDir)) {
    Write-Host "uiao-impl not found at $ImplDir — cloning..."
    Push-Location $RepoRoot
    git clone $RepoUrl
    Pop-Location
} else {
    Write-Host "uiao-impl already cloned at $ImplDir"
}
Set-Location $ImplDir

# Sanity: is it the right repo?
$remoteUrl = git config --get remote.origin.url
if ($remoteUrl -notmatch 'uiao-impl') {
    Write-Host "ERROR: $ImplDir remote is $remoteUrl — aborting." -ForegroundColor Red
    exit 1
}

# --- 2. Seed top-level files ---------------------------------------------------
Write-Step 'Seeding top-level files'

# pyproject.toml — minimal; Batch 4.1 overwrites this with the full carried-over version
@'
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "uiao-impl"
version = "0.1.0"
description = "UIAO implementation — Python library, CLI, generators, adapters, and tests. Consumes canon from WhalerMike/uiao-core."
readme = "README.md"
requires-python = ">=3.11"
license = { text = "Apache-2.0" }
authors = [{ name = "Michael Stratton", email = "michael.francis.stratton@gmail.com" }]
dependencies = []

[project.scripts]
uiao = "uiao_impl.cli.app:app"

[tool.setuptools.packages.find]
where = ["src"]
'@ | Set-Content 'pyproject.toml' -Encoding UTF8

# README.md
@'
# uiao-impl

Python implementation for the UIAO governance ecosystem: library, CLI, generators, adapters, and the pytest suite.

This repository holds **application code only**. Canonical governance artifacts (YAMLs, schemas, rules, playbooks) live in [`WhalerMike/uiao-core`](https://github.com/WhalerMike/uiao-core). Documentation and article series live in [`WhalerMike/uiao-docs`](https://github.com/WhalerMike/uiao-docs).

## Install

```bash
pip install git+https://github.com/WhalerMike/uiao-impl.git@v0.1.0
```

## CLI

```bash
uiao --help
```

## Development

```bash
git clone https://github.com/WhalerMike/uiao-impl.git
cd uiao-impl
pip install -e .[dev]
pytest
```

## Canon dependency

All generators and validators need a canon path at runtime:

```bash
uiao validate --canon-path ../uiao-core/canon
uiao generate-ssp --canon-path ../uiao-core/canon --out out/ssp.docx
```

## License

Apache 2.0
'@ | Set-Content 'README.md' -Encoding UTF8

# CLAUDE.md
@'
# CLAUDE.md — UIAO-Impl Repository

> Python application code for the UIAO governance ecosystem.

## Repository Identity
- **Name:** uiao-impl
- **Purpose:** Python library, CLI, generators, adapters, and pytest suite.
- **Canon Authority:** CONSUMER of `uiao-core` canon. Does NOT define canonical artifacts.
- **Cloud Boundary:** GCC-Moderate (Microsoft 365 SaaS). Exception: Amazon Connect in Commercial Cloud.

## Operating Principles
1. No-Hallucination Protocol available on demand.
2. All runtime canon reads go through `--canon-path` (no hard-coded `../uiao-core` paths).
3. Every CLI command is covered by pytest.
4. Breaking changes bump the minor version until `v1.0.0`.

## Directory Convention
```
uiao-impl/
├── CLAUDE.md
├── pyproject.toml
├── README.md
├── src/uiao_impl/        # Python package
├── tests/                # pytest suite
├── scripts/              # one-off generators, assemblers
├── adapters/             # cloud/database/government/scuba adapter plugins
└── .github/workflows/    # CI: pytest + wheel build
```

## Commit Convention
```
[UIAO-IMPL] <verb>: <module> — <short description>
```
Verbs: `CREATE`, `UPDATE`, `FIX`, `REFACTOR`, `TEST`, `DEPRECATE`.
'@ | Set-Content 'CLAUDE.md' -Encoding UTF8

# .gitignore — Python defaults + what we learned the hard way
@'
# Python
__pycache__/
*.py[cod]
*.egg-info/
build/
dist/
.eggs/
*.egg

# venv
.venv/
venv/
env/

# pytest / coverage
.pytest_cache/
.coverage
.coverage.*
htmlcov/

# IDE
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db

# Generated outputs (should never be committed)
out/
dryrun-output/
scuba-real-run/
artifacts/
reports/
'@ | Set-Content '.gitignore' -Encoding UTF8

# LICENSE — Apache 2.0 (match uiao-core)
Copy-Item -Path '..\uiao-core\LICENSE' -Destination '.\LICENSE' -Force

# src/uiao_impl/__init__.py placeholder — real contents arrive in Batch 4.1
New-Item -ItemType Directory -Force -Path 'src\uiao_impl' | Out-Null
@'
"""uiao_impl — Python implementation for UIAO governance."""

__version__ = "0.1.0"
'@ | Set-Content 'src\uiao_impl\__init__.py' -Encoding UTF8

# tests/__init__.py placeholder
New-Item -ItemType Directory -Force -Path 'tests' | Out-Null
@'
"""uiao_impl test suite."""
'@ | Set-Content 'tests\__init__.py' -Encoding UTF8

# .github/workflows/ci.yml — baseline pytest
New-Item -ItemType Directory -Force -Path '.github\workflows' | Out-Null
@'
name: CI
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - name: Install
        run: |
          python -m pip install --upgrade pip
          pip install -e .[dev] || pip install -e .
          pip install pytest
      - name: Run tests
        run: pytest -q
'@ | Set-Content '.github\workflows\ci.yml' -Encoding UTF8

# --- 3. Review + commit --------------------------------------------------------
Write-Step 'git status preview'
git status --short

Confirm-Or-Exit 'Stage and commit the initial scaffolding?'

git add pyproject.toml README.md CLAUDE.md .gitignore LICENSE `
        src/uiao_impl/__init__.py tests/__init__.py .github/workflows/ci.yml

git commit -m "[UIAO-IMPL] CREATE: initial scaffolding — pyproject, README, CLAUDE, CI"

Write-Step 'Batch 4.0 complete'
Write-Host 'Commit created locally on main. Review with: git log --oneline -1' -ForegroundColor Green
Write-Host 'When satisfied: git push -u origin main'                            -ForegroundColor Green
Write-Host 'Then proceed to Batch 4.1 (populate + rename).'                     -ForegroundColor Green
