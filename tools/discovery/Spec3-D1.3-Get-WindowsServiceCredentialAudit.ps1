<#
.SYNOPSIS
    UIAO Spec 3 — D1.3: Windows Service Credential Audit
.DESCRIPTION
    Scans local or remote Windows servers for services running under
    domain accounts (not LocalSystem, NetworkService, LocalService, or
    Virtual Service Accounts). Produces a comprehensive audit of every
    service credential dependency that must be migrated to workload
    identity federation (per ADR-004).

    Discovery includes:
    1. Full service enumeration via CIM (Win32_Service)
    2. Credential classification:
       - Built-in (LocalSystem, NetworkService, LocalService)
       - Virtual Service Account (NT SERVICE\...)
       - gMSA (domain\accountName$ — trailing $)
       - sMSA (domain\accountName$ flagged by objectClass if D1.1 available)
       - Domain Account (domain\user or user@domain)
       - Local Account (.\user or COMPUTERNAME\user)
       - Unresolved (unknown format)
    3. Service state and startup type analysis
    4. Binary path extraction and publisher detection
    5. Cross-reference with D1.1 service account scan (risk scores,
       migration targets) when available
    6. Migration target recommendation per ADR-004:
       - gMSA services → Workload Identity Federation or retain gMSA
       - Domain account services → Workload Identity Federation
       - Local accounts → Managed Identity (if Azure-hosted) or gMSA interim

    Ref: UIAO_136 Spec 3, Phase 1, Deliverable D1.3
         ADR-004 (Workload Identity Federation Default)
.PARAMETER ComputerName
    One or more computer names to scan. Defaults to localhost.
    Accepts pipeline input. Supports arrays and comma-separated values.
.PARAMETER OutputPath
    Directory for output files. Defaults to .\output
.PARAMETER D1InputFile
    Path to D1.1 Service Account Scan JSON for cross-reference enrichment.
    Optional.
.PARAMETER Credential
    PSCredential for remote WinRM connections. Optional.
.PARAMETER IncludeBuiltIn
    Include built-in service accounts in output. Default: $false
    (only non-default credentials are reported).
.PARAMETER TimeoutSeconds
    WinRM connection timeout per server. Default: 30.
.EXAMPLE
    .\Spec3-D1.3-Get-WindowsServiceCredentialAudit.ps1
    Scans localhost.
.EXAMPLE
    .\Spec3-D1.3-Get-WindowsServiceCredentialAudit.ps1 -ComputerName SERVER01,SERVER02
    Scans multiple remote servers via WinRM.
.EXAMPLE
    .\Spec3-D1.3-Get-WindowsServiceCredentialAudit.ps1 -ComputerName (Get-Content servers.txt)
    Scans all servers from a file list.
.EXAMPLE
    .\Spec3-D1.3-Get-WindowsServiceCredentialAudit.ps1 -D1InputFile .\output\UIAO_Spec3_D1.1_ServiceAccountScan.json
    Scans localhost and enriches with D1.1 risk scores.
.NOTES
    Requires: CIM/WMI access (local admin or WinRM for remote)
    Remote servers require: WinRM enabled, firewall rules, admin credentials
#>

[CmdletBinding()]
param(
    [Parameter(ValueFromPipeline, ValueFromPipelineByPropertyName)]
    [string[]]$ComputerName = @($env:COMPUTERNAME),

    [string]$OutputPath = ".\output",

    [string]$D1InputFile,

    [System.Management.Automation.PSCredential]$Credential,

    [switch]$IncludeBuiltIn,

    [int]$TimeoutSeconds = 30
)

