<#
.SYNOPSIS
    Inventory Entra ID application credentials for client-secret -> MI/WIF
    migration planning.

.DESCRIPTION
    Read-only assessment. Enumerates every Application object in the tenant
    along with its passwordCredentials, keyCredentials, and
    federatedIdentityCredentials; correlates each app with its matching
    service principal's sign-in activity; assigns a starting "disposition"
    hint; and writes timestamped CSV + JSON reports plus a per-credential
    detail report.

    Safe to re-run. Does NOT modify the tenant.

.PARAMETER OutputPath
    Folder to write reports into. Created if missing.

.PARAMETER ExpiryWarningDays
    Secrets expiring within this many days are flagged "expiring soon".
    Default 90.

.PARAMETER StaleDays
    Days since last service-principal sign-in that count as "stale".
    Default 180.

.PARAMETER IncludeMicrosoftBuiltIn
    Include first-party Microsoft-published service principals.
    Default off.

.PARAMETER SkipSignInActivity
    Skip the beta /reports/servicePrincipalSignInActivity call. Use when
    Reports.Read.All / AuditLog.Read.All are not granted, or when the
    beta endpoint is unavailable.

.EXAMPLE
    PS> .\Get-EntraAppCredentialInventory.ps1 -OutputPath .\out

.EXAMPLE
    PS> .\Get-EntraAppCredentialInventory.ps1 -OutputPath .\out -StaleDays 365 -IncludeMicrosoftBuiltIn

.NOTES
    Required Graph scopes:
      Application.Read.All
      Directory.Read.All
      AuditLog.Read.All
      Reports.Read.All

    Required modules (PowerShell 7+):
      Microsoft.Graph.Applications
      Microsoft.Graph.Identity.DirectoryManagement
      Microsoft.Graph.Authentication

    Sign in before running:
      Connect-MgGraph -Scopes Application.Read.All, Directory.Read.All, AuditLog.Read.All, Reports.Read.All
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string] $OutputPath,

    [int]    $ExpiryWarningDays = 90,
    [int]    $StaleDays         = 180,
    [switch] $IncludeMicrosoftBuiltIn,
    [switch] $SkipSignInActivity
)

# WHY: ErrorActionPreference=Stop turns non-terminating SDK errors into terminating
#      ones so a typo or schema drift fails loudly rather than producing empty output.
# WHY: StrictMode 3.0 catches references to non-existent properties on PSCustomObject.
#      It does NOT apply to hashtables — which is exactly why the Graph beta call below
#      uses hashtable output. See README "How the script works" sections 1 and 4.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 3.0

# ----- Setup -----------------------------------------------------------------

