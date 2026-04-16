# =============================================================================
# stage-4-batch-5.1-workflow-reconciliation.ps1
# Phase D Stage 5, Batch 5.1 — reconcile uiao-core GH Actions workflows to the
#                              post-split repo layout.
# -----------------------------------------------------------------------------
# What this does (single atomic commit, no push):
#   1. Rename schemas/uiao-governance.schema.json -> schemas/metadata-schema.json
#      and update the $id field inside it to match.
#   2. Delete .github/workflows/appendix-sync.yml (appendices/ moved to uiao-docs).
#   3. Rewrite .github/workflows/metadata-validator.yml:
#        - drop playbooks/ and appendices/ path filters
#        - drop the two playbooks/appendices validation steps
#        - narrow the "Fail on blocking issues" condition
#   4. Rewrite .github/workflows/dashboard-export.yml:
#        - drop the "Run appendix audit (metrics collection)" step
#   5. Compile-gate the 4 canon tools (regression check from Batch 4.4).
#   6. Dry-run metadata_validator.py against canon/ with the renamed schema to
#      prove the rename is wired correctly end-to-end.
#   7. Stage ONLY the intended files. Commit. Do NOT push — user inspects first.
#
# Assumptions / prereqs:
#   - Batch 4.4 landed (tools/*.py compile cleanly).
#   - Working tree on uiao-core main is clean (or only CRLF noise we'll ignore).
#   - $env:PYTHONIOENCODING = 'utf-8' is set if you want clean Rich output.
# =============================================================================

$ErrorActionPreference = 'Stop'
$RepoRoot = 'C:\Users\whale'
$CoreDir  = Join-Path $RepoRoot 'uiao-core'

function Write-Step($msg) { Write-Host "`n>>> $msg" -ForegroundColor Cyan }
function Write-OK($msg)   { Write-Host "[OK]  $msg"  -ForegroundColor Green }
function Write-Fail($msg) { Write-Host "[FAIL] $msg" -ForegroundColor Red }

Push-Location $CoreDir
try {
    # --- 0. Preflight -------------------------------------------------------
    Write-Step 'Preflight — confirm repo, branch, and schema source file'
    $branch = git rev-parse --abbrev-ref HEAD
    if ($branch -ne 'main') { Write-Fail "not on main (on $branch)"; exit 1 }
    if (-not (Test-Path 'schemas\uiao-governance.schema.json')) {
        Write-Fail 'schemas\uiao-governance.schema.json not found — already renamed?'; exit 1
    }
    if (Test-Path 'schemas\metadata-schema.json') {
        Write-Fail 'schemas\metadata-schema.json already exists — aborting to avoid clobber'; exit 1
    }
    Write-OK "on main; source schema present; target slot free"

    # --- 1. Rename schema via git mv, update $id ---------------------------
    Write-Step 'Step 1 — git mv schema and rewrite $id'
    git mv schemas/uiao-governance.schema.json schemas/metadata-schema.json
    $schemaPath = 'schemas\metadata-schema.json'
    $raw = Get-Content $schemaPath -Raw
    $new = $raw -replace 'uiao-governance\.schema\.json', 'metadata-schema.json'
    # Write back with UTF-8 no-BOM to avoid accidental byte diffs
    [System.IO.File]::WriteAllText((Resolve-Path $schemaPath), $new, (New-Object System.Text.UTF8Encoding($false)))
    Write-OK 'schema renamed; $id updated'

    # --- 2. Delete dead appendix-sync.yml ----------------------------------
    Write-Step 'Step 2 — git rm .github/workflows/appendix-sync.yml'
    if (Test-Path '.github\workflows\appendix-sync.yml') {
        git rm .github/workflows/appendix-sync.yml | Out-Null
        Write-OK 'appendix-sync.yml removed (belongs to uiao-docs now)'
    } else {
        Write-Host '  already absent — skipping' -ForegroundColor Yellow
    }

    # --- 3. Rewrite metadata-validator.yml ---------------------------------
    Write-Step 'Step 3 — rewrite metadata-validator.yml (canon-only)'
    $mvYaml = @'
name: Metadata Validator
on:
  pull_request:
    paths:
      - 'canon/**'
      - 'schemas/**'
  push:
    branches: [main]
    paths:
      - 'canon/**'
      - 'schemas/**'
  workflow_dispatch:

permissions:
  contents: read
  pull-requests: write

jobs:
  validate-metadata:
    name: Validate Artifact Metadata
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install pyyaml jsonschema

      - name: Run metadata validator (canon)
        id: validate
        run: |
          python tools/metadata_validator.py \
            --path canon/ \
            --schema schemas/metadata-schema.json \
            --output reports/validation-report.json \
            --ci
        continue-on-error: true

      - name: Upload validation reports
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: validation-reports
          path: reports/
          retention-days: 30

      - name: Comment on PR
        if: github.event_name == 'pull_request' && always()
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            let report = '';
            if (fs.existsSync('reports/validation-report.json')) {
              const data = JSON.parse(fs.readFileSync('reports/validation-report.json', 'utf8'));
              report += `### ${data.scope}\n`;
              report += `- Files scanned: ${data.files_scanned}\n`;
              report += `- BLOCKING: ${data.blocking} | WARNING: ${data.warning} | INFO: ${data.info}\n\n`;
            }
            await github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: context.issue.number,
              body: '## Metadata Validation Report\n\n' + report
            });

      - name: Fail on blocking issues
        if: steps.validate.outcome == 'failure'
        run: |
          echo "Metadata validation found BLOCKING issues."
          exit 1
