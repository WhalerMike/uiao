<#
.SYNOPSIS
    Audit and inspect the OrgPath narrative image manifest.

.DESCRIPTION
    Reads image-prompts.manifest.yaml under
    docs/customer-documents/orgpath-narrative/ and reconciles it against
    on-disk state: PNG files, .png.json sidecars, and the SHA256 fingerprints
    recorded at generation time.

    Three modes:

      -Audit (default)  Compare every manifest image against the on-disk
                        sidecar and the current .qmd fig-alt. Flag any of:
                            MissingPNG          PNG referenced by manifest is gone
                            MissingSidecar      .png.json next to PNG is gone
                            ChapterNotFound     manifest references a .qmd that no
                                                  longer exists
                            FigAltNotFound      .qmd has no figure block matching the
                                                  manifest's fig id
                            ManifestStale       current .qmd fig-alt differs from the
                                                  prompt text stored in the manifest
                                                  for this image — rebuild the
                                                  manifest with the helper script
                            SidecarMismatch     sidecar.document does not point at
                                                  the chapter file the manifest expects

                        NOT CHECKED:
                          - Raw PNG sha256: the generator embeds tEXt chunks AFTER
                            recording sha256, so on-disk bytes never match the
                            sidecar value. This is structural, not drift.
                          - PNG-vs-prompt freshness: the generator hashes the
                            original [IMAGE-NN: ...] placeholder body, which is
                            replaced when fig-alt is authored. The two texts are
                            not byte-equal, so prompt_sha256 in the sidecar cannot
                            be reproduced from the current .qmd. Treat the sidecar
                            generated_at timestamp as the freshness proxy and
                            regenerate manually if the .qmd fig-alt has been
                            edited since.

      -List             Print a one-line summary per chapter (series-order,
                        title, image count).

      -Show <id|slug>   Print full detail for a single image by fig id
                        (e.g. fig-05-orgpath-and-intune-diagram-01) or by
                        sidecar slug (e.g. left-to-right-flow-diagram-showi).

    The manifest is the source of truth for what SHOULD exist; the on-disk
    sidecars are the source of truth for what WAS generated. Drift between
    them is what this script surfaces.

    Does NOT regenerate images. To force regeneration after this script flags
    PromptDrift, delete the affected .png.json sidecar(s) and run
    `python scripts/generate_images.py` from the repo root — the generator
    cache key is sidecar prompt_sha256, so removing it forces a fresh call
    to Gemini Nano Banana.

.PARAMETER Audit
    Default mode. Compare manifest vs on-disk; report drift.

.PARAMETER List
    Print one-line summary per chapter; no per-image audit.

.PARAMETER Show
    Image id or slug to inspect in detail. Exact match on either field.

.PARAMETER ManifestPath
    Override the manifest path. Defaults to
    docs/customer-documents/orgpath-narrative/image-prompts.manifest.yaml
    relative to repo root.

.PARAMETER SectionRoot
    Override the section root. Defaults to
    docs/customer-documents/orgpath-narrative relative to repo root.

.EXAMPLE
    pwsh scripts/Invoke-OrgPathImageAudit.ps1
    Run a full audit against every image in the manifest.

.EXAMPLE
    pwsh scripts/Invoke-OrgPathImageAudit.ps1 -List
    One-line summary per chapter.

.EXAMPLE
    pwsh scripts/Invoke-OrgPathImageAudit.ps1 -Show fig-05-orgpath-and-intune-diagram-01
    Detail view for a single image.

.NOTES
    Requires the powershell-yaml module. If missing, install with:
        Install-Module powershell-yaml -Scope CurrentUser

    Exit codes:
        0   no drift
        1   drift detected (audit mode) or image not found (show mode)
        2   manifest missing, module missing, or other precondition failure
