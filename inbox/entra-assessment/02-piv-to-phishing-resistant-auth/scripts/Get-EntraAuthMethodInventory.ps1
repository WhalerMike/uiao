<#
.SYNOPSIS
    Inventory Entra ID user authentication-method registration plus
    tenant-wide auth policy posture, for PIV -> CBA + FIDO2 / WHfB
    migration planning.

.DESCRIPTION
    Read-only assessment. Two phases:

      1. Tenant config phase pulls singletons (authentication methods
         policy, CBA / FIDO2 / WHfB / TAP configurations, trusted
         certificate authorities, authentication strengths, Conditional
         Access policies, domain federation status). Outputs a single
         JSON + summary text describing the tenant's auth posture.

      2. User enumeration phase paginates through
         /reports/authenticationMethods/userRegistrationDetails to
         classify every Member user by which methods they have
         registered, then joins with the user's sign-in activity.
         Outputs a per-user CSV + JSON plus a summary text.

    Either phase can be skipped with -SkipTenantConfig / -SkipUserEnum.

    Safe to re-run. Does NOT modify the tenant.

.PARAMETER OutputPath
    Folder to write reports into. Created if missing.

.PARAMETER StaleDays
    Days since last user sign-in considered stale. Default 90. Stale
    users are flagged but not excluded from disposition classification.

.PARAMETER SkipTenantConfig
    Skip the tenant-config phase (e.g. when only the user inventory has
    changed since the last run).

.PARAMETER SkipUserEnum
    Skip the user-enumeration phase (e.g. to quickly inspect tenant
    config drift without re-enumerating thousands of users).

.PARAMETER IncludeGuests
    Include Guest users in the per-user output. By default they are
    written with disposition GUEST_OUT_OF_SCOPE so they appear in the
    CSV; this switch is currently a no-op and is reserved for future
    extension (skipping guests entirely).

.EXAMPLE
    PS> .\Get-EntraAuthMethodInventory.ps1 -OutputPath .\out

.EXAMPLE
    PS> .\Get-EntraAuthMethodInventory.ps1 -OutputPath .\out -SkipUserEnum

.NOTES
    Required Graph scopes:
      User.Read.All
      UserAuthenticationMethod.Read.All
      Policy.Read.All
      AuditLog.Read.All
      Reports.Read.All
      Directory.Read.All
      Organization.Read.All

    Required modules (PowerShell 7+):
      Microsoft.Graph.Authentication
      Microsoft.Graph.Identity.DirectoryManagement
      Microsoft.Graph.Identity.SignIns
      Microsoft.Graph.Users
      Microsoft.Graph.Reports

    Connect before running:
      Connect-MgGraph -Scopes User.Read.All, UserAuthenticationMethod.Read.All, Policy.Read.All, AuditLog.Read.All, Reports.Read.All, Directory.Read.All, Organization.Read.All
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string] $OutputPath,

    [int]    $StaleDays = 90,
    [switch] $SkipTenantConfig,
    [switch] $SkipUserEnum,
    [switch] $IncludeGuests
)

# WHY: ErrorActionPreference=Stop turns non-terminating SDK errors into
#      terminating ones so a typo / schema drift fails loudly. StrictMode 3.0
#      catches missing-property bugs on PSCustomObject; hashtables tolerate
#      missing keys, which is why all raw Graph calls use the default
#      hashtable output below.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 3.0

# WHY: The set of method strings (from userRegistrationDetails.methodsRegistered)
#      that count as phishing-resistant. Microsoft Authenticator "push" and
#      "softwareOneTimePasscode" are deliberately NOT in this list — they're
#      passwordless / MFA but not phishing-resistant under Authentication
#      Strengths. Keep in sync with Microsoft's growing list of method types.
$script:PhishingResistantMethods = @(
    'fido2SecurityKey',
    'windowsHelloForBusiness',
    'microsoftAuthenticatorPasswordless',
    'x509CertificateSingleFactor',
    'x509CertificateMultiFactor',
    'passKeyDeviceBound',
    'passKeyDeviceBoundAuthenticator',
    'passKeyDeviceBoundWindowsHello',
    'platformCredential'
)