'@
    Set-Content -Path '.github\workflows\metadata-validator.yml' -Value $mvYaml -Encoding UTF8 -NoNewline
    Write-OK 'metadata-validator.yml rewritten'

    # --- 4. Rewrite dashboard-export.yml (drop appendix step) --------------
    Write-Step 'Step 4 — rewrite dashboard-export.yml (drop appendix metrics)'
    $deYaml = @'
name: Dashboard Export
on:
  push:
    branches: [main]
  schedule:
    - cron: '0 7 * * *'
  workflow_dispatch:

permissions:
  contents: write
  pull-requests: read

jobs:
  dashboard-export:
    name: Export Governance Dashboard
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 30

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install pyyaml jsonschema

      - name: Create export directory
        run: mkdir -p dashboard/exports

      - name: Run metadata validation (metrics collection)
        run: |
          python tools/metadata_validator.py \
            --path canon/ \
            --schema schemas/metadata-schema.json \
            --output reports/validation-metrics.json \
            --ci --metrics-only
        continue-on-error: true

      - name: Run drift scan (metrics collection)
        run: |
          python tools/drift_detector.py \
            --path . \
            --mode full \
            --schema schemas/metadata-schema.json \
            --output reports/drift-metrics.json \
            --ci --metrics-only
        continue-on-error: true

      - name: Export dashboard data
        id: export
        run: |
          python tools/dashboard_exporter.py \
            --schema schemas/dashboard-schema.json \
            --export json \
            --output dashboard/exports/ \
            --trends 30 \
            --metrics-dir reports/
        continue-on-error: true

      - name: Validate export against schema
        run: |
          python tools/dashboard_exporter.py \
            --schema schemas/dashboard-schema.json \
            --validate \
            --input dashboard/exports/

      - name: Upload dashboard exports
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: dashboard-exports
          path: dashboard/exports/
          retention-days: 90

      - name: Commit dashboard export
        if: github.event_name != 'pull_request' && steps.export.outcome == 'success'
        run: |
          git config user.name "UIAO Governance Bot"
          git config user.email "governance-bot@uiao.local"
          git add dashboard/exports/
          git diff --staged --quiet || git commit -m "[UIAO-CORE] UPDATE: Dashboard export"
          git push
