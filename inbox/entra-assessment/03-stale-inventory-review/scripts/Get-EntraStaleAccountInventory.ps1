<#
.SYNOPSIS
    Inventory stale user accounts in an Entra ID tenant.

.DESCRIPTION
    Read-only assessment. Enumerates User objects (Members + Guests),
    correlates with sign-in activity, account age, manager presence, and
    on-prem sync state, and assigns a disposition hint for each.

    Does NOT enumerate owned objects (apps, groups, devices). Ownership
    must be checked manually before disabling or deleting — see README
    "Risks and edge cases".

    Safe to re-run. Does NOT modify the tenant.

.PARAMETER OutputPath
    Folder to write reports into. Created if missing.

.PARAMETER NotifyDays
    Days of dormancy at which to flag NOTIFY_NO_SIGNIN_*. Default 90.

.PARAMETER DisableDays
    Days of dormancy at which to flag DISABLE_NO_SIGNIN_*. Default 180.

.PARAMETER DeleteDays
    Days an account must be disabled before flagging DELETE_DISABLED_*.
    Default 365.

.PARAMETER NewAccountGraceDays
    Accounts younger than this that have never signed in are NOT flagged
    as REVIEW_NEVER_SIGNED_IN (still in onboarding). Default 30.

.PARAMETER GuestStaleDays
    Days of guest dormancy before flagging STALE_GUEST_*. Default 90.

.PARAMETER TrustedGuestDomains
    Domain suffixes (e.g. partner.com) considered known external. Guests
    from any other domain are flagged GUEST_UNKNOWN_TENANT.

.NOTES
    Required Graph scopes:
      User.Read.All
      Directory.Read.All
      AuditLog.Read.All

    Required modules (PowerShell 7+):
      Microsoft.Graph.Users
      Microsoft.Graph.Authentication

    Connect before running:
      Connect-MgGraph -Scopes User.Read.All, Directory.Read.All, AuditLog.Read.All
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]   $OutputPath,

    [int]      $NotifyDays           = 90,
    [int]      $DisableDays          = 180,
    [int]      $DeleteDays           = 365,
    [int]      $NewAccountGraceDays  = 30,
    [int]      $GuestStaleDays       = 90,
    [string[]] $TrustedGuestDomains
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 3.0

# ----- Setup -----------------------------------------------------------------

function Test-GraphContext {
    $ctx = Get-MgContext
    if (-not $ctx) { throw "Not connected to Microsoft Graph. See script header." }
    $required = @('User.Read.All','Directory.Read.All','AuditLog.Read.All')
    $missing  = $required | Where-Object { $_ -notin $ctx.Scopes }
    if ($missing) {
        Write-Warning ("Connected, but missing recommended scopes: {0}." -f ($missing -join ', '))
    }
    return $ctx
}

