# UIAO GitHub Import Guide
# GCC Boundary Problem + Solution — Complete File Set
# Repository: WhalerMike/uiao | Branch: main
# ============================================================
# Commit convention (AGENTS.md):
#   [UIAO-CORE] for src/uiao/canon/ changes
#   [UIAO-IMPL] for impl/ changes
#   [UIAO-DOCS] for docs/ changes
# ============================================================

## RECOMMENDED COMMIT SEQUENCE
## (split into 4 PRs for clean governance gates)

# ---------------------------------------------------------------
# PR 1: Canon — ADR and Gap Registry (governance gate first)
# ---------------------------------------------------------------
# Commit: [UIAO-CORE] add: ADR-030 — gcc-boundary-drift-class

src/uiao/canon/adr/adr-033-gcc-boundary-drift-class.md
src/uiao/canon/gcc-boundary-gap-registry.yaml

# Requires: 2 reviewer approvals, governance-steward + security-steward
# CI gates: schema-validation, metadata-validator, substrate-drift

# ---------------------------------------------------------------
# PR 2: Implementation — probe adapter and telemetry
# ---------------------------------------------------------------
# Commit: [UIAO-IMPL] add: gcc-boundary-probe-v1 adapter

src/uiao/adapters/modernization/gcc_boundary_probe/__init__.py
src/uiao/adapters/modernization/gcc_boundary_probe/probe.py
src/uiao/adapters/modernization/gcc_boundary_probe/telemetry.py
src/uiao/adapters/modernization/gcc_boundary_probe/adapter-manifest.json
src/uiao/api/routes/boundary.py

# Also update:
# src/uiao/api/app.py — add boundary router include
# src/uiao/canon/modernization-registry.yaml — add adapter entry
# pyproject.toml (repo root) — add httpx if not already present

# Requires: 2 approvals, identity-engineer
# CI gates: pytest, ruff, schema-validation

# ---------------------------------------------------------------
# PR 3: Documentation — drift standard amendment
# ---------------------------------------------------------------
# Commit: [UIAO-DOCS] add: drift-detection boundary amendment

docs/docs/drift-detection-boundary-amendment.md

# Requires: 2 approvals, governance-steward
# CI gates: quarto, link-check

# ---------------------------------------------------------------
# PR 4: Documentation — problem and solution docs
# ---------------------------------------------------------------
# Commit: [UIAO-DOCS] add: gcc-boundary problem statement and solution

docs/docs/gcc-boundary-problem-statement.md
docs/docs/gcc-boundary-solution-architecture.md

# Requires: 2 approvals, governance-steward
# CI gates: quarto, link-check

# ---------------------------------------------------------------
# FULL DIRECTORY MAP
# ---------------------------------------------------------------

uiao/
├── src/uiao/canon/
│   ├── adr/
│   │   └── adr-030-gcc-boundary-drift-class.md      [NEW — PR 1]
│   └── gcc-boundary-gap-registry.yaml               [NEW — PR 1]
│
├── src/uiao/
│   ├── adapters/modernization/
│   │   ├── active-directory/                        [FROM PREVIOUS SESSION]
│   │   │   ├── __init__.py
│   │   │   ├── survey.py
│   │   │   └── orgpath.py
│   │   └── gcc-boundary-probe/                      [NEW — PR 2]
│   │       ├── __init__.py
│   │       ├── probe.py
│   │       ├── telemetry.py
│   │       └── adapter-manifest.json
│   └── api/
│       └── routes/
│           └── boundary.py                          [NEW — PR 2]
│
├── deploy/windows-server/                           [FROM PREVIOUS SESSION]
│   ├── web.config
│   ├── run.py
│   └── requirements-windows.txt
│
├── scripts/
│   ├── ad-survey/
│   │   └── Invoke-ADSurvey.ps1                     [FROM PREVIOUS SESSION]
│   └── deploy/
│       ├── Install-UIAOServer.ps1                   [FROM PREVIOUS SESSION]
│       ├── Register-ServiceAccount.ps1              [FROM PREVIOUS SESSION]
│       └── Register-UIAOAPI.ps1                     [FROM PREVIOUS SESSION]
│
└── docs/docs/
    ├── drift-detection-boundary-amendment.md        [NEW — PR 3]
    ├── gcc-boundary-problem-statement.md            [NEW — PR 4]
    └── gcc-boundary-solution-architecture.md        [NEW — PR 4]

# ---------------------------------------------------------------
# UPDATES TO EXISTING FILES
# ---------------------------------------------------------------

# src/uiao/api/app.py
# Add after existing router includes:
#   from .routes.boundary import router as boundary_router
#   app.include_router(boundary_router, prefix="/api/v1/boundary", tags=["GCC Boundary"])

# src/uiao/canon/modernization-registry.yaml
# Append the gcc-boundary-probe entry from adapter-manifest.json

# pyproject.toml (repo root)
# Under [project].dependencies, confirm or add:
#   "httpx>=0.27",
#   "pyyaml>=6.0",

# docs/docs/16_DriftDetectionStandard.qmd
# Insert DRIFT-BOUNDARY section from drift-detection-boundary-amendment.md

# ---------------------------------------------------------------
# VALIDATION BEFORE MERGING PR 1
# ---------------------------------------------------------------
# Run locally:
#   uiao substrate walk
#   (must show zero P1 findings before adding new canon)
#
# After PR 1 merges, run probe:
#   POST /api/v1/boundary/run
#   Review gap registry output
#   Submit updated gcc-boundary-gap-registry.yaml as follow-up PR
#   with actual probe results (replaces draft values)

# ---------------------------------------------------------------
# ATO ACTIONS (parallel to GitHub work)
# ---------------------------------------------------------------
# 1. ISSO reviews SSP against gap registry
# 2. AO reviews 3 unmitigated P1 gaps:
#    - GAP-INT-008: Device Health Attestation
#    - GAP-ARC-004: Defender for Servers telemetry
#    - GAP-INT-006: Expedited updates (compensating control exists)
# 3. Risk acceptance memos drafted for unmitigated gaps
# 4. SSP Section 13 updated with compensating control language
# 5. Gap registry + probe reports added to evidence package
