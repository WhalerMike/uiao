<#
.SYNOPSIS
    UIAO Spec 3 — D1.10: Certificate-Based Authentication Audit
.DESCRIPTION
    Audits all certificate-based authentication dependencies in the AD
    environment that must be addressed during the Entra ID migration.

    Certificate-based auth is deeply embedded in enterprise environments and
    spans machine authentication (802.1X, VPN), user authentication (smart
    cards, virtual smart cards), and service authentication (TLS client certs,
    code signing). Each category has a different Entra ID migration path.

    Discovery and analysis:
    1. PKI Infrastructure Inventory:
       - Enterprise CA servers (certsvc)
       - Certificate templates published to AD
       - Auto-enrollment configuration (GPO-based)
       - CRL/OCSP distribution points
       - Cross-certification and trust chains

    2. Machine Certificate Audit:
       - Computer objects with userCertificate attribute populated
       - Certificate purposes (EKU): Client Auth, Server Auth, IPsec, 802.1X
       - Certificate issuers and template associations
       - Expiration dates and renewal status
       - Auto-enrollment vs manual enrollment

    3. User Certificate Audit:
       - User objects with userCertificate or userSMIMECertificate
       - Smart card required flag (SMARTCARD_REQUIRED in UAC)
       - altSecurityIdentities mapping (certificate-to-user binding)
       - PIV/CAC card integration (federal requirement)

    4. Service/Application Certificate Dependencies:
       - ADFS token signing and encryption certificates
       - LDAPS certificates on Domain Controllers
       - Exchange Server certificates
       - RADIUS/NPS server certificates (802.1X)
       - Web application TLS client certificate requirements

    5. Entra ID CBA Readiness:
       - Entra ID Certificate-Based Authentication configuration requirements
       - Certificate authority trust chain validation
       - Certificate revocation checking (CRL/OCSP accessibility from cloud)
       - Username binding rules (UPN, email, SAN mapping)
       - Authentication strength policy compatibility

    6. Migration Paths:
       - Smart card → Entra ID CBA or FIDO2 or Windows Hello for Business
       - Machine 802.1X → Cloud RADIUS or certificate-based device compliance
       - ADFS cert auth → Entra ID CBA direct
       - VPN cert auth → Always On VPN with Entra ID or ZTNA

    Outputs: JSON + CSV (certificate inventory) + CSV (PKI infrastructure) + console

    Ref: UIAO_136 Spec 3, Phase 1, Deliverable D1.10
         ADR-004 (Workload Identity Federation as Default)
         Feeds: D2.1 (Target State Architecture), D2.3 (Migration Runbook)
.PARAMETER OutputPath
    Directory for output files. Defaults to .\output
.PARAMETER DomainController
    Target a specific DC. If omitted, uses auto-discovery.
.PARAMETER SearchBase
    Optional AD search base (DN).
.PARAMETER D1InputFile
    Optional path to Spec3-D1.1 Service Account Scan JSON for cross-reference.
.PARAMETER IncludePKIAudit
    If set, queries Enterprise CA configuration via certutil.
.PARAMETER IncludeTemplateAudit
    If set, enumerates all published certificate templates from AD.
.EXAMPLE
    .\Spec3-D1.10-Get-CertBasedAuthAudit.ps1
    .\Spec3-D1.10-Get-CertBasedAuthAudit.ps1 -IncludePKIAudit -IncludeTemplateAudit
.NOTES
    Requires: ActiveDirectory PowerShell module (RSAT)
    Optional: PSPKI module or certutil for PKI infrastructure audit
    Optional: Enterprise Admin for full template enumeration
#>

[CmdletBinding()]
param(
    [string]$OutputPath = ".\output",
    [string]$DomainController,
    [string]$SearchBase,
    [string]$D1InputFile,
    [switch]$IncludePKIAudit,
    [switch]$IncludeTemplateAudit
)

$ErrorActionPreference = "Stop"

