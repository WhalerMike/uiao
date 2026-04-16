# Split-UIAODocs.ps1
# Run from your uiao-core repo root after downloading the Word doc
# Requires: pip install python-docx (or use pandoc)

param(
    [string]$DocxPath = ".\UIAO-Core SCuBA Documentation Suite.docx",
    [string]$RepoRoot = "."
)

# Convert DOCX to plain text using pandoc (recommended)
# Install pandoc: winget install JohnMacFarlane.Pandoc
$tempMd = Join-Path $env:TEMP "uiao-docs-combined.md"
pandoc $DocxPath -t markdown --wrap=none -o $tempMd

$content = Get-Content $tempMd -Raw

# Define file markers and output paths
$files = @(
    @{ Marker = "FILE: docs/MASTER_TEST_PLAN.md";       Output = "docs/MASTER_TEST_PLAN.md" },
    @{ Marker = "FILE: docs/scuba-architecture-guide.md"; Output = "docs/scuba-architecture-guide.md" },
    @{ Marker = "FILE: docs/scuba-operator-runbook.md";   Output = "docs/scuba-operator-runbook.md" },
    @{ Marker = "FILE: docs/api-reference.md";            Output = "docs/api-reference.md" },
    @{ Marker = "FILE: docs/configuration-reference.md";  Output = "docs/configuration-reference.md" },
    @{ Marker = "FILE: docs/adapter-development-guide.md"; Output = "docs/adapter-development-guide.md" },
    @{ Marker = "FILE: docs/deployment-guide.md";         Output = "docs/deployment-guide.md" },
    @{ Marker = "FILE: docs/compliance-mapping-matrix.md"; Output = "docs/compliance-mapping-matrix.md" },
    @{ Marker = "FILE: CHANGELOG.md";                     Output = "CHANGELOG.md" }
)

# Ensure docs/ directory exists
$docsDir = Join-Path $RepoRoot "docs"
if (-not (Test-Path $docsDir)) { New-Item -ItemType Directory -Path $docsDir -Force | Out-Null }

# Split on FILE: markers
for ($i = 0; $i -lt $files.Count; $i++) {
    $startMarker = $files[$i].Marker
    $startIdx = $content.IndexOf($startMarker)

    if ($startIdx -eq -1) {
        Write-Warning "Marker not found: $startMarker"
        continue
    }

    # Find the end (next FILE: marker or end of content)
    if ($i -lt $files.Count - 1) {
        $endMarker = $files[$i + 1].Marker
        $endIdx = $content.IndexOf($endMarker)
        if ($endIdx -eq -1) { $endIdx = $content.Length }
    } else {
        $endIdx = $content.Length
    }

    # Extract section, remove the "FILE: ..." header line itself
    $section = $content.Substring($startIdx, $endIdx - $startIdx)
    $section = $section -replace "^.*?FILE:.*?\n", ""
    $section = $section.Trim()

    # Write to target path
    $outPath = Join-Path $RepoRoot $files[$i].Output
    $outDir = Split-Path $outPath -Parent
    if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Path $outDir -Force | Out-Null }

    Set-Content -Path $outPath -Value $section -Encoding UTF8
    Write-Host "Wrote: $($files[$i].Output) ($([math]::Round((Get-Item $outPath).Length / 1KB, 1)) KB)" -ForegroundColor Green
}

# Cleanup
Remove-Item $tempMd -ErrorAction SilentlyContinue
Write-Host "`nDone! 9 files written. Ready to commit:" -ForegroundColor Cyan
Write-Host "  git add docs/ CHANGELOG.md"
Write-Host '  git commit -m "docs: master test plan, architecture guide, operator runbook, API/config/adapter/deployment refs, compliance matrix, changelog"'