'@
    Set-Content -Path '.github\workflows\dashboard-export.yml' -Value $deYaml -Encoding UTF8 -NoNewline
    Write-OK 'dashboard-export.yml rewritten'

    # --- 5. Regression: canon tools still compile --------------------------
    Write-Step 'Step 5 — py_compile gate on canon tools (regression from 4.4)'
    $tools = @('metadata_validator.py','drift_detector.py','dashboard_exporter.py','appendix_indexer.py','sync_canon.py')
    $allOk = $true
    foreach ($t in $tools) {
        $p = Join-Path 'tools' $t
        if (-not (Test-Path $p)) { continue }
        python -m py_compile $p 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) { Write-OK "$t compiles" }
        else { Write-Fail "$t failed compile"; $allOk = $false }
    }
    if (-not $allOk) { Write-Fail 'canon tool regression — bailing'; exit 1 }

    # --- 6. End-to-end: metadata_validator against canon/ w/ renamed schema
    Write-Step 'Step 6 — dry-run metadata_validator.py against canon/ with renamed schema'
    $null = New-Item -ItemType Directory -Force -Path 'reports' | Out-Null
    python tools/metadata_validator.py --path canon/ --schema schemas/metadata-schema.json --output reports/_5-1-dryrun.json --ci 2>&1 | Out-Host
    $dryExit = $LASTEXITCODE
    # exit 0 = no blockers; exit 1 = blockers found (still proves the pipeline runs)
    if ($dryExit -in 0,1) { Write-OK "validator ran end-to-end (exit $dryExit)" }
    else { Write-Fail "validator crashed unexpectedly (exit $dryExit)"; exit 1 }
    # throw away the dry-run report so it doesn't land in the commit
    if (Test-Path 'reports\_5-1-dryrun.json') { Remove-Item 'reports\_5-1-dryrun.json' -Force }

    # --- 7. Stage explicit set of files, commit, STOP before push ---------
    Write-Step 'Step 7 — stage + commit (no push)'
    # git mv and git rm already staged their changes. Only the two YAML rewrites
    # and the schema $id edit need explicit re-staging.
    git add .github/workflows/metadata-validator.yml
    git add .github/workflows/dashboard-export.yml
    git add schemas/metadata-schema.json

    Write-Host ''
    Write-Host '--- staged summary ---' -ForegroundColor Cyan
    git status --short

    $msgFile = Join-Path $env:TEMP 'uiao-core-5-1-msg.txt'
    @(
        '[UIAO-CORE] ENFORCE: workflow reconciliation — post-split cleanup',
        '',
        '- rename schemas/uiao-governance.schema.json -> metadata-schema.json',
        '  (aligns with tool CLIs and workflow YAMLs; $id updated in place)',
        '- delete .github/workflows/appendix-sync.yml',
        '  (appendices/ lives in uiao-docs; sync workflow belongs there)',
        '- metadata-validator.yml: drop playbooks/ and appendices/ steps,',
        '  narrow path filters and fail condition to canon only',
        '- dashboard-export.yml: drop appendix metrics collection step',
        '',
        'Tools compile (regression gate passed). End-to-end dry run of',
        'metadata_validator against canon/ with renamed schema succeeded.'
    ) | Set-Content -Path $msgFile -Encoding UTF8

    git commit -F $msgFile
    Remove-Item $msgFile -Force

    Write-Host ''
    Write-OK 'Commit created locally. Review with: git show --stat HEAD'
    Write-Host 'Next step (manual):' -ForegroundColor Yellow
    Write-Host '  git -C C:\Users\whale\uiao-core push origin main' -ForegroundColor Yellow
    Write-Host 'Then rerun the Batch 4.3 smoke test to confirm nothing regressed.' -ForegroundColor Yellow
}
finally {
    Pop-Location
}