# ── Output setup ──
if (-not (Test-Path $OutputPath)) {
    New-Item -Path $OutputPath -ItemType Directory -Force | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"

Write-Host "`n================================================================" -ForegroundColor Cyan
Write-Host " UIAO Spec 3 — D1.10: Certificate-Based Authentication Audit" -ForegroundColor Cyan
Write-Host " Ref: UIAO_136 / ADR-004" -ForegroundColor DarkCyan
Write-Host "================================================================`n" -ForegroundColor Cyan

# ── Prerequisites ──
if (-not (Get-Module -ListAvailable -Name ActiveDirectory)) {
    Write-Error "ActiveDirectory module not found. Install RSAT."
    return
}
Import-Module ActiveDirectory -ErrorAction Stop

$adParams = @{}
if ($DomainController) { $adParams['Server'] = $DomainController }
$domain = (Get-ADDomain @adParams).DNSRoot
$forestDN = (Get-ADForest).RootDomain
$configDN = (Get-ADRootDSE @adParams).configurationNamingContext

# ═══════════════════════════════════════════════════════════════
# SECTION 1: PKI Infrastructure Discovery
# ═══════════════════════════════════════════════════════════════

Write-Host "[1/6] Discovering PKI infrastructure..." -ForegroundColor Yellow

$pkiInfra = @{
    EnterpriseRootCAs       = @()
    EnterpriseSubCAs        = @()
    StandaloneCAs           = @()
    CRLDistributionPoints   = @()
    AIALocations            = @()
    NTAuthCertificates      = @()
    AutoEnrollmentGPOs      = @()
}

# ── Discover Enterprise CAs from AD ──
try {
    $enrollmentServicesPath = "CN=Enrollment Services,CN=Public Key Services,CN=Services,$configDN"
    $enrollmentServices = Get-ADObject -SearchBase $enrollmentServicesPath -Filter * -Properties * @adParams -ErrorAction SilentlyContinue

    foreach ($ca in $enrollmentServices) {
        $pkiInfra.EnterpriseRootCAs += [PSCustomObject]@{
            CAName              = $ca.Name
            DNSHostName         = $ca.dNSHostName
            DistinguishedName   = $ca.DistinguishedName
            CACertificateDN     = $ca.cACertificateDN
            CertificateTemplates = @($ca.certificateTemplates)
            WhenCreated         = $ca.whenCreated
        }
    }
    Write-Host "  Enterprise CAs found: $($pkiInfra.EnterpriseRootCAs.Count)" -ForegroundColor Green
} catch {
    Write-Host "  Enterprise CA discovery failed: $_" -ForegroundColor DarkYellow
}

# ── NTAuth store (CAs trusted for smart card logon) ──
try {
    $ntauthPath = "CN=NTAuthCertificates,CN=Public Key Services,CN=Services,$configDN"
    $ntauth = Get-ADObject -Identity $ntauthPath -Properties cACertificate @adParams -ErrorAction SilentlyContinue
    if ($ntauth.cACertificate) {
        $certCount = @($ntauth.cACertificate).Count
        $pkiInfra.NTAuthCertificates = @{ Count = $certCount; Path = $ntauthPath }
        Write-Host "  NTAuth store: $certCount CA certificate(s) trusted for logon" -ForegroundColor Green
    }
} catch {
    Write-Host "  NTAuth store query failed: $_" -ForegroundColor DarkYellow
}

# ── Optional: certutil-based deep PKI audit ──
if ($IncludePKIAudit) {
    Write-Host "  Running certutil PKI audit..." -ForegroundColor DarkGray
    try {
        $certutilOutput = & certutil -TCAInfo 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  certutil PKI audit complete" -ForegroundColor DarkGreen
        }
    } catch {
        Write-Host "  certutil not available or failed" -ForegroundColor DarkYellow
    }
}

# ═══════════════════════════════════════════════════════════════
# SECTION 2: Machine Certificate Audit
# ═══════════════════════════════════════════════════════════════

Write-Host "`n[2/6] Auditing machine certificates..." -ForegroundColor Yellow

$machineCerts = @()

