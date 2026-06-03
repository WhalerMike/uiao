<#
.SYNOPSIS
    Digest a Microsoft Zero Trust Assessment report into human-facing artefacts.

.DESCRIPTION
    Thin PowerShell wrapper over the `uiao zta digest` CLI so analysts who run
    the assessment in PowerShell 7 can produce the digest without invoking
    Python directly. Accepts the .html report the tool opens by default (or a
    .json export) and writes an executive summary, full Markdown digest, Excel
    workbook, slim annotated HTML, and a worklist CSV.

    Findings are Controlled tenant data — keep the output in-boundary and do
    not publish raw results.

.PARAMETER ReportPath
    Path to a ZeroTrustAssessmentReport .html or .json file.

.PARAMETER OutputDirectory
    Directory to write digest artefacts into. Default: ./zt-digest

.PARAMETER Format
    One or more of: exec, md, xlsx, html, csv, all. Default: all

.PARAMETER Risk
    Risk levels for the worklist: High, Medium, Low. Default: High

.EXAMPLE
    ./adapter-run-zta.ps1 -ReportPath .\ZeroTrustReport\ZeroTrustAssessmentReport.html

.EXAMPLE
    ./adapter-run-zta.ps1 -ReportPath report.json -OutputDirectory .\out -Format xlsx,csv -Risk High,Medium
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string] $ReportPath,

    [string] $OutputDirectory = "./zt-digest",

    [string[]] $Format = @("all"),

    [string[]] $Risk = @("High")
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $ReportPath)) {
    throw "Report not found: $ReportPath"
}

# Build the CLI argument list.
$cliArgs = @("zta", "digest", "--input", $ReportPath, "--out-dir", $OutputDirectory)
foreach ($f in $Format) { $cliArgs += @("--format", $f) }
foreach ($r in $Risk)   { $cliArgs += @("--risk",   $r) }

# Prefer the installed `uiao` console script; fall back to the module entry.
$uiao = Get-Command uiao -ErrorAction SilentlyContinue
if ($uiao) {
    & uiao @cliArgs
} else {
    Write-Verbose "uiao console script not found; falling back to 'python -m uiao.cli.app'."
    & python -m uiao.cli.app @cliArgs
}

exit $LASTEXITCODE
