<#
.SYNOPSIS
    Verify the TED Talk project and (re)scaffold the slides/ folder with one fully
    populated markdown file per slide, then print a pre-production checklist.

.DESCRIPTION
    Idempotent. Existing slide files are NOT overwritten (so hand-edits survive); use
    -Force to regenerate them from the canonical definitions below. Run from anywhere;
    paths resolve relative to this script's location.

    Hero images are canonical under assets\real-images\ (organized 2026-06-04).

.PARAMETER Force
    Overwrite existing slide markdown files with the canonical content.

.EXAMPLE
    .\Build-TedTalkSlides.ps1
.EXAMPLE
    .\Build-TedTalkSlides.ps1 -Force
#>
[CmdletBinding()]
param(
    [switch]$Force
)

$ErrorActionPreference = 'Stop'
$Root = $PSScriptRoot
if ([string]::IsNullOrWhiteSpace($Root)) { $Root = (Get-Location).Path }

function Write-Head($text) { Write-Host "`n=== $text ===" -ForegroundColor Cyan }
function Test-Item($relPath) {
    $full = Join-Path $Root $relPath
    if (Test-Path -LiteralPath $full) {
        Write-Host ("  [OK]   {0}" -f $relPath) -ForegroundColor Green
        return $true
    } else {
        Write-Host ("  [MISS] {0}" -f $relPath) -ForegroundColor Red
        return $false
    }
}

# --- 1. Verify key files -----------------------------------------------------
Write-Head "1. Verifying key project files"
$keyFiles = @(
    'README.md',
    'README-FINAL.md',
    'IMAGE-INVENTORY.md',
    'script\ted-talk-full-script.md',
    'script\speaker-notes.md',
    'video\FINAL-HEYGEN-SYNTHESIA-PROMPT.md',
    'video\ted-talk-slide-deck-outline.md',
    'video\image-placement-guide.md',
    'diagrams\diagram-generation-prompts.md'
)
$missing = 0
foreach ($f in $keyFiles) { if (-not (Test-Item $f)) { $missing++ } }

# --- 2. Verify recommended (clean, on-message) images ------------------------
Write-Head "2. Verifying recommended images"
$heroImages = @(
    'assets\real-images\hero-01-mainframe-room.jpg',
    'assets\real-images\hero-02-clientserver-map.jpg',
    'assets\real-images\hero-03-security-broken-sessions.jpg',
    'assets\real-images\hero-04-future-sdwan-ssot.jpg',
    'assets\cloud-chaos\cloud-collision-chaos-3d.jpg',
    'assets\cloud-chaos\cloud-collision-chaos-map.jpg'
)
$imgMissing = 0
foreach ($i in $heroImages) { if (-not (Test-Item $i)) { $imgMissing++ } }

# --- 3. (Re)scaffold the slides\ folder --------------------------------------
Write-Head "3. Scaffolding slides\ folder"
$slidesDir = Join-Path $Root 'slides'
if (-not (Test-Path -LiteralPath $slidesDir)) { New-Item -ItemType Directory -Path $slidesDir -Force | Out-Null }