# WHY: Missing scopes are warned, not errored. A reader with partial permissions
#      (e.g. Application.Read.All but no Reports.Read.All) can still get a useful
#      inventory; the sign-in activity columns will just be empty. Fail-soft beats
#      fail-fast for a learning / read-only tool.
function Test-GraphContext {
    $ctx = Get-MgContext
    if (-not $ctx) {
        throw "Not connected to Microsoft Graph. Run: Connect-MgGraph -Scopes Application.Read.All, Directory.Read.All, AuditLog.Read.All, Reports.Read.All"
    }
    $required = @('Application.Read.All', 'Directory.Read.All', 'AuditLog.Read.All', 'Reports.Read.All')
    $missing  = $required | Where-Object { $_ -notin $ctx.Scopes }
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

$ctx       = Test-GraphContext
$out       = New-OutputFolder -Path $OutputPath
$timestamp = (Get-Date).ToString('yyyy-MM-ddTHH-mm-ss')
$appsCsv   = Join-Path $out "apps-$timestamp.csv"
$credsCsv  = Join-Path $out "credentials-$timestamp.csv"
$appsJson  = Join-Path $out "apps-$timestamp.json"
$summary   = Join-Path $out "summary-$timestamp.txt"

Write-Host ("Tenant: {0}" -f $ctx.TenantId) -ForegroundColor Cyan
Write-Host ("Output: {0}" -f $out)          -ForegroundColor Cyan

# ----- Helpers ---------------------------------------------------------------

# WHY: Conservative regex list. Only well-known Azure-hosted domains and a few
#      common alternatives. A reply URL on mycompany.com tells us nothing about
#      where the workload runs — we leave those unclassified and let other signals
#      (tags, owners, sign-in activity) drive the disposition.
function Get-ReplyUrlHint {
    param([string[]] $ReplyUrls)
    if (-not $ReplyUrls) { return @() }

    $hints = New-Object System.Collections.Generic.List[string]
    foreach ($url in $ReplyUrls) {
        if (-not $url) { continue }
        switch -Regex ($url) {
            'azurewebsites\.net'                  { $hints.Add('AppService');     break }
            'azurecontainerapps\.io'              { $hints.Add('ContainerApps');  break }
            'azurestaticapps\.net'                { $hints.Add('StaticWebApps');  break }
            'azurefd\.(net|com)'                  { $hints.Add('FrontDoor');      break }
            'azure-api\.net'                      { $hints.Add('APIManagement');  break }
            'azureedge\.net'                      { $hints.Add('CDN');            break }
            'vault\.azure\.net'                   { $hints.Add('KeyVault');       break }
            'database\.windows\.net'              { $hints.Add('AzureSQL');       break }
            'servicebus\.windows\.net'            { $hints.Add('ServiceBus');     break }
            'github\.io'                          { $hints.Add('GitHubPages');    break }
            'vercel\.app'                         { $hints.Add('Vercel');         break }
            'netlify\.app'                        { $hints.Add('Netlify');        break }
            '(cloudfront\.net|amazonaws\.com)'    { $hints.Add('AWS');            break }
            '(localhost|127\.0\.0\.1)'            { $hints.Add('Localhost');      break }
            default { }
        }
    }
    return @($hints | Select-Object -Unique)
}

# WHY: All timestamps normalized to UTC before subtraction. Graph returns UTC;
#      PowerShell's Get-Date returns local time. Failing to normalize gives
#      off-by-one days near midnight in your timezone. [Nullable[datetime]]
#      lets callers skip a guard for every invocation.
function ConvertTo-Days {
    param(
        [Nullable[datetime]] $From,
        [Nullable[datetime]] $To
    )
    if (-not $From -or -not $To) { return $null }
    return [int][math]::Floor((($To.ToUniversalTime() - $From.ToUniversalTime())).TotalDays)
}

# WHY: Disposition is a single mutually-exclusive starting hint per app, with
#      accumulated "reasons" describing why we landed there. Cascade order matters:
#        1. NO_SECRET short-circuits — nothing to migrate.
#        2. STALE_NO_SIGNIN short-circuits — Track 3 will delete; no need to classify
#           where it runs.
#        3. KEEP_SECRET_CARVEOUT — explicit human tag overrides heuristic signals.
#        4. Tag/note hints (GitHub / ADO / K8s) — human-curated, most reliable.
#        5. Reply-URL hints — heuristic, correct most of the time but not authoritative.
#        6. INVESTIGATE — no signal landed.
#      See README "How the script works" section 7.
function Get-Disposition {
    param(
        [int]      $SecretCount,
        [int]      $CertCount,
        [int]      $FederatedCount,
        [int]      $OwnerCount,
        [object]   $SpLastSignInDays,    # int or $null
        [string[]] $ReplyUrlHints,
        [string]   $TagsJoined,
        [string]   $Notes,
        [string]   $SignInAudience,
        [int]      $StaleDays
    )

    $reasons = New-Object System.Collections.Generic.List[string]
    $disposition = 'INVESTIGATE'

    $haystack = ($TagsJoined + ' ' + ($Notes ?? '')).Trim()

    if ($SignInAudience -in 'AzureADMultipleOrgs','PersonalMicrosoftAccount','AzureADandPersonalMicrosoftAccount') {
        $reasons.Add('multi-tenant audience')
    }

    if ($SecretCount -eq 0) {
        $reasons.Add('no client secrets present')
        return @{ Disposition = 'NO_SECRET'; Reasons = ($reasons -join '; ') }
    }

    if ($null -ne $SpLastSignInDays -and [int]$SpLastSignInDays -gt $StaleDays) {
        $reasons.Add(("SP last signed in {0}d ago (> {1})" -f $SpLastSignInDays, $StaleDays))
        return @{ Disposition = 'STALE_NO_SIGNIN'; Reasons = ($reasons -join '; ') }
    }

    if ($haystack -match 'carveout:') {
        $reasons.Add('carveout tag/note present')
        return @{ Disposition = 'KEEP_SECRET_CARVEOUT'; Reasons = ($reasons -join '; ') }
    }

    if ($haystack -match '(?i)\bgithub\b') {
        $reasons.Add('GitHub mention in tags/notes')
        return @{ Disposition = 'MIGRATE_TO_WIF_GITHUB'; Reasons = ($reasons -join '; ') }
    }

    if ($haystack -match '(?i)\b(azure\s*devops|ado|vsts)\b') {
        $reasons.Add('Azure DevOps mention in tags/notes')
        return @{ Disposition = 'MIGRATE_TO_WIF_ADO'; Reasons = ($reasons -join '; ') }
    }

    if ($haystack -match '(?i)\b(aks|kubernetes|k8s)\b') {
        $reasons.Add('Kubernetes mention in tags/notes')
        return @{ Disposition = 'MIGRATE_TO_WIF_K8S'; Reasons = ($reasons -join '; ') }
    }

    $azureHints = @('AppService','ContainerApps','StaticWebApps','FrontDoor','APIManagement','KeyVault','AzureSQL','ServiceBus')
    $nonAzureHints = @('AWS','Vercel','Netlify','GitHubPages')

    if ($ReplyUrlHints | Where-Object { $_ -in $azureHints }) {
        $reasons.Add(("Azure-hosted hints: {0}" -f (($ReplyUrlHints | Where-Object { $_ -in $azureHints }) -join ',')))
        return @{ Disposition = 'MIGRATE_TO_MI'; Reasons = ($reasons -join '; ') }
    }

    if ($ReplyUrlHints | Where-Object { $_ -in $nonAzureHints }) {
        $reasons.Add(("Non-Azure host hints: {0}" -f (($ReplyUrlHints | Where-Object { $_ -in $nonAzureHints }) -join ',')))
        return @{ Disposition = 'MIGRATE_TO_WIF_OR_CERT'; Reasons = ($reasons -join '; ') }
    }

    if ($OwnerCount -eq 0) {
        $reasons.Add('no owners')
    }

    return @{ Disposition = $disposition; Reasons = ($reasons -join '; ') }
}

function ConvertTo-Datetime {
    param([object] $Value)
    if (-not $Value) { return $null }
    if ($Value -is [datetime]) { return $Value.ToUniversalTime() }
    try { return ([datetime]::Parse([string]$Value)).ToUniversalTime() } catch { return $null }
}

# ----- Enumerate apps --------------------------------------------------------

Write-Host "Enumerating application registrations..." -ForegroundColor Cyan
$apps = Get-MgApplication -All -PageSize 999 -Property @(
    'Id','AppId','DisplayName','PublisherDomain','SignInAudience',
    'PasswordCredentials','KeyCredentials',
    'Tags','Notes','ReplyUrls','IdentifierUris'
)

Write-Host ("  found {0} application(s)" -f $apps.Count)

# WHY: First-party Microsoft SPs (Graph, Exchange, Teams, etc.) appear in every
#      tenant. Their credentials are Microsoft-managed and customers can't rotate
#      them, so they add noise to a migration inventory. -IncludeMicrosoftBuiltIn
#      brings them back if you want to study the full picture.
if (-not $IncludeMicrosoftBuiltIn) {
    $before = $apps.Count
    $apps   = $apps | Where-Object { $_.PublisherDomain -notlike '*microsoft.com' }
    Write-Host ("  filtered out {0} Microsoft-published app(s)" -f ($before - $apps.Count))
}

# ----- SP sign-in activity ---------------------------------------------------

$spActivity = @{}
if (-not $SkipSignInActivity) {
    Write-Host "Fetching service principal sign-in activity (beta endpoint)..." -ForegroundColor Cyan
    try {
        # WHY: /beta endpoint. The v1.0 surface only exposes per-user interactive
        #      sign-ins. We need the per-SP rollup which is still in /beta as of 2026.
        #      Two timestamps come back per SP: lastSignInActivity (workload flows
        #      like client_credentials / federated / MI) and applicationAuthenticationClient
        #      (delegated). For secret-migration we care about the first.
        $uri = 'https://graph.microsoft.com/beta/reports/servicePrincipalSignInActivity?$top=999'
        do {
            # WHY: Hashtable output (the default). PSCustomObject + StrictMode 3.0
            #      throws on missing properties — bad for a beta endpoint whose
            #      schema may omit fields per row. Hashtables return $null on
            #      missing keys, which is the tolerance we want.
            $page = Invoke-MgGraphRequest -Method GET -Uri $uri
            foreach ($row in $page['value']) {
                if ($row['appId']) { $spActivity[$row['appId']] = $row }
            }
            $uri = $page['@odata.nextLink']
        } while ($uri)
        Write-Host ("  loaded sign-in activity for {0} SP(s)" -f $spActivity.Count)
    }
    catch {
        Write-Warning ("Could not load servicePrincipalSignInActivity: {0}" -f $_.Exception.Message)
    }
}
else {
    Write-Host "Skipping sign-in activity collection (-SkipSignInActivity)." -ForegroundColor Yellow
}

# ----- Build records ---------------------------------------------------------

Write-Host "Building per-app and per-credential records..." -ForegroundColor Cyan

$now         = (Get-Date).ToUniversalTime()
$appRecords  = New-Object System.Collections.Generic.List[object]
$credRecords = New-Object System.Collections.Generic.List[object]

$i = 0
foreach ($app in $apps) {
    $i++
    if ($i % 50 -eq 0) { Write-Host ("  processed {0}/{1}" -f $i, $apps.Count) }

    # Owners
    # WHY: Get-MgApplicationOwner returns DirectoryObject; concrete subtype
    #      (User / SP / Group) lives in AdditionalProperties (a Dictionary).
    #      Hashtable-style [] indexing tolerates missing keys under StrictMode,
    #      unlike .Property access. Fallback chain: UPN (outreach-friendly) →
    #      displayName (for non-user owners like a workspace SP) → object ID.
    $owners = @()
    try {
        $owners = @(
            Get-MgApplicationOwner -ApplicationId $app.Id -All -ErrorAction Stop | ForEach-Object {
                $ap = $_.AdditionalProperties
                if     ($ap['userPrincipalName']) { $ap['userPrincipalName'] }
                elseif ($ap['displayName'])       { $ap['displayName'] }
                else                              { $_.Id }
            }
        )
    }
    catch {
        Write-Verbose ("Could not read owners for {0}: {1}" -f $app.DisplayName, $_.Exception.Message)
    }

    # Federated credentials
    $fedCreds = @()
    try {
        $fedCreds = @(Get-MgApplicationFederatedIdentityCredential -ApplicationId $app.Id -All -ErrorAction Stop)
    }
    catch {
        Write-Verbose ("Could not read federated credentials for {0}: {1}" -f $app.DisplayName, $_.Exception.Message)
    }

    # Credentials
    $secrets    = @($app.PasswordCredentials)
    $certs      = @(($app.KeyCredentials) | Where-Object { $_.Type -eq 'AsymmetricX509Cert' })

    $nextExpiry = $null
    if ($secrets.Count -gt 0) {
        $nextExpiry = ($secrets | Sort-Object EndDateTime | Select-Object -First 1).EndDateTime
    }
    $daysToNext   = ConvertTo-Days -From $now -To $nextExpiry
    $expiringSoon = @($secrets | Where-Object { $_.EndDateTime -gt $now -and $_.EndDateTime -lt $now.AddDays($ExpiryWarningDays) }).Count
    $expired      = @($secrets | Where-Object { $_.EndDateTime -le $now }).Count

    # SP sign-in activity
    $spLastSignIn     = $null
    $spLastSignInDays = $null
    $appLastSignIn    = $null

    if ($spActivity.ContainsKey($app.AppId)) {
        $row = $spActivity[$app.AppId]
        $lsa = $row['lastSignInActivity']
        if ($lsa -and $lsa['lastSignInDateTime']) {
            $spLastSignIn     = ConvertTo-Datetime $lsa['lastSignInDateTime']
            $spLastSignInDays = ConvertTo-Days -From $spLastSignIn -To $now
        }
        $aaca = $row['applicationAuthenticationClientSignInActivity']
        if ($aaca -and $aaca['lastSignInDateTime']) {
            $appLastSignIn = ConvertTo-Datetime $aaca['lastSignInDateTime']
        }
    }

    # Hints + disposition
    $hints      = Get-ReplyUrlHint -ReplyUrls $app.ReplyUrls
    $tagsJoined = (($app.Tags | Where-Object { $_ }) -join ' ')

    $disp = Get-Disposition `
        -SecretCount      $secrets.Count `
        -CertCount        $certs.Count `
        -FederatedCount   $fedCreds.Count `
        -OwnerCount       $owners.Count `
        -SpLastSignInDays $spLastSignInDays `
        -ReplyUrlHints    $hints `
        -TagsJoined       $tagsJoined `
        -Notes            $app.Notes `
        -SignInAudience   $app.SignInAudience `
        -StaleDays        $StaleDays

    $appRecords.Add([pscustomobject]@{
        AppId                  = $app.AppId
        ObjectId               = $app.Id
        DisplayName            = $app.DisplayName
        Publisher              = $app.PublisherDomain
        SignInAudience         = $app.SignInAudience
        OwnerCount             = $owners.Count
        OwnerUpns              = ($owners -join ';')
        SecretCount            = $secrets.Count
        CertCount              = $certs.Count
        FederatedCredCount     = $fedCreds.Count
        NextSecretExpiry       = if ($nextExpiry)    { $nextExpiry.ToString('o') }    else { $null }
        DaysToNextSecretExpiry = $daysToNext
        SecretsExpiringSoon    = $expiringSoon
        SecretsAlreadyExpired  = $expired
        SpLastSignIn           = if ($spLastSignIn)  { $spLastSignIn.ToString('o') }  else { $null }
        SpLastSignInDays       = $spLastSignInDays
        AppLastSignIn          = if ($appLastSignIn) { $appLastSignIn.ToString('o') } else { $null }
        ReplyUrls              = (($app.ReplyUrls | Where-Object { $_ }) -join ';')
        ReplyUrlHints          = ($hints -join ';')
        Tags                   = (($app.Tags     | Where-Object { $_ }) -join ';')
        Notes                  = $app.Notes
        Disposition            = $disp.Disposition
        DispositionReasons     = $disp.Reasons
    }) | Out-Null

    # Per-credential rows
    foreach ($s in $secrets) {
        $credRecords.Add([pscustomobject]@{
            AppId          = $app.AppId
            AppDisplayName = $app.DisplayName
            CredentialType = 'Secret'
            KeyId          = $s.KeyId
            DisplayName    = $s.DisplayName
            Hint           = $s.Hint
            StartDate      = if ($s.StartDateTime) { $s.StartDateTime.ToString('o') } else { $null }
            EndDate        = if ($s.EndDateTime)   { $s.EndDateTime.ToString('o') }   else { $null }
            DaysToExpiry   = ConvertTo-Days -From $now -To $s.EndDateTime
            Issuer         = $null
            Subject        = $null
            Audiences      = $null
        }) | Out-Null
    }
    foreach ($c in $certs) {
        $credRecords.Add([pscustomobject]@{
            AppId          = $app.AppId
            AppDisplayName = $app.DisplayName
            CredentialType = 'Certificate'
            KeyId          = $c.KeyId
            DisplayName    = $c.DisplayName
            Hint           = $null
            StartDate      = if ($c.StartDateTime) { $c.StartDateTime.ToString('o') } else { $null }
            EndDate        = if ($c.EndDateTime)   { $c.EndDateTime.ToString('o') }   else { $null }
            DaysToExpiry   = ConvertTo-Days -From $now -To $c.EndDateTime
            Issuer         = $null
            Subject        = $null
            Audiences      = $null
        }) | Out-Null
    }
    foreach ($f in $fedCreds) {
        $credRecords.Add([pscustomobject]@{
            AppId          = $app.AppId
            AppDisplayName = $app.DisplayName
            CredentialType = 'Federated'
            KeyId          = $f.Id
            DisplayName    = $f.Name
            Hint           = $null
            StartDate      = $null
            EndDate        = $null
            DaysToExpiry   = $null
            Issuer         = $f.Issuer
            Subject        = $f.Subject
            Audiences      = (($f.Audiences) -join ',')
        }) | Out-Null
    }
}

# ----- Write outputs ---------------------------------------------------------

Write-Host "Writing reports..." -ForegroundColor Cyan
$appRecords  | Export-Csv -LiteralPath $appsCsv  -NoTypeInformation -Encoding UTF8
$credRecords | Export-Csv -LiteralPath $credsCsv -NoTypeInformation -Encoding UTF8
$appRecords  | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $appsJson -Encoding UTF8

# ----- Summary ---------------------------------------------------------------

$dispGroups    = $appRecords | Group-Object Disposition | Sort-Object Count -Descending
$secretTotal   = ($appRecords | Measure-Object SecretCount -Sum).Sum
$appsWithSec   = @($appRecords | Where-Object { [int]$_.SecretCount -gt 0 }).Count
$expiredTotal  = ($appRecords | Measure-Object SecretsAlreadyExpired -Sum).Sum
$soonTotal     = ($appRecords | Measure-Object SecretsExpiringSoon -Sum).Sum

$summaryLines = @(
    "Entra ID app credential inventory"
    ("Tenant:    {0}" -f $ctx.TenantId)
    ("Generated: {0}" -f (Get-Date).ToString('o'))
    ""
    ("Apps total:                  {0}" -f $appRecords.Count)
    ("Apps with >=1 client secret: {0}" -f $appsWithSec)
    ("Total client secrets:        {0}" -f $secretTotal)
    ("Already-expired secrets:     {0}" -f $expiredTotal)
    ("Secrets expiring < {0,3} d:     {1}" -f $ExpiryWarningDays, $soonTotal)
    ""
    "Disposition breakdown:"
)
foreach ($g in $dispGroups) {
    $summaryLines += ("  {0,-28} {1,5}" -f $g.Name, $g.Count)
}
$summaryLines | Set-Content -LiteralPath $summary -Encoding UTF8

Write-Host ""
Write-Host "Done." -ForegroundColor Green
Write-Host ("  Apps CSV:        {0}" -f $appsCsv)
Write-Host ("  Credentials CSV: {0}" -f $credsCsv)
Write-Host ("  Apps JSON:       {0}" -f $appsJson)
Write-Host ("  Summary:         {0}" -f $summary)
Write-Host ""
$summaryLines | Write-Host