begin {
    $ErrorActionPreference = "Stop"

    # ── Output setup ──
    if (-not (Test-Path $OutputPath)) {
        New-Item -Path $OutputPath -ItemType Directory -Force | Out-Null
    }

    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"

    Write-Host "`n================================================================" -ForegroundColor Cyan
    Write-Host "  UIAO Spec 3 — D1.3: Windows Service Credential Audit"        -ForegroundColor Cyan
    Write-Host "  Timestamp: $timestamp"                                        -ForegroundColor Cyan
    Write-Host "================================================================`n" -ForegroundColor Cyan

    # ── Load optional D1.1 cross-reference data ──
    $d1Data = $null
    $d1AccountLookup = @{}
    if ($D1InputFile -and (Test-Path $D1InputFile)) {
        Write-Host "  Loading D1.1 service account scan for cross-reference..." -ForegroundColor Yellow
        $d1Data = Get-Content $D1InputFile -Raw -Encoding UTF8 | ConvertFrom-Json
        # Build lookup by sAMAccountName
        if ($d1Data.ServiceAccounts) {
            foreach ($sa in $d1Data.ServiceAccounts) {
                $key = $sa.sAMAccountName
                if ($key) { $d1AccountLookup[$key.ToLower()] = $sa }
            }
        }
        Write-Host "  Loaded D1.1 data ($($d1AccountLookup.Count) service accounts indexed)" -ForegroundColor Green
    }

    # ── Built-in account patterns ──
    $builtInAccounts = @(
        'LocalSystem',
        'NT AUTHORITY\SYSTEM',
        'NT AUTHORITY\LocalService',
        'NT AUTHORITY\NetworkService',
        'Local System',
        'Local Service',
        'Network Service'
    )

    $virtualServicePattern = '^NT SERVICE\\'

    # ── Credential classification function ──
    function Get-CredentialClass {
        param([string]$StartName, [string]$ComputerName)

        if ([string]::IsNullOrWhiteSpace($StartName)) {
            return 'Built-in'  # null/empty = LocalSystem
        }

        # Built-in accounts
        if ($builtInAccounts -contains $StartName) {
            return 'Built-in'
        }

        # Virtual service accounts (NT SERVICE\...)
        if ($StartName -match $virtualServicePattern) {
            return 'VirtualServiceAccount'
        }

        # gMSA or sMSA (trailing $)
        if ($StartName -match '\$$') {
            # Check D1.1 for objectClass distinction
            $samName = ($StartName -split '\\')[-1]
            if ($d1AccountLookup.ContainsKey($samName.ToLower())) {
                $d1Entry = $d1AccountLookup[$samName.ToLower()]
                if ($d1Entry.DiscoveryPass -eq 'gMSA') { return 'gMSA' }
                if ($d1Entry.DiscoveryPass -eq 'sMSA') { return 'sMSA' }
            }
            return 'gMSA'  # Default assumption for $ suffix
        }

        # Local account (.\user or COMPUTERNAME\user)
        if ($StartName -match '^\.\\'  -or
            $StartName -match "^${ComputerName}\\" -or
            $StartName -match '^[^\\@]+$') {
            # Plain username with no domain qualifier — likely local
            if ($StartName -notmatch '\\' -and $StartName -notmatch '@') {
                return 'Unresolved'
            }
            return 'LocalAccount'
        }

        # Domain account (DOMAIN\user or user@domain)
        if ($StartName -match '\\' -or $StartName -match '@') {
            return 'DomainAccount'
        }

        return 'Unresolved'
    }

    # ── Migration target recommendation ──
    function Get-MigrationTarget {
        param([string]$CredentialClass, [string]$ServiceName)

        switch ($CredentialClass) {
            'DomainAccount' {
                return 'Workload Identity Federation (ADR-004) — Managed Identity or Federated Credential'
            }
            'gMSA' {
                return 'Evaluate: retain gMSA (low risk) or migrate to Workload Identity Federation'
            }
            'sMSA' {
                return 'Convert to gMSA first, then evaluate Workload Identity Federation'
            }
            'LocalAccount' {
                return 'Convert to gMSA (on-prem) or Managed Identity (Azure-hosted)'
            }
            'VirtualServiceAccount' {
                return 'No action — Virtual Service Accounts are best practice for single-server'
            }
            'Built-in' {
                return 'No action — built-in identity'
            }
            default {
                return 'Manual review required'
            }
        }
    }

    # ── Risk scoring ──
    function Get-ServiceRiskScore {
        param(
            [string]$CredentialClass,
            [string]$StartMode,
            [string]$State,
            [object]$D1Entry
        )

        $score = 0
        $factors = [System.Collections.Generic.List[string]]::new()

        # Credential type risk
        switch ($CredentialClass) {
            'DomainAccount' { $score += 40; $factors.Add("Domain account credential (40)") }
            'LocalAccount'  { $score += 25; $factors.Add("Local account credential (25)") }
            'sMSA'          { $score += 15; $factors.Add("Standalone MSA — no failover (15)") }
            'gMSA'          { $score += 5;  $factors.Add("gMSA — managed but evaluate (5)") }
        }

        # Running state risk
        if ($State -eq 'Running') {
            $score += 20
            $factors.Add("Currently running (20)")
        }

        # Auto-start risk
        if ($StartMode -eq 'Auto') {
            $score += 10
            $factors.Add("Auto-start enabled (10)")
        }

        # D1.1 cross-reference risk
        if ($D1Entry) {
            if ($D1Entry.RiskLevel -eq 'Critical') {
                $score += 30
                $factors.Add("D1.1 risk: Critical (30)")
            }
            elseif ($D1Entry.RiskLevel -eq 'High') {
                $score += 20
                $factors.Add("D1.1 risk: High (20)")
            }
            elseif ($D1Entry.RiskLevel -eq 'Medium') {
                $score += 10
                $factors.Add("D1.1 risk: Medium (10)")
            }

            if ($D1Entry.HasSPN) {
                $score += 10
                $factors.Add("Has SPN — Kerberos dependency (10)")
            }

            if ($D1Entry.AdminCount -eq 1) {
                $score += 20
                $factors.Add("AdminCount=1 — privileged (20)")
            }

            if ($D1Entry.PasswordNeverExpires) {
                $score += 15
                $factors.Add("Password never expires (15)")
            }
        }

        $riskLevel = switch {
            ($score -ge 80) { 'Critical' }
            ($score -ge 50) { 'High' }
            ($score -ge 25) { 'Medium' }
            default         { 'Low' }
        }

        return [ordered]@{
            Score   = [math]::Min($score, 100)
            Level   = $riskLevel
            Factors = @($factors)
        }
    }

    # Results collection
    $allResults = [System.Collections.Generic.List[object]]::new()
    $serverSummaries = [System.Collections.Generic.List[object]]::new()
    $errors = [System.Collections.Generic.List[object]]::new()
    $allComputers = [System.Collections.Generic.List[string]]::new()
}