# WHY: Method strings indicating CBA / FIDO2 / WHfB specifically (so we can
#      surface "CBA registered but no backup" disposition).
$script:CbaMethods    = @('x509CertificateSingleFactor', 'x509CertificateMultiFactor', 'certificateBasedAuthentication')
$script:Fido2Methods  = @('fido2SecurityKey')
$script:WhfbMethods   = @('windowsHelloForBusiness')
$script:PasskeyMethods = @('microsoftAuthenticatorPasswordless', 'passKeyDeviceBound', 'passKeyDeviceBoundAuthenticator', 'passKeyDeviceBoundWindowsHello')
$script:TapMethods    = @('temporaryAccessPass')

# ----- Setup -----------------------------------------------------------------

function Test-GraphContext {
    $ctx = Get-MgContext
    if (-not $ctx) {
        throw "Not connected to Microsoft Graph. See script header for the Connect-MgGraph command."
    }
    $required = @(
        'User.Read.All', 'UserAuthenticationMethod.Read.All',
        'Policy.Read.All', 'AuditLog.Read.All', 'Reports.Read.All',
        'Directory.Read.All', 'Organization.Read.All'
    )
    $missing = $required | Where-Object { $_ -notin $ctx.Scopes }
    if ($missing) {
        Write-Warning ("Connected, but missing recommended scopes: {0}. Some columns may be empty." -f ($missing -join ', '))
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

# WHY: Invoke-MgGraphRequest returns hashtable by default; this helper keeps
#      caller code tidy when retrieving a single document from Graph that may
#      404 (e.g. tenant doesn't have a CBA configuration yet).
function Invoke-GraphGet {
    param(
        [Parameter(Mandatory)][string] $Uri,
        [switch] $AllowNotFound
    )
    try {
        return Invoke-MgGraphRequest -Method GET -Uri $Uri
    }
    catch {
        if ($AllowNotFound -and ($_.Exception.Message -match '404|NotFound')) {
            return $null
        }
        throw
    }
}

$ctx       = Test-GraphContext
$out       = New-OutputFolder -Path $OutputPath
$timestamp = (Get-Date).ToString('yyyy-MM-ddTHH-mm-ss')

Write-Host ("Tenant: {0}" -f $ctx.TenantId) -ForegroundColor Cyan
Write-Host ("Output: {0}" -f $out)          -ForegroundColor Cyan

# ----- Phase 1: Tenant config -----------------------------------------------

$tenantConfig = $null
if (-not $SkipTenantConfig) {
    Write-Host "Phase 1: Tenant config audit..." -ForegroundColor Cyan

    $tenantConfig = [ordered]@{
        tenantId                    = $ctx.TenantId
        generatedUtc                = (Get-Date).ToUniversalTime().ToString('o')
        domains                     = @()
        federatedDomainCount        = 0
        managedDomainCount          = 0
        certificateAuthorities      = @()
        cbaConfiguration            = $null
        fido2Configuration          = $null
        whfbConfiguration           = $null
        tapConfiguration            = $null
        microsoftAuthenticator      = $null
        smsConfiguration            = $null
        voiceConfiguration          = $null
        emailConfiguration          = $null
        authenticationStrengths     = @()
        conditionalAccessPolicies   = @()
    }

    # Domains + federation status
    Write-Host "  domains / federation..."
    $domainsResp = Invoke-GraphGet -Uri 'https://graph.microsoft.com/v1.0/domains'
    foreach ($d in $domainsResp['value']) {
        $tenantConfig.domains += [ordered]@{
            id                  = $d['id']
            authenticationType  = $d['authenticationType']
            isVerified          = $d['isVerified']
            isDefault           = $d['isDefault']
        }
        if ($d['authenticationType'] -eq 'Federated') { $tenantConfig.federatedDomainCount++ } else { $tenantConfig.managedDomainCount++ }
    }

    # Certificate authorities for CBA
    # WHY: This endpoint returns null/404 when no CAs have ever been uploaded —
    #      common in tenants that haven't started CBA. AllowNotFound keeps the
    #      script useful in that state.
    Write-Host "  trusted certificate authorities..."
    $caResp = Invoke-GraphGet -Uri ("https://graph.microsoft.com/v1.0/organization/{0}/certificateBasedAuthConfiguration" -f $ctx.TenantId) -AllowNotFound
    if ($caResp -and $caResp['value']) {
        foreach ($caCfg in $caResp['value']) {
            foreach ($ca in $caCfg['certificateAuthorities']) {
                $tenantConfig.certificateAuthorities += [ordered]@{
                    isRootAuthority            = $ca['isRootAuthority']
                    issuer                     = $ca['issuer']
                    issuerSki                  = $ca['issuerSki']
                    crlDistributionPoint       = $ca['crlDistributionPoint']
                    deltaCrlDistributionPoint  = $ca['deltaCrlDistributionPoint']
                }
            }
        }
    }

    # Authentication method configurations (CBA, FIDO2, WHfB, TAP, etc.)
    # WHY: Each method type is a child resource of the singleton
    #      /policies/authenticationMethodsPolicy/authenticationMethodConfigurations.
    #      The well-known IDs are X509Certificate, Fido2, WindowsHelloForBusiness,
    #      TemporaryAccessPass, MicrosoftAuthenticator, Sms, Voice, Email.
    $methodIds = @(
        @{ id = 'X509Certificate';          field = 'cbaConfiguration' },
        @{ id = 'Fido2';                    field = 'fido2Configuration' },
        @{ id = 'WindowsHelloForBusiness';  field = 'whfbConfiguration' },
        @{ id = 'TemporaryAccessPass';      field = 'tapConfiguration' },
        @{ id = 'MicrosoftAuthenticator';   field = 'microsoftAuthenticator' },
        @{ id = 'Sms';                      field = 'smsConfiguration' },
        @{ id = 'Voice';                    field = 'voiceConfiguration' },
        @{ id = 'Email';                    field = 'emailConfiguration' }
    )
    foreach ($m in $methodIds) {
        Write-Host ("  auth method config: {0}" -f $m.id)
        $uri = "https://graph.microsoft.com/v1.0/policies/authenticationMethodsPolicy/authenticationMethodConfigurations/$($m.id)"
        $cfg = Invoke-GraphGet -Uri $uri -AllowNotFound
        $tenantConfig[$m.field] = $cfg
    }

    # Authentication strengths
    Write-Host "  authentication strengths..."
    $strResp = Invoke-GraphGet -Uri 'https://graph.microsoft.com/v1.0/policies/authenticationStrengthPolicies'
    foreach ($s in $strResp['value']) {
        $tenantConfig.authenticationStrengths += [ordered]@{
            id                  = $s['id']
            displayName         = $s['displayName']
            policyType          = $s['policyType']
            allowedCombinations = $s['allowedCombinations']
            requirementsSatisfied = $s['requirementsSatisfied']
        }
    }

    # Conditional Access policies
    Write-Host "  conditional access policies..."
    $caPolUri = 'https://graph.microsoft.com/v1.0/identity/conditionalAccess/policies'
    do {
        $page = Invoke-GraphGet -Uri $caPolUri
        foreach ($p in $page['value']) {
            $tenantConfig.conditionalAccessPolicies += [ordered]@{
                id                          = $p['id']
                displayName                 = $p['displayName']
                state                       = $p['state']
                referencesAuthStrength      = ($null -ne $p['grantControls']['authenticationStrength'])
                authenticationStrengthId    = if ($p['grantControls']) { $p['grantControls']['authenticationStrength']?['id'] } else { $null }
                authenticationStrengthName  = if ($p['grantControls']) { $p['grantControls']['authenticationStrength']?['displayName'] } else { $null }
            }
        }
        $caPolUri = $page['@odata.nextLink']
    } while ($caPolUri)

    # Write tenant config artifacts
    $tcJson = Join-Path $out "tenant-config-$timestamp.json"
    $tcTxt  = Join-Path $out "tenant-config-$timestamp.txt"

    $tenantConfig | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $tcJson -Encoding UTF8

    # Human-readable summary
    $lines = New-Object System.Collections.Generic.List[string]
    $lines.Add("Tenant authentication posture")
    $lines.Add(("Tenant:    {0}" -f $ctx.TenantId))
    $lines.Add(("Generated: {0}" -f $tenantConfig.generatedUtc))
    $lines.Add('')
    $lines.Add("Domains:")
    $lines.Add(("  Federated (external IdP):  {0}" -f $tenantConfig.federatedDomainCount))
    foreach ($d in ($tenantConfig.domains | Where-Object { $_.authenticationType -eq 'Federated' })) { $lines.Add("    $($d.id)") }
    $lines.Add(("  Managed (Entra-native):    {0}" -f $tenantConfig.managedDomainCount))
    foreach ($d in ($tenantConfig.domains | Where-Object { $_.authenticationType -ne 'Federated' })) { $lines.Add("    $($d.id)") }
    $lines.Add('')
    $lines.Add(("Certificate Authorities uploaded: {0}" -f $tenantConfig.certificateAuthorities.Count))
    foreach ($ca in $tenantConfig.certificateAuthorities) { $lines.Add("    $($ca.issuer)") }
    $lines.Add('')
    $lines.Add("Authentication method policy states:")
    foreach ($m in $methodIds) {
        $cfg = $tenantConfig[$m.field]
        $state = if ($cfg -and $cfg['state']) { $cfg['state'] } else { 'not-configured' }
        $lines.Add(("  {0,-32} {1}" -f $m.id, $state))
    }
    $lines.Add('')
    $lines.Add(("Authentication strengths defined: {0}" -f $tenantConfig.authenticationStrengths.Count))
    foreach ($s in $tenantConfig.authenticationStrengths) {
        $lines.Add(("  [{0}] {1}" -f $s.policyType, $s.displayName))
    }
    $lines.Add('')
    $caRefs = @($tenantConfig.conditionalAccessPolicies | Where-Object { $_.referencesAuthStrength })
    $lines.Add(("Conditional Access policies: {0} total, {1} reference an auth strength" -f $tenantConfig.conditionalAccessPolicies.Count, $caRefs.Count))
    foreach ($p in $caRefs) {
        $lines.Add(("  [{0}] {1}  ->  strength: {2}" -f $p.state, $p.displayName, $p.authenticationStrengthName))
    }
    $lines | Set-Content -LiteralPath $tcTxt -Encoding UTF8

    Write-Host ("  wrote {0}" -f $tcJson)
    Write-Host ("  wrote {0}" -f $tcTxt)
}
else {
    Write-Host "Skipping Phase 1 (-SkipTenantConfig)." -ForegroundColor Yellow
}

# ----- Phase 2: User enumeration --------------------------------------------

if ($SkipUserEnum) {
    Write-Host "Skipping Phase 2 (-SkipUserEnum)." -ForegroundColor Yellow
    return
}

Write-Host "Phase 2: Per-user auth method registration..." -ForegroundColor Cyan

# WHY: One Graph call returns registration details for every user — orders of
#      magnitude faster than calling Get-MgUserAuthenticationMethod per user.
#      Endpoint is in /beta as of 2026.
$regDetails = @{}
Write-Host "  fetching userRegistrationDetails (beta, paged)..."
$uri = 'https://graph.microsoft.com/beta/reports/authenticationMethods/userRegistrationDetails?$top=999'
do {
    $page = Invoke-GraphGet -Uri $uri
    foreach ($row in $page['value']) {
        if ($row['id']) { $regDetails[$row['id']] = $row }
    }
    $uri = $page['@odata.nextLink']
} while ($uri)
Write-Host ("  loaded registration details for {0} user(s)" -f $regDetails.Count)

# WHY: Enumerate users from /users (not /reports/.../userRegistrationDetails),
#      because we need signInActivity, accountEnabled, userType, and the
#      directory-role membership heuristic for IsAdmin. We then join in the
#      registration details by user object ID.
Write-Host "  enumerating users (signInActivity included)..."
$users = Get-MgUser -All -PageSize 999 -Property @(
    'Id','UserPrincipalName','DisplayName','UserType','AccountEnabled','SignInActivity'
)
Write-Host ("  found {0} user(s)" -f $users.Count)

# Directory role members for IsAdmin heuristic
# WHY: Get-MgDirectoryRoleMember enumerates per role; aggregate to a set of
#      user object IDs that hold at least one directory role.
Write-Host "  building admin set from directory roles..."
$adminIds = New-Object System.Collections.Generic.HashSet[string]
try {
    $roles = Get-MgDirectoryRole -All
    foreach ($r in $roles) {
        $members = Get-MgDirectoryRoleMember -DirectoryRoleId $r.Id -All -ErrorAction Stop
        foreach ($m in $members) {
            if ($m.Id) { [void]$adminIds.Add($m.Id) }
        }
    }
}
catch {
    Write-Warning ("Could not fully enumerate directory roles: {0}" -f $_.Exception.Message)
}
Write-Host ("  identified {0} user(s) holding at least one directory role" -f $adminIds.Count)

# ----- Build per-user records ------------------------------------------------

$now         = (Get-Date).ToUniversalTime()
$userRecords = New-Object System.Collections.Generic.List[object]

$i = 0
foreach ($u in $users) {
    $i++
    if ($i % 250 -eq 0) { Write-Host ("  processed {0}/{1}" -f $i, $users.Count) }

    $reg     = $regDetails[$u.Id]
    $methods = @()
    $defaultMethod    = $null
    $isMfaRegistered  = $false
    $isMfaCapable     = $false
    $isPwlessCapable  = $false

    if ($reg) {
        $methods         = @($reg['methodsRegistered'])
        $defaultMethod   = $reg['defaultMfaMethod']
        $isMfaRegistered = [bool]$reg['isMfaRegistered']
        $isMfaCapable    = [bool]$reg['isMfaCapable']
        $isPwlessCapable = [bool]$reg['isPasswordlessCapable']
    }

    # Method-class flags
    $hasCba     = ($methods | Where-Object { $_ -in $script:CbaMethods }).Count    -gt 0
    $hasFido2   = ($methods | Where-Object { $_ -in $script:Fido2Methods }).Count  -gt 0
    $hasWhfb    = ($methods | Where-Object { $_ -in $script:WhfbMethods }).Count   -gt 0
    $hasPasskey = ($methods | Where-Object { $_ -in $script:PasskeyMethods }).Count -gt 0
    $hasTap     = ($methods | Where-Object { $_ -in $script:TapMethods }).Count    -gt 0
    $hasPR      = ($methods | Where-Object { $_ -in $script:PhishingResistantMethods }).Count -gt 0

    # Sign-in activity
    $lastSignIn = $null
    if ($u.SignInActivity -and $u.SignInActivity.LastSignInDateTime) {
        $lastSignIn = ConvertTo-DatetimeOrNull $u.SignInActivity.LastSignInDateTime
    }
    $lastSignInDays = ConvertTo-Days -From $lastSignIn -To $now

    # Disposition cascade (see README "How the script works" section 4)
    $reasons = New-Object System.Collections.Generic.List[string]
    $disp    = 'INVESTIGATE'

    if ($u.UserType -eq 'Guest') {
        $reasons.Add('Guest user — managed by home tenant')
        $disp = 'GUEST_OUT_OF_SCOPE'
    }
    elseif (-not $u.AccountEnabled) {
        $reasons.Add('account disabled')
        $disp = 'DISABLED_ACCOUNT'
    }
    elseif (-not $isMfaRegistered) {
        $reasons.Add('no MFA method registered')
        $disp = 'PASSWORD_ONLY_HIGH_RISK'
    }
    elseif (-not $hasPR) {
        $reasons.Add('MFA registered but no phishing-resistant method')
        $disp = 'MFA_NOT_PHISHING_RESISTANT'
    }
    elseif ($hasCba -and -not ($hasFido2 -or $hasWhfb -or $hasPasskey)) {
        $reasons.Add('CBA only — no backup phishing-resistant method')
        $disp = 'CBA_ONLY_ADD_BACKUP'
    }
    elseif ($hasFido2 -and -not ($hasCba -or $hasWhfb -or $hasPasskey)) {
        $reasons.Add('FIDO2 only — no backup phishing-resistant method')
        $disp = 'FIDO2_ONLY_ADD_BACKUP'
    }
    else {
        $reasons.Add('phishing-resistant method registered with backup')
        $disp = 'PHISHING_RESISTANT_READY'
    }

    if ($null -ne $lastSignInDays -and $lastSignInDays -gt $StaleDays) {
        $reasons.Add(("last sign-in {0}d ago (> {1})" -f $lastSignInDays, $StaleDays))
    }

    $userRecords.Add([pscustomobject]@{
        Upn                   = $u.UserPrincipalName
        ObjectId              = $u.Id
        DisplayName           = $u.DisplayName
        UserType              = $u.UserType
        AccountEnabled        = $u.AccountEnabled
        IsAdmin               = [bool]$adminIds.Contains($u.Id)
        IsMfaRegistered       = $isMfaRegistered
        IsMfaCapable          = $isMfaCapable
        IsPasswordlessCapable = $isPwlessCapable
        DefaultMfaMethod      = $defaultMethod
        MethodsRegistered     = ($methods -join ';')
        HasPhishingResistant  = $hasPR
        HasCBA                = $hasCba
        HasFido2              = $hasFido2
        HasWHfB               = $hasWhfb
        HasPasskey            = $hasPasskey
        HasTAP                = $hasTap
        LastSignIn            = if ($lastSignIn) { $lastSignIn.ToString('o') } else { $null }
        LastSignInDays        = $lastSignInDays
        Disposition           = $disp
        DispositionReasons    = ($reasons -join '; ')
    }) | Out-Null
}

# ----- Write user outputs ----------------------------------------------------

$usersCsv  = Join-Path $out "users-$timestamp.csv"
$usersJson = Join-Path $out "users-$timestamp.json"
$summary   = Join-Path $out "summary-$timestamp.txt"

Write-Host "Writing user reports..." -ForegroundColor Cyan
$userRecords | Export-Csv -LiteralPath $usersCsv -NoTypeInformation -Encoding UTF8
$userRecords | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $usersJson -Encoding UTF8

# Summary statistics
$members      = @($userRecords | Where-Object { $_.UserType -eq 'Member' -and $_.AccountEnabled })
$prReady      = @($members | Where-Object { $_.HasPhishingResistant }).Count
$cbaRegistered= @($members | Where-Object { $_.HasCBA }).Count
$fido2Registered = @($members | Where-Object { $_.HasFido2 }).Count
$whfbRegistered  = @($members | Where-Object { $_.HasWHfB }).Count
$passwordOnly = @($members | Where-Object { -not $_.IsMfaRegistered }).Count
$mfaWeak      = @($members | Where-Object { $_.IsMfaRegistered -and -not $_.HasPhishingResistant }).Count

function Pct { param([int]$Num, [int]$Den) if ($Den -eq 0) { return '   - ' } return ("{0,5:N1}%" -f (100.0 * $Num / $Den)) }

$summaryLines = @(
    "Entra ID authentication method inventory"
    ("Tenant:    {0}" -f $ctx.TenantId)
    ("Generated: {0}" -f (Get-Date).ToString('o'))
    ""
    ("Users total (all rows):                  {0,6}" -f $userRecords.Count)
    ("Members, enabled:                        {0,6}" -f $members.Count)
    ("  with phishing-resistant method:        {0,6}  {1}" -f $prReady, (Pct $prReady $members.Count))
    ("  with CBA registered:                   {0,6}  {1}" -f $cbaRegistered, (Pct $cbaRegistered $members.Count))
    ("  with FIDO2 registered:                 {0,6}  {1}" -f $fido2Registered, (Pct $fido2Registered $members.Count))
    ("  with WHfB registered:                  {0,6}  {1}" -f $whfbRegistered, (Pct $whfbRegistered $members.Count))
    ("  with MFA but no phishing-resistant:    {0,6}  {1}" -f $mfaWeak, (Pct $mfaWeak $members.Count))
    ("  with no MFA registered:                {0,6}  {1}" -f $passwordOnly, (Pct $passwordOnly $members.Count))
    ""
    "Disposition breakdown:"
)
foreach ($g in ($userRecords | Group-Object Disposition | Sort-Object Count -Descending)) {
    $summaryLines += ("  {0,-32} {1,6}" -f $g.Name, $g.Count)
}
$summaryLines | Set-Content -LiteralPath $summary -Encoding UTF8

Write-Host ""
Write-Host "Done." -ForegroundColor Green
if (-not $SkipTenantConfig) {
    Write-Host ("  Tenant JSON:    {0}" -f (Join-Path $out "tenant-config-$timestamp.json"))
    Write-Host ("  Tenant summary: {0}" -f (Join-Path $out "tenant-config-$timestamp.txt"))
}
Write-Host ("  Users CSV:      {0}" -f $usersCsv)
Write-Host ("  Users JSON:     {0}" -f $usersJson)
Write-Host ("  Summary:        {0}" -f $summary)
Write-Host ""
$summaryLines | Write-Host