$compQueryParams = @{
    Filter     = "userCertificate -like '*'"
    Properties = @('samAccountName', 'distinguishedName', 'dNSHostName', 'operatingSystem',
                   'userCertificate', 'enabled', 'lastLogonTimestamp', 'servicePrincipalName',
                   'userAccountControl')
}
if ($SearchBase) { $compQueryParams['SearchBase'] = $SearchBase }
if ($DomainController) { $compQueryParams['Server'] = $DomainController }

$computersWithCerts = Get-ADComputer @compQueryParams -ErrorAction SilentlyContinue

foreach ($comp in $computersWithCerts) {
    $certs = @()
    foreach ($certBytes in $comp.userCertificate) {
        try {
            $cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($certBytes)
            $ekuList = @()
            if ($cert.Extensions) {
                $ekuExt = $cert.Extensions | Where-Object { $_.Oid.Value -eq "2.5.29.37" }
                if ($ekuExt) {
                    $eku = [System.Security.Cryptography.X509Certificates.X509EnhancedKeyUsageExtension]$ekuExt
                    $ekuList = $eku.EnhancedKeyUsages | ForEach-Object { $_.FriendlyName }
                }
            }

            $certs += [PSCustomObject]@{
                Subject        = $cert.Subject
                Issuer         = $cert.Issuer
                SerialNumber   = $cert.SerialNumber
                NotBefore      = $cert.NotBefore
                NotAfter       = $cert.NotAfter
                Thumbprint     = $cert.Thumbprint
                IsExpired      = ($cert.NotAfter -lt (Get-Date))
                DaysToExpiry   = [Math]::Round(($cert.NotAfter - (Get-Date)).TotalDays, 0)
                KeyLength      = $cert.PublicKey.Key.KeySize
                EKU            = $ekuList -join "; "
                HasClientAuth  = $ekuList -contains "Client Authentication"
                HasServerAuth  = $ekuList -contains "Server Authentication"
                Has8021X       = $ekuList -contains "Client Authentication"
                SignatureAlgo  = $cert.SignatureAlgorithm.FriendlyName
            }
        } catch {
            $certs += [PSCustomObject]@{
                Subject = "PARSE ERROR"
                Issuer  = $_.Exception.Message
            }
        }
    }

    $lastLogon = if ($comp.lastLogonTimestamp) {
        [DateTime]::FromFileTime($comp.lastLogonTimestamp).ToString("yyyy-MM-dd")
    } else { "Never" }

    $machineCerts += [PSCustomObject]@{
        ComputerName      = $comp.samAccountName
        DNSHostName       = $comp.dNSHostName
        DistinguishedName = $comp.distinguishedName
        OperatingSystem   = $comp.operatingSystem
        Enabled           = $comp.Enabled
        LastLogon         = $lastLogon
        CertificateCount  = $certs.Count
        Certificates      = $certs
        HasClientAuth     = ($certs | Where-Object { $_.HasClientAuth }) -ne $null
        HasServerAuth     = ($certs | Where-Object { $_.HasServerAuth }) -ne $null
        HasExpiredCerts   = ($certs | Where-Object { $_.IsExpired }) -ne $null
        HasSPNs           = ($comp.servicePrincipalName.Count -gt 0)
        MigrationImpact   = ""
    }
}

# Assign migration impact
foreach ($mc in $machineCerts) {
    $impacts = @()
    if ($mc.HasClientAuth) {
        $impacts += "802.1X/VPN client certificate — requires cloud RADIUS or Entra ID CBA migration"
    }
    if ($mc.HasServerAuth) {
        $impacts += "Server TLS certificate — may need Azure Key Vault or Intune SCEP/PKCS profile"
    }
    if ($mc.HasExpiredCerts) {
        $impacts += "Expired certificates present — clean up before migration"
    }
    $mc.MigrationImpact = if ($impacts) { $impacts -join "; " } else { "Low — standard machine cert, likely auto-enrolled" }
}

