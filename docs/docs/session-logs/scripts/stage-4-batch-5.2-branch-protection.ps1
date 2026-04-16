# =============================================================================
# stage-4-batch-5.2-branch-protection.ps1
# Phase D Stage 5, Batch 5.2 - branch protection on uiao-core/main
# -----------------------------------------------------------------------------
# Creates a GitHub Ruleset named 'uiao-core-main-protection' targeting the
# default branch (main) with:
#
#   - Require pull request before merging (0 approvals; self-merge OK)
#   - Require status checks: metadata-validator, drift-scan, dashboard-export
#   - Block force pushes (non_fast_forward)
#   - Block branch deletion
#   - Bypass actor: Repository Admin role (covers Mike)
#
# Deliberately NOT configured via API:
#   - github-actions[bot] bypass. The bypass-actor ID for the GH Actions
#     integration is fragile across setups. Final step is a 30-second web-UI
#     addition so the dashboard-export workflow keeps pushing directly to main.
#     The script prints the exact URL at the end.
#
# Safety:
#   - Idempotent: removes any existing ruleset with the same name before
#     creating the new one.
#   - Enforcement starts at 'evaluate' (report-only) so you can verify the
#     rule reports correctly before flipping to 'active'. The script creates
#     it in 'active' mode but the flip can be reverted with one PATCH.
#   - Uses the ruleset API (not the older classic branch protection API) so
#     the configuration shows up cleanly under Settings > Rules.
#   - Does NOT touch uiao-docs or any other repo. 5.2 is uiao-core only.
#
# Prerequisites:
#   - gh CLI installed and authenticated as a repo admin
#     (gh auth status must show 'repo, admin:repo_hook' scopes, or similar)
# =============================================================================

$ErrorActionPreference = 'Stop'
$Owner     = 'WhalerMike'
$Repo      = 'uiao-core'
$RuleName  = 'uiao-core-main-protection'

function Write-Step($msg) { Write-Host "`n>>> $msg" -ForegroundColor Cyan }
function Write-OK($msg)   { Write-Host "[OK]  $msg"  -ForegroundColor Green }
function Write-Fail($msg) { Write-Host "[FAIL] $msg" -ForegroundColor Red }

# --- 0. Preflight ----------------------------------------------------------
Write-Step 'Preflight'
$ghVersion = gh --version 2>$null
if (-not $ghVersion) { Write-Fail 'gh CLI not installed or not on PATH'; exit 1 }
Write-OK ("gh found: " + ($ghVersion -split "`n")[0])

gh auth status 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Fail 'gh not authenticated. Run: gh auth login'
    exit 1
}
Write-OK 'gh authenticated'

# Confirm repo visibility and admin role
$repoInfo = gh api "repos/$Owner/$Repo" 2>$null | ConvertFrom-Json
if (-not $repoInfo) { Write-Fail "cannot read repos/$Owner/$Repo"; exit 1 }
if (-not $repoInfo.permissions.admin) {
    Write-Fail 'current gh user does not have admin on this repo'
    exit 1
}
Write-OK ("repo confirmed: {0}/{1} (default_branch={2}, admin=true)" -f $Owner, $Repo, $repoInfo.default_branch)

# --- 1. Show existing rulesets --------------------------------------------
Write-Step 'Step 1 - Enumerate existing rulesets'
$existing = gh api "repos/$Owner/$Repo/rulesets" | ConvertFrom-Json
if ($existing.Count -eq 0) {
    Write-OK 'no existing rulesets'
} else {
    Write-Host ("found {0} existing ruleset(s):" -f $existing.Count) -ForegroundColor Yellow
    $existing | ForEach-Object {
        Write-Host ("   id={0}  name='{1}'  enforcement={2}" -f $_.id, $_.name, $_.enforcement) -ForegroundColor Yellow
    }
}

# --- 2. Remove prior version of our ruleset (idempotency) -----------------
Write-Step "Step 2 - Remove any prior '$RuleName' ruleset (idempotent)"
$prior = $existing | Where-Object { $_.name -eq $RuleName }
if ($prior) {
    foreach ($p in $prior) {
        gh api -X DELETE "repos/$Owner/$Repo/rulesets/$($p.id)" | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Write-Fail "failed to delete prior ruleset id=$($p.id)"
            exit 1
        }
        Write-OK ("deleted prior ruleset id={0}" -f $p.id)
    }
} else {
    Write-OK 'no prior ruleset with that name'
}

# --- 3. Build ruleset payload ---------------------------------------------
Write-Step 'Step 3 - Build ruleset payload'

# NOTE: actor_type 'RepositoryRole' with actor_id 5 = 'Admin' role.
# bypass_mode 'always' means admins bypass both push and PR merge rules.
$payload = [ordered]@{
    name        = $RuleName
    target      = 'branch'
    enforcement = 'active'
    bypass_actors = @(
        @{
            actor_id    = 5
            actor_type  = 'RepositoryRole'
            bypass_mode = 'always'
        }
    )
    conditions = @{
        ref_name = @{
            include = @('~DEFAULT_BRANCH')
            exclude = @()
        }
    }
    rules = @(
        @{
            type = 'pull_request'
            parameters = @{
                required_approving_review_count   = 0
                dismiss_stale_reviews_on_push     = $false
                require_code_owner_review         = $false
                require_last_push_approval        = $false
                required_review_thread_resolution = $false
            }
        },
        @{
            type = 'required_status_checks'
            parameters = @{
                required_status_checks = @(
                    @{ context = 'metadata-validator' },
                    @{ context = 'drift-scan' },
                    @{ context = 'dashboard-export' }
                )
                strict_required_status_checks_policy = $false
            }
        },
        @{ type = 'non_fast_forward' },
        @{ type = 'deletion' }
    )
}

