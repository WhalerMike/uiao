<#
.SYNOPSIS
    UIAO CLI Registration & Smoke-Test Harness
.DESCRIPTION
    Tests every registered `uiao` CLI command by invoking --help and
    validating exit codes. Produces a colour-coded pass/fail summary.

    Inventory source: impl/src/uiao/impl/cli/app.py  (34 top-level)
                      + scuba.py, ksi.py, evidence.py, oscal.py, substrate.py (6 sub-cmds)
                      = 40 testable surfaces

    Prerequisites:
      cd $env:UIAO_WORKSPACE_ROOT\impl
      pip install -e ".[dev]"

.NOTES
    Generated 2026-04-18 — UIAO monorepo (WhalerMike/uiao)
    Requires: Python >= 3.10, uiao-impl installed, Windows PowerShell 5.1+
#>

[CmdletBinding()]
param(
    [switch]$ShowDetails,
    [switch]$StopOnFail
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Continue'

# ─── colour helpers ───────────────────────────────────────────────────
function Write-Pass  { param([string]$Msg) Write-Host "  PASS  " -ForegroundColor Green  -NoNewline; Write-Host " $Msg" }
function Write-Fail  { param([string]$Msg) Write-Host "  FAIL  " -ForegroundColor Red    -NoNewline; Write-Host " $Msg" }
function Write-Skip  { param([string]$Msg) Write-Host "  SKIP  " -ForegroundColor Yellow -NoNewline; Write-Host " $Msg" }
function Write-Section { param([string]$Msg)
    Write-Host ""
    Write-Host ("=" * 72) -ForegroundColor Cyan
    Write-Host "  $Msg" -ForegroundColor Cyan
    Write-Host ("=" * 72) -ForegroundColor Cyan
}

# ─── result counters ──────────────────────────────────────────────────
$script:Passed  = 0
$script:Failed  = 0
$script:Skipped = 0
$script:Results = [System.Collections.ArrayList]::new()

function Test-Command {
    <#
    .SYNOPSIS Run a single CLI test and record the result.
    #>
    param(
        [string]$Label,
        [string[]]$CmdArgs,
        [int]$ExpectedExit = 0,
        [string]$ExpectOutputContains = '',
        [switch]$AllowNonZero
    )

    $cmdLine = "uiao $($CmdArgs -join ' ')"

    try {
        $output = & uiao @CmdArgs 2>&1 | Out-String
        $exit   = $LASTEXITCODE
    }
    catch {
        $output = $_.Exception.Message
        $exit   = 999
    }

    $passed = $false

    if ($AllowNonZero) {
        $passed = ($exit -ne 999)
    }
    elseif ($exit -eq $ExpectedExit) {
        if ($ExpectOutputContains -and $output -notmatch [regex]::Escape($ExpectOutputContains)) {
            $passed = $false
        }
        else {
            $passed = $true
        }
    }

    if ($passed) {
        Write-Pass $Label
        $script:Passed++
        $status = 'PASS'
    }
    else {
        Write-Fail "$Label  (exit=$exit)"
        if ($ShowDetails) { Write-Host "         stdout/stderr: $($output.Trim().Substring(0, [Math]::Min(300, $output.Trim().Length)))" -ForegroundColor DarkGray }
        $script:Failed++
        $status = 'FAIL'
        if ($StopOnFail) { throw "StopOnFail: $Label" }
    }

    [void]$script:Results.Add([PSCustomObject]@{
        Test     = $Label
        Command  = $cmdLine
        ExitCode = $exit
        Status   = $status
    })
}

# ─── pre-flight ───────────────────────────────────────────────────────
Write-Section "UIAO CLI Test Harness"
Write-Host "  Timestamp : $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Write-Host "  Host      : $($env:COMPUTERNAME)"
Write-Host "  PS Version: $($PSVersionTable.PSVersion)"
Write-Host ""

# Verify uiao is on PATH
$uiaoPath = Get-Command uiao -ErrorAction SilentlyContinue
if (-not $uiaoPath) {
    Write-Fail "uiao not found on PATH. Install: cd impl && pip install -e '.[dev]'"
    exit 1
}
Write-Host "  uiao path : $($uiaoPath.Source)" -ForegroundColor DarkGray

# ─── 1. Version ───────────────────────────────────────────────────────
Write-Section "1 · Version check"
Test-Command -Label "uiao --version" -CmdArgs @("--version") -ExpectedExit 0

# ─── 2. Root --help ──────────────────────────────────────────────────
Write-Section "2 · Root help"
Test-Command -Label "uiao --help" -CmdArgs @("--help") -ExpectedExit 0

# ─── 3. Top-level commands via --help ─────────────────────────────────
Write-Section "3 · Top-level commands (--help registration)"

$topLevelCommands = @(
    'generate-ssp',
    'validate',
    'canon-check',
    'validate-ssp',
    'generate-visuals',
    'generate-gemini',
    'generate-pptx',
    'generate-docx',
    'generate-diagrams',
    'generate-docs',
    'generate-artifacts',
    'generate-sbom',
    'conmon-process',
    'conmon-export-oa',
    'conmon-dashboard',
    'generate-all',
    'adapter-run',
    'generate-briefing',
    'adapter-run-scuba',
    'ir-scuba-transform',
    'ir-evidence-bundle',
    'ir-poam-export',
    'ir-drift-detect',
    'ir-governance-report',
    'ir-ssp-report',
    'ir-auditor-bundle',
    'ir-diff',
    'ir-validate',
    'ir-freshness',
    'ir-dashboard',
    'ir-freshness-schedule',
    'ir-generate-sar',
    'ir-ssp-inject'
)

foreach ($cmd in $topLevelCommands) {
    Test-Command -Label "uiao $cmd --help" -CmdArgs @($cmd, '--help') -ExpectedExit 0
}

# ─── 4. Sub-command groups (group --help) ─────────────────────────────
Write-Section "4 · Sub-command groups (--help)"

$subGroups = @('scuba', 'ksi', 'evidence', 'oscal', 'substrate')
foreach ($grp in $subGroups) {
    Test-Command -Label "uiao $grp --help" -CmdArgs @($grp, '--help') -ExpectedExit 0
}

# ─── 5. Sub-commands via --help ───────────────────────────────────────
Write-Section "5 · Sub-commands (--help registration)"

$subCommands = @(
    @('scuba',     'transform'),
    @('ksi',       'evaluate'),
    @('evidence',  'build'),
    @('oscal',     'generate'),
    @('substrate', 'walk'),
    @('substrate', 'drift')
)

foreach ($pair in $subCommands) {
    $grp = $pair[0]
    $sub = $pair[1]
    Test-Command -Label "uiao $grp $sub --help" -CmdArgs @($grp, $sub, '--help') -ExpectedExit 0
}

# ─── 6. Negative / edge-case tests ───────────────────────────────────
Write-Section "6 · Negative & edge-case tests"

# Unknown command should fail
try {
    & uiao bogus-command 2>&1 | Out-String | Out-Null
    $bogusExit = $LASTEXITCODE
}
catch { $bogusExit = 999 }

if ($bogusExit -ne 0) {
    Write-Pass "uiao bogus-command → non-zero exit ($bogusExit)"
    $script:Passed++
    [void]$script:Results.Add([PSCustomObject]@{ Test = 'bogus-command rejects'; Command = 'uiao bogus-command'; ExitCode = $bogusExit; Status = 'PASS' })
}
else {
    Write-Fail "uiao bogus-command → exit 0 (expected non-zero)"
    $script:Failed++
    [void]$script:Results.Add([PSCustomObject]@{ Test = 'bogus-command rejects'; Command = 'uiao bogus-command'; ExitCode = $bogusExit; Status = 'FAIL' })
}

# Commands that require args should fail without them
$requiresArgs = @(
    @('validate',            'validate (no path)'),
    @('adapter-run',         'adapter-run (no vendor)'),
    @('ir-scuba-transform',  'ir-scuba-transform (no file)'),
    @('ir-evidence-bundle',  'ir-evidence-bundle (no file)'),
    @('ir-drift-detect',     'ir-drift-detect (no files)'),
    @('ir-diff',             'ir-diff (no files)'),
    @('ir-validate',         'ir-validate (no file)'),
    @('ir-freshness',        'ir-freshness (no file)')
)

foreach ($item in $requiresArgs) {
    $cmd   = $item[0]
    $label = $item[1]
    try {
        & uiao $cmd 2>&1 | Out-String | Out-Null
        $argExit = $LASTEXITCODE
    }
    catch { $argExit = 999 }

    if ($argExit -ne 0) {
        Write-Pass "$label → non-zero exit ($argExit)"
        $script:Passed++
        $st = 'PASS'
    }
    else {
        Write-Fail "$label → exit 0 (expected non-zero for missing args)"
        $script:Failed++
        $st = 'FAIL'
    }
    [void]$script:Results.Add([PSCustomObject]@{ Test = $label; Command = "uiao $cmd"; ExitCode = $argExit; Status = $st })
}

# ─── Summary ──────────────────────────────────────────────────────────
Write-Section "Summary"

$total = $script:Passed + $script:Failed + $script:Skipped
Write-Host ""
Write-Host "  Total : $total" -ForegroundColor White
Write-Host "  Passed: $($script:Passed)" -ForegroundColor Green
Write-Host "  Failed: $($script:Failed)" -ForegroundColor $(if ($script:Failed -gt 0) { 'Red' } else { 'Green' })
Write-Host "  Skipped: $($script:Skipped)" -ForegroundColor $(if ($script:Skipped -gt 0) { 'Yellow' } else { 'Green' })
Write-Host ""

# Dump CSV
$csvPath = Join-Path $PSScriptRoot "uiao-cli-test-results.csv"
$script:Results | Export-Csv -Path $csvPath -NoTypeInformation -Encoding UTF8
Write-Host "  Results written to: $csvPath" -ForegroundColor DarkGray

if ($script:Failed -gt 0) {
    Write-Host ""
    Write-Host "  OVERALL: FAIL" -ForegroundColor Red
    Write-Host ""
    $script:Results | Where-Object Status -eq 'FAIL' | ForEach-Object {
        Write-Host "    ✗ $($_.Test)  →  exit $($_.ExitCode)" -ForegroundColor Red
    }
    Write-Host ""
    exit 1
}
else {
    Write-Host ""
    Write-Host "  OVERALL: PASS" -ForegroundColor Green
    Write-Host ""
    exit 0
}