process {
    foreach ($computer in $ComputerName) {
        $computer = $computer.Trim()
        if ([string]::IsNullOrWhiteSpace($computer)) { continue }
        $allComputers.Add($computer)

        Write-Host "  Scanning: $computer" -ForegroundColor Yellow

        $serverServices = $null
        $isLocal = ($computer -eq $env:COMPUTERNAME -or
                    $computer -eq 'localhost' -or
                    $computer -eq '.' -or
                    $computer -eq '127.0.0.1')

        try {
            # ── CIM session setup ──
            if ($isLocal) {
                $cimParams = @{}
            }
            else {
                $sessionOption = New-CimSessionOption -Protocol Wsman
                $cimSessionParams = @{
                    ComputerName  = $computer
                    SessionOption = $sessionOption
                    OperationTimeoutSec = $TimeoutSeconds
                }
                if ($Credential) {
                    $cimSessionParams['Credential'] = $Credential
                }

                $cimSession = New-CimSession @cimSessionParams
                $cimParams = @{ CimSession = $cimSession }
            }

            # ── Enumerate services ──
            $serverServices = Get-CimInstance -ClassName Win32_Service @cimParams |
                Select-Object Name, DisplayName, StartName, StartMode, State,
                              PathName, Description, ProcessId, ServiceType,
                              DelayedAutoStart

            if (-not $isLocal -and $cimSession) {
                Remove-CimSession $cimSession -ErrorAction SilentlyContinue
            }

            Write-Host "    Found $($serverServices.Count) total services" -ForegroundColor DarkGray

            $serverDomainCount = 0
            $serverGmsaCount = 0
            $serverLocalCount = 0
            $serverBuiltInCount = 0
            $serverOtherCount = 0

            foreach ($svc in $serverServices) {
                $credClass = Get-CredentialClass -StartName $svc.StartName -ComputerName $computer

                # Skip built-in unless explicitly requested
                if (-not $IncludeBuiltIn -and $credClass -eq 'Built-in') {
                    $serverBuiltInCount++
                    continue
                }
                if (-not $IncludeBuiltIn -and $credClass -eq 'VirtualServiceAccount') {
                    $serverBuiltInCount++
                    continue
                }

                # Extract binary path (strip arguments)
                $binaryPath = $svc.PathName
                $cleanBinary = $binaryPath
                if ($binaryPath) {
                    if ($binaryPath.StartsWith('"')) {
                        $endQuote = $binaryPath.IndexOf('"', 1)
                        if ($endQuote -gt 0) {
                            $cleanBinary = $binaryPath.Substring(1, $endQuote - 1)
                        }
                    }
                    else {
                        $spaceIdx = $binaryPath.IndexOf(' ')
                        if ($spaceIdx -gt 0) {
                            $cleanBinary = $binaryPath.Substring(0, $spaceIdx)
                        }
                    }
                }

                # D1.1 cross-reference
                $d1Match = $null
                $samLookup = ($svc.StartName -split '\\')[-1]
                if ($samLookup -and $d1AccountLookup.ContainsKey($samLookup.ToLower())) {
                    $d1Match = $d1AccountLookup[$samLookup.ToLower()]
                }

                $risk = Get-ServiceRiskScore `
                    -CredentialClass $credClass `
                    -StartMode $svc.StartMode `
                    -State $svc.State `
                    -D1Entry $d1Match

                $result = [ordered]@{
                    ComputerName      = $computer
                    ServiceName       = $svc.Name
                    DisplayName       = $svc.DisplayName
                    RunAsAccount      = if ($svc.StartName) { $svc.StartName } else { 'LocalSystem' }
                    CredentialClass   = $credClass
                    StartupType       = $svc.StartMode
                    DelayedAutoStart  = [bool]$svc.DelayedAutoStart
                    State             = $svc.State
                    BinaryPath        = $cleanBinary
                    FullPathName      = $binaryPath
                    Description       = $svc.Description
                    ServiceType       = $svc.ServiceType
                    ProcessId         = $svc.ProcessId
                    RiskScore         = $risk.Score
                    RiskLevel         = $risk.Level
                    RiskFactors       = ($risk.Factors -join '; ')
                    MigrationTarget   = Get-MigrationTarget -CredentialClass $credClass -ServiceName $svc.Name
                    D1_1_Match        = if ($d1Match) { $d1Match.sAMAccountName } else { $null }
                    D1_1_RiskLevel    = if ($d1Match) { $d1Match.RiskLevel } else { $null }
                    D1_1_HasSPN       = if ($d1Match) { $d1Match.HasSPN } else { $null }
                    D1_1_MigrationTarget = if ($d1Match) { $d1Match.MigrationTarget } else { $null }
                }

                $allResults.Add($result)

                # Counters
                switch ($credClass) {
                    'DomainAccount' { $serverDomainCount++ }
                    'gMSA'          { $serverGmsaCount++ }
                    'sMSA'          { $serverGmsaCount++ }
                    'LocalAccount'  { $serverLocalCount++ }
                    default         { $serverOtherCount++ }
                }
            }

            $serverSummaries.Add([ordered]@{
                ComputerName      = $computer
                Status            = 'Success'
                TotalServices     = $serverServices.Count
                DomainAccounts    = $serverDomainCount
                gMSA_sMSA         = $serverGmsaCount
                LocalAccounts     = $serverLocalCount
                BuiltIn_Skipped   = $serverBuiltInCount
                Other             = $serverOtherCount
                NonDefaultTotal   = $serverDomainCount + $serverGmsaCount + $serverLocalCount + $serverOtherCount
            })

            Write-Host "    Domain: $serverDomainCount | gMSA/sMSA: $serverGmsaCount | Local: $serverLocalCount | Built-in (skipped): $serverBuiltInCount" -ForegroundColor DarkGray
        }
        catch {
            $errMsg = $_.Exception.Message
            Write-Host "    ERROR: $errMsg" -ForegroundColor Red
            $errors.Add([ordered]@{
                ComputerName = $computer
                Error        = $errMsg
                Timestamp    = (Get-Date).ToString("o")
            })
            $serverSummaries.Add([ordered]@{
                ComputerName      = $computer
                Status            = 'Failed'
                TotalServices     = 0
                DomainAccounts    = 0
                gMSA_sMSA         = 0
                LocalAccounts     = 0
                BuiltIn_Skipped   = 0
                Other             = 0
                NonDefaultTotal   = 0
                Error             = $errMsg
            })
        }
    }
}