function New-OutputFolder {
    param([string] $Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
    return (Resolve-Path -LiteralPath $Path).Path
}

function ConvertTo-Days {
    param(
        [Nullable[datetime]] $From,
        [Nullable[datetime]] $To
    )
    if (-not $From -or -not $To) { return $null }
    return [int][math]::Floor((($To.ToUniversalTime() - $From.ToUniversalTime())).TotalDays)
}

function ConvertTo-DatetimeOrNull {
    param([object] $Value)
    if (-not $Value) { return $null }
    if ($Value -is [datetime]) { return $Value.ToUniversalTime() }
    try { return ([datetime]::Parse([string]$Value)).ToUniversalTime() } catch { return $null }
}

$ctx       = Test-GraphContext
$out       = New-OutputFolder -Path $OutputPath
$timestamp = (Get-Date).ToString('yyyy-MM-ddTHH-mm-ss')

Write-Host ("Tenant: {0}" -f $ctx.TenantId) -ForegroundColor Cyan
Write-Host ("Output: {0}" -f $out)          -ForegroundColor Cyan

# ----- Enumerate users ------------------------------------------------------

# WHY: $expand=manager pulls the manager reference per user in the same
#      response, avoiding a per-user follow-up call. Trade-off: larger
#      per-page payload. For tenants > ~50k users, switch to per-user
#      lookups if expansion times out.
Write-Host "Enumerating users (with manager expand, signInActivity)..." -ForegroundColor Cyan
$users = Get-MgUser -All -PageSize 999 `
    -Property @(
        'Id','UserPrincipalName','DisplayName','UserType','AccountEnabled',
        'CreatedDateTime','SignInActivity','OnPremisesSyncEnabled',
        'OnPremisesImmutableId','ExternalUserState','Mail'
    ) `
    -ExpandProperty 'manager'

Write-Host ("  found {0} user(s)" -f $users.Count)

# ----- Classify --------------------------------------------------------------

Write-Host "Classifying users..." -ForegroundColor Cyan
$now     = (Get-Date).ToUniversalTime()
$records = New-Object System.Collections.Generic.List[object]

foreach ($u in $users) {
    $created          = ConvertTo-DatetimeOrNull $u.CreatedDateTime
    $accountAgeDays   = ConvertTo-Days -From $created -To $now

    $lastSignIn       = $null
    $lastNonInteractive = $null
    if ($u.SignInActivity) {
        if ($u.SignInActivity.LastSignInDateTime) {
            $lastSignIn = ConvertTo-DatetimeOrNull $u.SignInActivity.LastSignInDateTime
        }
        if ($u.SignInActivity.LastNonInteractiveSignInDateTime) {
            $lastNonInteractive = ConvertTo-DatetimeOrNull $u.SignInActivity.LastNonInteractiveSignInDateTime
        }
    }
    $lastSignInDays   = ConvertTo-Days -From $lastSignIn -To $now

    $hasManager = $false
    if ($u.Manager) { $hasManager = $true }

    # Disposition cascade — see README "User accounts" decision tree
    $reasons = New-Object System.Collections.Generic.List[string]
    $disp    = 'KEEP'

    # Carve-out check — UPN or display name tagged
    # WHY: Users can't have arbitrary tags like apps can. The convention here
    #      is a "carveout:" token in the user's DisplayName, or some other
    #      out-of-band allowlist. For learning purposes, the script just
    #      surfaces this token if present; teams typically maintain a
    #      separate allowlist file.
    $carveout = ($u.DisplayName -and $u.DisplayName -match 'carveout:')

    if ($carveout) {
        $reasons.Add('carveout token in DisplayName')
        $disp = 'KEEP_LEGAL_HOLD'
    }
    elseif ($u.UserType -eq 'Guest') {
        if ($u.ExternalUserState -eq 'PendingAcceptance') {
            $reasons.Add('guest invitation pending acceptance')
            $disp = 'REVIEW'
        }
        elseif ($null -ne $lastSignInDays -and $lastSignInDays -gt $GuestStaleDays) {
            $reasons.Add(("guest no sign-in {0}d" -f $lastSignInDays))
            $disp = 'STALE_GUEST_90'
        }
        else {
            $upnDomain = if ($u.UserPrincipalName -match '#EXT#@') {
                # Guests have UPN like external_domain.com#EXT#@yourtenant.onmicrosoft.com
                ($u.UserPrincipalName -split '#EXT#@')[0] -replace '_', '@' -replace '^.+@', ''
            } else { '' }
            if ($TrustedGuestDomains -and $upnDomain -and ($upnDomain -notin $TrustedGuestDomains)) {
                $reasons.Add(("guest from unlisted domain: {0}" -f $upnDomain))
                $disp = 'GUEST_UNKNOWN_TENANT'
            }
            else {
                $reasons.Add('guest active')
                $disp = 'KEEP'
            }
        }
    }
    elseif (-not $u.AccountEnabled) {
        # Disabled member — how long?
        # WHY: We don't have "disabled-since" directly. SignInActivity is the
        #      best proxy: a user disabled long ago will have an old
        #      lastSignInDateTime (no activity since disable).
        if ($null -ne $lastSignInDays -and $lastSignInDays -gt $DeleteDays) {
            $reasons.Add(("disabled; last sign-in {0}d ago" -f $lastSignInDays))
            $disp = 'DELETE_DISABLED_365'
        }
        else {
            $reasons.Add('account disabled')
            $disp = 'DISABLED_ACCOUNT'
        }
    }
    elseif ($null -eq $lastSignIn -and $null -ne $accountAgeDays -and $accountAgeDays -gt $NewAccountGraceDays) {
        $reasons.Add(("enabled, never signed in; account {0}d old" -f $accountAgeDays))
        $disp = 'REVIEW_NEVER_SIGNED_IN'
    }
    elseif ($null -ne $lastSignInDays -and $lastSignInDays -gt $DisableDays) {
        $reasons.Add(("no sign-in {0}d ({1}+)" -f $lastSignInDays, $DisableDays))
        $disp = 'DISABLE_NO_SIGNIN_180'
    }
    elseif ($null -ne $lastSignInDays -and $lastSignInDays -gt $NotifyDays) {
        $reasons.Add(("no sign-in {0}d ({1}+)" -f $lastSignInDays, $NotifyDays))
        $disp = 'NOTIFY_NO_SIGNIN_90'
    }
    elseif (-not $hasManager -and $u.UserType -eq 'Member' -and $u.AccountEnabled) {
        # WHY: Manager presence is a JML governance signal; missing manager
        #      is a gap but not in itself a deletion candidate.
        $reasons.Add('member, enabled, no manager assigned')
        $disp = 'REVIEW_NO_MANAGER'
    }
    else {
        $reasons.Add('recent sign-in / healthy')
        $disp = 'KEEP'
    }

    $records.Add([pscustomobject]@{
        Upn                    = $u.UserPrincipalName
        ObjectId               = $u.Id
        DisplayName            = $u.DisplayName
        UserType               = $u.UserType
        AccountEnabled         = $u.AccountEnabled
        CreatedDateTime        = if ($created) { $created.ToString('o') } else { $null }
        AccountAgeDays         = $accountAgeDays
        LastSignIn             = if ($lastSignIn) { $lastSignIn.ToString('o') } else { $null }
        LastSignInDays         = $lastSignInDays
        LastNonInteractiveSignIn = if ($lastNonInteractive) { $lastNonInteractive.ToString('o') } else { $null }
        HasManager             = $hasManager
        OnPremSync             = [bool]$u.OnPremisesSyncEnabled
        ExternalUserState      = $u.ExternalUserState
        Disposition            = $disp
        DispositionReasons     = ($reasons -join '; ')
    }) | Out-Null
}

# ----- Write outputs ---------------------------------------------------------

$csv     = Join-Path $out "stale-accounts-$timestamp.csv"
$json    = Join-Path $out "stale-accounts-$timestamp.json"
$summary = Join-Path $out "summary-$timestamp.txt"

$records | Export-Csv -LiteralPath $csv -NoTypeInformation -Encoding UTF8
$records | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $json -Encoding UTF8

$members = @($records | Where-Object { $_.UserType -eq 'Member' })
$guests  = @($records | Where-Object { $_.UserType -eq 'Guest' })

$lines = @(
    "Stale user accounts inventory"
    ("Tenant:    {0}" -f $ctx.TenantId)
    ("Generated: {0}" -f (Get-Date).ToString('o'))
    ""
    ("Users total:                       {0,6}" -f $records.Count)
    ("  Members:                         {0,6}" -f $members.Count)
    ("  Guests:                          {0,6}" -f $guests.Count)
    ""
    "Disposition breakdown:"
)
foreach ($g in ($records | Group-Object Disposition | Sort-Object Count -Descending)) {
    $lines += ("  {0,-32} {1,6}" -f $g.Name, $g.Count)
}
$lines | Set-Content -LiteralPath $summary -Encoding UTF8

Write-Host ""
Write-Host "Done." -ForegroundColor Green
Write-Host ("  Accounts CSV:  {0}" -f $csv)
Write-Host ("  Accounts JSON: {0}" -f $json)
Write-Host ("  Summary:       {0}" -f $summary)
Write-Host ""
$lines | Write-Host