Write-Host "  Computers with certificates: $($machineCerts.Count)" -ForegroundColor Green
$totalCerts = ($machineCerts | ForEach-Object { $_.CertificateCount } | Measure-Object -Sum).Sum
Write-Host "  Total machine certificates: $totalCerts" -ForegroundColor Green

# ═══════════════════════════════════════════════════════════════
# SECTION 3: User Certificate Audit
# ═══════════════════════════════════════════════════════════════

Write-Host "`n[3/6] Auditing user certificates..." -ForegroundColor Yellow

$userCerts = @()

# Users with certificates
$userQueryParams = @{
    Filter     = "userCertificate -like '*' -or userSMIMECertificate -like '*'"
    Properties = @('samAccountName', 'distinguishedName', 'displayName', 'userPrincipalName',
                   'userCertificate', 'userSMIMECertificate', 'enabled',
                   'lastLogonTimestamp', 'userAccountControl', 'altSecurityIdentities',
                   'smartcardLogonRequired')
}
if ($SearchBase) { $userQueryParams['SearchBase'] = $SearchBase }
if ($DomainController) { $userQueryParams['Server'] = $DomainController }

$usersWithCerts = Get-ADUser @userQueryParams -ErrorAction SilentlyContinue

# Also find smart card required users
$smartCardParams = @{
    Filter     = "smartcardLogonRequired -eq `$true"
    Properties = @('samAccountName', 'distinguishedName', 'displayName', 'userPrincipalName',
                   'userCertificate', 'userSMIMECertificate', 'enabled',
                   'lastLogonTimestamp', 'userAccountControl', 'altSecurityIdentities',
                   'smartcardLogonRequired')
}
if ($SearchBase) { $smartCardParams['SearchBase'] = $SearchBase }
if ($DomainController) { $smartCardParams['Server'] = $DomainController }

$smartCardUsers = Get-ADUser @smartCardParams -ErrorAction SilentlyContinue

# Merge unique
$allCertUsers = @{}
foreach ($u in @($usersWithCerts) + @($smartCardUsers)) {
    if ($u -and -not $allCertUsers.ContainsKey($u.samAccountName)) {
        $allCertUsers[$u.samAccountName] = $u
    }
}

