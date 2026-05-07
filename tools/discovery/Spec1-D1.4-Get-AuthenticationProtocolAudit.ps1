<#
.SYNOPSIS
    UIAO Spec 1 — D1.4: Authentication Protocol Audit
.DESCRIPTION
    Identifies all computer objects using legacy or complex authentication
    protocols that must be addressed before domain-join removal:

    1. Kerberos Constrained Delegation (KCD) — computer objects with
       msDS-AllowedToDelegateTo populated
    2. Resource-Based Constrained Delegation (RBCD) — computer objects with
       msDS-AllowedToActOnBehalfOfOtherIdentity populated
    3. Unconstrained Delegation — computer objects with
       TrustedForDelegation flag (excluding DCs)
    4. NTLM Dependency Indicators — computer objects in NTLM-exempt
       security groups, computers with NTLM audit events (if Defender
       for Identity data available)
    5. Certificate-Based Machine Auth — computer objects with certificates
       in userCertificate attribute, auto-enrollment flags
    6. Protocol Transition — TrustedToAuthForDelegation flag
    7. SPN-to-Delegation Chain Mapping — which SPNs are delegated to
       which target services, building full delegation chains

    Outputs structured JSON with delegation chain graphs, risk
    classifications, and migration recommendations.

    Ref: UIAO_136 Spec 1, Phase 1, Deliverable D1.4
         Feeds: D1.5 (Kerberos SPN Inventory), D2.1 (Target State Architecture)
.PARAMETER OutputPath
    Directory for output files. Defaults to .\output
.PARAMETER DomainController
    Target a specific DC. If omitted, uses auto-discovery.
.PARAMETER SearchBase
    Optional AD search base (DN). If omitted, searches entire domain.
.PARAMETER D1InputFile
    Optional path to D1.1 Computer Inventory JSON for cross-reference.
.EXAMPLE
    .\Spec1-D1.4-Get-AuthenticationProtocolAudit.ps1
    .\Spec1-D1.4-Get-AuthenticationProtocolAudit.ps1 -OutputPath C:\exports
.NOTES
    Requires: ActiveDirectory PowerShell module (RSAT)
    Requires: Read access to computer objects and delegation attributes
#>

[CmdletBinding()]
param(
    [string]$OutputPath = ".\output",
    [string]$DomainController,
    [string]$SearchBase,
    [string]$D1InputFile
)

$ErrorActionPreference = "Stop"

if (-not (Get-Module -ListAvailable -Name ActiveDirectory)) {
    Write-Error "ActiveDirectory module not found. Install RSAT."
    return
}
Import-Module ActiveDirectory -ErrorAction Stop