# Canonical per-slide definitions (image paths are repo-relative).
$slides = @(
    @{ n='01'; slug='title';                 title='Title';                                      time='0:00-0:15';   img='(TED background; optional faded assets\real-images\hero-04-future-sdwan-ssot.jpg)'; head='The Hidden Cost of Progress'; sup='How We Lost Truth in Our Systems - And How to Get It Back'; pt='Title + subtitle + your name/agency. Hold a beat of silence before line one.' },
    @{ n='02'; slug='opening-hook';          title='Opening Hook';                               time='0:15-1:00';   img='assets\real-images\hero-01-mainframe-room.jpg'; head='What if we KNEW the data was true?'; sup='Not hoped. Knew.'; pt='"Imagine a world where we do not just hope the data is correct - we know it is." Land on KNOW.' },
    @{ n='03'; slug='mainframe-era';          title='Mainframe Era (1940s-1990s)';                time='1:00-2:00';   img='assets\real-images\hero-01-mainframe-room.jpg'; head='One Source. One Truth.'; sup='1940s-1990s: one central computer, one definitive answer.'; pt='Dumb green-screen terminals. The system KNEW who was alive, eligible, and true.' },
    @{ n='04'; slug='act1-decentralization';  title='Act 1 - The Great Decentralization';         time='2:00-6:00';   img='assets\real-images\hero-02-clientserver-map.jpg'; head='The Great Decentralization'; sup='12 regions. 12 versions of reality. SSOT lost.'; pt='Client-server liberates the edge - but different schemas, rules, and interpretations split the truth.' },
    @{ n='05'; slug='act2-security';          title='Act 2 - When Security Ate the Architecture'; time='6:00-10:00';  img='assets\real-images\hero-03-security-broken-sessions.jpg'; head='When Security Ate the Architecture'; sup='Defense-in-depth broke the session. Latency is physics.'; pt='F5 proxies, IPS, stacked firewalls, NAT. Kerberos failed; provenance disappeared.' },
    @{ n='06'; slug='act3-cloud-collision';   title='Act 3 - The Cloud Collision';                time='10:00-13:00'; img='assets\cloud-chaos\cloud-collision-chaos-3d.jpg'; head='The Cloud Collision'; sup='Cloud compute, early-2000s identity. Variation became a hiding place.'; pt='M365/Azure/AWS arrive; regional AD forest and session assumptions stay rooted in 2003.' },
    @{ n='07'; slug='breaking-point';         title='The Breaking Point (2025-2026)';             time='13:00-14:00'; img='assets\cloud-chaos\cloud-collision-chaos-map.jpg'; head="We Don't Know What's True Anymore"; sup='Fraud, duplicate and deceased payments, eroded trust.'; pt='Drop to your most serious register. Long pause after the line.' },
    @{ n='08'; slug='act4-way-forward';       title='Act 4 - The Way Forward';                    time='14:00-16:00'; img='assets\real-images\hero-04-future-sdwan-ssot.jpg'; head='We Must Rebuild the Foundation'; sup='Not patch. Rebuild.'; pt='Shift energy from diagnosis to hope. "We must rebuild" is a highlight phrase.' },
    @{ n='09'; slug='four-pillars';           title='The Four Pillars';                           time='16:00-18:30'; img='assets\future-state\future-state-sdwan-architecture.png'; head='The Four Pillars'; sup='SSOT - Application-Aware Networking - Token Identity + OrgPath - SD-WAN Mesh'; pt='Reveal one pillar per click. Emphasize OrgPath and Application-Aware.' },
    @{ n='10'; slug='new-architecture';       title='The New Architecture';                       time='18:30-19:30'; img='assets\real-images\hero-04-future-sdwan-ssot.jpg'; head='Restoring the Soul of Our Systems'; sup='OrgPath governance over an intelligent mesh.'; pt='"This is not just technical modernization - it is the ability to KNOW what is true."' },
    @{ n='11'; slug='call-to-action';         title='Call to Action';                             time='19:30-20:30'; img='assets\real-images\hero-04-future-sdwan-ssot.jpg (faded)'; head="Systems That Don't Just Act - But KNOW"; sup='We have the responsibility. We have the tools.'; pt='Callback to the opening KNOW. Slow and deliberate.' },
    @{ n='12'; slug='thank-you';              title='Thank You + Q&A';                            time='20:30-end';   img='(Title background)'; head='Thank You'; sup='github.com/WhalerMike/uiao  -  Q&A'; pt='Hold eye contact. Open the floor.' }
)

$created = 0; $skipped = 0; $overwritten = 0
foreach ($s in $slides) {
    $fileName = "{0}-{1}.md" -f $s.n, $s.slug
    $filePath = Join-Path $slidesDir $fileName
    $exists = Test-Path -LiteralPath $filePath
    if ($exists -and -not $Force) {
        Write-Host ("  [SKIP] {0} (exists; use -Force to regenerate)" -f $fileName) -ForegroundColor DarkGray
        $skipped++
        continue
    }
    $content = @"
# Slide $($s.n): $($s.title)

- **Timing:** $($s.time)
- **Primary visual:** $($s.img)

## On-screen text
- **Headline:** $($s.head)
- **Supporting:** $($s.sup)

## Talking point
$($s.pt)

## Production notes
- Pause 4-6s after the Act for the visual to land.
- See ..\script\speaker-notes.md for full narration cues.
"@
    Set-Content -LiteralPath $filePath -Value $content -Encoding UTF8
    if ($exists) {
        Write-Host ("  [OVR]  {0}" -f $fileName) -ForegroundColor Yellow
        $overwritten++
    } else {
        Write-Host ("  [NEW]  {0}" -f $fileName) -ForegroundColor Green
        $created++
    }
}

# --- 4. Final checklist ------------------------------------------------------
Write-Head "4. Pre-production checklist"
Write-Host ("  Key files present  : {0}/{1}" -f ($keyFiles.Count - $missing), $keyFiles.Count)
Write-Host ("  Hero images present: {0}/{1}" -f ($heroImages.Count - $imgMissing), $heroImages.Count)
Write-Host ("  Slide templates    : {0} new, {1} overwritten, {2} skipped" -f $created, $overwritten, $skipped)
Write-Host ""
Write-Host "  [ ] Lock script         -> script\ted-talk-full-script.md"
Write-Host "  [ ] Review speaker notes -> script\speaker-notes.md"
Write-Host "  [ ] Avoid branded imgs   -> see IMAGE-INVENTORY.md (Alamy/Juniper/EdgeDC/Fortinet)"
Write-Host "  [ ] Avatar + style       -> video\FINAL-HEYGEN-SYNTHESIA-PROMPT.md"
Write-Host "  [ ] Build deck (12)      -> slides\*.md + visuals per slide"
Write-Host "  [ ] 16:9 HD, timeline bar 1940s->2026, ambient music"
Write-Host "  [ ] Render, check pacing (18-22 min), export"
Write-Host ""
if ($missing -eq 0 -and $imgMissing -eq 0) {
    Write-Host "  STATUS: READY FOR VIDEO PRODUCTION" -ForegroundColor Green
} else {
    Write-Host "  STATUS: RESOLVE MISSING ITEMS ABOVE BEFORE PRODUCTION" -ForegroundColor Yellow
}
