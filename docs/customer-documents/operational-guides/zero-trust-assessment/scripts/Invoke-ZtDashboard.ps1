<#
.SYNOPSIS
    Turn a Microsoft Zero Trust Assessment report into an analytics dashboard,
    Excel workbook, and Power BI-ready dataset.

.DESCRIPTION
    Customer-facing wrapper over the UIAO toolkit's `uiao zta dashboard` command.
    Point it at the `ZeroTrustAssessmentReport.html` the assessment opens by
    default (or a `.json` export) and it produces, in the output directory:

      * <tenant>-<date>-dashboard.xlsx  — Dashboard (charts + heatmap), Findings
        (severity-scored, remediation-prioritized P1-P4), By Pillar, All Tests,
        and a Methodology sheet
      * charts\*.png                    — the individual charts
      * <tenant>-<date>-powerbi.csv     — one row per test, every derived column
        (import straight into Power BI)

    The report contains sensitive tenant configuration. Treat all output as
    Controlled data: keep it inside your authorization boundary and do not
    publish raw findings. Remediation guidance is advisory — apply changes only
    through your normal change-control process.

.PARAMETER ReportPath
    Path to a ZeroTrustAssessmentReport .html (or .json export).

.PARAMETER OutputDirectory
    Where to write the dashboard, charts, and Power BI CSV. Default: .\zt-dashboard

.EXAMPLE
    .\Invoke-ZtDashboard.ps1 -ReportPath .\ZeroTrustReport\ZeroTrustAssessmentReport.html

.EXAMPLE
    .\Invoke-ZtDashboard.ps1 -ReportPath .\report.json -OutputDirectory .\out

.NOTES
    Prerequisites: PowerShell 7+, Python 3.11+, and the UIAO toolkit
    (`pip install uiao` from the repository). See the accompanying guide.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string] $ReportPath,

    [string] $OutputDirectory = "./zt-dashboard"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $ReportPath)) {
    throw "Report not found: $ReportPath"
}

$cliArgs = @("zta", "dashboard", "--input", $ReportPath, "--out-dir", $OutputDirectory)

# Prefer the installed `uiao` console script; fall back to the module entry point.
if (Get-Command uiao -ErrorAction SilentlyContinue) {
    & uiao @cliArgs
}
elseif (Get-Command python -ErrorAction SilentlyContinue) {
    Write-Verbose "uiao console script not found; using 'python -m uiao.cli.app'."
    & python -m uiao.cli.app @cliArgs
}
else {
    throw "Neither 'uiao' nor 'python' was found on PATH. Install the UIAO toolkit (pip install uiao) first."
}

exit $LASTEXITCODE