if (-not (Test-Path $OutputPath)) {
    New-Item -Path $OutputPath -ItemType Directory -Force | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$domain = (Get-ADDomain).DNSRoot
$outPrefix = "UIAO_Spec1_D1.4_AuthProtocolAudit_${domain}_${timestamp}"

Write-Host "`n================================================================" -ForegroundColor Cyan
Write-Host "  UIAO Spec 1 — D1.4: Authentication Protocol Audit"            -ForegroundColor Cyan
Write-Host "  Domain:    $domain"                                            -ForegroundColor Cyan
Write-Host "  Timestamp: $timestamp"                                         -ForegroundColor Cyan
Write-Host "================================================================`n" -ForegroundColor Cyan

$adParams = @{}
if ($DomainController) { $adParams['Server'] = $DomainController }
if ($SearchBase) { $adParams['SearchBase'] = $SearchBase }

$compProps = @(
    'DistinguishedName', 'Name', 'DNSHostName', 'SamAccountName',
    'ObjectGUID', 'Enabled', 'OperatingSystem',
    'ServicePrincipalName', 'LastLogonDate',
    'TrustedForDelegation', 'TrustedToAuthForDelegation',
    'msDS-AllowedToDelegateTo',
    'msDS-AllowedToActOnBehalfOfOtherIdentity',
    'PrimaryGroupID', 'UserAccountControl',
    'userCertificate', 'WhenCreated', 'WhenChanged',
    'extensionAttribute1'
)

# ══════════════════════════════════════════════════════════════
# Pass 1: Unconstrained Delegation (Excluding DCs)
# ══════════════════════════════════════════════════════════════
Write-Host "  [1/6] Unconstrained delegation scan..." -ForegroundColor Yellow

$unconstrainedAll = @(Get-ADComputer -Filter { TrustedForDelegation -eq $true } `
    -Properties $compProps @adParams)

# DCs have unconstrained delegation by design (PrimaryGroupID = 516)
$unconstrainedDCs = @($unconstrainedAll | Where-Object { $_.PrimaryGroupID -eq 516 })
$unconstrainedNonDC = @($unconstrainedAll | Where-Object { $_.PrimaryGroupID -ne 516 })

Write-Host "    Domain Controllers (expected):     $($unconstrainedDCs.Count)" -ForegroundColor DarkGray
Write-Host "    Non-DC unconstrained (CRITICAL):   $($unconstrainedNonDC.Count)" -ForegroundColor $(if ($unconstrainedNonDC.Count -gt 0) { 'Red' } else { 'Green' })

$unconstrainedResults = $unconstrainedNonDC | ForEach-Object {
    [ordered]@{
        Name              = $_.Name
        DNSHostName       = $_.DNSHostName
        ObjectGUID        = $_.ObjectGUID.ToString()
        DistinguishedName = $_.DistinguishedName
        OperatingSystem   = $_.OperatingSystem
        Enabled           = $_.Enabled
        LastLogonDate     = if ($_.LastLogonDate) { $_.LastLogonDate.ToString("o") } else { $null }
        SPNCount          = @($_.ServicePrincipalName).Count
        SPNs              = @($_.ServicePrincipalName)
        OrgPath           = $_.extensionAttribute1
        DelegationType    = "Unconstrained"
        Risk              = "CRITICAL — can impersonate any user to any service in the domain"
        Remediation       = "Convert to Constrained Delegation (KCD) or Resource-Based (RBCD), or remove delegation entirely if not required"
        MigrationImpact   = "Must be resolved BEFORE domain-join removal — unconstrained delegation cannot exist in cloud-native state"
    }
}

# ══════════════════════════════════════════════════════════════
# Pass 2: Kerberos Constrained Delegation (KCD)
# ══════════════════════════════════════════════════════════════
Write-Host "  [2/6] Constrained delegation (KCD) scan..." -ForegroundColor Yellow

$kcdComputers = @(Get-ADComputer -Filter "msDS-AllowedToDelegateTo -like '*'" `
    -Properties $compProps @adParams)

Write-Host "    Computers with KCD: $($kcdComputers.Count)" -ForegroundColor $(if ($kcdComputers.Count -gt 0) { 'Yellow' } else { 'Green' })

$kcdResults = [System.Collections.Generic.List[object]]::new()
foreach ($comp in $kcdComputers) {
    $delegationTargets = @($comp.'msDS-AllowedToDelegateTo')

    # Parse delegation targets into structured form
    $parsedTargets = $delegationTargets | ForEach-Object {
        $spn = $_
        $parts = $spn -split '/'
        [ordered]@{
            FullSPN       = $spn
            ServiceClass  = if ($parts.Count -ge 1) { $parts[0] } else { $null }
            HostOrService = if ($parts.Count -ge 2) { $parts[1] } else { $null }
            Port          = if ($parts.Count -ge 3) { $parts[2] } else { $null }
        }
    }

    # Classify delegation risk
    $serviceClasses = @($parsedTargets | ForEach-Object { $_.ServiceClass } | Sort-Object -Unique)
    $hasProtocolTransition = [bool]$comp.TrustedToAuthForDelegation

    $risk = "MEDIUM — constrained delegation with defined targets"
    if ($hasProtocolTransition) {
        $risk = "HIGH — protocol transition enabled (any auth protocol accepted)"
    }
    if ($serviceClasses -contains 'ldap' -or $serviceClasses -contains 'cifs') {
        $risk = "HIGH — delegation to sensitive services (LDAP/CIFS)"
    }
    if ($hasProtocolTransition -and ($serviceClasses -contains 'ldap')) {
        $risk = "CRITICAL — protocol transition to LDAP (potential DC compromise)"
    }

    $kcdResults.Add([ordered]@{
        Name                    = $comp.Name
        DNSHostName             = $comp.DNSHostName
        ObjectGUID              = $comp.ObjectGUID.ToString()
        DistinguishedName       = $comp.DistinguishedName
        OperatingSystem         = $comp.OperatingSystem
        Enabled                 = $comp.Enabled
        LastLogonDate           = if ($comp.LastLogonDate) { $comp.LastLogonDate.ToString("o") } else { $null }
        OrgPath                 = $comp.extensionAttribute1
        DelegationType          = "Constrained (KCD)"
        ProtocolTransition      = $hasProtocolTransition
        DelegationTargets       = @($parsedTargets)
        DelegationTargetCount   = $delegationTargets.Count
        TargetServiceClasses    = $serviceClasses
        DelegationTargetSPNs    = $delegationTargets
        Risk                    = $risk
        Remediation             = if ($hasProtocolTransition) {
            "Review protocol transition necessity. Convert to RBCD where possible. For cloud migration: Entra Application Proxy or Azure AD Kerberos for on-prem resource access."
        } else {
            "Document business justification. For cloud migration: convert to Entra Application Proxy (web apps) or retain KCD during coexistence."
        }
        MigrationImpact         = "KCD chains must be mapped and tested before migrating either the source or target server. Break one link and the chain fails."
    })
}

# ══════════════════════════════════════════════════════════════
# Pass 3: Resource-Based Constrained Delegation (RBCD)
# ══════════════════════════════════════════════════════════════
Write-Host "  [3/6] Resource-Based Constrained Delegation (RBCD) scan..." -ForegroundColor Yellow

$rbcdComputers = @(Get-ADComputer -Filter * -Properties $compProps @adParams |
    Where-Object { $_.'msDS-AllowedToActOnBehalfOfOtherIdentity' -ne $null })

Write-Host "    Computers with RBCD: $($rbcdComputers.Count)" -ForegroundColor $(if ($rbcdComputers.Count -gt 0) { 'Yellow' } else { 'Green' })

$rbcdResults = $rbcdComputers | ForEach-Object {
    $rbcdSd = $_.'msDS-AllowedToActOnBehalfOfOtherIdentity'
    $allowedPrincipals = @()

    if ($rbcdSd) {
        try {
            $sd = New-Object System.DirectoryServices.ActiveDirectorySecurity
            $sd.SetSecurityDescriptorBinaryForm($rbcdSd)
            $allowedPrincipals = @($sd.Access | ForEach-Object {
                [ordered]@{
                    Principal    = $_.IdentityReference.Value
                    AccessType   = $_.AccessControlType.ToString()
                    Rights       = $_.ActiveDirectoryRights.ToString()
                }
            })
        }
        catch {
            $allowedPrincipals = @([ordered]@{ Error = "Could not parse RBCD descriptor: $($_.Exception.Message)" })
        }
    }

    [ordered]@{
        Name                  = $_.Name
        DNSHostName           = $_.DNSHostName
        ObjectGUID            = $_.ObjectGUID.ToString()
        DistinguishedName     = $_.DistinguishedName
        OperatingSystem       = $_.OperatingSystem
        Enabled               = $_.Enabled
        LastLogonDate         = if ($_.LastLogonDate) { $_.LastLogonDate.ToString("o") } else { $null }
        OrgPath               = $_.extensionAttribute1
        DelegationType        = "Resource-Based (RBCD)"
        AllowedPrincipals     = $allowedPrincipals
        AllowedPrincipalCount = $allowedPrincipals.Count
        Risk                  = "MEDIUM — RBCD is the modern pattern but must be documented"
        Remediation           = "RBCD is the preferred delegation model. Document all principals. For cloud migration: convert to Managed Identity where applicable."
        MigrationImpact       = "RBCD is set on the target (resource), not the source. Migration order matters — migrate the resource last."
    }
}

# ══════════════════════════════════════════════════════════════
# Pass 4: Protocol Transition
# ══════════════════════════════════════════════════════════════
Write-Host "  [4/6] Protocol transition scan..." -ForegroundColor Yellow

$protocolTransition = @(Get-ADComputer -Filter { TrustedToAuthForDelegation -eq $true } `
    -Properties $compProps @adParams)

# Filter to non-KCD (those already captured) — just count overlap
$ptOnlyCount = ($protocolTransition | Where-Object {
    -not ($kcdComputers | Where-Object { $_.ObjectGUID -eq $_.ObjectGUID })
}).Count

Write-Host "    Protocol transition enabled: $($protocolTransition.Count) (overlap with KCD captured above)" -ForegroundColor DarkGray

# ══════════════════════════════════════════════════════════════
# Pass 5: Certificate-Based Machine Authentication
# ══════════════════════════════════════════════════════════════
Write-Host "  [5/6] Certificate-based machine auth scan..." -ForegroundColor Yellow

$certComputers = @(Get-ADComputer -Filter * -Properties 'Name','DNSHostName','ObjectGUID',
    'DistinguishedName','OperatingSystem','Enabled','userCertificate',
    'LastLogonDate','extensionAttribute1' @adParams |
    Where-Object { $_.userCertificate -and $_.userCertificate.Count -gt 0 })

Write-Host "    Computers with certificates in AD: $($certComputers.Count)" -ForegroundColor DarkGray

$certResults = $certComputers | ForEach-Object {
    $certs = @($_.userCertificate)
    $certDetails = @()

    foreach ($certBytes in $certs) {
        try {
            $cert = [System.Security.Cryptography.X509Certificates.X509Certificate2]::new($certBytes)
            $certDetails += [ordered]@{
                Subject      = $cert.Subject
                Issuer       = $cert.Issuer
                NotBefore    = $cert.NotBefore.ToString("o")
                NotAfter     = $cert.NotAfter.ToString("o")
                Thumbprint   = $cert.Thumbprint
                IsExpired    = ($cert.NotAfter -lt (Get-Date))
                KeyUsage     = $cert.Extensions |
                    Where-Object { $_ -is [System.Security.Cryptography.X509Certificates.X509KeyUsageExtension] } |
                    ForEach-Object { $_.KeyUsages.ToString() }
                DaysToExpiry = [int]($cert.NotAfter - (Get-Date)).TotalDays
            }
        }
        catch {
            $certDetails += [ordered]@{ Error = "Could not parse certificate: $($_.Exception.Message)" }
        }
    }

    $validCerts = @($certDetails | Where-Object { -not $_.IsExpired -and -not $_.Error })
    $expiredCerts = @($certDetails | Where-Object { $_.IsExpired })

    [ordered]@{
        Name              = $_.Name
        DNSHostName       = $_.DNSHostName
        ObjectGUID        = $_.ObjectGUID.ToString()
        DistinguishedName = $_.DistinguishedName
        OperatingSystem   = $_.OperatingSystem
        Enabled           = $_.Enabled
        LastLogonDate     = if ($_.LastLogonDate) { $_.LastLogonDate.ToString("o") } else { $null }
        OrgPath           = $_.extensionAttribute1
        TotalCertificates = $certs.Count
        ValidCertificates = $validCerts.Count
        ExpiredCertificates = $expiredCerts.Count
        Certificates      = $certDetails
        Risk              = if ($validCerts.Count -gt 0) { "LOW — certificate-based auth is supported in Entra ID (CBA)" } else { "NONE — all certificates expired" }
        MigrationImpact   = "Certificate-based machine auth transitions to Entra ID CBA + device certificates (issued by Intune/Cloud PKI). ADCS dependency must be mapped."
    }
}

# ══════════════════════════════════════════════════════════════
# Pass 6: NTLM Dependency Indicators
# ══════════════════════════════════════════════════════════════
Write-Host "  [6/6] NTLM dependency indicators..." -ForegroundColor Yellow

# Check for computers in NTLM-related security groups
$ntlmIndicators = [System.Collections.Generic.List[object]]::new()

# Check network security GPO settings (NTLM restriction groups)
$ntlmGroups = @(
    'Network access: Restrict NTLM: Add server exceptions',
    'Network access: Restrict NTLM: Audit NTLM authentication in this domain',
    'Protected Users'
)

# Check Protected Users group membership
$protectedUsers = @()
try {
    $puGroup = Get-ADGroup -Identity "Protected Users" @adParams -ErrorAction SilentlyContinue
    if ($puGroup) {
        $puMembers = Get-ADGroupMember -Identity $puGroup @adParams -ErrorAction SilentlyContinue
        $protectedUsers = @($puMembers | Where-Object { $_.objectClass -eq 'computer' })
    }
}
catch { }

# Check Authentication Policy Silos
$authPolicies = @()
try {
    $authPolicies = @(Get-ADAuthenticationPolicy -Filter * @adParams -ErrorAction SilentlyContinue)
}
catch { }

$authPolicySilos = @()
try {
    $authPolicySilos = @(Get-ADAuthenticationPolicySilo -Filter * @adParams -ErrorAction SilentlyContinue)
}
catch { }

$ntlmSummary = [ordered]@{
    ProtectedUsersComputers      = $protectedUsers.Count
    ProtectedUsersList           = @($protectedUsers | ForEach-Object { $_.Name })
    AuthenticationPolicies       = $authPolicies.Count
    AuthenticationPolicySilos    = $authPolicySilos.Count
    Note                         = "Full NTLM audit requires Defender for Identity or NTLM audit event log analysis (Event IDs 4624 type 3, 8001-8004). This scan captures structural indicators only."
    Recommendation               = "Enable NTLM auditing (GPO: Network Security > Restrict NTLM > Audit incoming NTLM traffic) on all DCs and servers before migration planning. Feed audit logs to Defender for Identity for comprehensive NTLM dependency mapping."
}

Write-Host "    Protected Users (computers): $($protectedUsers.Count)" -ForegroundColor DarkGray
Write-Host "    Authentication Policies:     $($authPolicies.Count)" -ForegroundColor DarkGray

# ══════════════════════════════════════════════════════════════
# Delegation Chain Graph
# ══════════════════════════════════════════════════════════════
Write-Host "`n  Building delegation chain graph..." -ForegroundColor Yellow

$delegationChains = [System.Collections.Generic.List[object]]::new()

foreach ($kcd in $kcdResults) {
    foreach ($target in $kcd.DelegationTargets) {
        $delegationChains.Add([ordered]@{
            SourceComputer     = $kcd.Name
            SourceDNS          = $kcd.DNSHostName
            TargetSPN          = $target.FullSPN
            TargetServiceClass = $target.ServiceClass
            TargetHost         = $target.HostOrService
            ProtocolTransition = $kcd.ProtocolTransition
            DelegationType     = "KCD"
        })
    }
}

# RBCD chains (reverse direction — target allows source)
foreach ($rbcd in $rbcdResults) {
    foreach ($principal in $rbcd.AllowedPrincipals) {
        if ($principal.Error) { continue }
        $delegationChains.Add([ordered]@{
            SourceComputer     = $principal.Principal
            SourceDNS          = $null
            TargetSPN          = "(any SPN on $($rbcd.Name))"
            TargetServiceClass = "(resource-based)"
            TargetHost         = $rbcd.Name
            ProtocolTransition = $false
            DelegationType     = "RBCD"
        })
    }
}

Write-Host "    Total delegation chain links: $($delegationChains.Count)" -ForegroundColor Green

# ══════════════════════════════════════════════════════════════
# Summary
# ══════════════════════════════════════════════════════════════

$summary = [ordered]@{
    ExportMetadata = [ordered]@{
        Domain           = $domain
        Timestamp        = (Get-Date).ToString("o")
        Script           = "UIAO Spec 1 D1.4 — Authentication Protocol Audit"
        Reference        = "UIAO_136"
    }
    Statistics = [ordered]@{
        DomainControllers             = $unconstrainedDCs.Count
        UnconstrainedDelegation_NonDC = $unconstrainedNonDC.Count
        ConstrainedDelegation_KCD     = $kcdComputers.Count
        ResourceBasedDelegation_RBCD  = @($rbcdResults).Count
        ProtocolTransitionEnabled     = $protocolTransition.Count
        CertificateBasedAuth          = $certComputers.Count
        DelegationChainLinks          = $delegationChains.Count
    }
    RiskSummary = [ordered]@{
        Critical = @(@($unconstrainedResults) | Where-Object { $_.Risk -match 'CRITICAL' }).Count +
                   @($kcdResults | Where-Object { $_.Risk -match 'CRITICAL' }).Count
        High     = @($kcdResults | Where-Object { $_.Risk -match '^HIGH' }).Count
        Medium   = @($kcdResults | Where-Object { $_.Risk -match '^MEDIUM' }).Count +
                   @(@($rbcdResults) | Where-Object { $_.Risk -match '^MEDIUM' }).Count
        Low      = @(@($certResults) | Where-Object { $_.Risk -match '^LOW' }).Count
    }
    NTLMIndicators = $ntlmSummary
    MigrationBlocking = [ordered]@{
        UnconstrainedDelegation = @{
            Count  = $unconstrainedNonDC.Count
            Action = "MUST resolve before any device migration — convert to KCD/RBCD or remove"
        }
        ProtocolTransitionToLDAP = @{
            Count  = @($kcdResults | Where-Object { $_.Risk -match 'CRITICAL' }).Count
            Action = "MUST resolve — potential DC compromise vector"
        }
        KCDChains = @{
            Count  = $kcdComputers.Count
            Action = "Map all chains, document business justification, plan migration order (source before target or vice versa)"
        }
    }
}

# ══════════════════════════════════════════════════════════════
# Output
# ══════════════════════════════════════════════════════════════

$output = [ordered]@{
    Summary                = $summary
    UnconstrainedDelegation = @($unconstrainedResults)
    ConstrainedDelegation   = @($kcdResults)
    ResourceBasedDelegation = @($rbcdResults)
    CertificateBasedAuth    = @($certResults)
    DelegationChainGraph    = @($delegationChains)
}

$jsonFile = Join-Path $OutputPath "${outPrefix}.json"
$output | ConvertTo-Json -Depth 10 | Out-File -FilePath $jsonFile -Encoding utf8NoBOM
Write-Host "`n  JSON: $jsonFile" -ForegroundColor Green

# CSV — delegation chains for graph visualization
$csvFile = Join-Path $OutputPath "${outPrefix}_chains.csv"
$delegationChains | ForEach-Object { [PSCustomObject]$_ } |
    Export-Csv -Path $csvFile -NoTypeInformation -Encoding utf8NoBOM
Write-Host "  CSV (chains): $csvFile" -ForegroundColor Green

# CSV — all findings
$findingsCsv = Join-Path $OutputPath "${outPrefix}_findings.csv"
$allFindings = @()
$allFindings += $unconstrainedResults | ForEach-Object { [PSCustomObject]([ordered]@{ Name=$_.Name; DelegationType=$_.DelegationType; Risk=$_.Risk; ProtocolTransition=$false; TargetCount=0; Remediation=$_.Remediation }) }
$allFindings += $kcdResults | ForEach-Object { [PSCustomObject]([ordered]@{ Name=$_.Name; DelegationType=$_.DelegationType; Risk=$_.Risk; ProtocolTransition=$_.ProtocolTransition; TargetCount=$_.DelegationTargetCount; Remediation=$_.Remediation }) }
$allFindings += @($rbcdResults) | ForEach-Object { [PSCustomObject]([ordered]@{ Name=$_.Name; DelegationType=$_.DelegationType; Risk=$_.Risk; ProtocolTransition=$false; TargetCount=$_.AllowedPrincipalCount; Remediation=$_.Remediation }) }
$allFindings | Export-Csv -Path $findingsCsv -NoTypeInformation -Encoding utf8NoBOM
Write-Host "  CSV (findings): $findingsCsv" -ForegroundColor Green

# Console
Write-Host "`n-- Authentication Protocol Audit --" -ForegroundColor Cyan
Write-Host "  Domain Controllers:               $($unconstrainedDCs.Count)"
Write-Host "  Unconstrained Delegation (non-DC): $($unconstrainedNonDC.Count)" -ForegroundColor $(if ($unconstrainedNonDC.Count -gt 0) { 'Red' } else { 'Green' })
Write-Host "  Constrained Delegation (KCD):      $($kcdComputers.Count)" -ForegroundColor $(if ($kcdComputers.Count -gt 0) { 'Yellow' } else { 'Green' })
Write-Host "  Resource-Based (RBCD):             $(@($rbcdResults).Count)"
Write-Host "  Protocol Transition:               $($protocolTransition.Count)" -ForegroundColor $(if ($protocolTransition.Count -gt 0) { 'Yellow' } else { 'Green' })
Write-Host "  Certificate-Based Auth:            $($certComputers.Count)"
Write-Host "  Delegation Chain Links:            $($delegationChains.Count)"

Write-Host "`n-- Risk Distribution --" -ForegroundColor Cyan
Write-Host "  CRITICAL: $($summary.RiskSummary.Critical)" -ForegroundColor $(if ($summary.RiskSummary.Critical -gt 0) { 'Red' } else { 'Green' })
Write-Host "  HIGH:     $($summary.RiskSummary.High)" -ForegroundColor $(if ($summary.RiskSummary.High -gt 0) { 'Red' } else { 'Green' })
Write-Host "  MEDIUM:   $($summary.RiskSummary.Medium)"
Write-Host "  LOW:      $($summary.RiskSummary.Low)"

if ($unconstrainedNonDC.Count -gt 0) {
    Write-Host "`n-- MIGRATION BLOCKERS: Unconstrained Delegation --" -ForegroundColor Red
    foreach ($u in $unconstrainedResults) {
        Write-Host "  ! $($u.Name) ($($u.OperatingSystem))" -ForegroundColor Red
    }
}

if ($kcdResults.Count -gt 0) {
    Write-Host "`n-- KCD Chains (Top 15) --" -ForegroundColor Yellow
    foreach ($k in ($kcdResults | Select-Object -First 15)) {
        $targets = ($k.TargetServiceClasses -join ',')
        $pt = if ($k.ProtocolTransition) { " [PROTOCOL TRANSITION]" } else { "" }
        Write-Host "  $($k.Name) -> $targets ($($k.DelegationTargetCount) targets)$pt"
    }
}

Write-Host "`n-- Complete --`n" -ForegroundColor Cyan