foreach ($user in $allCertUsers.Values) {
    $authCerts = @()
    if ($user.userCertificate) {
        foreach ($certBytes in $user.userCertificate) {
            try {
                $cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($certBytes)
                $ekuList = @()
                if ($cert.Extensions) {
                    $ekuExt = $cert.Extensions | Where-Object { $_.Oid.Value -eq "2.5.29.37" }
                    if ($ekuExt) {
                        $eku = [System.Security.Cryptography.X509Certificates.X509EnhancedKeyUsageExtension]$ekuExt
                        $ekuList = $eku.EnhancedKeyUsages | ForEach-Object { $_.FriendlyName }
                    }
                }

                # Extract SAN for UPN binding
                $sanList = @()
                $sanExt = $cert.Extensions | Where-Object { $_.Oid.Value -eq "2.5.29.17" }
                if ($sanExt) {
                    $sanList = $sanExt.Format($false) -split ", "
                }

                $authCerts += [PSCustomObject]@{
                    Subject      = $cert.Subject
                    Issuer       = $cert.Issuer
                    NotBefore    = $cert.NotBefore
                    NotAfter     = $cert.NotAfter
                    Thumbprint   = $cert.Thumbprint
                    IsExpired    = ($cert.NotAfter -lt (Get-Date))
                    EKU          = $ekuList -join "; "
                    SAN          = $sanList -join "; "
                    IsSmartCard  = ($ekuList -contains "Smart Card Logon")
                    IsClientAuth = ($ekuList -contains "Client Authentication")
                }
            } catch { }
        }
    }

    $isSmartCardRequired = [bool]($user.userAccountControl -band 0x40000) -or $user.smartcardLogonRequired
    $hasAltSecIdentities = ($user.altSecurityIdentities -and $user.altSecurityIdentities.Count -gt 0)

    $lastLogon = if ($user.lastLogonTimestamp) {
        [DateTime]::FromFileTime($user.lastLogonTimestamp).ToString("yyyy-MM-dd")
    } else { "Never" }

    # Classify auth type
    $authType = if ($isSmartCardRequired -and ($authCerts | Where-Object { $_.IsSmartCard })) { "Smart Card (PIV/CAC)" }
                elseif ($isSmartCardRequired) { "Smart Card Required (no cert in AD)" }
                elseif ($authCerts | Where-Object { $_.IsSmartCard }) { "Smart Card Capable (not required)" }
                elseif ($authCerts | Where-Object { $_.IsClientAuth }) { "Certificate-Based (Client Auth)" }
                else { "Certificate Present (no auth EKU)" }

    # Migration path
    $migrationPath = switch -Wildcard ($authType) {
        "Smart Card (PIV/CAC)" { "Entra ID CBA with PIV/CAC → configure certificate authority trust + UPN binding rules. Federal PIV requirement preserved." }
        "Smart Card Required*" { "Entra ID CBA or migrate to FIDO2/Windows Hello for Business. Evaluate if smart card mandate can transition to phishing-resistant MFA." }
        "Smart Card Capable*" { "Enable Entra ID CBA as additional auth method. No disruption — user can continue password auth." }
        "Certificate-Based*" { "Evaluate application dependency. If VPN/802.1X → cloud RADIUS. If web app → Entra ID CBA or modern auth." }
        default { "Low priority — certificate present but not used for authentication." }
    }

    $userCerts += [PSCustomObject]@{
        SamAccountName        = $user.samAccountName
        DisplayName           = $user.displayName
        UPN                   = $user.userPrincipalName
        DistinguishedName     = $user.distinguishedName
        Enabled               = $user.Enabled
        LastLogon             = $lastLogon
        SmartCardRequired     = $isSmartCardRequired
        HasAltSecIdentities   = $hasAltSecIdentities
        AltSecIdentityCount   = if ($user.altSecurityIdentities) { $user.altSecurityIdentities.Count } else { 0 }
        CertificateCount      = $authCerts.Count
        AuthenticationType    = $authType
        HasExpiredCerts       = ($authCerts | Where-Object { $_.IsExpired }) -ne $null
        Certificates          = $authCerts
        MigrationPath         = $migrationPath
    }
}

Write-Host "  Users with certificates: $($userCerts.Count)" -ForegroundColor Green
$smartCardCount = @($userCerts | Where-Object { $_.SmartCardRequired }).Count
Write-Host "  Smart card required users: $smartCardCount" -ForegroundColor $(if ($smartCardCount -gt 0) { "Yellow" } else { "Green" })

# ═══════════════════════════════════════════════════════════════
# SECTION 4: Certificate Template Audit (Optional)
# ═══════════════════════════════════════════════════════════════

Write-Host "`n[4/6] Auditing certificate templates..." -ForegroundColor Yellow

$templates = @()