#>
[CmdletBinding(DefaultParameterSetName = 'Audit')]
param(
    [Parameter(ParameterSetName = 'Audit')]
    [switch]$Audit,

    [Parameter(ParameterSetName = 'List')]
    [switch]$List,

    [Parameter(ParameterSetName = 'Show', Mandatory = $true)]
    [string]$Show,

    [string]$ManifestPath,
    [string]$SectionRoot
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 3.0

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
if (-not $SectionRoot) {
    $SectionRoot = Join-Path $repoRoot 'docs\customer-documents\orgpath-narrative'
}
if (-not $ManifestPath) {
    $ManifestPath = Join-Path $SectionRoot 'image-prompts.manifest.yaml'
}

if (-not (Test-Path $ManifestPath)) {
    Write-Error "Manifest not found: $ManifestPath"
    exit 2
}

if (-not (Get-Module -ListAvailable -Name powershell-yaml)) {
    Write-Error @'
powershell-yaml module not installed. Install with:
    Install-Module powershell-yaml -Scope CurrentUser
'@
    exit 2
}
Import-Module powershell-yaml -ErrorAction Stop

$rawYaml = Get-Content -Path $ManifestPath -Raw -Encoding UTF8
$manifest = ConvertFrom-Yaml -Yaml $rawYaml

# Flatten the chapters[].images[] tree into a single audit list with parent context.
$entries = foreach ($chapter in $manifest['chapters']) {
    foreach ($image in $chapter['images']) {
        [pscustomobject]@{
            ChapterFile   = $chapter['file']
            SeriesOrder   = $chapter['series-order']
            ChapterTitle  = $chapter['title']
            Id            = $image['id']
            Slug          = $image['slug']
            PlaceholderId = $image['placeholder-id']
            File          = $image['file']
            Sidecar       = $image['sidecar']
            Caption       = $image['caption']
            ManifestSha256       = $image['sha256']
            ManifestPromptSha256 = $image['prompt-sha256']
            Prompt        = $image['prompt']
            GeneratedAt   = $image['generated-at']
        }
    }
}

function Get-SidecarField {
    param([string]$Path)
    if (-not (Test-Path $Path)) { return $null }
    Get-Content -Path $Path -Raw -Encoding UTF8 | ConvertFrom-Json
}

# Hash a string using the same rule the generator's sha256_text uses:
# normalize CRLF/CR to LF first so Windows vs Unix checkouts agree.
function Get-PromptSha256 {
    param([string]$Text)
    $normalized = $Text -replace "`r`n", "`n" -replace "`r", "`n"
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($normalized)
    $sha   = [System.Security.Cryptography.SHA256]::Create()
    try {
        $hash = $sha.ComputeHash($bytes)
        return ([System.BitConverter]::ToString($hash) -replace '-', '').ToLower()
    } finally {
        $sha.Dispose()
    }
}

# Extract a single figure's fig-alt body from a chapter .qmd, matching by
# fig id (the {#fig-...} cross-reference identifier). Returns the unescaped
# fig-alt text, or $null if no match. Pattern mirrors the manifest builder:
# tolerant of literal { } inside the alt text (e.g. ORG-NODE-{id}) by
# anchoring the closing brace on width="...".
function Get-FigAltByIdFromQmd {
    param(
        [string]$QmdPath,
        [string]$FigId
    )
    if (-not (Test-Path $QmdPath)) { return $null }
    $text = Get-Content -Path $QmdPath -Raw -Encoding UTF8

    $escId = [regex]::Escape($FigId)
    $pattern = '!\[(?<caption>[^\]]*)\]\((?<src>images/[^)]+\.png)\)\{(?<attrs>.*?width="[^"]+"\s*)\}'
    $rxOptions = [System.Text.RegularExpressions.RegexOptions]::Singleline
    foreach ($m in [regex]::Matches($text, $pattern, $rxOptions)) {
        $attrs = $m.Groups['attrs'].Value
        if ($attrs -notmatch ('#' + $escId + '\b')) { continue }
        $altMatch = [regex]::Match(
            $attrs,
            'fig-alt="(?<alt>(?:[^"\\]|\\.)*)"',
            $rxOptions
        )
        if ($altMatch.Success) {
            # Unescape \" → " inside the captured alt text.
            return $altMatch.Groups['alt'].Value -replace '\\"', '"'
        }
    }
    return $null
}

switch ($PSCmdlet.ParameterSetName) {

    'List' {
        Write-Host "OrgPath narrative — manifest summary" -ForegroundColor Cyan
        Write-Host "Section: $SectionRoot"
        Write-Host ("Total chapters: {0}    Total images: {1}" -f $manifest['chapters'].Count, $entries.Count)
        Write-Host ""
        $manifest['chapters'] | ForEach-Object {
            $imgCount = $_.images.Count
            $status   = $_.status
            $order    = $_.'series-order'
            $title    = $_.title
            "{0,-3}  {1,-10}  {2,2} img   {3}" -f $order, $status, $imgCount, $title
        }
        exit 0
    }

    'Show' {
        $hit = $entries | Where-Object { $_.Id -eq $Show -or $_.Slug -eq $Show } | Select-Object -First 1
        if (-not $hit) {
            Write-Error "No image matched id or slug: $Show"
            exit 1
        }
        Write-Host "Image: $($hit.Id)" -ForegroundColor Cyan
        Write-Host "Chapter:        $($hit.SeriesOrder) — $($hit.ChapterTitle)"
        Write-Host "File:           $($hit.File)"
        Write-Host "Sidecar:        $($hit.Sidecar)"
        Write-Host "Slug:           $($hit.Slug)"
        Write-Host "Placeholder:    $($hit.PlaceholderId)"
        Write-Host "Caption:        $($hit.Caption)"
        Write-Host "Generated:      $($hit.GeneratedAt)"
        Write-Host "sha256:         $($hit.ManifestSha256)"
        Write-Host "prompt-sha256:  $($hit.ManifestPromptSha256)"
        Write-Host ""
        Write-Host "Prompt:" -ForegroundColor Cyan
        Write-Host $hit.Prompt
        exit 0
    }

    default {
        # Audit mode (also the default when no switch is given).
        $results = foreach ($e in $entries) {
            $pngPath     = Join-Path $SectionRoot $e.File
            $sidecarPath = Join-Path $SectionRoot $e.Sidecar
            $qmdPath     = Join-Path $SectionRoot $e.ChapterFile
            $issues      = New-Object System.Collections.Generic.List[string]

            if (-not (Test-Path $pngPath))     { $issues.Add('MissingPNG') }
            if (-not (Test-Path $sidecarPath)) { $issues.Add('MissingSidecar') }
            if (-not (Test-Path $qmdPath))     { $issues.Add('ChapterNotFound') }

            if ($issues.Count -eq 0) {
                $side       = Get-SidecarField -Path $sidecarPath
                $currentAlt = Get-FigAltByIdFromQmd -QmdPath $qmdPath -FigId $e.Id
                if (-not $currentAlt) {
                    $issues.Add('FigAltNotFound')
                } else {
                    # Normalize both manifest-stored prompt and current fig-alt for
                    # line-ending differences before comparing.
                    $manifestPrompt = ($e.Prompt -replace "`r`n", "`n" -replace "`r", "`n").TrimEnd("`n")
                    $currentNorm    = ($currentAlt -replace "`r`n", "`n" -replace "`r", "`n").TrimEnd("`n")
                    if ($manifestPrompt -ne $currentNorm) { $issues.Add('ManifestStale') }
                }
                # Sidecar back-reference: should point at the chapter the manifest expects.
                if ($side.PSObject.Properties.Name -contains 'document') {
                    $expected = ($e.ChapterFile -replace '\\', '/')
                    $actual   = ($side.document -replace '\\', '/')
                    if ($actual -notmatch ([regex]::Escape($expected) + '$')) {
                        $issues.Add('SidecarMismatch')
                    }
                }
            }

            [pscustomobject]@{
                Chapter = $e.SeriesOrder
                Id      = $e.Id
                Status  = if ($issues.Count -eq 0) { 'OK' } else { ($issues -join ',') }
                Slug    = $e.Slug
            }
        }

        $results    = @($results)
        $okCount    = @($results | Where-Object Status -eq 'OK').Count
        $driftCount = $results.Count - $okCount

        Write-Host "OrgPath narrative — image audit" -ForegroundColor Cyan
        Write-Host "Manifest: $ManifestPath"
        Write-Host ""
        $results | Format-Table -AutoSize | Out-String | Write-Host
        Write-Host ("OK: {0}   Drift: {1}   Total: {2}" -f $okCount, $driftCount, $results.Count) -ForegroundColor $(if ($driftCount -eq 0) { 'Green' } else { 'Yellow' })

        if ($driftCount -gt 0) { exit 1 } else { exit 0 }
    }
}
