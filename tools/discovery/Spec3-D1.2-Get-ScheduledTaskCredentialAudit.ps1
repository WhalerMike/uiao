<#
.SYNOPSIS
    UIAO Spec 3 — D1.2: Scheduled Task Credential Audit
.DESCRIPTION
    Scans servers for scheduled tasks running under domain accounts.
    Can operate in two modes:
      A) Remote scan — query target servers via WinRM (CIM/WMI)
      B) Local scan + D1.1 correlation — scan local machine and/or
         correlate with D1.1 service account scan results

    Collects per task:
      - Task name and path
      - Run-as account (principal)
      - Last run time and result
      - Next run time
      - Trigger schedule
      - Action (script path, executable, arguments)
      - Task state (Ready, Running, Disabled)
      - Registration date
      - Author

    Classifies each credential finding:
      - Domain user account (HIGH — migration candidate)
      - Local account (LOW — no AD dependency)
      - gMSA (LOW — already managed)
      - SYSTEM/NetworkService/LocalService (NONE — built-in)
      - Unresolvable (MEDIUM — investigate)

    Ref: UIAO_136 Spec 3, Phase 1, Deliverable D1.2
         ADR-004 (Workload Identity Federation Default)
.PARAMETER ComputerName
    Array of server names to scan remotely via WinRM.
    If omitted, scans local machine only.
.PARAMETER D1InputFile
    Path to D1.1 Service Account Scan JSON for cross-reference.
    Optional — enriches results with D1.1 risk scores.
.PARAMETER OutputPath
    Directory for output files. Defaults to .\output
.PARAMETER Credential
    PSCredential for remote server authentication.
    If omitted, uses current user's credentials.
.PARAMETER ThrottleLimit
    Maximum concurrent remote connections. Default: 10.
.EXAMPLE
    .\Spec3-D1.2-Get-ScheduledTaskCredentialAudit.ps1
    .\Spec3-D1.2-Get-ScheduledTaskCredentialAudit.ps1 -ComputerName (Get-Content .\servers.txt)
    .\Spec3-D1.2-Get-ScheduledTaskCredentialAudit.ps1 -ComputerName SRV01,SRV02 -D1InputFile .\output\UIAO_Spec3_D1.1_ServiceAccountScan.json
.NOTES
    Requires: ScheduledTasks module (built-in on Windows Server 2012+)
    Requires: WinRM enabled on target servers (for remote scan)
    Requires: Admin access on target servers
#>

[CmdletBinding()]
param(
    [string[]]$ComputerName,
    [string]$D1InputFile,
    [string]$OutputPath = ".\output",
    [PSCredential]$Credential,
    [int]$ThrottleLimit = 10
)

$ErrorActionPreference = "Stop"