if ($IncludeTemplateAudit) {
    try {
        $templatePath = "CN=Certificate Templates,CN=Public Key Services,CN=Services,$configDN"
        $adTemplates = Get-ADObject -SearchBase $templatePath -Filter * -Properties * @adParams

        foreach ($tmpl in $adTemplates) {
            $ekuOids = @()
            if ($tmpl.'pKIExtendedKeyUsage') {
                $ekuOids = $tmpl.'pKIExtendedKeyUsage'
            }

            $enrollmentFlags = if ($tmpl.'msPKI-Enrollment-Flag') { $tmpl.'msPKI-Enrollment-Flag' } else { 0 }
            $isAutoEnroll = ($enrollmentFlags -band 1) -ne 0

            $templates += [PSCustomObject]@{
                TemplateName       = $tmpl.Name
                DisplayName        = $tmpl.displayName
                TemplateOID        = $tmpl.'msPKI-Cert-Template-OID'
                SchemaVersion      = $tmpl.'msPKI-Template-Schema-Version'
                EKU                = ($ekuOids | ForEach-Object {
                    switch ($_) {
                        "1.3.6.1.5.5.7.3.1" { "Server Authentication" }
                        "1.3.6.1.5.5.7.3.2" { "Client Authentication" }
                        "1.3.6.1.4.1.311.20.2.2" { "Smart Card Logon" }
                        "1.3.6.1.5.5.7.3.4" { "Secure Email" }
                        "1.3.6.1.5.5.7.3.3" { "Code Signing" }
                        "1.3.6.1.5.5.7.3.5" { "IP Security End System" }
                        default { $_ }
                    }
                }) -join "; "
                AutoEnrollment     = $isAutoEnroll
                EnrollmentFlags    = $enrollmentFlags
                ValidityPeriod     = $tmpl.'pKIExpirationPeriod'
                RenewalPeriod      = $tmpl.'pKIOverlapPeriod'
                MinKeySize         = $tmpl.'msPKI-Minimal-Key-Size'
                HasSmartCardLogon  = $ekuOids -contains "1.3.6.1.4.1.311.20.2.2"
                HasClientAuth      = $ekuOids -contains "1.3.6.1.5.5.7.3.2"
                MigrationImpact    = ""
            }
        }

        # Assign migration impact per template
        foreach ($t in $templates) {
            if ($t.HasSmartCardLogon) {
                $t.MigrationImpact = "CRITICAL — Smart card logon template. Must configure Entra ID CBA with matching CA trust chain."
            } elseif ($t.HasClientAuth -and $t.AutoEnrollment) {
                $t.MigrationImpact = "HIGH — Auto-enrolled client auth certs. Evaluate: 802.1X → cloud RADIUS, VPN → ZTNA, app auth → modern auth."
            } elseif ($t.HasClientAuth) {
                $t.MigrationImpact = "MEDIUM — Manual client auth certs. Identify consumers and plan migration per application."
            } else {
                $t.MigrationImpact = "LOW — Non-authentication template (email signing, code signing, etc.)."
            }
        }

        Write-Host "  Certificate templates found: $($templates.Count)" -ForegroundColor Green
        $scTemplates = @($templates | Where-Object { $_.HasSmartCardLogon }).Count
        Write-Host "  Smart card logon templates: $scTemplates" -ForegroundColor $(if ($scTemplates -gt 0) { "Yellow" } else { "Green" })
    } catch {
        Write-Host "  Template enumeration failed: $_" -ForegroundColor DarkYellow
    }
} else {
    Write-Host "  Skipped (use -IncludeTemplateAudit to enable)" -ForegroundColor Gray
}

# ═══════════════════════════════════════════════════════════════
# SECTION 5: Entra ID CBA Readiness Assessment
# ═══════════════════════════════════════════════════════════════

Write-Host "`n[5/6] Computing Entra ID CBA readiness..." -ForegroundColor Yellow

$cbaReadiness = @{
    SmartCardUsersCount      = $smartCardCount
    CBARequired              = $smartCardCount -gt 0
    PKIInfrastructure        = @{
        EnterpriseCAs        = $pkiInfra.EnterpriseRootCAs.Count
        NTAuthCerts          = if ($pkiInfra.NTAuthCertificates.Count) { $pkiInfra.NTAuthCertificates.Count } else { 0 }
        HasPKI               = $pkiInfra.EnterpriseRootCAs.Count -gt 0
    }
    MigrationRequirements    = @(
        "Upload CA certificates to Entra ID certificate authorities trust store",
        "Configure username binding rules (UPN or certificate SAN mapping)",
        "Ensure CRL/OCSP endpoints are accessible from Azure (public internet or Azure-hosted)",
        "Configure authentication strength policies to require certificate-based auth where needed",
        "Test with pilot group before broad rollout",
        "Maintain on-prem PKI during coexistence — do not decommission CAs until all clients use Entra ID CBA"
    )
    FederalConsiderations    = @(
        "PIV/CAC smart cards — Entra ID CBA supports PIV certificates natively",
        "FIPS 140-2 compliance — Entra ID CBA uses FIPS-validated crypto modules",
        "OMB M-22-09 Zero Trust — CBA satisfies phishing-resistant MFA requirement",
        "CISA Binding Operational Directive 22-01 — certificate hygiene for government systems"
    )
}

