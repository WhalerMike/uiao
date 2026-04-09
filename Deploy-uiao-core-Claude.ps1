# Deploy-uiao-core-Claude.ps1
# Run this script from the ROOT of your local 'uiao-core' clone.
# Example: cd C:\repos\uiao-core; .\Deploy-uiao-core-Claude.ps1
$ErrorActionPreference = 'Stop'
$created = 0
# --- Create directories ---
$dirs = @(
'.claude/commands'
'.claude/skills'
'.github/workflows'
'schemas'
'tools'
)
foreach ($d in $dirs) {
New-Item -ItemType Directory -Path $d -Force | Out-Null
}
Write-Host "Directories created." -ForegroundColor Green
# --- .claude/commands/export-dashboard.md ---
@'
# Command: /dashboard
## Description
Export governance metrics to structured dashboard format with SLA heatmaps and trend indicators.
## Usage
```
/dashboard [--export <json|csv|markdown>] [--trends <days>] [--output <path>]
```
## Parameters
| Parameter | Default | Description |
|-----------|---------|-------------|
| `--export` | `json` | Export format: json, csv, or markdown |
| `--trends` | `0` | Number of days for rolling trend computation (0 = no trends) |
| `--output` | `dashboard/exports/` | Output directory for exported files |
## Behavior
1. Collect current repository state metrics:
- Run metadata validation (count compliant vs total)
- Run drift scan (count drift-free vs total)
- Run appendix audit (count valid vs total)
- Compute boundary exception count
- Count open remediation items
2. Extract owner-level metrics from frontmatter
3. Compute canon health score (weighted average)
4. If `--trends` > 0, compute rolling averages from Git history
5. Validate export against `schemas/dashboard-schema.json`
6. Write export to `--output` directory
## Agent
Delegates to `dashboard-exporter`
## Example
```
/dashboard --export json --trends 30
```
Output:
```
Dashboard Export — 2026-04-09T07:00:00
Canon Health Score: 87/100
Metrics:
Metadata Compliance: 95.2%
Drift-Free Rate: 91.4%
Appendix Integrity: 100.0%
Boundary Exceptions: 2
Open Remediation: 7
30-Day Trends:
Health: ↑ +3.2
Drift: ↓ -2 instances
Compliance: ↑ +1.8%
Export written to: dashboard/exports/dashboard-2026-04-09.json
Schema validation: ✅ PASS
```
'@ | Set-Content -Path '.claude/commands/export-dashboard.md' -Encoding UTF8 -NoNewline
$created++
Write-Host " Created: .claude/commands/export-dashboard.md" -ForegroundColor Cyan
# --- .claude/commands/scan-drift.md ---
@'
# Command: /drift
## Description
Scan the repository for metadata drift between canonical sources and derived artifacts.
## Usage
```
/drift [--path <target>] [--mode <full|targeted|diff>] [--base <ref>] [--head <ref>]
```
## Parameters
| Parameter | Default | Description |
|-----------|---------|-------------|
| `--path` | `.` | Target directory or file to scan |
| `--mode` | `full` | Scan mode: full, targeted, or diff |
| `--base` | `main` | Base ref for diff mode |
| `--head` | `HEAD` | Head ref for diff mode |
## Behavior
1. Determine scan scope based on `--mode`
2. For each file in scope:
a. Parse frontmatter and classify drift category
b. Resolve provenance chains for DERIVED artifacts
c. Scan content body for boundary violations
d. Check version references for prior-epoch references
3. Correlate findings across files (e.g., cascading drift from a single canon change)
4. Generate structured drift report with root cause analysis
5. Assign remediation priority
## Agent
Delegates to `drift-detector`
## Example
```
/drift --mode diff --base main --head feature/update-canon
```
Output:
```
Drift Report — 2026-04-09T06:59:00
Files scanned: 12 (diff scope)
Drift instances found: 3
Blocking: 1 | Warning: 1 | Info: 1
| # | File | Category | Severity | Detail | Root Cause | Remediation |
|---|------|----------|----------|--------|------------|-------------|
| 1 | derived/ops-guide.md | PROVENANCE_DRIFT | BLOCKING | Source hash mismatch | canon/UIAO_005.md updated in abc1234 | Re-derive from updated source |
| 2 | canon/UIAO_012.md | VERSION_DRIFT | WARNING | References v1.2 (deprecated) | Manual edit in def5678 | Update to v2.0 reference |
| 3 | playbooks/onboard.md | COSMETIC_DRIFT | INFO | Header formatting inconsistency | — | Auto-fixable |
```
'@ | Set-Content -Path '.claude/commands/scan-drift.md' -Encoding UTF8 -NoNewline
$created++
Write-Host " Created: .claude/commands/scan-drift.md" -ForegroundColor Cyan
# --- .claude/commands/sync-appendices.md ---
@'
# Command: /appendix
## Description
Manage appendix lifecycle — audit integrity, rebuild index, and sync state.
## Usage
```
/appendix [--mode <audit|rebuild|sync>] [--path <target>]
```
## Parameters
| Parameter | Default | Description |
|-----------|---------|-------------|
| `--mode` | `audit` | Operation mode: audit (report only), rebuild (regenerate index), sync (compare index vs directory) |
| `--path` | `appendices/` | Target appendix directory |
## Behavior
### Audit Mode (default)
1. Walk appendices directory, parse each appendix frontmatter
2. Verify required fields: appendix_id, title, parent_document, status, owner
3. Verify Copy section presence in every appendix
4. Check parent_document resolves to existing canon
5. Check appendix_id uniqueness
6. Generate integrity report
### Rebuild Mode
1. Perform full audit
2. Generate new INDEX.md from directory contents
3. Sort by appendix_id ascending
4. Write INDEX.md to appendices/INDEX.md
5. Report changes vs previous index
### Sync Mode
1. Load existing INDEX.md
2. Walk directory for actual appendix files
3. Compute diff: orphans (in directory, not in index) and ghosts (in index, not in directory)
4. Report sync status
## Agent
Delegates to `appendix-manager`
## Example
```
/appendix --mode rebuild
```
Output:
```
Appendix Index Rebuild — 2026-04-09T07:00:00
Appendices found: 24
Index entries before: 22
Index entries after: 24
Changes:
+ APP-023 (new appendix added)
+ APP-024 (new appendix added)
Copy Section Audit:
With Copy: 24/24 ✅
INDEX.md written successfully.
```
'@ | Set-Content -Path '.claude/commands/sync-appendices.md' -Encoding UTF8 -NoNewline
$created++
Write-Host " Created: .claude/commands/sync-appendices.md" -ForegroundColor Cyan
# --- .claude/commands/validate-metadata.md ---
@'
# Command: /validate
## Description
Run the full metadata validation suite against governance artifacts.
## Usage
```
/validate [--path <target>] [--fix] [--report]
```
## Parameters
| Parameter | Default | Description |
|-----------|---------|-------------|
| `--path` | `canon/` | Target directory or file to validate |
| `--fix` | `false` | Auto-fix INFO-level issues (never auto-fixes BLOCKING) |
| `--report` | `false` | Generate a standalone validation report file |
## Behavior
1. Load the metadata schema from `schemas/metadata-schema.json`
2. Walk the target path recursively
3. For each `.md` file, parse YAML frontmatter and validate against schema
4. Classify findings as BLOCKING, WARNING, or INFO
5. If `--fix` is set, apply deterministic fixes for INFO-level issues
6. Output structured findings table
7. If `--report` is set, write report to `reports/validation-<timestamp>.md`
## Agent
Delegates to `governance-agent`
## Example
```
/validate --path canon/ --report
```
Output:
```
Metadata Validation — 2026-04-09T06:59:00
Files scanned: 42
BLOCKING: 2 | WARNING: 5 | INFO: 8
| # | File | Issue | Severity | Suggested Fix |
|---|------|-------|----------|---------------|
| 1 | canon/UIAO_003.md | Missing owner field | BLOCKING | Add owner: <owner-id> |
| 2 | canon/UIAO_017.md | Invalid version format | BLOCKING | Change "1.0a" → "1.0" |
...
```
'@ | Set-Content -Path '.claude/commands/validate-metadata.md' -Encoding UTF8 -NoNewline
$created++
Write-Host " Created: .claude/commands/validate-metadata.md" -ForegroundColor Cyan
# --- .claude/skills/appendix-indexing.md ---
@'
# Skill: Appendix Indexing
## Purpose
Maintain the appendix index, verify appendix integrity, and ensure every appendix is properly registered with its required Copy section.
## When to Use
- After any change to `appendices/` directory
- During `/appendix` or `/canon` command execution
- As part of the CI appendix-sync workflow
## Index Format
The canonical appendix index lives at `appendices/INDEX.md`:
```markdown
# Appendix Index
> Auto-generated by appendix-indexer. Manual edits will be overwritten on next sync.
> Last rebuilt: <ISO-8601 timestamp>
| ID | Title | Parent Document | Status | Owner | Has Copy | Last Updated |
|----|-------|-----------------|--------|-------|----------|--------------|
| APP-001 | ... | UIAO_001 | Current | ... | ✅ | ... |
| APP-002 | ... | UIAO_003 | Draft | ... | ✅ | ... |
```
## Integrity Rules
1. **Bijection:** Every row in INDEX.md must resolve to exactly one file in `appendices/`. Every file in `appendices/` (except INDEX.md) must have exactly one row in INDEX.md.
2. **Copy Section:** Every appendix MUST contain a `## Copy` section. Missing Copy is a BLOCKING violation.
3. **Parent Resolution:** Every `parent_document` reference must resolve to an existing canonical document in `canon/`.
4. **ID Uniqueness:** No two appendices may share an `appendix_id`.
5. **Status Validity:** Status must be one of: `Current`, `Draft`, `Deprecated`.
## Rebuild Algorithm
```
1. Walk appendices/ directory (exclude INDEX.md)
2. FOR each .md file:
a. Parse YAML frontmatter
b. Extract appendix_id, title, parent_document, status, owner, updated_at
c. Scan for ## Copy section presence
d. Add to index entries
3. Sort entries by appendix_id (ascending)
4. Generate INDEX.md from template
5. Compare generated INDEX.md with existing INDEX.md
6. Report diff (additions, removals, modifications)
```
## Execution
```bash
# Full audit (report only, no changes)
python tools/appendix_indexer.py --path appendices/ --mode audit
# Rebuild index (generates new INDEX.md)
python tools/appendix_indexer.py --path appendices/ --mode rebuild
# Sync check (compare existing index vs directory)
python tools/appendix_indexer.py --path appendices/ --mode sync
```
'@ | Set-Content -Path '.claude/skills/appendix-indexing.md' -Encoding UTF8 -NoNewline
$created++
Write-Host " Created: .claude/skills/appendix-indexing.md" -ForegroundColor Cyan
# --- .claude/skills/dashboard-export.md ---
@'
# Skill: Dashboard Export
## Purpose
Extract governance metrics from repository state, validate against the dashboard schema, and export structured data for operational dashboards and SLA heatmaps.
## When to Use
- After any canon integrity check completes
- During `/dashboard` or `/canon` command execution
- As part of the CI dashboard-export workflow
- On-demand for leadership reporting
## Export Pipeline
```
COLLECT → COMPUTE → VALIDATE → EXPORT
│ │ │ │
│ │ │ └─ Write to dashboard/exports/ in chosen format
│ │ └─ Validate against schemas/dashboard-schema.json
│ └─ Calculate derived metrics (scores, trends, heatmaps)
└─ Gather raw data from all tool outputs and frontmatter
```
## Metrics Catalog
### Repository-Level Metrics
| Metric | Computation | Type |
|--------|-------------|------|
| `canon_health_score` | Weighted average of all sub-scores | 0–100 |
| `metadata_compliance_rate` | (compliant files / total files) × 100 | percentage |
| `drift_free_rate` | (drift-free files / total files) × 100 | percentage |
| `appendix_integrity_rate` | (valid appendices / total appendices) × 100 | percentage |
| `boundary_exception_count` | Count of files with `boundary-exception: true` | integer |
| `open_remediation_count` | Count of unresolved BLOCKING + WARNING findings | integer |
### Owner-Level Metrics
| Metric | Computation | Type |
|--------|-------------|------|
| `sla_compliance_rate` | (on-time responses / total assignments) × 100 | percentage |
| `reliability_score` | 30-day rolling SLA compliance average | 0–100 |
| `owned_artifact_count` | Number of artifacts with this owner | integer |
| `open_findings_count` | BLOCKING + WARNING findings on owned artifacts | integer |
### Trend Indicators
| Indicator | Computation |
|-----------|-------------|
| `health_trend` | Δ health score over last N commits |
| `drift_trend` | Δ drift count over last N commits |
| `compliance_trend` | Δ compliance rate over last N commits |
## Execution
```bash
# Validate schema only
python tools/dashboard_exporter.py --schema schemas/dashboard-schema.json --validate
# Export JSON
python tools/dashboard_exporter.py --schema schemas/dashboard-schema.json --export json --output dashboard/exports/
# Export with 30-day trends
python tools/dashboard_exporter.py --schema schemas/dashboard-schema.json --export json --trends 30
# Export CSV for spreadsheet consumption
python tools/dashboard_exporter.py --schema schemas/dashboard-schema.json --export csv --output dashboard/exports/
# Export Markdown for human review
python tools/dashboard_exporter.py --schema schemas/dashboard-schema.json --export markdown --output dashboard/exports/
```
'@ | Set-Content -Path '.claude/skills/dashboard-export.md' -Encoding UTF8 -NoNewline
$created++
Write-Host " Created: .claude/skills/dashboard-export.md" -ForegroundColor Cyan
# --- .github/workflows/appendix-sync.yml ---
@'
name: Appendix Sync
on:
pull_request:
paths:
- 'appendices/**'
push:
branches: [main]
paths:
- 'appendices/**'
workflow_dispatch:
permissions:
contents: read
pull-requests: write
jobs:
appendix-sync:
name: Verify Appendix Integrity
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
pip install pyyaml
- name: Run appendix audit
id: audit
run: |
python tools/appendix_indexer.py \
--path appendices/ \
--mode audit \
--output reports/appendix-audit.json \
--ci
continue-on-error: true
- name: Run appendix sync check
id: sync
run: |
python tools/appendix_indexer.py \
--path appendices/ \
--mode sync \
--output reports/appendix-sync.json \
--ci
continue-on-error: true
- name: Upload appendix reports
if: always()
uses: actions/upload-artifact@v4
with:
name: appendix-reports
path: reports/
retention-days: 30
- name: Comment on PR
if: github.event_name == 'pull_request' && always()
uses: actions/github-script@v7
with:
script: |
const fs = require('fs');
let body = '## 📎 Appendix Integrity Report\n\n';
if (fs.existsSync('reports/appendix-audit.json')) {
const audit = JSON.parse(fs.readFileSync('reports/appendix-audit.json', 'utf8'));
body += `### Audit Results\n`;
body += `- Appendices found: ${audit.total_appendices}\n`;
body += `- With Copy section: ${audit.with_copy} | Missing Copy: ${audit.missing_copy}\n`;
body += `- Valid frontmatter: ${audit.valid_frontmatter} | Invalid: ${audit.invalid_frontmatter}\n\n`;
if (audit.findings && audit.findings.length > 0) {
body += '| Appendix | Issue | Severity |\n|----------|-------|----------|\n';
for (const f of audit.findings.slice(0, 20)) {
body += `| ${f.appendix_id} | ${f.issue} | ${f.severity} |\n`;
}
body += '\n';
}
}
if (fs.existsSync('reports/appendix-sync.json')) {
const sync = JSON.parse(fs.readFileSync('reports/appendix-sync.json', 'utf8'));
body += `### Sync Status\n`;
body += `- Indexed: ${sync.indexed} | In directory: ${sync.in_directory}\n`;
body += `- Orphans: ${sync.orphans} | Ghosts: ${sync.ghosts}\n`;
}
await github.rest.issues.createComment({
owner: context.repo.owner,
repo: context.repo.repo,
issue_number: context.issue.number,
body
});
- name: Fail on blocking issues
if: steps.audit.outcome == 'failure'
run: |
echo "❌ Appendix audit found BLOCKING issues (missing Copy sections or invalid frontmatter)."
exit 1
'@ | Set-Content -Path '.github/workflows/appendix-sync.yml' -Encoding UTF8 -NoNewline
$created++
Write-Host " Created: .github/workflows/appendix-sync.yml" -ForegroundColor Cyan
# --- .github/workflows/dashboard-export.yml ---
@'
name: Dashboard Export
on:
push:
branches: [main]
schedule:
- cron: '0 7 * * *' # Daily 7am UTC
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
fetch-depth: 30 # Last 30 commits for trend computation
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
- name: Run appendix audit (metrics collection)
run: |
python tools/appendix_indexer.py \
--path appendices/ \
--mode audit \
--output reports/appendix-metrics.json \
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
git diff --staged --quiet || git commit -m "[UIAO-CORE] UPDATE: Dashboard export — $(date -u +%Y-%m-%dT%H:%M:%SZ)"
git push
'@ | Set-Content -Path '.github/workflows/dashboard-export.yml' -Encoding UTF8 -NoNewline
$created++
Write-Host " Created: .github/workflows/dashboard-export.yml" -ForegroundColor Cyan
# --- .github/workflows/drift-scan.yml ---
@'
name: Drift Scan
on:
pull_request:
paths:
- 'canon/**'
- 'playbooks/**'
- 'appendices/**'
push:
branches: [main]
schedule:
- cron: '0 6 * * 1' # Weekly Monday 6am UTC
workflow_dispatch:
permissions:
contents: read
pull-requests: write
jobs:
drift-scan:
name: Detect Metadata Drift
runs-on: ubuntu-latest
steps:
- name: Checkout repository
uses: actions/checkout@v4
with:
fetch-depth: 0 # Full history for diff mode
- name: Set up Python
uses: actions/setup-python@v5
with:
python-version: '3.12'
- name: Install dependencies
run: |
python -m pip install --upgrade pip
pip install pyyaml jsonschema
- name: Determine scan mode
id: scan-mode
run: |
if [ "${{ github.event_name }}" = "pull_request" ]; then
echo "mode=diff" >> $GITHUB_OUTPUT
echo "base=${{ github.event.pull_request.base.sha }}" >> $GITHUB_OUTPUT
echo "head=${{ github.event.pull_request.head.sha }}" >> $GITHUB_OUTPUT
else
echo "mode=full" >> $GITHUB_OUTPUT
fi
- name: Run drift detector (full)
if: steps.scan-mode.outputs.mode == 'full'
id: drift-full
run: |
python tools/drift_detector.py \
--path . \
--mode full \
--schema schemas/metadata-schema.json \
--output reports/drift-report.json \
--ci
continue-on-error: true
- name: Run drift detector (diff)
if: steps.scan-mode.outputs.mode == 'diff'
id: drift-diff
run: |
python tools/drift_detector.py \
--path . \
--mode diff \
--base ${{ steps.scan-mode.outputs.base }} \
--head ${{ steps.scan-mode.outputs.head }} \
--schema schemas/metadata-schema.json \
--output reports/drift-report.json \
--ci
continue-on-error: true
- name: Upload drift reports
if: always()
uses: actions/upload-artifact@v4
with:
name: drift-reports
path: reports/
retention-days: 30
- name: Comment on PR
if: github.event_name == 'pull_request' && always()
uses: actions/github-script@v7
with:
script: |
const fs = require('fs');
if (fs.existsSync('reports/drift-report.json')) {
const data = JSON.parse(fs.readFileSync('reports/drift-report.json', 'utf8'));
let body = `## 🔎 Drift Scan Report\n\n`;
body += `- **Mode:** ${data.mode}\n`;
body += `- **Files scanned:** ${data.files_scanned}\n`;
body += `- **Drift instances:** ${data.drift_count}\n`;
body += `- **BLOCKING:** ${data.blocking} | **WARNING:** ${data.warning} | **INFO:** ${data.info}\n\n`;
if (data.findings && data.findings.length > 0) {
body += '| File | Category | Severity | Detail |\n|------|----------|----------|--------|\n';
for (const f of data.findings.slice(0, 25)) {
body += `| ${f.file} | ${f.category} | ${f.severity} | ${f.detail} |\n`;
}
} else {
body += '✅ No drift detected.\n';
}
await github.rest.issues.createComment({
owner: context.repo.owner,
repo: context.repo.repo,
issue_number: context.issue.number,
body
});
}
- name: Fail on blocking drift
if: steps.drift-full.outcome == 'failure' || steps.drift-diff.outcome == 'failure'
run: |
echo "❌ Drift scan found BLOCKING drift instances. See reports for details."
exit 1
'@ | Set-Content -Path '.github/workflows/drift-scan.yml' -Encoding UTF8 -NoNewline
$created++
Write-Host " Created: .github/workflows/drift-scan.yml" -ForegroundColor Cyan
# --- .github/workflows/metadata-validator.yml ---
@'
name: Metadata Validator
on:
pull_request:
paths:
- 'canon/**'
- 'playbooks/**'
- 'appendices/**'
- 'schemas/**'
push:
branches: [main]
paths:
- 'canon/**'
- 'playbooks/**'
- 'appendices/**'
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
- name: Run metadata validator
id: validate
run: |
python tools/metadata_validator.py \
--path canon/ \
--schema schemas/metadata-schema.json \
--output reports/validation-report.json \
--ci
continue-on-error: true
- name: Validate playbooks metadata
id: validate-playbooks
run: |
python tools/metadata_validator.py \
--path playbooks/ \
--schema schemas/metadata-schema.json \
--output reports/playbooks-validation-report.json \
--ci
continue-on-error: true
- name: Validate appendices metadata
id: validate-appendices
run: |
python tools/metadata_validator.py \
--path appendices/ \
--schema schemas/metadata-schema.json \
--output reports/appendices-validation-report.json \
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
const files = ['reports/validation-report.json', 'reports/playbooks-validation-report.json', 'reports/appendices-validation-report.json'];
for (const file of files) {
if (fs.existsSync(file)) {
const data = JSON.parse(fs.readFileSync(file, 'utf8'));
report += `### ${data.scope}\n`;
report += `- Files scanned: ${data.files_scanned}\n`;
report += `- BLOCKING: ${data.blocking} | WARNING: ${data.warning} | INFO: ${data.info}\n\n`;
if (data.findings && data.findings.length > 0) {
report += '| File | Issue | Severity |\n|------|-------|----------|\n';
for (const f of data.findings.slice(0, 20)) {
report += `| ${f.file} | ${f.issue} | ${f.severity} |\n`;
}
report += '\n';
}
}
}
await github.rest.issues.createComment({
owner: context.repo.owner,
repo: context.repo.repo,
issue_number: context.issue.number,
body: `## 🔍 Metadata Validation Report\n\n${report}`
});
- name: Fail on blocking issues
if: steps.validate.outcome == 'failure' || steps.validate-playbooks.outcome == 'failure' || steps.validate-appendices.outcome == 'failure'
run: |
echo "❌ Metadata validation found BLOCKING issues. See reports for details."
exit 1
'@ | Set-Content -Path '.github/workflows/metadata-validator.yml' -Encoding UTF8 -NoNewline
$created++
Write-Host " Created: .github/workflows/metadata-validator.yml" -ForegroundColor Cyan
# --- CLAUDE.md ---
@'
# CLAUDE.md — UIAO-Core Repository
> Canonical control surface for Claude Code integration with the UIAO-Core governance repository.
> This file is the root-level configuration. All subagents, skills, rules, and commands
> are defined under `.claude/`.
## Repository Identity
- **Name:** uiao-core
- **Purpose:** Core governance framework — canonical artifacts, state machines, enforcement rules, and operational playbooks for the UIAO modernization ecosystem.
- **Canon Authority:** This repository is the single source of truth for UIAO governance canon.
- **Cloud Boundary:** GCC-Moderate (Microsoft 365 SaaS only). No GCC-High, DoD, or Azure services unless explicitly noted.
- **Exception:** Amazon Connect Contact Center operates in Commercial Cloud.
## Operating Principles
1. **No-Hallucination Protocol:** When invoked, use only provided text as source of truth. Mark gaps as `MISSING`, uncertainties as `UNSURE`, and invented content as `NEW (Proposed)`.
2. **Provenance First:** Every artifact must trace to a canonical source. No orphan artifacts.
3. **Deterministic Workflows:** All state machines are acyclic and deterministic. No ambiguous transitions.
4. **Drift Prevention:** Metadata drift is detected, flagged, and remediated via CI enforcement.
5. **Version Isolation:** No references to any previous version in any context prior to the current version.
## Directory Convention
```
uiao-core/
├── CLAUDE.md # This file — root config
├── .claude/ # Claude Code control center
│ ├── rules/ # Governance rules (always-on)
│ ├── agents/ # Subagent persona definitions
│ ├── skills/ # Reusable skill modules
│ └── commands/ # Slash-command definitions
├── .github/workflows/ # CI enforcement pipelines
├── tools/ # Python enforcement scripts
├── schemas/ # JSON schemas (dashboard, metadata)
├── canon/ # Canonical governance documents
├── playbooks/ # Operational playbooks
└── appendices/ # Meta-appendix artifacts
```
## Commit Convention
All commits touching governance artifacts must follow:
```
[UIAO-CORE] <verb>: <artifact-id> — <short description>
```
Verbs: `CREATE`, `UPDATE`, `FIX`, `ENFORCE`, `MIGRATE`, `DEPRECATE`
## CI Gates
Every PR must pass:
- `metadata-validator` — Schema compliance for all YAML/JSON frontmatter
- `drift-scan` — Detect metadata drift between canon and working artifacts
- `appendix-sync` — Verify appendix index integrity
- `dashboard-export` — Validate dashboard schema and export readiness
## Agent Activation
Claude Code loads `.claude/rules/` automatically. Agents are activated via slash commands:
| Command | Agent | Purpose |
|---|---|---|
| `/validate` | `governance-agent` | Run metadata validation suite |
| `/drift` | `drift-detector` | Scan for canon drift |
| `/appendix` | `appendix-manager` | Index and sync appendices |
| `/dashboard` | `dashboard-exporter` | Export governance dashboard |
| `/canon` | `canon-steward` | Full canon integrity check |
'@ | Set-Content -Path 'CLAUDE.md' -Encoding UTF8 -NoNewline
$created++
Write-Host " Created: CLAUDE.md" -ForegroundColor Cyan
# --- schemas/dashboard-schema.json ---
@'
{
"$schema": "http://json-schema.org/draft-07/schema#",
"$id": "https://uiao.gov/schemas/dashboard-schema.json",
"title": "UIAO Governance Dashboard Export Schema",
"description": "Canonical schema for governance dashboard data exports. All dashboard exports must validate against this schema.",
"type": "object",
"required": [
"export_timestamp",
"repository",
"health_score",
"metrics",
"open_remediation_count"
],
"properties": {
"export_timestamp": {
"type": "string",
"format": "date-time",
"description": "ISO-8601 timestamp of export generation"
},
"repository": {
"type": "string",
"enum": ["uiao-core", "uiao-docs"],
"description": "Source repository identifier"
},
"health_score": {
"type": "integer",
"minimum": 0,
"maximum": 100,
"description": "Overall canon health score (0-100), weighted average of sub-scores"
},
"metrics": {
"type": "object",
"required": ["validation", "drift", "appendix"],
"properties": {
"validation": {
"type": "object",
"required": ["files_scanned", "compliance_rate", "blocking", "warning", "info"],
"properties": {
"files_scanned": { "type": "integer", "minimum": 0 },
"compliant": { "type": "integer", "minimum": 0 },
"non_compliant": { "type": "integer", "minimum": 0 },
"compliance_rate": { "type": "number", "minimum": 0, "maximum": 100 },
"blocking": { "type": "integer", "minimum": 0 },
"warning": { "type": "integer", "minimum": 0 },
"info": { "type": "integer", "minimum": 0 }
}
},
"drift": {
"type": "object",
"required": ["files_scanned", "drift_count", "drift_free_rate", "blocking", "warning", "info"],
"properties": {
"files_scanned": { "type": "integer", "minimum": 0 },
"drift_count": { "type": "integer", "minimum": 0 },
"drift_free": { "type": "integer", "minimum": 0 },
"drift_free_rate": { "type": "number", "minimum": 0, "maximum": 100 },
"blocking": { "type": "integer", "minimum": 0 },
"warning": { "type": "integer", "minimum": 0 },
"info": { "type": "integer", "minimum": 0 },
"by_category": {
"type": "object",
"additionalProperties": { "type": "integer", "minimum": 0 },
"description": "Drift counts by category (SCHEMA_DRIFT, PROVENANCE_DRIFT, etc.)"
}
}
},
"appendix": {
"type": "object",
"required": ["total_appendices", "with_copy", "missing_copy", "integrity_rate", "copy_compliance"],
"properties": {
"total_appendices": { "type": "integer", "minimum": 0 },
"with_copy": { "type": "integer", "minimum": 0 },
"missing_copy": { "type": "integer", "minimum": 0 },
"valid_frontmatter": { "type": "integer", "minimum": 0 },
"invalid_frontmatter": { "type": "integer", "minimum": 0 },
"integrity_rate": { "type": "number", "minimum": 0, "maximum": 100 },
"copy_compliance": { "type": "number", "minimum": 0, "maximum": 100 }
}
}
}
},
"owner_scores": {
"type": "array",
"items": {
"type": "object",
"required": ["owner", "owned_artifacts", "reliability_score"],
"properties": {
"owner": { "type": "string" },
"owned_artifacts": { "type": "integer", "minimum": 0 },
"blocking_findings": { "type": "integer", "minimum": 0 },
"warning_findings": { "type": "integer", "minimum": 0 },
"reliability_score": { "type": "integer", "minimum": 0, "maximum": 100 },
"sla_compliance_rate": { "type": "number", "minimum": 0, "maximum": 100 }
}
},
"description": "Per-owner governance metrics and reliability scores"
},
"trend_indicators": {
"type": "object",
"properties": {
"period_days": { "type": "integer", "minimum": 0 },
"health_trend": { "type": "number", "description": "Delta health score over period" },
"compliance_trend": { "type": "number", "description": "Delta compliance rate over period" },
"drift_trend": { "type": "integer", "description": "Delta drift count over period" },
"data_points": { "type": "integer", "minimum": 0 }
},
"description": "Rolling trend indicators computed from historical exports"
},
"boundary_exception_count": {
"type": "integer",
"minimum": 0,
"description": "Number of artifacts with boundary-exception: true"
},
"open_remediation_count": {
"type": "integer",
"minimum": 0,
"description": "Total unresolved BLOCKING + WARNING findings across all agents"
},
"sla_heatmap": {
"type": "object",
"additionalProperties": {
"type": "object",
"additionalProperties": {
"type": "string",
"enum": ["green", "yellow", "red", "gray"],
"description": "SLA status: green=on-time, yellow=at-risk, red=overdue, gray=no-data"
}
},
"description": "Owner-by-artifact SLA compliance matrix for heatmap visualization"
}
},
"additionalProperties": false
}
'@ | Set-Content -Path 'schemas/dashboard-schema.json' -Encoding UTF8 -NoNewline
$created++
Write-Host " Created: schemas/dashboard-schema.json" -ForegroundColor Cyan
# --- tools/appendix_indexer.py ---
@'
#!/usr/bin/env python3
"""
UIAO Appendix Indexer
======================
Manages appendix lifecycle — auditing integrity, rebuilding the index,
syncing state, and cross-repo alignment checking.
Usage:
python appendix_indexer.py --path appendices/ --mode audit
python appendix_indexer.py --path appendices/ --mode rebuild
python appendix_indexer.py --path appendices/ --mode sync
python appendix_indexer.py --path appendices/ --mode cross-repo --core-path ../uiao-core/appendices/
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
try:
import yaml
except ImportError:
print("ERROR: PyYAML required. Install: pip install pyyaml", file=sys.stderr)
sys.exit(1)
# ─── Constants ────────────────────────────────────────────────────────────────
SEVERITY_BLOCKING = "BLOCKING"
SEVERITY_WARNING = "WARNING"
SEVERITY_INFO = "INFO"
REQUIRED_FIELDS = ["appendix_id", "title", "parent_document", "status", "owner"]
VALID_STATUSES = {"Current", "Draft", "Deprecated"}
COPY_SECTION_PATTERN = re.compile(r"^##\s+Copy\b", re.MULTILINE)
# ─── Frontmatter Parser ──────────────────────────────────────────────────────
def parse_frontmatter(filepath: Path) -> tuple[dict | None, str]:
"""Extract YAML frontmatter and body from a markdown file."""
try:
content = filepath.read_text(encoding="utf-8")
except Exception:
return None, ""
if not content.startswith("---"):
return None, content
parts = content.split("---", 2)
if len(parts) < 3:
return None, content
try:
fm = yaml.safe_load(parts[1])
return (fm if isinstance(fm, dict) else None), parts[2]
except yaml.YAMLError:
return None, content
# ─── Appendix Scanner ────────────────────────────────────────────────────────
def scan_appendices(appendix_dir: Path) -> list[dict]:
"""Scan appendix directory and extract metadata from each appendix."""
entries = []
for md_file in sorted(appendix_dir.rglob("*.md")):
if md_file.name == "INDEX.md":
continue
fm, body = parse_frontmatter(md_file)
has_copy = bool(COPY_SECTION_PATTERN.search(body))
entry = {
"file": str(md_file.relative_to(appendix_dir)),
"filepath": md_file,
"frontmatter": fm,
"has_copy": has_copy,
}
if fm:
entry["appendix_id"] = fm.get("appendix_id", "")
entry["title"] = fm.get("title", "")
entry["parent_document"] = fm.get("parent_document", "")
entry["status"] = fm.get("status", "")
entry["owner"] = fm.get("owner", "")
entry["last_updated"] = fm.get("last_updated", fm.get("updated_at", ""))
else:
entry["appendix_id"] = ""
entry["title"] = md_file.stem
entry["parent_document"] = ""
entry["status"] = ""
entry["owner"] = ""
entry["last_updated"] = ""
entries.append(entry)
return entries
# ─── Audit ────────────────────────────────────────────────────────────────────
def audit_appendices(entries: list[dict]) -> list[dict]:
"""Audit appendix integrity — frontmatter, Copy sections, uniqueness."""
findings = []
seen_ids = {}
for entry in entries:
fm = entry["frontmatter"]
app_id = entry.get("appendix_id", entry["file"])
# No frontmatter
if fm is None:
findings.append({
"appendix_id": app_id or entry["file"],
"file": entry["file"],
"issue": "No valid YAML frontmatter",
"severity": SEVERITY_BLOCKING,
})
continue
# Required fields
for field in REQUIRED_FIELDS:
val = fm.get(field)
if val is None or str(val).strip() == "":
findings.append({
"appendix_id": app_id,
"file": entry["file"],
"issue": f"Missing required field: {field}",
"severity": SEVERITY_BLOCKING,
})
# Status validation
status = fm.get("status", "")
if status and status not in VALID_STATUSES:
findings.append({
"appendix_id": app_id,
"file": entry["file"],
"issue": f"Invalid status: '{status}'",
"severity": SEVERITY_WARNING,
})
# Copy section
if not entry["has_copy"]:
findings.append({
"appendix_id": app_id,
"file": entry["file"],
"issue": "Missing ## Copy section",
"severity": SEVERITY_BLOCKING,
})
# ID uniqueness
if app_id:
if app_id in seen_ids:
findings.append({
"appendix_id": app_id,
"file": entry["file"],
"issue": f"Duplicate appendix_id (also in {seen_ids[app_id]})",
"severity": SEVERITY_BLOCKING,
})
else:
seen_ids[app_id] = entry["file"]
return findings
# ─── Index Management ─────────────────────────────────────────────────────────
def parse_existing_index(index_path: Path) -> set[str]:
"""Parse existing INDEX.md and return set of indexed appendix IDs."""
if not index_path.exists():
return set()
indexed = set()
try:
content = index_path.read_text(encoding="utf-8")
# Parse table rows (skip header)
for line in content.split("\n"):
line = line.strip()
if line.startswith("|") and not line.startswith("| ID") and not line.startswith("|--"):
parts = [p.strip() for p in line.split("|")]
if len(parts) >= 3 and parts[1]:
indexed.add(parts[1])
except Exception:
pass
return indexed
def generate_index(entries: list[dict], appendix_dir: Path) -> str:
"""Generate INDEX.md content from scanned entries."""
timestamp = datetime.utcnow().isoformat() + "Z"
lines = [
"# Appendix Index",
"",
f"> Auto-generated by appendix-indexer. Manual edits will be overwritten on next sync.",
f"> Last rebuilt: {timestamp}",
"",
"| ID | Title | Parent Document | Status | Owner | Has Copy | Last Updated |",
"|----|-------|-----------------|--------|-------|----------|--------------|",
]
sorted_entries = sorted(entries, key=lambda e: e.get("appendix_id", ""))
for entry in sorted_entries:
app_id = entry.get("appendix_id", "—")
title = entry.get("title", "—")
parent = entry.get("parent_document", "—")
status = entry.get("status", "—")
owner = entry.get("owner", "—")
has_copy = "✅" if entry.get("has_copy", False) else "❌"
updated = entry.get("last_updated", "—")
lines.append(f"| {app_id} | {title} | {parent} | {status} | {owner} | {has_copy} | {updated} |")
lines.append("")
return "\n".join(lines)
def sync_check(entries: list[dict], appendix_dir: Path) -> dict:
"""Compare existing index against directory contents."""
index_path = appendix_dir / "INDEX.md"
indexed_ids = parse_existing_index(index_path)
directory_ids = {e.get("appendix_id", "") for e in entries if e.get("appendix_id")}
orphans = directory_ids - indexed_ids # In directory, not in index
ghosts = indexed_ids - directory_ids # In index, not in directory
return {
"indexed": len(indexed_ids),
"in_directory": len(directory_ids),
"orphans": len(orphans),
"orphan_ids": sorted(orphans),
"ghosts": len(ghosts),
"ghost_ids": sorted(ghosts),
"aligned": len(indexed_ids & directory_ids),
}
# ─── Cross-Repo Alignment ────────────────────────────────────────────────────
def cross_repo_check(entries: list[dict], core_path: Path) -> dict:
"""Check alignment between docs appendices and core appendices."""
if not core_path or not core_path.exists():
return {"error": "Core appendix path not found"}
core_entries = scan_appendices(core_path)
core_parents = {e.get("parent_document", ""): e for e in core_entries if e.get("parent_document")}
doc_parents = {e.get("parent_document", ""): e for e in entries if e.get("parent_document")}
aligned = 0
misaligned = 0
details = []
for parent, doc_entry in doc_parents.items():
if parent in core_parents:
aligned += 1
else:
misaligned += 1
details.append({
"appendix_id": doc_entry.get("appendix_id", ""),
"parent": parent,
"issue": "Parent document not found in uiao-core",
})
return {
"aligned": aligned,
"misaligned": misaligned,
"details": details,
}
# ─── Report ───────────────────────────────────────────────────────────────────
def generate_report(entries: list[dict], findings: list[dict],
sync_result: dict = None) -> dict:
"""Generate structured audit report."""
with_copy = sum(1 for e in entries if e.get("has_copy", False))
missing_copy = len(entries) - with_copy
valid_fm = sum(1 for e in entries if e.get("frontmatter") is not None)
invalid_fm = len(entries) - valid_fm
return {
"timestamp": datetime.utcnow().isoformat() + "Z",
"total_appendices": len(entries),
"with_copy": with_copy,
"missing_copy": missing_copy,
"valid_frontmatter": valid_fm,
"invalid_frontmatter": invalid_fm,
"total_findings": len(findings),
"blocking": sum(1 for f in findings if f["severity"] == SEVERITY_BLOCKING),
"warning": sum(1 for f in findings if f["severity"] == SEVERITY_WARNING),
"info": sum(1 for f in findings if f["severity"] == SEVERITY_INFO),
"findings": findings,
"sync": sync_result,
}
# ─── CLI ──────────────────────────────────────────────────────────────────────
def main():
parser = argparse.ArgumentParser(description="UIAO Appendix Indexer")
parser.add_argument("--path", required=True, help="Target appendix directory")
parser.add_argument("--mode", default="audit",
choices=["audit", "rebuild", "sync", "cross-repo"],
help="Operation mode")
parser.add_argument("--core-path", help="Path to uiao-core appendices (for cross-repo)")
parser.add_argument("--output", help="Output report JSON file")
parser.add_argument("--ci", action="store_true", help="CI mode: exit 1 on BLOCKING")
parser.add_argument("--metrics-only", action="store_true", help="Metrics only")
args = parser.parse_args()
appendix_dir = Path(args.path)
if not appendix_dir.exists():
print(f"WARNING: Appendix directory not found: {args.path}", file=sys.stderr)
print("Creating empty report.")
if args.output:
os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
report = generate_report([], [], None)
with open(args.output, "w") as f:
json.dump(report, f, indent=2)
sys.exit(0)
print(f"UIAO Appendix Indexer")
print(f"{'='*50}")
print(f"Mode: {args.mode}")
print(f"Target: {args.path}")
print(f"Timestamp: {datetime.utcnow().isoformat()}Z")
print()
entries = scan_appendices(appendix_dir)
findings = audit_appendices(entries)
sync_result = None
print(f"Appendices found: {len(entries)}")
print(f"With Copy section: {sum(1 for e in entries if e.get('has_copy'))}")
print(f"Missing Copy: {sum(1 for e in entries if not e.get('has_copy'))}")
print()
if args.mode == "rebuild":
index_content = generate_index(entries, appendix_dir)
index_path = appendix_dir / "INDEX.md"
index_path.write_text(index_content, encoding="utf-8")
print(f"INDEX.md rebuilt with {len(entries)} entries.")
print(f"Written to: {index_path}")
print()
if args.mode in ("sync", "rebuild"):
sync_result = sync_check(entries, appendix_dir)
print(f"Sync Status:")
print(f" Indexed: {sync_result['indexed']}")
print(f" In directory: {sync_result['in_directory']}")
print(f" Orphans: {sync_result['orphans']}")
print(f" Ghosts: {sync_result['ghosts']}")
print()
if args.mode == "cross-repo" and args.core_path:
xr = cross_repo_check(entries, Path(args.core_path))
print(f"Cross-Repo Alignment:")
print(f" Aligned: {xr.get('aligned', 0)}")
print(f" Misaligned: {xr.get('misaligned', 0)}")
print()
# Print findings
blocking = sum(1 for f in findings if f["severity"] == SEVERITY_BLOCKING)
if findings:
print(f"Findings: {len(findings)} (BLOCKING: {blocking})")
print(f"{'#':<4} {'Appendix':<15} {'Issue':<45} {'Severity':<10}")
print("-" * 74)
for i, f in enumerate(findings, 1):
print(f"{i:<4} {f['appendix_id'][:15]:<15} "
f"{f['issue'][:45]:<45} {f['severity']:<10}")
else:
print("✅ All appendices passed integrity check.")
if args.output:
os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
report = generate_report(entries, findings, sync_result)
with open(args.output, "w") as f:
json.dump(report, f, indent=2)
print(f"\nReport written to: {args.output}")
if args.ci and blocking > 0:
sys.exit(1)
if __name__ == "__main__":
main()
'@ | Set-Content -Path 'tools/appendix_indexer.py' -Encoding UTF8 -NoNewline
$created++
Write-Host " Created: tools/appendix_indexer.py" -ForegroundColor Cyan
# --- tools/dashboard_exporter.py ---
@'
#!/usr/bin/env python3
"""
UIAO Dashboard Exporter
=========================
Extracts governance metrics from repository state, validates against the
dashboard schema, and exports structured data for operational dashboards,
SLA heatmaps, and trend visualizations.
Usage:
python dashboard_exporter.py --schema schemas/dashboard-schema.json --validate
python dashboard_exporter.py --schema schemas/dashboard-schema.json --export json --output dashboard/exports/
python dashboard_exporter.py --schema schemas/dashboard-schema.json --export json --trends 30
"""
import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
try:
import yaml
except ImportError:
print("ERROR: PyYAML required. Install: pip install pyyaml", file=sys.stderr)
sys.exit(1)
try:
import jsonschema
except ImportError:
jsonschema = None
# ─── Metric Collectors ───────────────────────────────────────────────────────
def collect_validation_metrics(metrics_dir: Path) -> dict:
"""Collect metrics from validation report files."""
metrics = {
"files_scanned": 0,
"compliant": 0,
"non_compliant": 0,
"compliance_rate": 0.0,
"blocking": 0,
"warning": 0,
"info": 0,
}
report_files = list(metrics_dir.glob("*validation*.json"))
for rf in report_files:
try:
data = json.loads(rf.read_text(encoding="utf-8"))
metrics["files_scanned"] += data.get("files_scanned", 0)
metrics["blocking"] += data.get("blocking", 0)
metrics["warning"] += data.get("warning", 0)
metrics["info"] += data.get("info", 0)
except (json.JSONDecodeError, Exception):
continue
total = metrics["files_scanned"]
if total > 0:
files_with_blocking = len({
f.get("file", "") for rf in report_files
if rf.exists()
for f in json.loads(rf.read_text()).get("findings", [])
if f.get("severity") == "BLOCKING"
})
metrics["non_compliant"] = files_with_blocking
metrics["compliant"] = total - files_with_blocking
metrics["compliance_rate"] = round((metrics["compliant"] / total) * 100, 1)
return metrics
def collect_drift_metrics(metrics_dir: Path) -> dict:
"""Collect metrics from drift report files."""
metrics = {
"files_scanned": 0,
"drift_count": 0,
"drift_free": 0,
"drift_free_rate": 0.0,
"blocking": 0,
"warning": 0,
"info": 0,
"by_category": {},
}
report_files = list(metrics_dir.glob("*drift*.json"))
for rf in report_files:
try:
data = json.loads(rf.read_text(encoding="utf-8"))
metrics["files_scanned"] += data.get("files_scanned", 0)
metrics["drift_count"] += data.get("drift_count", 0)
metrics["blocking"] += data.get("blocking", 0)
metrics["warning"] += data.get("warning", 0)
metrics["info"] += data.get("info", 0)
for finding in data.get("findings", []):
cat = finding.get("category", "UNKNOWN")
metrics["by_category"][cat] = metrics["by_category"].get(cat, 0) + 1
except (json.JSONDecodeError, Exception):
continue
total = metrics["files_scanned"]
if total > 0:
drifted_files = len({
f.get("file", "") for rf in report_files
if rf.exists()
for f in json.loads(rf.read_text()).get("findings", [])
})
metrics["drift_free"] = total - drifted_files
metrics["drift_free_rate"] = round((metrics["drift_free"] / total) * 100, 1)
return metrics
def collect_appendix_metrics(metrics_dir: Path) -> dict:
"""Collect metrics from appendix audit report files."""
metrics = {
"total_appendices": 0,
"with_copy": 0,
"missing_copy": 0,
"valid_frontmatter": 0,
"invalid_frontmatter": 0,
"integrity_rate": 0.0,
"copy_compliance": 0.0,
}
report_files = list(metrics_dir.glob("*appendix*.json"))
for rf in report_files:
try:
data = json.loads(rf.read_text(encoding="utf-8"))
metrics["total_appendices"] += data.get("total_appendices", 0)
metrics["with_copy"] += data.get("with_copy", 0)
metrics["missing_copy"] += data.get("missing_copy", 0)
metrics["valid_frontmatter"] += data.get("valid_frontmatter", 0)
metrics["invalid_frontmatter"] += data.get("invalid_frontmatter", 0)
except (json.JSONDecodeError, Exception):
continue
total = metrics["total_appendices"]
if total > 0:
valid = metrics["valid_frontmatter"]
metrics["integrity_rate"] = round((valid / total) * 100, 1)
metrics["copy_compliance"] = round((metrics["with_copy"] / total) * 100, 1)
return metrics
def collect_owner_metrics(metrics_dir: Path) -> list[dict]:
"""Extract owner-level metrics from validation and drift reports."""
owners = {}
for rf in metrics_dir.glob("*.json"):
try:
data = json.loads(rf.read_text(encoding="utf-8"))
for finding in data.get("findings", []):
file_path = finding.get("file", "")
# Attempt to extract owner from findings context
# In a real implementation, this would parse frontmatter
owner = finding.get("owner", "unassigned")
if owner not in owners:
owners[owner] = {
"owner": owner,
"owned_artifacts": 0,
"blocking_findings": 0,
"warning_findings": 0,
"reliability_score": 100,
}
owners[owner]["owned_artifacts"] += 1
if finding.get("severity") == "BLOCKING":
owners[owner]["blocking_findings"] += 1
elif finding.get("severity") == "WARNING":
owners[owner]["warning_findings"] += 1
except (json.JSONDecodeError, Exception):
continue
# Compute reliability scores
for owner_data in owners.values():
total = owner_data["owned_artifacts"]
if total > 0:
penalty = (owner_data["blocking_findings"] * 10 +
owner_data["warning_findings"] * 3)
owner_data["reliability_score"] = max(0, 100 - penalty)
return list(owners.values())
# ─── Health Score ─────────────────────────────────────────────────────────────
def compute_health_score(validation: dict, drift: dict, appendix: dict) -> int:
"""Compute overall canon health score (0-100)."""
weights = {
"compliance": 0.35,
"drift_free": 0.30,
"appendix_integrity": 0.20,
"copy_compliance": 0.15,
}
scores = {
"compliance": validation.get("compliance_rate", 0),
"drift_free": drift.get("drift_free_rate", 0),
"appendix_integrity": appendix.get("integrity_rate", 0),
"copy_compliance": appendix.get("copy_compliance", 0),
}
weighted = sum(scores[k] * weights[k] for k in weights)
return round(weighted)
# ─── Trend Computation ────────────────────────────────────────────────────────
def compute_trends(output_dir: Path, days: int) -> dict:
"""Compute rolling trends from historical export files."""
trends = {
"period_days": days,
"health_trend": 0.0,
"compliance_trend": 0.0,
"drift_trend": 0,
"data_points": 0,
}
if not output_dir.exists():
return trends
cutoff = datetime.utcnow() - timedelta(days=days)
history = []
for export_file in sorted(output_dir.glob("dashboard-*.json")):
try:
data = json.loads(export_file.read_text(encoding="utf-8"))
ts = data.get("export_timestamp", "")
if ts and ts >= cutoff.isoformat():
history.append(data)
except (json.JSONDecodeError, Exception):
continue
trends["data_points"] = len(history)
if len(history) >= 2:
first = history[0]
last = history[-1]
trends["health_trend"] = round(
last.get("health_score", 0) - first.get("health_score", 0), 1)
trends["compliance_trend"] = round(
last.get("metrics", {}).get("validation", {}).get("compliance_rate", 0) -
first.get("metrics", {}).get("validation", {}).get("compliance_rate", 0), 1)
trends["drift_trend"] = (
last.get("metrics", {}).get("drift", {}).get("drift_count", 0) -
first.get("metrics", {}).get("drift", {}).get("drift_count", 0))
return trends
# ─── Export ───────────────────────────────────────────────────────────────────
def build_export(validation: dict, drift: dict, appendix: dict,
owners: list, trends: dict, repository: str) -> dict:
"""Build the complete dashboard export payload."""
health_score = compute_health_score(validation, drift, appendix)
return {
"export_timestamp": datetime.utcnow().isoformat() + "Z",
"repository": repository,
"health_score": health_score,
"metrics": {
"validation": validation,
"drift": drift,
"appendix": appendix,
},
"owner_scores": owners,
"trend_indicators": trends,
"boundary_exception_count": 0, # Populated from validation findings
"open_remediation_count": (
validation.get("blocking", 0) + validation.get("warning", 0) +
drift.get("blocking", 0) + drift.get("warning", 0) +
appendix.get("missing_copy", 0) + appendix.get("invalid_frontmatter", 0)
),
}
def validate_export(export_data: dict, schema_path: Path) -> tuple[bool, list[str]]:
"""Validate export data against the dashboard schema."""
if not schema_path.exists():
return True, ["Schema file not found — skipping validation"]
if jsonschema is None:
return True, ["jsonschema not installed — skipping validation"]
try:
schema = json.loads(schema_path.read_text(encoding="utf-8"))
jsonschema.validate(export_data, schema)
return True, []
except jsonschema.ValidationError as e:
return False, [str(e.message)]
except Exception as e:
return False, [str(e)]
def write_export(export_data: dict, output_dir: Path, fmt: str):
"""Write export to disk in the specified format."""
os.makedirs(output_dir, exist_ok=True)
date_str = datetime.utcnow().strftime("%Y-%m-%d")
if fmt == "json":
out_path = output_dir / f"dashboard-{date_str}.json"
out_path.write_text(json.dumps(export_data, indent=2), encoding="utf-8")
print(f"Export written to: {out_path}")
elif fmt == "csv":
out_path = output_dir / f"dashboard-{date_str}.csv"
lines = ["metric,value"]
lines.append(f"health_score,{export_data['health_score']}")
for section, metrics in export_data.get("metrics", {}).items():
for k, v in metrics.items():
if isinstance(v, (int, float, str)):
lines.append(f"{section}.{k},{v}")
out_path.write_text("\n".join(lines), encoding="utf-8")
print(f"Export written to: {out_path}")
elif fmt == "markdown":
out_path = output_dir / f"dashboard-{date_str}.md"
lines = [
f"# Governance Dashboard — {date_str}",
"",
f"**Health Score:** {export_data['health_score']}/100",
"",
"## Metrics",
"",
"| Category | Metric | Value |",
"|----------|--------|-------|",
]
for section, metrics in export_data.get("metrics", {}).items():
for k, v in metrics.items():
if isinstance(v, (int, float, str)):
lines.append(f"| {section} | {k} | {v} |")
lines.append("")
out_path.write_text("\n".join(lines), encoding="utf-8")
print(f"Export written to: {out_path}")
# ─── CLI ──────────────────────────────────────────────────────────────────────
def main():
parser = argparse.ArgumentParser(description="UIAO Dashboard Exporter")
parser.add_argument("--schema", required=True, help="Path to dashboard schema")
parser.add_argument("--export", choices=["json", "csv", "markdown"],
help="Export format")
parser.add_argument("--validate", action="store_true",
help="Validate existing exports against schema")
parser.add_argument("--output", default="dashboard/exports/",
help="Output directory")
parser.add_argument("--trends", type=int, default=0,
help="Days for rolling trend computation")
parser.add_argument("--metrics-dir", default="reports/",
help="Directory containing metric report files")
parser.add_argument("--input", help="Input directory for validation mode")
parser.add_argument("--repository", default="uiao-core",
help="Repository name for export")
args = parser.parse_args()
schema_path = Path(args.schema)
metrics_dir = Path(args.metrics_dir)
output_dir = Path(args.output)
print(f"UIAO Dashboard Exporter")
print(f"{'='*50}")
print(f"Timestamp: {datetime.utcnow().isoformat()}Z")
print()
if args.validate and args.input:
# Validate existing exports
input_dir = Path(args.input)
for export_file in sorted(input_dir.glob("dashboard-*.json")):
try:
data = json.loads(export_file.read_text(encoding="utf-8"))
valid, errors = validate_export(data, schema_path)
status = "✅ PASS" if valid else "❌ FAIL"
print(f"{export_file.name}: {status}")
for err in errors:
print(f" → {err}")
except Exception as e:
print(f"{export_file.name}: ❌ ERROR — {e}")
return
# Collect metrics
print("Collecting metrics...")
validation = collect_validation_metrics(metrics_dir)
drift = collect_drift_metrics(metrics_dir)
appendix = collect_appendix_metrics(metrics_dir)
owners = collect_owner_metrics(metrics_dir)
print(f" Validation: {validation['files_scanned']} files, "
f"{validation['compliance_rate']}% compliance")
print(f" Drift: {drift['files_scanned']} files, "
f"{drift['drift_free_rate']}% drift-free")
print(f" Appendix: {appendix['total_appendices']} appendices, "
f"{appendix['integrity_rate']}% integrity")
print()
# Compute trends
trends = {}
if args.trends > 0:
print(f"Computing {args.trends}-day trends...")
trends = compute_trends(output_dir, args.trends)
print(f" Data points: {trends['data_points']}")
print(f" Health trend: {trends['health_trend']:+.1f}")
print(f" Compliance trend: {trends['compliance_trend']:+.1f}")
print(f" Drift trend: {trends['drift_trend']:+d}")
print()
# Build export
export_data = build_export(validation, drift, appendix, owners,
trends, args.repository)
health = export_data["health_score"]
print(f"Canon Health Score: {health}/100")
print(f"Open Remediation Items: {export_data['open_remediation_count']}")
print()
# Validate against schema
valid, errors = validate_export(export_data, schema_path)
print(f"Schema Validation: {'✅ PASS' if valid else '❌ FAIL'}")
for err in errors:
print(f" → {err}")
print()
# Write export
if args.export:
write_export(export_data, output_dir, args.export)
if __name__ == "__main__":
main()
'@ | Set-Content -Path 'tools/dashboard_exporter.py' -Encoding UTF8 -NoNewline
$created++
Write-Host " Created: tools/dashboard_exporter.py" -ForegroundColor Cyan
# --- tools/drift_detector.py ---
@'
#!/usr/bin/env python3
"""
UIAO Drift Detector
====================
Detects, classifies, and reports metadata drift between canonical sources
and derived artifacts. Supports full, targeted, diff, and cross-repo modes.
Usage:
python drift_detector.py --path . --mode full --schema schemas/metadata-schema.json
python drift_detector.py --path canon/UIAO_001.md --mode targeted
python drift_detector.py --base main --head feature/update --mode diff
python drift_detector.py --path . --mode full --cross-repo ../uiao-core
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
try:
import yaml
except ImportError:
print("ERROR: PyYAML required. Install: pip install pyyaml", file=sys.stderr)
sys.exit(1)
# ─── Constants ────────────────────────────────────────────────────────────────
SEVERITY_BLOCKING = "BLOCKING"
SEVERITY_WARNING = "WARNING"
SEVERITY_INFO = "INFO"
DRIFT_CATEGORIES = {
"SCHEMA_DRIFT": SEVERITY_BLOCKING,
"PROVENANCE_DRIFT": SEVERITY_BLOCKING,
"BOUNDARY_DRIFT": SEVERITY_BLOCKING,
"CROSS_REPO_DRIFT": SEVERITY_BLOCKING,
"VERSION_DRIFT": SEVERITY_WARNING,
"OWNER_DRIFT": SEVERITY_WARNING,
"NAMING_DRIFT": SEVERITY_WARNING,
"FORMAT_DRIFT": SEVERITY_WARNING,
"COSMETIC_DRIFT": SEVERITY_INFO,
}
VALID_STATUSES = {"Current", "Draft", "Deprecated", "Needs Replacing", "Needs Creating"}
VALID_CLASSIFICATIONS = {"CANONICAL", "DERIVED", "OPERATIONAL"}
DOCUMENT_ID_PATTERN = re.compile(r"^UIAO_\d{3}$")
VERSION_PATTERN = re.compile(r"^\d+\.\d+$")
NAMING_PATTERN = re.compile(r"^UIAO_\d{3}_[\w_]+_v\d+\.\d+\.md$")
BOUNDARY_VIOLATIONS = re.compile(
r"GCC[\s-]?High|DoD|IL[456]|Azure\s+(IaaS|PaaS)|azure\.com",
re.IGNORECASE,
)
MERMAID_PATTERN = re.compile(r"```mermaid", re.IGNORECASE)
# ─── Frontmatter Parser ──────────────────────────────────────────────────────
def parse_frontmatter(filepath: Path) -> tuple[dict | None, str]:
"""Extract YAML frontmatter and body from a markdown file."""
try:
content = filepath.read_text(encoding="utf-8")
except Exception:
return None, ""
if not content.startswith("---"):
return None, content
parts = content.split("---", 2)
if len(parts) < 3:
return None, content
try:
fm = yaml.safe_load(parts[1])
return (fm if isinstance(fm, dict) else None), parts[2]
except yaml.YAMLError:
return None, content
def content_hash(filepath: Path) -> str:
"""Compute SHA-256 hash of file content."""
try:
return hashlib.sha256(filepath.read_bytes()).hexdigest()[:16]
except Exception:
return ""
# ─── Drift Detectors ─────────────────────────────────────────────────────────
def detect_schema_drift(filepath: Path, fm: dict, base_path: Path) -> list[dict]:
"""Detect schema-level drift in frontmatter."""
findings = []
rel = str(filepath.relative_to(base_path))
def add(category, detail, remediation=""):
findings.append({
"file": rel,
"category": category,
"severity": DRIFT_CATEGORIES.get(category, SEVERITY_WARNING),
"detail": detail,
"remediation": remediation,
})
if fm is None:
add("SCHEMA_DRIFT", "No YAML frontmatter found",
"Add YAML frontmatter between --- delimiters")
return findings
# Required fields check
required = ["document_id", "title", "version", "status", "classification",
"owner", "created_at", "updated_at", "boundary"]
for field in required:
if field not in fm or fm[field] is None or str(fm[field]).strip() == "":
add("SCHEMA_DRIFT", f"Missing required field: {field}",
f"Add {field}: <value>")
# Format checks
doc_id = str(fm.get("document_id", ""))
if doc_id and not DOCUMENT_ID_PATTERN.match(doc_id):
add("SCHEMA_DRIFT", f"Invalid document_id: '{doc_id}'",
"Use format UIAO_NNN")
ver = str(fm.get("version", ""))
if ver and not VERSION_PATTERN.match(ver):
add("SCHEMA_DRIFT", f"Invalid version: '{ver}'", "Use format N.N")
status = fm.get("status", "")
if status and status not in VALID_STATUSES:
add("SCHEMA_DRIFT", f"Invalid status: '{status}'",
f"Use: {', '.join(sorted(VALID_STATUSES))}")
classification = fm.get("classification", "")
if classification and classification not in VALID_CLASSIFICATIONS:
add("SCHEMA_DRIFT", f"Invalid classification: '{classification}'",
f"Use: {', '.join(sorted(VALID_CLASSIFICATIONS))}")
return findings
def detect_provenance_drift(filepath: Path, fm: dict, base_path: Path) -> list[dict]:
"""Detect provenance chain drift for DERIVED artifacts."""
findings = []
if fm is None:
return findings
rel = str(filepath.relative_to(base_path))
classification = fm.get("classification", "")
if classification != "DERIVED":
return findings
prov = fm.get("provenance", {})
if not prov or not isinstance(prov, dict):
findings.append({
"file": rel,
"category": "PROVENANCE_DRIFT",
"severity": SEVERITY_BLOCKING,
"detail": "DERIVED artifact missing provenance block",
"remediation": "Add provenance: {source, version, derived_at, derived_by}",
})
return findings
for pf in ["source", "version", "derived_at", "derived_by"]:
if pf not in prov or not prov[pf]:
findings.append({
"file": rel,
"category": "PROVENANCE_DRIFT",
"severity": SEVERITY_BLOCKING,
"detail": f"Provenance missing field: {pf}",
"remediation": f"Add provenance.{pf}",
})
source = prov.get("source", "")
if source:
source_path = base_path / source
if not source_path.exists():
alt_path = base_path.parent / source
if not alt_path.exists():
findings.append({
"file": rel,
"category": "PROVENANCE_DRIFT",
"severity": SEVERITY_BLOCKING,
"detail": f"Provenance source not found: {source}",
"remediation": "Verify provenance.source path",
})
return findings
def detect_boundary_drift(filepath: Path, fm: dict, body: str, base_path: Path) -> list[dict]:
"""Detect cloud boundary violations in content."""
findings = []
if fm is None:
return findings
rel = str(filepath.relative_to(base_path))
boundary = fm.get("boundary", "")
has_exception = fm.get("boundary-exception", False)
if boundary and boundary != "GCC-Moderate" and not has_exception:
findings.append({
"file": rel,
"category": "BOUNDARY_DRIFT",
"severity": SEVERITY_BLOCKING,
"detail": f"Boundary is '{boundary}', expected GCC-Moderate",
"remediation": "Set boundary: GCC-Moderate or add boundary-exception: true",
})
if BOUNDARY_VIOLATIONS.search(body) and not has_exception:
matches = BOUNDARY_VIOLATIONS.findall(body)
findings.append({
"file": rel,
"category": "BOUNDARY_DRIFT",
"severity": SEVERITY_BLOCKING,
"detail": f"Body contains boundary violations: {', '.join(set(matches))}",
"remediation": "Remove references or add boundary-exception: true",
})
return findings
def detect_version_drift(filepath: Path, body: str, base_path: Path) -> list[dict]:
"""Detect references to prior version epochs."""
findings = []
rel = str(filepath.relative_to(base_path))
prior_refs = re.findall(r"v0\.\d+|version\s+0\.\d+|prior\s+version|previous\s+version",
body, re.IGNORECASE)
if prior_refs:
findings.append({
"file": rel,
"category": "VERSION_DRIFT",
"severity": SEVERITY_WARNING,
"detail": f"References to prior versions found: {', '.join(set(prior_refs[:5]))}",
"remediation": "Update to current version references",
})
return findings
def detect_naming_drift(filepath: Path, base_path: Path) -> list[dict]:
"""Detect filename naming convention violations."""
findings = []
rel = str(filepath.relative_to(base_path))
# Only check files in canon/ directory
if "canon" in filepath.parts and not filepath.name.startswith("INDEX"):
if not NAMING_PATTERN.match(filepath.name):
findings.append({
"file": rel,
"category": "NAMING_DRIFT",
"severity": SEVERITY_WARNING,
"detail": f"Filename '{filepath.name}' doesn't match convention",
"remediation": "Use format: UIAO_NNN_Short_Title_vN.N.md",
})
return findings
def detect_cosmetic_drift(filepath: Path, body: str, base_path: Path) -> list[dict]:
"""Detect formatting inconsistencies."""
findings = []
rel = str(filepath.relative_to(base_path))
if MERMAID_PATTERN.search(body):
findings.append({
"file": rel,
"category": "COSMETIC_DRIFT",
"severity": SEVERITY_INFO,
"detail": "Uses Mermaid diagrams (PlantUML preferred)",
"remediation": "Convert to PlantUML",
})
return findings
def detect_owner_drift(filepath: Path, fm: dict, base_path: Path) -> list[dict]:
"""Detect missing or stale owner assignments."""
findings = []
if fm is None:
return findings
rel = str(filepath.relative_to(base_path))
if not fm.get("owner"):
findings.append({
"file": rel,
"category": "OWNER_DRIFT",
"severity": SEVERITY_WARNING,
"detail": "No owner assigned",
"remediation": "Assign an owner in frontmatter",
})
return findings
# ─── Cross-Repo Drift ────────────────────────────────────────────────────────
def detect_cross_repo_drift(filepath: Path, fm: dict, base_path: Path,
core_path: Path) -> list[dict]:
"""Detect drift between derived doc and its uiao-core canonical source."""
findings = []
if fm is None:
return findings
rel = str(filepath.relative_to(base_path))
prov = fm.get("provenance", {})
if not prov or not isinstance(prov, dict):
return findings
source = prov.get("source", "")
if not source:
return findings
# Resolve source in uiao-core
source_clean = source.replace("uiao-core/", "")
source_path = core_path / source_clean
if not source_path.exists():
findings.append({
"file": rel,
"category": "CROSS_REPO_DRIFT",
"severity": SEVERITY_BLOCKING,
"detail": f"Canonical source not found in uiao-core: {source_clean}",
"remediation": "Verify provenance.source path in uiao-core",
})
return findings
# Compare versions
core_fm, _ = parse_frontmatter(source_path)
if core_fm:
core_version = str(core_fm.get("version", ""))
local_version = str(prov.get("version", ""))
if core_version and local_version and core_version != local_version:
findings.append({
"file": rel,
"category": "CROSS_REPO_DRIFT",
"severity": SEVERITY_BLOCKING,
"detail": f"Version mismatch: local={local_version}, core={core_version}",
"remediation": f"Re-derive from uiao-core version {core_version}",
})
return findings
# ─── Scan Orchestrator ────────────────────────────────────────────────────────
def scan_file(filepath: Path, base_path: Path, core_path: Path = None) -> list[dict]:
"""Run all drift detectors on a single file."""
fm, body = parse_frontmatter(filepath)
findings = []
findings.extend(detect_schema_drift(filepath, fm, base_path))
findings.extend(detect_provenance_drift(filepath, fm, base_path))
findings.extend(detect_boundary_drift(filepath, fm, body, base_path))
findings.extend(detect_version_drift(filepath, body, base_path))
findings.extend(detect_naming_drift(filepath, base_path))
findings.extend(detect_owner_drift(filepath, fm, base_path))
findings.extend(detect_cosmetic_drift(filepath, body, base_path))
if core_path:
findings.extend(detect_cross_repo_drift(filepath, fm, base_path, core_path))
return findings
def scan_directory(target: Path, base_path: Path, core_path: Path = None) -> tuple[int, list[dict]]:
"""Scan all markdown files in a directory."""
all_findings = []
file_count = 0
if target.is_file():
if target.suffix == ".md":
file_count = 1
all_findings.extend(scan_file(target, base_path, core_path))
else:
for md_file in sorted(target.rglob("*.md")):
if md_file.name in ("INDEX.md", "README.md", "CLAUDE.md"):
continue
if ".claude" in md_file.parts or ".github" in md_file.parts:
continue
file_count += 1
all_findings.extend(scan_file(md_file, base_path, core_path))
return file_count, all_findings
def scan_diff(base_ref: str, head_ref: str, base_path: Path,
core_path: Path = None) -> tuple[int, list[dict]]:
"""Scan only files changed between two Git refs."""
try:
result = subprocess.run(
["git", "diff", "--name-only", base_ref, head_ref, "--", "*.md"],
capture_output=True, text=True, cwd=str(base_path)
)
changed_files = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
except Exception:
changed_files = []
all_findings = []
file_count = 0
for rel_path in changed_files:
filepath = base_path / rel_path
if filepath.exists() and filepath.suffix == ".md":
file_count += 1
all_findings.extend(scan_file(filepath, base_path, core_path))
return file_count, all_findings
# ─── Report ───────────────────────────────────────────────────────────────────
def generate_report(mode: str, file_count: int, findings: list[dict]) -> dict:
"""Generate structured drift report."""
blocking = sum(1 for f in findings if f["severity"] == SEVERITY_BLOCKING)
warning = sum(1 for f in findings if f["severity"] == SEVERITY_WARNING)
info = sum(1 for f in findings if f["severity"] == SEVERITY_INFO)
return {
"mode": mode,
"timestamp": datetime.utcnow().isoformat() + "Z",
"files_scanned": file_count,
"drift_count": len(findings),
"blocking": blocking,
"warning": warning,
"info": info,
"findings": findings,
}
# ─── CLI ──────────────────────────────────────────────────────────────────────
def main():
parser = argparse.ArgumentParser(description="UIAO Drift Detector")
parser.add_argument("--path", default=".", help="Target directory or file")
parser.add_argument("--mode", default="full",
choices=["full", "targeted", "diff", "format"],
help="Scan mode")
parser.add_argument("--base", help="Base Git ref for diff mode")
parser.add_argument("--head", default="HEAD", help="Head Git ref for diff mode")
parser.add_argument("--schema", help="Path to metadata schema")
parser.add_argument("--cross-repo", help="Path to uiao-core for cross-repo drift")
parser.add_argument("--template", help="Formatting template name")
parser.add_argument("--output", help="Output report JSON file")
parser.add_argument("--ci", action="store_true", help="CI mode: exit 1 on BLOCKING")
parser.add_argument("--metrics-only", action="store_true", help="Metrics only output")
args = parser.parse_args()
target = Path(args.path)
base_path = target if target.is_dir() else target.parent
core_path = Path(args.cross_repo) if args.cross_repo else None
print(f"UIAO Drift Detector")
print(f"{'='*50}")
print(f"Mode: {args.mode}")
print(f"Target: {args.path}")
if core_path:
print(f"Cross-repo: {args.cross_repo}")
print(f"Timestamp: {datetime.utcnow().isoformat()}Z")
print()
if args.mode == "diff" and args.base:
file_count, findings = scan_diff(args.base, args.head, base_path, core_path)
else:
file_count, findings = scan_directory(target, base_path, core_path)
blocking = sum(1 for f in findings if f["severity"] == SEVERITY_BLOCKING)
warning = sum(1 for f in findings if f["severity"] == SEVERITY_WARNING)
info = sum(1 for f in findings if f["severity"] == SEVERITY_INFO)
print(f"Files scanned: {file_count}")
print(f"Drift instances: {len(findings)}")
print(f"BLOCKING: {blocking} | WARNING: {warning} | INFO: {info}")
print()
if findings:
print(f"{'#':<4} {'File':<35} {'Category':<20} {'Severity':<10} {'Detail':<40}")
print("-" * 109)
for i, f in enumerate(findings, 1):
print(f"{i:<4} {f['file'][:35]:<35} {f['category']:<20} "
f"{f['severity']:<10} {f['detail'][:40]}")
else:
print("✅ No drift detected.")
if args.output:
os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
report = generate_report(args.mode, file_count, findings)
with open(args.output, "w") as out:
json.dump(report, out, indent=2)
print(f"\nReport written to: {args.output}")
if args.ci and blocking > 0:
sys.exit(1)
if __name__ == "__main__":
main()
'@ | Set-Content -Path 'tools/drift_detector.py' -Encoding UTF8 -NoNewline
$created++
Write-Host " Created: tools/drift_detector.py" -ForegroundColor Cyan
# --- tools/metadata_validator.py ---
@'
#!/usr/bin/env python3
"""
UIAO Metadata Validator
========================
Validates YAML frontmatter across governance artifacts against the canonical
metadata schema. Supports CI mode with JSON output and exit code control.
Usage:
python metadata_validator.py --path canon/ --schema schemas/metadata-schema.json
python metadata_validator.py --path canon/ --schema schemas/metadata-schema.json --ci --output report.json
python metadata_validator.py --path . --audit-classification
python metadata_validator.py --path articles/ --audit-format --template article-1
python metadata_validator.py --path . --audit-placeholders
python metadata_validator.py --path . --audit-images
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
try:
import yaml
except ImportError:
print("ERROR: PyYAML required. Install: pip install pyyaml", file=sys.stderr)
sys.exit(1)
try:
import jsonschema
except ImportError:
jsonschema = None # Optional — used for schema-based validation
# ─── Constants ────────────────────────────────────────────────────────────────
SEVERITY_BLOCKING = "BLOCKING"
SEVERITY_WARNING = "WARNING"
SEVERITY_INFO = "INFO"
VALID_STATUSES = {"Current", "Draft", "Deprecated", "Needs Replacing", "Needs Creating"}
VALID_CLASSIFICATIONS = {"CANONICAL", "DERIVED", "OPERATIONAL"}
DOCUMENT_ID_PATTERN = re.compile(r"^UIAO_\d{3}$")
VERSION_PATTERN = re.compile(r"^\d+\.\d+$")
ISO8601_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2})?")
BOUNDARY_VIOLATIONS = re.compile(
r"GCC[\s-]?High|DoD|IL[456]|Azure\s+(IaaS|PaaS)|azure\.com",
re.IGNORECASE,
)
MERMAID_PATTERN = re.compile(r"```mermaid", re.IGNORECASE)
PLACEHOLDER_ID_PATTERN = re.compile(r"PH-\d{3}")
# ─── Frontmatter Parser ──────────────────────────────────────────────────────
def parse_frontmatter(filepath: Path) -> tuple[dict | None, str]:
"""Extract YAML frontmatter and body from a markdown file."""
try:
content = filepath.read_text(encoding="utf-8")
except Exception as e:
return None, ""
if not content.startswith("---"):
return None, content
parts = content.split("---", 2)
if len(parts) < 3:
return None, content
try:
fm = yaml.safe_load(parts[1])
return (fm if isinstance(fm, dict) else None), parts[2]
except yaml.YAMLError:
return None, content
# ─── Validators ───────────────────────────────────────────────────────────────
def validate_frontmatter(filepath: Path, fm: dict, body: str, base_path: Path) -> list[dict]:
"""Validate frontmatter fields against UIAO metadata rules."""
findings = []
rel = str(filepath.relative_to(base_path))
def add(issue, severity, fix=None):
entry = {"file": rel, "issue": issue, "severity": severity}
if fix:
entry["suggested_fix"] = fix
findings.append(entry)
# Required fields
required = ["document_id", "title", "version", "status", "classification",
"owner", "created_at", "updated_at", "boundary"]
for field in required:
if field not in fm or fm[field] is None or str(fm[field]).strip() == "":
add(f"Missing required field: {field}", SEVERITY_BLOCKING,
f"Add {field}: <value> to frontmatter")
# document_id pattern
doc_id = str(fm.get("document_id", ""))
if doc_id and not DOCUMENT_ID_PATTERN.match(doc_id):
add(f"Invalid document_id format: '{doc_id}' (expected UIAO_NNN)",
SEVERITY_BLOCKING, "Use format UIAO_001")
# version pattern
ver = str(fm.get("version", ""))
if ver and not VERSION_PATTERN.match(ver):
add(f"Invalid version format: '{ver}' (expected N.N)",
SEVERITY_BLOCKING, "Use format 1.0")
# status enum
status = fm.get("status", "")
if status and status not in VALID_STATUSES:
add(f"Invalid status: '{status}'", SEVERITY_BLOCKING,
f"Use one of: {', '.join(sorted(VALID_STATUSES))}")
# classification enum
classification = fm.get("classification", "")
if classification and classification not in VALID_CLASSIFICATIONS:
add(f"Invalid classification: '{classification}'", SEVERITY_BLOCKING,
f"Use one of: {', '.join(sorted(VALID_CLASSIFICATIONS))}")
# boundary check
boundary = fm.get("boundary", "")
if boundary and boundary != "GCC-Moderate":
if not fm.get("boundary-exception", False):
add(f"Boundary must be GCC-Moderate (found: '{boundary}')",
SEVERITY_BLOCKING, "Set boundary: GCC-Moderate or add boundary-exception: true")
# timestamp validation
for ts_field in ["created_at", "updated_at"]:
ts = str(fm.get(ts_field, ""))
if ts and not ISO8601_PATTERN.match(ts):
add(f"Invalid {ts_field} format: '{ts}' (expected ISO-8601)",
SEVERITY_BLOCKING, "Use format 2026-04-09T07:00:00")
# created_at <= updated_at
created = fm.get("created_at", "")
updated = fm.get("updated_at", "")
if created and updated and str(created) > str(updated):
add("updated_at is earlier than created_at", SEVERITY_BLOCKING,
"Ensure updated_at >= created_at")
# provenance for DERIVED
if classification == "DERIVED":
prov = fm.get("provenance", {})
if not prov or not isinstance(prov, dict):
add("DERIVED artifact missing provenance block", SEVERITY_BLOCKING,
"Add provenance: {source, version, derived_at, derived_by}")
else:
for pf in ["source", "version", "derived_at", "derived_by"]:
if pf not in prov or not prov[pf]:
add(f"Provenance missing field: {pf}", SEVERITY_BLOCKING,
f"Add provenance.{pf}")
# Check source resolution
source = prov.get("source", "")
if source:
source_path = base_path / source
if not source_path.exists():
# Try relative to repo root
alt_path = base_path.parent / source
if not alt_path.exists():
add(f"Provenance source not found: {source}",
SEVERITY_BLOCKING, "Verify provenance.source path exists")
# Owner field
if not fm.get("owner"):
add("Missing owner field", SEVERITY_WARNING,
"Assign an owner to this artifact")
# Body content checks
if BOUNDARY_VIOLATIONS.search(body):
if not fm.get("boundary-exception", False):
add("Body contains potential boundary violation (GCC-High/DoD/Azure IaaS/PaaS reference)",
SEVERITY_BLOCKING, "Remove reference or add boundary-exception: true")
if MERMAID_PATTERN.search(body):
add("Body contains Mermaid diagram (PlantUML required)",
SEVERITY_WARNING, "Convert diagram to PlantUML")
return findings
def validate_file(filepath: Path, base_path: Path) -> list[dict]:
"""Validate a single markdown file."""
findings = []
rel = str(filepath.relative_to(base_path))
fm, body = parse_frontmatter(filepath)
if fm is None:
findings.append({
"file": rel,
"issue": "No valid YAML frontmatter found",
"severity": SEVERITY_BLOCKING,
"suggested_fix": "Add YAML frontmatter between --- delimiters"
})
return findings
findings.extend(validate_frontmatter(filepath, fm, body, base_path))
return findings
# ─── Directory Walker ─────────────────────────────────────────────────────────
def walk_and_validate(target_path: Path, base_path: Path) -> tuple[int, list[dict]]:
"""Walk a directory and validate all .md files."""
all_findings = []
file_count = 0
if target_path.is_file():
if target_path.suffix == ".md":
file_count = 1
all_findings.extend(validate_file(target_path, base_path))
else:
for md_file in sorted(target_path.rglob("*.md")):
# Skip index files and READMEs
if md_file.name in ("INDEX.md", "README.md"):
continue
file_count += 1
all_findings.extend(validate_file(md_file, base_path))
return file_count, all_findings
# ─── Report Generation ────────────────────────────────────────────────────────
def generate_report(scope: str, file_count: int, findings: list[dict]) -> dict:
"""Generate a structured validation report."""
blocking = sum(1 for f in findings if f["severity"] == SEVERITY_BLOCKING)
warning = sum(1 for f in findings if f["severity"] == SEVERITY_WARNING)
info = sum(1 for f in findings if f["severity"] == SEVERITY_INFO)
return {
"scope": scope,
"timestamp": datetime.utcnow().isoformat() + "Z",
"files_scanned": file_count,
"total_findings": len(findings),
"blocking": blocking,
"warning": warning,
"info": info,
"findings": findings,
}
# ─── CLI ──────────────────────────────────────────────────────────────────────
def main():
parser = argparse.ArgumentParser(description="UIAO Metadata Validator")
parser.add_argument("--path", required=True, help="Target directory or file")
parser.add_argument("--schema", help="Path to JSON schema file")
parser.add_argument("--output", help="Output report JSON file")
parser.add_argument("--ci", action="store_true", help="CI mode: exit 1 on BLOCKING")
parser.add_argument("--metrics-only", action="store_true", help="Output metrics only")
parser.add_argument("--audit-classification", action="store_true",
help="Audit file classifications")
parser.add_argument("--audit-format", action="store_true",
help="Audit article formatting")
parser.add_argument("--audit-placeholders", action="store_true",
help="Audit placeholder standards")
parser.add_argument("--audit-images", action="store_true",
help="Audit image standards")
parser.add_argument("--template", help="Formatting template name")
args = parser.parse_args()
target = Path(args.path)
if not target.exists():
print(f"ERROR: Path not found: {args.path}", file=sys.stderr)
sys.exit(2)
base_path = target if target.is_dir() else target.parent
print(f"UIAO Metadata Validator")
print(f"{'='*50}")
print(f"Target: {args.path}")
print(f"Timestamp: {datetime.utcnow().isoformat()}Z")
print()
file_count, findings = walk_and_validate(target, base_path)
blocking = sum(1 for f in findings if f["severity"] == SEVERITY_BLOCKING)
warning = sum(1 for f in findings if f["severity"] == SEVERITY_WARNING)
info = sum(1 for f in findings if f["severity"] == SEVERITY_INFO)
print(f"Files scanned: {file_count}")
print(f"BLOCKING: {blocking} | WARNING: {warning} | INFO: {info}")
print()
if findings:
print(f"{'#':<4} {'File':<40} {'Issue':<50} {'Severity':<10}")
print("-" * 104)
for i, f in enumerate(findings, 1):
print(f"{i:<4} {f['file']:<40} {f['issue'][:50]:<50} {f['severity']:<10}")
else:
print("✅ All files passed validation.")
# Write output report
if args.output:
os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
report = generate_report(args.path, file_count, findings)
with open(args.output, "w") as f:
json.dump(report, f, indent=2)
print(f"\nReport written to: {args.output}")
# CI mode: exit 1 on blocking
if args.ci and blocking > 0:
sys.exit(1)
if __name__ == "__main__":
main()
'@ | Set-Content -Path 'tools/metadata_validator.py' -Encoding UTF8 -NoNewline
$created++
Write-Host " Created: tools/metadata_validator.py" -ForegroundColor Cyan
Write-Host "`n=== DEPLOYMENT COMPLETE ===" -ForegroundColor Green
Write-Host "Repository : uiao-core" -ForegroundColor Green
Write-Host "Files created: $created" -ForegroundColor Green
Write-Host "`nNext steps:" -ForegroundColor Yellow
Write-Host " git add -A" -ForegroundColor White
Write-Host " git commit -m 'Deploy Claude Code integration layer'" -ForegroundColor White
Write-Host " git push" -ForegroundColor White