end {
    # ══════════════════════════════════════════════════════════════
    # Output
    # ══════════════════════════════════════════════════════════════

    $outPrefix = "UIAO_Spec3_D1.3_WindowsServiceCredentialAudit_${timestamp}"

    # ── Aggregate statistics ──
    $totalDomain = ($allResults | Where-Object { $_.CredentialClass -eq 'DomainAccount' }).Count
    $totalGmsa   = ($allResults | Where-Object { $_.CredentialClass -in @('gMSA','sMSA') }).Count
    $totalLocal  = ($allResults | Where-Object { $_.CredentialClass -eq 'LocalAccount' }).Count
    $totalCritical = ($allResults | Where-Object { $_.RiskLevel -eq 'Critical' }).Count
    $totalHigh     = ($allResults | Where-Object { $_.RiskLevel -eq 'High' }).Count

    # Unique accounts
    $uniqueAccounts = $allResults |
        Where-Object { $_.CredentialClass -in @('DomainAccount','gMSA','sMSA','LocalAccount') } |
        Select-Object -ExpandProperty RunAsAccount -Unique

    # Multi-server accounts (same account on multiple servers)
    $multiServerAccounts = $allResults |
        Where-Object { $_.CredentialClass -eq 'DomainAccount' } |
        Group-Object RunAsAccount |
        Where-Object { ($_.Group | Select-Object -ExpandProperty ComputerName -Unique).Count -gt 1 } |
        ForEach-Object {
            [ordered]@{
                Account    = $_.Name
                ServerCount = ($_.Group | Select-Object -ExpandProperty ComputerName -Unique).Count
                Servers     = ($_.Group | Select-Object -ExpandProperty ComputerName -Unique) -join '; '
                Services    = ($_.Group | Select-Object -ExpandProperty ServiceName -Unique) -join '; '
            }
        }

    $summary = [ordered]@{
        ExportMetadata = [ordered]@{
            Timestamp      = (Get-Date).ToString("o")
            Script         = "UIAO Spec 3 D1.3 — Windows Service Credential Audit"
            Reference      = "UIAO_136, ADR-004"
            D1_1_Source    = if ($D1InputFile) { $D1InputFile } else { "Not provided" }
            ServersScanned = $allComputers.Count
            ServersFailed  = $errors.Count
        }
        Statistics = [ordered]@{
            TotalServicesAudited  = $allResults.Count
            DomainAccountServices = $totalDomain
            gMSA_sMSA_Services    = $totalGmsa
            LocalAccountServices  = $totalLocal
            UniqueCredentials     = $uniqueAccounts.Count
            CriticalRisk          = $totalCritical
            HighRisk              = $totalHigh
            MultiServerAccounts   = @($multiServerAccounts).Count
        }
        ServerSummaries    = @($serverSummaries)
        MultiServerAccounts = @($multiServerAccounts)
        Errors             = @($errors)
    }

    # ── JSON ──
    $jsonFile = Join-Path $OutputPath "${outPrefix}.json"
    [ordered]@{ Summary = $summary; Services = @($allResults) } |
        ConvertTo-Json -Depth 10 |
        Out-File -FilePath $jsonFile -Encoding utf8NoBOM
    Write-Host "`n  JSON: $jsonFile" -ForegroundColor Green

    # ── CSV ──
    $csvFile = Join-Path $OutputPath "${outPrefix}.csv"
    $allResults | ForEach-Object {
        [PSCustomObject]@{
            ComputerName     = $_.ComputerName
            ServiceName      = $_.ServiceName
            DisplayName      = $_.DisplayName
            RunAsAccount     = $_.RunAsAccount
            CredentialClass  = $_.CredentialClass
            StartupType      = $_.StartupType
            DelayedAutoStart = $_.DelayedAutoStart
            State            = $_.State
            BinaryPath       = $_.BinaryPath
            FullPathName     = $_.FullPathName
            Description      = $_.Description
            RiskScore        = $_.RiskScore
            RiskLevel        = $_.RiskLevel
            RiskFactors      = $_.RiskFactors
            MigrationTarget  = $_.MigrationTarget
            D1_1_Match       = $_.D1_1_Match
            D1_1_RiskLevel   = $_.D1_1_RiskLevel
        }
    } | Export-Csv -Path $csvFile -NoTypeInformation -Encoding utf8NoBOM
    Write-Host "  CSV:  $csvFile" -ForegroundColor Green

    # ── Console Summary ──
    Write-Host "`n-- Windows Service Credential Audit Summary --" -ForegroundColor Cyan
    Write-Host "  Servers scanned:       $($allComputers.Count)"
    Write-Host "  Servers failed:        $($errors.Count)"
    Write-Host "  Total services found:  $($allResults.Count) (non-default credentials)"

    Write-Host "`n-- Credential Classification --" -ForegroundColor Cyan
    Write-Host "  Domain Accounts:       $totalDomain" -ForegroundColor $(if ($totalDomain -gt 0) { 'Red' } else { 'Green' })
    Write-Host "  gMSA / sMSA:           $totalGmsa" -ForegroundColor $(if ($totalGmsa -gt 0) { 'Yellow' } else { 'Green' })
    Write-Host "  Local Accounts:        $totalLocal" -ForegroundColor $(if ($totalLocal -gt 0) { 'Yellow' } else { 'Green' })
    Write-Host "  Unique Credentials:    $($uniqueAccounts.Count)"

    Write-Host "`n-- Risk Distribution --" -ForegroundColor Cyan
    Write-Host "  Critical: $totalCritical" -ForegroundColor $(if ($totalCritical -gt 0) { 'Red' } else { 'Green' })
    Write-Host "  High:     $totalHigh" -ForegroundColor $(if ($totalHigh -gt 0) { 'Red' } else { 'Green' })
    Write-Host "  Medium:   $(($allResults | Where-Object { $_.RiskLevel -eq 'Medium' }).Count)"
    Write-Host "  Low:      $(($allResults | Where-Object { $_.RiskLevel -eq 'Low' }).Count)"

    if ($multiServerAccounts.Count -gt 0) {
        Write-Host "`n-- Multi-Server Domain Accounts (shared credentials) --" -ForegroundColor Red
        foreach ($msa in $multiServerAccounts) {
            Write-Host "  $($msa.Account) -> $($msa.ServerCount) servers ($($msa.Servers))"
        }
    }

    if ($errors.Count -gt 0) {
        Write-Host "`n-- Errors --" -ForegroundColor Red
        foreach ($err in $errors) {
            Write-Host "  $($err.ComputerName): $($err.Error)"
        }
    }

    Write-Host "`n-- Complete --`n" -ForegroundColor Cyan
}