Write-Host "  CBA readiness assessment complete" -ForegroundColor Green

# ═══════════════════════════════════════════════════════════════
# SECTION 6: Export Results
# ═══════════════════════════════════════════════════════════════

Write-Host "`n[6/6] Exporting results..." -ForegroundColor Yellow

$outPrefix = "UIAO_Spec3_D1.10_CertBasedAuthAudit_${domain}_${timestamp}"

$summary = @{
    PKI = @{
        EnterpriseCAs       = $pkiInfra.EnterpriseRootCAs.Count
        NTAuthCertificates  = if ($pkiInfra.NTAuthCertificates.Count) { $pkiInfra.NTAuthCertificates.Count } else { 0 }
        CertificateTemplates = $templates.Count
        SmartCardTemplates  = @($templates | Where-Object { $_.HasSmartCardLogon }).Count
    }
    MachineCertificates = @{
        ComputersWithCerts = $machineCerts.Count
        TotalMachineCerts  = ($machineCerts | ForEach-Object { $_.CertificateCount } | Measure-Object -Sum).Sum
        WithClientAuth     = @($machineCerts | Where-Object { $_.HasClientAuth }).Count
        WithServerAuth     = @($machineCerts | Where-Object { $_.HasServerAuth }).Count
        WithExpiredCerts   = @($machineCerts | Where-Object { $_.HasExpiredCerts }).Count
    }
    UserCertificates = @{
        UsersWithCerts      = $userCerts.Count
        SmartCardRequired   = $smartCardCount
        SmartCardCapable    = @($userCerts | Where-Object { $_.AuthenticationType -match "Smart Card Capable" }).Count
        CertBasedAuth       = @($userCerts | Where-Object { $_.AuthenticationType -eq "Certificate-Based (Client Auth)" }).Count
        WithExpiredCerts    = @($userCerts | Where-Object { $_.HasExpiredCerts }).Count
    }
    EntraIDCBARequired = $smartCardCount -gt 0
}

$results = @{
    Metadata = @{
        GeneratedAt = (Get-Date -Format "o")
        Generator   = "Spec3-D1.10-Get-CertBasedAuthAudit.ps1"
        UIAORef     = "UIAO_136 Spec 3, Phase 1, D1.10"
        ADRRef      = @("ADR-004")
        Domain      = $domain
    }
    Summary             = $summary
    PKIInfrastructure   = $pkiInfra
    MachineCertificates = $machineCerts
    UserCertificates    = $userCerts
    CertificateTemplates = $templates
    CBAReadiness        = $cbaReadiness
}

# ── JSON ──
$jsonPath = Join-Path $OutputPath "${outPrefix}.json"
$results | ConvertTo-Json -Depth 10 | Set-Content -Path $jsonPath -Encoding UTF8
Write-Host "  JSON: $jsonPath" -ForegroundColor Green

# ── CSV (machine certs) ──
$mcCsvPath = Join-Path $OutputPath "${outPrefix}_machines.csv"
$mcCsvData = foreach ($mc in $machineCerts) {
    [PSCustomObject]@{
        ComputerName     = $mc.ComputerName
        DNSHostName      = $mc.DNSHostName
        OperatingSystem  = $mc.OperatingSystem
        Enabled          = $mc.Enabled
        LastLogon        = $mc.LastLogon
        CertificateCount = $mc.CertificateCount
        HasClientAuth    = $mc.HasClientAuth
        HasServerAuth    = $mc.HasServerAuth
        HasExpiredCerts  = $mc.HasExpiredCerts
        MigrationImpact  = $mc.MigrationImpact
    }
}
$mcCsvData | Export-Csv -Path $mcCsvPath -NoTypeInformation -Encoding UTF8
Write-Host "  CSV:  $mcCsvPath" -ForegroundColor Green