# ── Output setup ──
if (-not (Test-Path $OutputPath)) {
    New-Item -Path $OutputPath -ItemType Directory -Force | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$domain = try { (Get-ADDomain -ErrorAction SilentlyContinue).DNSRoot } catch { $env:USERDNSDOMAIN }
if (-not $domain) { $domain = "local" }

Write-Host "`n================================================================" -ForegroundColor Cyan
Write-Host "  UIAO Spec 3 — D1.2: Scheduled Task Credential Audit"          -ForegroundColor Cyan
Write-Host "  Targets:   $(if ($ComputerName) { $ComputerName.Count } else { 'Local machine' })" -ForegroundColor Cyan
Write-Host "  Timestamp: $timestamp"                                         -ForegroundColor Cyan
Write-Host "================================================================`n" -ForegroundColor Cyan

# ── Load D1.1 cross-reference (optional) ──
$d1Accounts = @{}
if ($D1InputFile -and (Test-Path $D1InputFile)) {
    Write-Host "  Loading D1.1 service account data for cross-reference..." -ForegroundColor Yellow
    $d1Raw = Get-Content $D1InputFile -Raw -Encoding UTF8 | ConvertFrom-Json
    foreach ($acct in $d1Raw.ServiceAccounts) {
        $key = $acct.SamAccountName.ToLower()
        $d1Accounts[$key] = $acct
    }
    Write-Host "  Loaded $($d1Accounts.Count) service accounts from D1.1" -ForegroundColor Green
}

# ══════════════════════════════════════════════════════════════
# Credential Classification
# ══════════════════════════════════════════════════════════════

function Get-CredentialClassification {
    param([string]$RunAsUser)

    if (-not $RunAsUser) {
        return [ordered]@{
            Type     = "Unknown"
            Risk     = "MEDIUM"
            Category = "Investigate — no run-as account specified"
        }
    }

    $user = $RunAsUser.Trim()

    # Built-in accounts — no risk
    $builtIn = @(
        'SYSTEM', 'NT AUTHORITY\SYSTEM', 'LOCAL SYSTEM',
        'NT AUTHORITY\LOCAL SERVICE', 'LOCAL SERVICE',
        'NT AUTHORITY\NETWORK SERVICE', 'NETWORK SERVICE',
        'NT AUTHORITY\LOCALSERVICE', 'NT AUTHORITY\NETWORKSERVICE',
        'INTERACTIVE', 'NT AUTHORITY\INTERACTIVE',
        'S-1-5-18', 'S-1-5-19', 'S-1-5-20',
        'BUILTIN\Administrators', 'Users'
    )

    if ($builtIn -contains $user -or $user -match '^(S-1-5-(18|19|20))$') {
        return [ordered]@{
            Type     = "Built-in"
            Risk     = "NONE"
            Category = "System/service account — no AD dependency"
        }
    }

    # gMSA — ends with $ and contains domain prefix
    if ($user -match '\\[^\\]+\$$' -or $user -match '^[^\\]+\$$') {
        return [ordered]@{
            Type     = "gMSA"
            Risk     = "LOW"
            Category = "Group Managed Service Account — auto-rotated credentials"
        }
    }

    # Local account (no domain prefix, or .\)
    if ($user -match '^\.\\'  -or $user -eq $env:COMPUTERNAME + '\' + ($user -split '\\')[-1]) {
        return [ordered]@{
            Type     = "Local"
            Risk     = "LOW"
            Category = "Local machine account — no AD dependency"
        }
    }

    # Domain account (DOMAIN\user or user@domain)
    if ($user -match '\\' -or $user -match '@') {
        return [ordered]@{
            Type     = "Domain Account"
            Risk     = "HIGH"
            Category = "Domain credential — migration candidate (ADR-004)"
        }
    }

    # Bare username — likely domain in single-domain environments
    return [ordered]@{
        Type     = "Unqualified"
        Risk     = "MEDIUM"
        Category = "Bare username — verify if domain or local account"
    }
}

# ══════════════════════════════════════════════════════════════
# Migration Target Recommendation
# ══════════════════════════════════════════════════════════════

function Get-TaskMigrationTarget {
    param($Task, $Classification)

    if ($Classification.Risk -eq 'NONE' -or $Classification.Risk -eq 'LOW') {
        return "No migration needed"
    }

    $actions = @($Task.Actions)
    $actionStr = ($actions | ForEach-Object { $_.Execute }) -join '; '

    # PowerShell script
    if ($actionStr -match 'powershell|pwsh|\.ps1') {
        return "Azure Automation Runbook (Managed Identity) or gMSA (interim on-prem)"
    }

    # Python / other scripting
    if ($actionStr -match 'python|\.py|cscript|wscript|\.vbs') {
        return "Azure Functions Timer Trigger (Managed Identity) or gMSA (interim on-prem)"
    }

    # SQL-related
    if ($actionStr -match 'sqlcmd|osql|dtexec|SSIS|bcp') {
        return "SQL Agent Job with Entra ID Auth (SQL 2022+) or Azure Data Factory"
    }

    # Backup software
    if ($actionStr -match 'backup|veeam|commvault|arcserve|robocopy') {
        return "Azure Backup / vendor cloud service or gMSA (interim on-prem)"
    }

    # File operations
    if ($actionStr -match 'xcopy|robocopy|copy|move') {
        return "Azure Storage Sync or Logic App (Managed Identity) or gMSA (interim on-prem)"
    }

    # SCCM / ConfigMgr
    if ($actionStr -match 'SCCM|ConfigMgr|ccmexec') {
        return "Intune Remediation Script (replaces ConfigMgr task sequences)"
    }

    return "Evaluate: Azure Automation / Functions (cloud) or gMSA (on-prem interim)"
}

# ══════════════════════════════════════════════════════════════
# Task Scanner (runs locally or on remote targets)
# ══════════════════════════════════════════════════════════════

$scanScript = {
    param([string]$TargetComputer)

    $results = [System.Collections.Generic.List[object]]::new()

    try {
        # Get all scheduled tasks
        $tasks = Get-ScheduledTask -ErrorAction SilentlyContinue

        foreach ($task in $tasks) {
            # Skip Microsoft built-in tasks in most cases
            $taskPath = $task.TaskPath
            $isMicrosoft = $taskPath -match '^\\Microsoft\\'

            # Get task info
            $taskInfo = $null
            try {
                $taskInfo = Get-ScheduledTaskInfo -TaskName $task.TaskName -TaskPath $task.TaskPath -ErrorAction SilentlyContinue
            }
            catch { }

            # Principal (run-as)
            $runAs = $null
            $logonType = $null
            $runLevel = $null
            if ($task.Principal) {
                $runAs = if ($task.Principal.UserId) { $task.Principal.UserId }
                         elseif ($task.Principal.GroupId) { $task.Principal.GroupId }
                         else { $null }
                $logonType = $task.Principal.LogonType
                $runLevel = $task.Principal.RunLevel
            }

            # Triggers
            $triggers = @()
            foreach ($trigger in $task.Triggers) {
                $triggerInfo = [ordered]@{
                    Type        = $trigger.CimClass.CimClassName -replace 'MSFT_Task', '' -replace 'Trigger', ''
                    Enabled     = $trigger.Enabled
                    StartBoundary = $trigger.StartBoundary
                    EndBoundary   = $trigger.EndBoundary
                    Repetition    = if ($trigger.Repetition) {
                        [ordered]@{
                            Interval = $trigger.Repetition.Interval
                            Duration = $trigger.Repetition.Duration
                        }
                    } else { $null }
                }

                # Add type-specific details
                if ($trigger -is [CimInstance]) {
                    if ($trigger.CimClass.CimClassName -match 'Daily') {
                        $triggerInfo['DaysInterval'] = $trigger.DaysInterval
                    }
                    elseif ($trigger.CimClass.CimClassName -match 'Weekly') {
                        $triggerInfo['WeeksInterval'] = $trigger.WeeksInterval
                        $triggerInfo['DaysOfWeek'] = $trigger.DaysOfWeek
                    }
                }

                $triggers += $triggerInfo
            }

            # Actions
            $actions = @()
            foreach ($action in $task.Actions) {
                $actions += [ordered]@{
                    Type      = $action.CimClass.CimClassName -replace 'MSFT_Task', '' -replace 'Action', ''
                    Execute   = $action.Execute
                    Arguments = $action.Arguments
                    WorkingDirectory = $action.WorkingDirectory
                }
            }

            $record = [ordered]@{
                ComputerName       = if ($TargetComputer) { $TargetComputer } else { $env:COMPUTERNAME }
                TaskName           = $task.TaskName
                TaskPath           = $task.TaskPath
                FullPath           = $task.TaskPath + $task.TaskName
                State              = $task.State.ToString()
                IsMicrosoftTask    = $isMicrosoft

                # Principal
                RunAsAccount       = $runAs
                LogonType          = if ($logonType) { $logonType.ToString() } else { $null }
                RunLevel           = if ($runLevel) { $runLevel.ToString() } else { $null }

                # Timing
                LastRunTime        = if ($taskInfo -and $taskInfo.LastRunTime -and $taskInfo.LastRunTime.Year -gt 1999) { $taskInfo.LastRunTime.ToString("o") } else { $null }
                LastTaskResult     = if ($taskInfo) { $taskInfo.LastTaskResult } else { $null }
                LastTaskResultHex  = if ($taskInfo) { '0x{0:X8}' -f $taskInfo.LastTaskResult } else { $null }
                NextRunTime        = if ($taskInfo -and $taskInfo.NextRunTime -and $taskInfo.NextRunTime.Year -gt 1999) { $taskInfo.NextRunTime.ToString("o") } else { $null }
                NumberOfMissedRuns = if ($taskInfo) { $taskInfo.NumberOfMissedRuns } else { $null }

                # Registration
                Date               = $task.Date
                Author             = $task.Author
                Description        = $task.Description

                # Triggers and Actions
                Triggers           = $triggers
                TriggerCount       = $triggers.Count
                Actions            = $actions
                ActionCount        = $actions.Count
                ActionSummary      = ($actions | ForEach-Object { $_.Execute }) -join '; '
            }

            $results.Add($record)
        }
    }
    catch {
        $results.Add([ordered]@{
            ComputerName = if ($TargetComputer) { $TargetComputer } else { $env:COMPUTERNAME }
            Error        = $_.Exception.Message
        })
    }

    return $results
}

# ══════════════════════════════════════════════════════════════
# Execute Scan
# ══════════════════════════════════════════════════════════════

$allTasks = [System.Collections.Generic.List[object]]::new()
$scanErrors = [System.Collections.Generic.List[object]]::new()

if (-not $ComputerName -or $ComputerName.Count -eq 0) {
    # Local scan
    Write-Host "  Scanning local machine ($env:COMPUTERNAME)..." -ForegroundColor Yellow
    $localResults = & $scanScript -TargetComputer $env:COMPUTERNAME
    foreach ($r in $localResults) {
        if ($r.Error) {
            $scanErrors.Add($r)
        }
        else {
            $allTasks.Add($r)
        }
    }
    Write-Host "  Found $($allTasks.Count) scheduled tasks" -ForegroundColor Green
}
else {
    # Remote scan
    $total = $ComputerName.Count
    $counter = 0
    Write-Host "  Scanning $total servers..." -ForegroundColor Yellow

    foreach ($server in $ComputerName) {
        $counter++
        Write-Progress -Activity "Scanning scheduled tasks" -Status "$counter / $total — $server" -PercentComplete (($counter / $total) * 100)

        try {
            $invokeParams = @{
                ComputerName = $server
                ScriptBlock  = $scanScript
                ArgumentList = $server
                ErrorAction  = 'Stop'
            }
            if ($Credential) { $invokeParams['Credential'] = $Credential }

            $remoteResults = Invoke-Command @invokeParams

            foreach ($r in $remoteResults) {
                if ($r.Error) {
                    $scanErrors.Add($r)
                }
                else {
                    $allTasks.Add($r)
                }
            }
        }
        catch {
            $scanErrors.Add([ordered]@{
                ComputerName = $server
                Error        = $_.Exception.Message
            })
            Write-Host "    FAILED: $server — $($_.Exception.Message)" -ForegroundColor Red
        }
    }

    Write-Progress -Activity "Scanning scheduled tasks" -Completed
    Write-Host "  Found $($allTasks.Count) scheduled tasks across $($total - $scanErrors.Count) servers" -ForegroundColor Green
    if ($scanErrors.Count -gt 0) {
        Write-Host "  Failed to scan $($scanErrors.Count) servers" -ForegroundColor Red
    }
}

# ══════════════════════════════════════════════════════════════
# Classify and Enrich Results
# ══════════════════════════════════════════════════════════════
Write-Host "`n  Classifying credentials and enriching results..." -ForegroundColor Yellow

$classifiedTasks = [System.Collections.Generic.List[object]]::new()

foreach ($task in $allTasks) {
    # Skip error records
    if ($task.Error) { continue }

    # Classify credential
    $classification = Get-CredentialClassification -RunAsUser $task.RunAsAccount

    # Migration target
    $migTarget = Get-TaskMigrationTarget -Task $task -Classification $classification

    # Cross-reference with D1.1
    $d1Match = $null
    $d1RiskScore = $null
    $d1RiskTier = $null
    if ($task.RunAsAccount -and $d1Accounts.Count -gt 0) {
        $samName = ($task.RunAsAccount -split '\\')[-1].ToLower().TrimEnd('$')
        if ($d1Accounts.ContainsKey($samName)) {
            $d1Match = $d1Accounts[$samName]
            $d1RiskScore = $d1Match.RiskAssessment.Score
            $d1RiskTier = $d1Match.RiskAssessment.Tier
        }
    }

    # Last run age
    $lastRunAgeDays = $null
    if ($task.LastRunTime) {
        try {
            $lastRunAgeDays = [int]((Get-Date) - [DateTime]$task.LastRunTime).TotalDays
        }
        catch { }
    }

    # Activity classification
    $activityState = "Unknown"
    if ($lastRunAgeDays -ne $null) {
        if ($lastRunAgeDays -le 7) { $activityState = "Active (last 7 days)" }
        elseif ($lastRunAgeDays -le 30) { $activityState = "Recent (last 30 days)" }
        elseif ($lastRunAgeDays -le 90) { $activityState = "Stale (30-90 days)" }
        else { $activityState = "Dormant (>90 days)" }
    }

    $enriched = [ordered]@{
        # Source identification
        ComputerName            = $task.ComputerName
        TaskName                = $task.TaskName
        TaskPath                = $task.TaskPath
        FullPath                = $task.FullPath
        State                   = $task.State
        IsMicrosoftTask         = $task.IsMicrosoftTask

        # Credential analysis
        RunAsAccount            = $task.RunAsAccount
        CredentialType          = $classification.Type
        CredentialRisk          = $classification.Risk
        CredentialCategory      = $classification.Category
        LogonType               = $task.LogonType
        RunLevel                = $task.RunLevel

        # Activity
        LastRunTime             = $task.LastRunTime
        LastRunAgeDays          = $lastRunAgeDays
        ActivityState           = $activityState
        LastTaskResult          = $task.LastTaskResult
        LastTaskResultHex       = $task.LastTaskResultHex
        LastTaskSuccess         = ($task.LastTaskResult -eq 0)
        NextRunTime             = $task.NextRunTime
        MissedRuns              = $task.NumberOfMissedRuns

        # Actions
        ActionSummary           = $task.ActionSummary
        Actions                 = $task.Actions
        ActionCount             = $task.ActionCount
        Triggers                = $task.Triggers
        TriggerCount            = $task.TriggerCount

        # Metadata
        Author                  = $task.Author
        Description             = $task.Description
        RegistrationDate        = $task.Date

        # Migration
        MigrationTarget         = $migTarget

        # D1.1 cross-reference
        D1_1_Match              = if ($d1Match) { $true } else { $false }
        D1_1_RiskScore          = $d1RiskScore
        D1_1_RiskTier           = $d1RiskTier
        D1_1_AccountType        = if ($d1Match) { $d1Match.AccountType } else { $null }
    }

    $classifiedTasks.Add($enriched)
}

# ══════════════════════════════════════════════════════════════
# Summary Statistics
# ══════════════════════════════════════════════════════════════
Write-Host "  Computing summary statistics..." -ForegroundColor Yellow

# Filter to non-Microsoft tasks with credentials
$customTasks = @($classifiedTasks | Where-Object { -not $_.IsMicrosoftTask })
$credentialTasks = @($customTasks | Where-Object { $_.CredentialRisk -in @('HIGH', 'MEDIUM') })

$riskDistribution = [ordered]@{
    HIGH   = ($classifiedTasks | Where-Object { $_.CredentialRisk -eq 'HIGH' }).Count
    MEDIUM = ($classifiedTasks | Where-Object { $_.CredentialRisk -eq 'MEDIUM' }).Count
    LOW    = ($classifiedTasks | Where-Object { $_.CredentialRisk -eq 'LOW' }).Count
    NONE   = ($classifiedTasks | Where-Object { $_.CredentialRisk -eq 'NONE' }).Count
}

$credentialTypes = $classifiedTasks |
    Group-Object -Property CredentialType |
    Sort-Object Count -Descending |
    ForEach-Object { [ordered]@{ Type = $_.Name; Count = $_.Count } }

$activityDistribution = $classifiedTasks |
    Where-Object { $_.CredentialRisk -in @('HIGH', 'MEDIUM') } |
    Group-Object -Property ActivityState |
    Sort-Object Count -Descending |
    ForEach-Object { [ordered]@{ State = $_.Name; Count = $_.Count } }

# Unique domain accounts used
$uniqueDomainAccounts = @($classifiedTasks |
    Where-Object { $_.CredentialType -eq 'Domain Account' } |
    ForEach-Object { $_.RunAsAccount } |
    Sort-Object -Unique)

# Servers with domain-credential tasks
$serversWithDomainCreds = @($classifiedTasks |
    Where-Object { $_.CredentialType -eq 'Domain Account' } |
    ForEach-Object { $_.ComputerName } |
    Sort-Object -Unique)

# Failed tasks with domain credentials
$failedDomainTasks = @($classifiedTasks |
    Where-Object { $_.CredentialType -eq 'Domain Account' -and $_.LastTaskResult -ne 0 -and $_.LastTaskResult -ne $null })

# Dormant tasks with domain credentials (cleanup candidates)
$dormantDomainTasks = @($classifiedTasks |
    Where-Object { $_.CredentialType -eq 'Domain Account' -and $_.ActivityState -match 'Dormant|Stale' })

$summary = [ordered]@{
    ExportMetadata = [ordered]@{
        Timestamp        = (Get-Date).ToString("o")
        ServersScanned   = if ($ComputerName) { $ComputerName.Count } else { 1 }
        ServersFailed    = $scanErrors.Count
        TotalTasks       = $classifiedTasks.Count
        CustomTasks      = $customTasks.Count
        MicrosoftTasks   = ($classifiedTasks | Where-Object { $_.IsMicrosoftTask }).Count
        Script           = "UIAO Spec 3 D1.2 — Scheduled Task Credential Audit"
        Reference        = "UIAO_136, ADR-004"
        D1_1_CrossRef    = if ($D1InputFile) { $D1InputFile } else { "Not provided" }
    }
    RiskDistribution      = $riskDistribution
    CredentialTypes       = @($credentialTypes)
    ActivityDistribution  = @($activityDistribution)
    UniqueAccounts = [ordered]@{
        DomainAccounts         = $uniqueDomainAccounts.Count
        AccountList            = $uniqueDomainAccounts
        ServersWithDomainCreds = $serversWithDomainCreds.Count
        ServerList             = $serversWithDomainCreds
    }
    ActionItems = [ordered]@{
        HighRiskTasks          = $riskDistribution.HIGH
        MediumRiskTasks        = $riskDistribution.MEDIUM
        FailedDomainTasks      = $failedDomainTasks.Count
        DormantDomainTasks     = $dormantDomainTasks.Count
        D1_1_Matches           = ($classifiedTasks | Where-Object { $_.D1_1_Match }).Count
    }
    ScanErrors = @($scanErrors)
}

# ══════════════════════════════════════════════════════════════
# Output: JSON
# ══════════════════════════════════════════════════════════════
$jsonOutput = [ordered]@{
    Summary = $summary
    Tasks   = @($classifiedTasks | Sort-Object @{Expression={
        switch ($_.CredentialRisk) { 'HIGH' { 0 } 'MEDIUM' { 1 } 'LOW' { 2 } 'NONE' { 3 } default { 4 } }
    }}, @{Expression={ $_.ComputerName }}, @{Expression={ $_.FullPath }})
}

$jsonFile = Join-Path $OutputPath "UIAO_Spec3_D1.2_ScheduledTaskAudit_${domain}_${timestamp}.json"
$jsonOutput | ConvertTo-Json -Depth 10 | Out-File -FilePath $jsonFile -Encoding utf8NoBOM
Write-Host "`n  JSON output: $jsonFile" -ForegroundColor Green

# ══════════════════════════════════════════════════════════════
# Output: CSV (HIGH and MEDIUM risk only — actionable subset)
# ══════════════════════════════════════════════════════════════
$csvFile = Join-Path $OutputPath "UIAO_Spec3_D1.2_ScheduledTaskAudit_${domain}_${timestamp}.csv"

$csvRecords = $classifiedTasks |
    Where-Object { $_.CredentialRisk -in @('HIGH', 'MEDIUM') } |
    ForEach-Object {
        [PSCustomObject]@{
            ComputerName     = $_.ComputerName
            TaskName         = $_.TaskName
            TaskPath         = $_.TaskPath
            State            = $_.State
            RunAsAccount     = $_.RunAsAccount
            CredentialType   = $_.CredentialType
            CredentialRisk   = $_.CredentialRisk
            ActivityState    = $_.ActivityState
            LastRunTime      = $_.LastRunTime
            LastRunAgeDays   = $_.LastRunAgeDays
            LastTaskSuccess  = $_.LastTaskSuccess
            NextRunTime      = $_.NextRunTime
            ActionSummary    = $_.ActionSummary
            MigrationTarget  = $_.MigrationTarget
            D1_1_RiskTier    = $_.D1_1_RiskTier
            Author           = $_.Author
            Description      = $_.Description
        }
    }

$csvRecords | Export-Csv -Path $csvFile -NoTypeInformation -Encoding utf8NoBOM
Write-Host "  CSV output (HIGH/MEDIUM risk): $csvFile" -ForegroundColor Green

# ══════════════════════════════════════════════════════════════
# Console Dashboard
# ══════════════════════════════════════════════════════════════
Write-Host "`n-- Scheduled Task Scan Summary --" -ForegroundColor Cyan
Write-Host "  Total tasks scanned:      $($classifiedTasks.Count)"
Write-Host "  Custom (non-Microsoft):   $($customTasks.Count)"
Write-Host "  Microsoft built-in:       $(($classifiedTasks | Where-Object { $_.IsMicrosoftTask }).Count)"

Write-Host "`n-- Credential Risk Distribution --" -ForegroundColor Cyan
Write-Host "  HIGH (domain accounts):   $($riskDistribution.HIGH)" -ForegroundColor $(if ($riskDistribution.HIGH -gt 0) { 'Red' } else { 'Green' })
Write-Host "  MEDIUM (investigate):     $($riskDistribution.MEDIUM)" -ForegroundColor $(if ($riskDistribution.MEDIUM -gt 0) { 'Yellow' } else { 'Green' })
Write-Host "  LOW (local/gMSA):         $($riskDistribution.LOW)" -ForegroundColor Green
Write-Host "  NONE (built-in):          $($riskDistribution.NONE)" -ForegroundColor DarkGray

Write-Host "`n-- Domain Account Analysis --" -ForegroundColor Cyan
Write-Host "  Unique domain accounts:   $($uniqueDomainAccounts.Count)"
Write-Host "  Servers with domain creds:$($serversWithDomainCreds.Count)"
if ($uniqueDomainAccounts.Count -gt 0 -and $uniqueDomainAccounts.Count -le 20) {
    foreach ($acct in $uniqueDomainAccounts) {
        $taskCount = ($classifiedTasks | Where-Object { $_.RunAsAccount -eq $acct }).Count
        $d1Info = ""
        $samName = ($acct -split '\\')[-1].ToLower()
        if ($d1Accounts.ContainsKey($samName)) {
            $d1Info = " [D1.1: $($d1Accounts[$samName].RiskAssessment.Tier)]"
        }
        Write-Host "    $acct ($taskCount tasks)$d1Info"
    }
}

Write-Host "`n-- Activity State (HIGH/MEDIUM risk only) --" -ForegroundColor Cyan
foreach ($a in $activityDistribution) {
    $color = switch -Wildcard ($a.State) {
        'Active*'  { 'Green' }
        'Recent*'  { 'Yellow' }
        'Stale*'   { 'DarkYellow' }
        'Dormant*' { 'Red' }
        default    { 'Gray' }
    }
    Write-Host "  $($a.Count.ToString().PadLeft(6))  $($a.State)" -ForegroundColor $color
}

Write-Host "`n-- Action Required --" -ForegroundColor Cyan
Write-Host "  Migration candidates:     $($riskDistribution.HIGH)" -ForegroundColor $(if ($riskDistribution.HIGH -gt 0) { 'Red' } else { 'Green' })
Write-Host "  Failed (domain creds):    $($failedDomainTasks.Count)" -ForegroundColor $(if ($failedDomainTasks.Count -gt 0) { 'Red' } else { 'Green' })
Write-Host "  Dormant (cleanup):        $($dormantDomainTasks.Count)" -ForegroundColor $(if ($dormantDomainTasks.Count -gt 0) { 'Yellow' } else { 'Green' })

if ($scanErrors.Count -gt 0) {
    Write-Host "`n-- Scan Errors ($($scanErrors.Count)) --" -ForegroundColor Red
    foreach ($err in $scanErrors) {
        Write-Host "  $($err.ComputerName): $($err.Error)" -ForegroundColor Red
    }
}

Write-Host "`n-- Complete --`n" -ForegroundColor Cyan
