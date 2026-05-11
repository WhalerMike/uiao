<#
.SYNOPSIS
  UIAO Fix 04 — Add comprehensive UIAO overview content to the landing page.

.DESCRIPTION
  Inserts four new sections into docs/index.qmd between the existing
  "Problem" section and the "Architecture" section:

    A. "What UIAO Actually Is" — narrative overview
    B. "The Hidden Governance Crisis" — the 11 AD dependency categories
    C. "The Modernization Arc" — Phase 0-5 visual progression
    D. "Read the Full Story" — card-style links to key documents

  Also adds the required CSS for the new sections to the <style> block.

.NOTES
  Run from the repo root after 03-fix-index-page-links.ps1.
  Idempotent — checks for sentinel markers before inserting.
#>

param(
    [switch]$DryRun,
    [string]$RepoRoot = (Get-Location).Path
)

$indexPath = Join-Path $RepoRoot "docs" "index.qmd"
if (-not (Test-Path $indexPath)) {
    Write-Error "docs/index.qmd not found at $indexPath. Run from the repo root."
    exit 1
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  UIAO Fix 04: Enrich Landing Page" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

if ($DryRun) {
    Write-Host "[DRY RUN] No files will be modified.`n" -ForegroundColor Yellow
}

$content = Get-Content -Path $indexPath -Raw -Encoding UTF8

# ── IDEMPOTENCY CHECK ──
if ($content -match 'uiao-overview-section') {
    Write-Host "  [SKIP] Landing page overview sections already present." -ForegroundColor DarkGray
    Write-Host "`nNo changes needed.`n" -ForegroundColor Green
    exit 0
}

# ── CSS ADDITIONS ──
# Insert before the closing </style> tag
$cssAdditions = @'

            /* Overview narrative */
            .uiao-landing .uiao-overview-section {
              max-width: 1200px; margin: 0 auto;
            }
            .uiao-landing .overview-narrative {
              max-width: 72ch; margin: 0 auto 2.5rem;
              color: var(--uiao-ink); font-size: 1.05rem; line-height: 1.75;
            }
            .uiao-landing .overview-narrative strong {
              color: var(--uiao-navy); font-weight: 600;
            }

            /* Dependency table */
            .uiao-landing .dep-table {
              width: 100%; border-collapse: collapse;
              margin: 2rem 0; font-size: .92rem;
            }
            .uiao-landing .dep-table th {
              font-family: 'IBM Plex Mono', monospace;
              font-size: .72rem; letter-spacing: .15em;
              text-transform: uppercase; color: var(--uiao-teal);
              text-align: left; padding: .9rem 1rem;
              border-bottom: 2px solid var(--uiao-teal);
              background: var(--uiao-paper-2);
            }
            .uiao-landing .dep-table td {
              padding: .75rem 1rem; border-bottom: 1px solid var(--uiao-line);
              color: var(--uiao-ink); vertical-align: top;
            }
            .uiao-landing .dep-table tr:hover td {
              background: var(--uiao-teal-bg);
            }
            .uiao-landing .dep-table .dep-id {
              font-family: 'IBM Plex Mono', monospace;
              font-size: .78rem; color: var(--uiao-teal); font-weight: 500;
            }

            /* Modernization arc */
            .uiao-landing .arc-grid {
              display: grid;
              grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
              gap: 1px; background: var(--uiao-line);
              border: 1px solid var(--uiao-line); border-radius: 6px;
              overflow: hidden; margin: 2rem 0;
            }
            .uiao-landing .arc-phase {
              background: white; padding: 1.5rem 1.2rem;
              text-align: center;
              transition: background .2s;
            }
            .uiao-landing .arc-phase:hover { background: var(--uiao-teal-bg); }
            .uiao-landing .arc-phase .phase-num {
              font-family: 'IBM Plex Mono', monospace;
              font-size: 1.6rem; font-weight: 500;
              color: var(--uiao-teal); margin-bottom: .4rem;
            }
            .uiao-landing .arc-phase .phase-name {
              font-family: 'DM Serif Display', serif; font-weight: 400;
              font-size: 1.05rem; color: var(--uiao-navy);
              margin-bottom: .4rem; line-height: 1.25;
            }
            .uiao-landing .arc-phase .phase-desc {
              font-size: .82rem; color: var(--uiao-muted); line-height: 1.45;
            }

            /* Document cards */
            .uiao-landing .doc-cards {
              display: grid;
              grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
              gap: 1.25rem; margin: 2rem 0;
            }
            .uiao-landing .doc-card {
              background: white; border: 1px solid var(--uiao-line);
              border-radius: 6px; padding: 1.6rem 1.4rem;
              text-decoration: none;
              transition: transform .15s, box-shadow .15s, border-color .15s;
            }
            .uiao-landing .doc-card:hover {
              transform: translateY(-2px);
              box-shadow: 0 14px 30px -18px rgba(13,27,46,0.18);
              border-color: var(--uiao-teal);
            }
            .uiao-landing .doc-card .doc-type {
              font-family: 'IBM Plex Mono', monospace;
              font-size: .68rem; letter-spacing: .18em;
              text-transform: uppercase; color: var(--uiao-amber);
              margin-bottom: .5rem; font-weight: 500;
            }
            .uiao-landing .doc-card .doc-title {
              font-family: 'DM Serif Display', serif; font-weight: 400;
              font-size: 1.15rem; color: var(--uiao-navy);
              margin-bottom: .5rem; line-height: 1.25;
            }
            .uiao-landing .doc-card .doc-desc {
              font-size: .85rem; color: var(--uiao-muted); line-height: 1.5;
            }
'@

# ── NEW HTML SECTIONS ──
$newSections = @'

<!-- ═══ SECTION A: What UIAO Actually Is ═══ -->
<section class="uiao-section" id="what-is-uiao">
  <div class="uiao-overview-section">
    <p class="section-label">Understanding UIAO</p>
    <h2 class="section-title">What UIAO actually is.</h2>
    <div class="overview-narrative">
      <p><strong>UIAO is not a dashboard, a monitoring tool, or a consulting engagement.</strong> It is a governance transformation platform — a universal substrate that unifies identity, addressing, and overlay network governance under a single architectural model. Every governance claim in UIAO traces to a cryptographically-anchored origin. No backfilling. No orphan assertions. No "we'll fix it in the audit."</p>
      <p>The thesis is straightforward: <strong>Active Directory was never just an identity store.</strong> For twenty-five years, AD silently governed DNS resolution, DHCP scoping, certificate issuance, network segmentation, application authentication, Group Policy enforcement, and service account lifecycles. When organizations migrate to Entra ID, they move the identity — but leave behind the governance surface that AD provided. The result is an invisible crisis: eleven categories of hidden dependencies that break silently across security, compliance, and operations.</p>
      <p>UIAO exists to solve that crisis. It maps every hidden AD dependency, builds a vendor-neutral adapter layer across heterogeneous infrastructure, and delivers continuous, evidence-driven governance — not quarterly attestation artifacts. The platform operates alongside existing infrastructure with no rip-and-replace requirement, enabling incremental, reversible, and auditable modernization at every step.</p>
    </div>
  </div>
</section>

<!-- ═══ SECTION B: The Hidden Governance Crisis ═══ -->
<section class="uiao-section problem" id="governance-crisis">
  <div class="uiao-overview-section">
    <p class="section-label">The Root Cause</p>
    <h2 class="section-title">Eleven hidden dependencies that break when AD goes away.</h2>
    <p class="section-body" style="margin-bottom:1.5rem;">Every enterprise migrating from Active Directory to Entra ID faces the same invisible problem. These eleven dependency categories silently govern your infrastructure — and none of them migrate automatically.</p>
    <table class="dep-table">
      <thead>
        <tr><th>#</th><th>Dependency Category</th><th>What Breaks</th></tr>
      </thead>
      <tbody>
        <tr><td class="dep-id">D-01</td><td>Group Policy Objects (GPO)</td><td>Security baselines, drive maps, login scripts, software deployment</td></tr>
        <tr><td class="dep-id">D-02</td><td>DNS / DHCP / IPAM</td><td>Name resolution, scope assignment, IP address management integrity</td></tr>
        <tr><td class="dep-id">D-03</td><td>Service Principal Names (SPN)</td><td>Kerberos delegation, SQL auth, IIS app pools, clustered services</td></tr>
        <tr><td class="dep-id">D-04</td><td>Certificate Authority / PKI</td><td>Auto-enrollment, certificate templates, OCSP, CRL distribution</td></tr>
        <tr><td class="dep-id">D-05</td><td>RADIUS / NPS</td><td>Network access control, 802.1X, VPN authentication</td></tr>
        <tr><td class="dep-id">D-06</td><td>LDAP-Bound Applications</td><td>Legacy apps using LDAP bind for authentication and authorization</td></tr>
        <tr><td class="dep-id">D-07</td><td>Service Accounts</td><td>Unmanaged credentials, password rotation, privilege escalation paths</td></tr>
        <tr><td class="dep-id">D-08</td><td>OU-Based Delegation</td><td>Administrative boundaries, RBAC models, help desk permissions</td></tr>
        <tr><td class="dep-id">D-09</td><td>Trust Relationships</td><td>Cross-forest authentication, resource access, SID history</td></tr>
        <tr><td class="dep-id">D-10</td><td>Schema Extensions</td><td>Custom attributes, third-party integrations, directory-dependent workflows</td></tr>
        <tr><td class="dep-id">D-11</td><td>Site Topology / Replication</td><td>DC placement, replication boundaries, subnet-to-site mappings</td></tr>
      </tbody>
    </table>
  </div>
</section>

<!-- ═══ SECTION C: The Modernization Arc ═══ -->
<section class="uiao-section" id="modernization-arc">
  <div class="uiao-overview-section">
    <p class="section-label">The Journey</p>
    <h2 class="section-title">Six phases from legacy to continuous governance.</h2>
    <p class="section-body" style="margin-bottom:1rem;">UIAO guides organizations through a structured modernization arc — each phase is incremental, reversible, and evidence-driven.</p>
    <div class="arc-grid">
      <div class="arc-phase">
        <div class="phase-num">00</div>
        <div class="phase-name">Discovery</div>
        <div class="phase-desc">Map every AD dependency, hidden governance surface, and implicit trust relationship</div>
      </div>
      <div class="arc-phase">
        <div class="phase-num">01</div>
        <div class="phase-name">Foundation</div>
        <div class="phase-desc">Stand up the platform substrate, adapter registry, and canon governance layer</div>
      </div>
      <div class="arc-phase">
        <div class="phase-num">02</div>
        <div class="phase-name">Ingestion</div>
        <div class="phase-desc">Connect legacy systems via FIMF adapters; ingest current-state telemetry</div>
      </div>
      <div class="arc-phase">
        <div class="phase-num">03</div>
        <div class="phase-name">Transformation</div>
        <div class="phase-desc">Apply identity, policy, and network transforms with drift detection at every step</div>
      </div>
      <div class="arc-phase">
        <div class="phase-num">04</div>
        <div class="phase-name">Validation</div>
        <div class="phase-desc">Run validation suites against target state; produce compliance evidence artifacts</div>
      </div>
      <div class="arc-phase">
        <div class="phase-num">05</div>
        <div class="phase-name">Governance</div>
        <div class="phase-desc">Continuous monitoring, drift remediation, and evidence-driven compliance posture</div>
      </div>
    </div>
  </div>
</section>

<!-- ═══ SECTION D: Read the Full Story ═══ -->
<section class="uiao-section problem" id="key-documents">
  <div class="uiao-overview-section">
    <p class="section-label">Deep Dive</p>
    <h2 class="section-title">Read the full story.</h2>
    <p class="section-body" style="margin-bottom:1rem;">These four documents tell the complete UIAO narrative — from the problem statement through the architecture and into operational governance.</p>
    <div class="doc-cards">
      <a class="doc-card" href="customer-documents/executive-briefs/uiao-executive-brief.html">
        <div class="doc-type">Executive Brief</div>
        <div class="doc-title">UIAO Executive Brief</div>
        <div class="doc-desc">The authoritative overview: what UIAO is, what problem it solves, and how the governance substrate works.</div>
      </a>
      <a class="doc-card" href="customer-documents/modernization/client-server-to-hybrid-cloud/00-introduction.html">
        <div class="doc-type">Architecture Series</div>
        <div class="doc-title">Client-Server to Hybrid-Cloud</div>
        <div class="doc-desc">The 11-chapter series covering the full transformation arc from legacy AD to cloud-native governance.</div>
      </a>
      <a class="doc-card" href="customer-documents/architecture-series/aodim-architecture.html">
        <div class="doc-type">Architecture</div>
        <div class="doc-title">AODIM Architecture</div>
        <div class="doc-desc">The Attribute-Oriented Dynamic Identity Model — UIAO's approach to identity as governance surface.</div>
      </a>
      <a class="doc-card" href="customer-documents/whitepapers/ad-to-entraid-migration-problem.html">
        <div class="doc-type">Whitepaper</div>
        <div class="doc-title">AD to Entra ID: The Migration Problem</div>
        <div class="doc-desc">Why every AD migration is a governance migration in disguise, and what organizations miss.</div>
      </a>
    </div>
  </div>
</section>
'@

# ── INJECT CSS ──
$styleCloseTag = "          </style>"
if ($content -match [regex]::Escape($styleCloseTag)) {
    $content = $content.Replace($styleCloseTag, "$cssAdditions`n$styleCloseTag")
    Write-Host "  [ADD] CSS for overview, dependency table, arc, and doc-card sections" -ForegroundColor Green
} else {
    Write-Host "  [WARN] Could not find </style> tag. CSS injection skipped." -ForegroundColor Yellow
}

# ── INJECT HTML ──
# Insert BEFORE the architecture section: <section id="architecture"
$archSectionTag = '<section id="architecture" class="uiao-section concepts">'
if ($content -match [regex]::Escape($archSectionTag)) {
    $content = $content.Replace($archSectionTag, "$newSections`n$archSectionTag")
    Write-Host "  [ADD] 4 new content sections (What Is UIAO, Governance Crisis, Modernization Arc, Key Documents)" -ForegroundColor Green
} else {
    Write-Host "  [WARN] Could not find architecture section anchor. HTML injection skipped." -ForegroundColor Yellow
}

# ── WRITE ──
if ($DryRun) {
    Write-Host "`nDRY RUN COMPLETE: Changes identified but not written." -ForegroundColor Yellow
} else {
    Set-Content -Path $indexPath -Value $content -Encoding UTF8 -NoNewline
    Write-Host "`nCOMPLETE: docs/index.qmd enriched with UIAO overview content." -ForegroundColor Green
}

Write-Host "`nVERIFICATION:" -ForegroundColor Cyan
Write-Host "  Run 'quarto preview docs/' and check the landing page for:" -ForegroundColor White
Write-Host "    - 'What UIAO Actually Is' section with 3-paragraph narrative" -ForegroundColor White
Write-Host "    - '11 Hidden Dependencies' table" -ForegroundColor White
Write-Host "    - 'Six Phases' modernization arc grid" -ForegroundColor White
Write-Host "    - 'Read the Full Story' document cards" -ForegroundColor White
Write-Host ""
Write-Host "Next step: Run 05-seed-image-prompts.ps1`n" -ForegroundColor Cyan