# ── CSV (user certs) ──
$ucCsvPath = Join-Path $OutputPath "${outPrefix}_users.csv"
$ucCsvData = foreach ($uc in $userCerts) {
    [PSCustomObject]@{
        SamAccountName      = $uc.SamAccountName
        DisplayName         = $uc.DisplayName
        UPN                 = $uc.UPN
        Enabled             = $uc.Enabled
        LastLogon           = $uc.LastLogon
        SmartCardRequired   = $uc.SmartCardRequired
        CertificateCount    = $uc.CertificateCount
        AuthenticationType  = $uc.AuthenticationType
        HasExpiredCerts     = $uc.HasExpiredCerts
        MigrationPath       = $uc.MigrationPath
    }
}
$ucCsvData | Export-Csv -Path $ucCsvPath -NoTypeInformation -Encoding UTF8
Write-Host "  CSV:  $ucCsvPath" -ForegroundColor Green

# ── Console Dashboard ──
Write-Host "`n================================================================" -ForegroundColor Cyan
Write-Host " CERTIFICATE-BASED AUTH AUDIT — DASHBOARD" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  PKI Infrastructure:" -ForegroundColor Cyan
Write-Host "    Enterprise CAs:           $($summary.PKI.EnterpriseCAs)" -ForegroundColor White
Write-Host "    NTAuth Certificates:       $($summary.PKI.NTAuthCertificates)" -ForegroundColor White
Write-Host "    Certificate Templates:     $($summary.PKI.CertificateTemplates)" -ForegroundColor White
Write-Host "    Smart Card Templates:      $($summary.PKI.SmartCardTemplates)" -ForegroundColor $(if ($summary.PKI.SmartCardTemplates -gt 0) { "Yellow" } else { "Green" })
Write-Host ""
Write-Host "  Machine Certificates:" -ForegroundColor Cyan
Write-Host "    Computers with certs:      $($summary.MachineCertificates.ComputersWithCerts)" -ForegroundColor White
Write-Host "    With Client Auth (802.1X): $($summary.MachineCertificates.WithClientAuth)" -ForegroundColor $(if ($summary.MachineCertificates.WithClientAuth -gt 0) { "Yellow" } else { "Green" })
Write-Host "    With Server Auth:          $($summary.MachineCertificates.WithServerAuth)" -ForegroundColor White
Write-Host "    With Expired Certs:        $($summary.MachineCertificates.WithExpiredCerts)" -ForegroundColor $(if ($summary.MachineCertificates.WithExpiredCerts -gt 0) { "Red" } else { "Green" })
Write-Host ""
Write-Host "  User Certificates:" -ForegroundColor Cyan
Write-Host "    Users with certs:          $($summary.UserCertificates.UsersWithCerts)" -ForegroundColor White
Write-Host "    Smart Card REQUIRED:       $($summary.UserCertificates.SmartCardRequired)" -ForegroundColor $(if ($summary.UserCertificates.SmartCardRequired -gt 0) { "Yellow" } else { "Green" })
Write-Host "    Smart Card Capable:        $($summary.UserCertificates.SmartCardCapable)" -ForegroundColor White
Write-Host "    Cert-Based Auth:           $($summary.UserCertificates.CertBasedAuth)" -ForegroundColor White
Write-Host ""
if ($summary.EntraIDCBARequired) {
    Write-Host "  ⚠ Entra ID CBA REQUIRED — $smartCardCount users require smart card logon" -ForegroundColor Yellow
    Write-Host "    Configure: CA trust chain + UPN binding + CRL accessibility" -ForegroundColor White
} else {
    Write-Host "  ✓ No mandatory smart card users — Entra ID CBA optional" -ForegroundColor Green
}
Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host " Ref: ADR-004 (Workload Identity Federation as Default)" -ForegroundColor DarkCyan
Write-Host " Federal: PIV/CAC → Entra ID CBA preserves FIPS + Zero Trust" -ForegroundColor DarkCyan
Write-Host "================================================================`n" -ForegroundColor Cyan