$json = $payload | ConvertTo-Json -Depth 10 -Compress
$payloadFile = Join-Path $env:TEMP 'uiao-core-5-2-ruleset.json'
[System.IO.File]::WriteAllText(
    $payloadFile,
    $json,
    (New-Object System.Text.UTF8Encoding($false))
)
Write-OK ("payload written: {0} ({1} bytes)" -f $payloadFile, (Get-Item $payloadFile).Length)
Write-Host ''
Write-Host '--- payload preview ---' -ForegroundColor Cyan
($payload | ConvertTo-Json -Depth 10)

# --- 4. Create ruleset -----------------------------------------------------
Write-Step 'Step 4 - Create ruleset'
$createResult = gh api -X POST "repos/$Owner/$Repo/rulesets" --input $payloadFile 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Fail 'ruleset creation failed'
    Write-Host $createResult -ForegroundColor Red
    exit 1
}
$created = $createResult | ConvertFrom-Json
Write-OK ("created ruleset id={0} name='{1}' enforcement={2}" -f $created.id, $created.name, $created.enforcement)

Remove-Item $payloadFile -Force -ErrorAction SilentlyContinue

# --- 5. Verify by readback ------------------------------------------------
Write-Step 'Step 5 - Verify (readback)'
$verify = gh api "repos/$Owner/$Repo/rulesets/$($created.id)" | ConvertFrom-Json
Write-Host ('name        : {0}' -f $verify.name)
Write-Host ('enforcement : {0}' -f $verify.enforcement)
Write-Host ('target      : {0}' -f $verify.target)
Write-Host 'bypass_actors:'
$verify.bypass_actors | ForEach-Object {
    Write-Host ('   - actor_type={0} actor_id={1} bypass_mode={2}' -f $_.actor_type, $_.actor_id, $_.bypass_mode)
}
Write-Host 'conditions.ref_name:'
Write-Host ('   include=[{0}]' -f ($verify.conditions.ref_name.include -join ','))
Write-Host ('   exclude=[{0}]' -f ($verify.conditions.ref_name.exclude -join ','))
Write-Host 'rules:'
$verify.rules | ForEach-Object {
    $t = $_.type
    if ($_.parameters) {
        $p = $_.parameters | ConvertTo-Json -Compress -Depth 5
        Write-Host ("   - $t  $p")
    } else {
        Write-Host ("   - $t")
    }
}
Write-OK 'ruleset is live'

# --- 6. Closing guidance ---------------------------------------------------
Write-Host ''
Write-Host '==============================================================' -ForegroundColor Cyan
Write-Host 'ONE MANUAL STEP REMAINS:' -ForegroundColor Yellow
Write-Host '==============================================================' -ForegroundColor Cyan
Write-Host ''
Write-Host 'Add GitHub Actions as a bypass actor so the dashboard bot can' -ForegroundColor Yellow
Write-Host 'keep pushing directly to main without opening PRs:' -ForegroundColor Yellow
Write-Host ''
Write-Host ('  1. Open: https://github.com/{0}/{1}/settings/rules' -f $Owner, $Repo) -ForegroundColor White
Write-Host ("  2. Click the '{0}' ruleset" -f $RuleName) -ForegroundColor White
Write-Host "  3. Under 'Bypass list', click 'Add bypass'" -ForegroundColor White
Write-Host "  4. Select role/team/integration: 'GitHub Actions'" -ForegroundColor White
Write-Host "  5. Bypass mode: 'Always'" -ForegroundColor White
Write-Host "  6. Save" -ForegroundColor White
Write-Host ''
Write-Host 'Until you do this, the next dashboard-export bot push to main' -ForegroundColor Yellow
Write-Host 'will be BLOCKED (it will error with something like:' -ForegroundColor Yellow
Write-Host "'changes must be made through a pull request').  Tap the" -ForegroundColor Yellow
Write-Host 'checkbox before the next scheduled export run.' -ForegroundColor Yellow
Write-Host ''
Write-Host 'To verify the bot bypass was added, after the UI step run:' -ForegroundColor Yellow
Write-Host ('  gh api repos/{0}/{1}/rulesets/{2} | ConvertFrom-Json | Select-Object -ExpandProperty bypass_actors' -f $Owner, $Repo, $created.id) -ForegroundColor White
Write-Host ''
Write-Host 'You should see TWO entries: one RepositoryRole (admin, id=5)' -ForegroundColor Yellow
Write-Host "and one Integration actor for GitHub Actions." -ForegroundColor Yellow
Write-Host ''
Write-Host 'After Stage 5.2 completes, Stage 5 is done. Remaining roadmap:' -ForegroundColor Cyan
Write-Host '  5.3 - uiao-docs fix-up script triage' -ForegroundColor White
Write-Host '  5.1.9 - (optional) mojibake sweep across canon' -ForegroundColor White
Write-Host '  6    - lychee link sweep' -ForegroundColor White
Write-Host '  7    - doc refreshes (ARCHITECTURE.md, CLAUDE.md, README.md)' -ForegroundColor White
