param(
    [string]$ModelPath = "C:\Users\whale\git\uiao\canon\phase2\UIAO_Phase2_TSA.psd1",
    [string]$OutputRoot = "C:\Users\whale\git\uiao\phase2"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $ModelPath)) {
    throw "Model file not found: $ModelPath"
}

$model = Import-PowerShellDataFile -LiteralPath $ModelPath

if (-not (Test-Path -LiteralPath $OutputRoot)) {
    New-Item -ItemType Directory -Path $OutputRoot -Force | Out-Null
}

# -----------------------------
# Write Overview File
# -----------------------------
$overview = Join-Path $OutputRoot "UIAO_P2_TSA_Overview.md"
$lines = @()

$lines += "# UIAO Phase 2 Target State Architecture"
$lines += ""
$lines += "Id: $($model.Metadata.Id)"
$lines += "Version: $($model.Metadata.Version)"
$lines += "Owner: $($model.Metadata.Owner)"
$lines += "Phase: $($model.Metadata.Phase)"
$lines += ""
$lines += "## Description"
$lines += $model.Metadata.Description
$lines += ""
$lines += "## Source Specifications"
foreach ($src in $model.Metadata.SourceSpecs) { $lines += "- $src" }
$lines += ""

$lines += "## Planes"
foreach ($plane in $model.Planes) {
    $lines += "### $($plane.Name) (`$($plane.Id)`)"
    $lines += $plane.Description
    $lines += ""
}

$lines += "## Lifecycles"
foreach ($lc in $model.Lifecycles) {
    $lines += "### $($lc.Name) (`$($lc.Id)`)"
    $lines += $lc.Description
    $lines += ""
    if ($lc.Drivers) {
        $lines += "**Drivers**"
        foreach ($d in $lc.Drivers) { $lines += "- $d" }
        $lines += ""
    }
    if ($lc.KeyFlows) {
        $lines += "**Key Flows**"
        foreach ($f in $lc.KeyFlows) { $lines += "- $f" }
        $lines += ""
    }
}

$lines += "## Domains"
foreach ($dom in $model.Domains) {
    $plane = $model.Planes | Where-Object { $_.Id -eq $dom.PlaneId }
    $planeName = if ($plane) { $plane.Name } else { $dom.PlaneId }

    $lines += "### $($dom.Name) (`$($dom.Id)`)"
    $lines += "**Plane:** $planeName"
    $lines += $dom.Description
    $lines += ""

    $lines += "**Source State**"
    foreach ($s in $dom.SourceState) { $lines += "- $s" }
    $lines += ""

    $lines += "**Target State**"
    foreach ($t in $dom.TargetState) { $lines += "- $t" }
    $lines += ""

    $lines += "**Key Transformations**"
    foreach ($k in $dom.KeyTransformations) { $lines += "- $k" }
    $lines += ""

    $lines += "**Dependencies**"
    foreach ($dep in $dom.Dependencies) { $lines += "- $dep" }
    $lines += ""
}

$lines | Set-Content -LiteralPath $overview -Encoding ASCII -Force

# -----------------------------
# Write Per-Domain Files
# -----------------------------
foreach ($dom in $model.Domains) {
    $fileName = "UIAO_P2_DOM_{0}.md" -f $dom.Id
    $path = Join-Path $OutputRoot $fileName

    $d = @()
    $d += "# $($dom.Name)"
    $d += "Id: $($dom.Id)"
    $d += "PlaneId: $($dom.PlaneId)"
    $d += ""
    $d += "## Description"
    $d += $dom.Description
    $d += ""
    $d += "## Source State"
    foreach ($s in $dom.SourceState) { $d += "- $s" }
    $d += ""
    $d += "## Target State"
    foreach ($t in $dom.TargetState) { $d += "- $t" }
    $d += ""
    $d += "## Key Transformations"
    foreach ($k in $dom.KeyTransformations) { $d += "- $k" }
    $d += ""
    $d += "## Dependencies"
    foreach ($dep in $dom.Dependencies) { $d += "- $dep" }
    $d += ""
    $d += "## Detailed Design"
    $d += "_To be elaborated in Phase 2 design sessions._"
    $d += ""

    $d | Set-Content -LiteralPath $path -Encoding ASCII -Force
}

Write-Host "UIAO Phase 2 TSA files written to $OutputRoot" -ForegroundColor Green
