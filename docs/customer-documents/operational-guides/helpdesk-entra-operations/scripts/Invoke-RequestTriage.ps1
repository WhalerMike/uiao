#requires -Modules Microsoft.Graph.Authentication, Microsoft.Graph.Mail
<#
.SYNOPSIS
    Triage the Help Desk shared mailbox: classify each incoming request by the
    authority it requires, then route it to ServiceNow (A0/A1) or SAM (A2/A3),
    or escalate (OOS). Nothing reaches the Cloud Services Team as actionable
    work until it has been approved in the destination system.

.DESCRIPTION
    This is the operational expression of the Task Authority & Routing Matrix
    (defined in ..\lib\HelpDeskEntra.psm1). For each unread message:

      1. HARD RULE - any mail from microsoft.com (esp. MSSecurity-noreply@
         microsoft.com) is force-classified as a Microsoft Security
         Notification: authority A3, TriageEscalateOnly. It is NEVER actioned
         directly and NEVER allowed to fall through to a lower-authority rule.
         (Agency decision, 2026-06-08; consistent with all three governance
         docs: Admin Consent is triage-and-escalate only.)

      2. Otherwise the subject+body is classified by Resolve-RequestRoute.

      3. The message is routed to the matched destination via a pluggable
         connector (New-ServiceNowWorkItem / New-SamAccessRequest). Those
         connectors are scaffolded with the canonical REST shapes but must be
         pointed at your instances ( # CONFIGURE: ).

      4. The message is categorized/marked read so it is not re-processed, and
         a triage row is emitted to the report.

    SAFETY: -WhatIf is honored. Run with -WhatIf first to see the routing
    decisions without creating any work items or touching mail state.

.PARAMETER MailboxUpn
    The Help Desk shared mailbox to read.  # CONFIGURE

.PARAMETER ReportPath
    CSV path for the triage report. Defaults to .\triage-report.csv

.EXAMPLE
    .\Invoke-RequestTriage.ps1 -MailboxUpn helpdesk@agency.gov -WhatIf
.EXAMPLE
    .\Invoke-RequestTriage.ps1 -MailboxUpn helpdesk@agency.gov
#>
[CmdletBinding(SupportsShouldProcess, ConfirmImpact='High')]
param(
    [Parameter(Mandatory)][string]$MailboxUpn,
    [string]$ReportPath = (Join-Path $PSScriptRoot 'triage-report.csv'),
    [int]$MaxMessages = 50,
    [string]$TenantId
)

Import-Module (Join-Path $PSScriptRoot '..\lib\HelpDeskEntra.psm1') -Force

# --- Connector configuration -------------------------------------------------
# CONFIGURE: point these at your real ServiceNow and SAM (SailPoint) endpoints.
# Stored here as a single block so there is one place to wire up integrations.
$Connectors = @{
    ServiceNow = @{
        InstanceUrl = 'https://YOURINSTANCE.service-now.com'   # CONFIGURE
        # Auth: prefer OAuth client credentials over basic. Supply a PSCredential
        # or token retrieval as your environment dictates.
        Credential  = $null   # CONFIGURE: Get-Credential or OAuth token
        Table       = 'sc_request'   # or 'incident' for A0 record-only items
    }
    SAM = @{
        # SailPoint Identity Security Cloud (ISC) access-request API base.
        BaseUrl      = 'https://YOURTENANT.api.identitynow.com'   # CONFIGURE
        ClientId     = $null   # CONFIGURE
        ClientSecret = $null   # CONFIGURE (use a secret store, not plaintext)
    }
}

# --- Destination connectors (pluggable) -------------------------------------
function New-ServiceNowWorkItem {
    param([pscustomobject]$Request, [pscustomobject]$Rule)
    # Canonical ServiceNow Table API call. Left as a guarded scaffold because
    # it writes to your ITSM system of record.
    $cfg = $Connectors.ServiceNow
    $table = if ($Rule.Authority -eq 'A0') { 'incident' } else { $cfg.Table }
    $body = @{
        short_description = "[$($Rule.Key)] $($Request.Subject)"
        description       = "Requester: $($Request.From)`nAuthority: $($Rule.Authority)`nApprover: $($Rule.Approver)`nTeam role: $($Rule.TeamRole)`n`n$($Request.BodyPreview)"
        u_required_approver = $Rule.Approver       # CONFIGURE: map to your approval field
        u_authority_tier    = $Rule.Authority
    } | ConvertTo-Json
    $uri = "$($cfg.InstanceUrl)/api/now/table/$table"
    Write-HelpDeskLog -Level ACTION -Message "ServiceNow -> $table : $($Rule.Key) ($($Rule.Authority)); approver=$($Rule.Approver)"
    # if ($cfg.Credential) { Invoke-RestMethod -Method POST -Uri $uri -Body $body -ContentType 'application/json' -Credential $cfg.Credential }
    return "ServiceNow:$table (stub)"
}

function New-SamAccessRequest {
    param([pscustomobject]$Request, [pscustomobject]$Rule)
    # SailPoint ISC access-request scaffold. A2/A3 items flow through SAM
    # approval first; on approval SAM raises a ServiceNow RITM back to the team.
    $cfg = $Connectors.SAM
    Write-HelpDeskLog -Level ACTION -Message "SAM (SailPoint) access request: $($Rule.Key) ($($Rule.Authority)); approver=$($Rule.Approver)"
    # $token = Get-SamToken @cfg ; Invoke-RestMethod -Method POST -Uri "$($cfg.BaseUrl)/v3/access-requests" -Headers @{Authorization="Bearer $token"} -Body (...)
    return "SAM:access-request (stub)"
}

function Send-ToEscalationQueue {
    param([pscustomobject]$Request, [pscustomobject]$Rule)
    Write-HelpDeskLog -Level WARN -Message "ESCALATE (out of Help Desk scope): $($Rule.Key) -> $($Rule.Approver)"
    return "Escalate:$($Rule.Approver) (stub)"
}

# --- Classification ----------------------------------------------------------
function Get-MessageClassification {
    param([Parameter(Mandatory)]$Message)

    $fromAddr = $Message.From.EmailAddress.Address
    # HARD RULE: anything from microsoft.com is a security notification and
    # must be triaged, never actioned directly.
    if ($fromAddr -imatch '@microsoft\.com$' -or $fromAddr -ieq 'MSSecurity-noreply@microsoft.com') {
        return (Get-RequestRoutingTable | Where-Object Key -eq 'MicrosoftSecurityNotification')
    }
    $text = "$($Message.Subject) `n $($Message.BodyPreview)"
    return Resolve-RequestRoute -Text $text
}

# --- Main --------------------------------------------------------------------
Connect-HelpDeskGraph -ScopeSet MailTriage -TenantId $TenantId

Write-HelpDeskLog -Level INFO -Message "Reading up to $MaxMessages unread messages from $MailboxUpn"
$messages = Get-MgUserMessage -UserId $MailboxUpn -Filter 'isRead eq false' -Top $MaxMessages `
            -Property 'id,subject,from,bodyPreview,receivedDateTime' -ErrorAction Stop

$report = foreach ($m in $messages) {
    $rule = Get-MessageClassification -Message $m
    $from = $m.From.EmailAddress.Address

    $action = switch ($rule.Destination) {
        'ServiceNow' { New-ServiceNowWorkItem -Request ([pscustomobject]@{From=$from;Subject=$m.Subject;BodyPreview=$m.BodyPreview}) -Rule $rule }
        'SAM'        { New-SamAccessRequest   -Request ([pscustomobject]@{From=$from;Subject=$m.Subject;BodyPreview=$m.BodyPreview}) -Rule $rule }
        'Escalate'   { Send-ToEscalationQueue -Request ([pscustomobject]@{From=$from;Subject=$m.Subject;BodyPreview=$m.BodyPreview}) -Rule $rule }
    }

    if ($PSCmdlet.ShouldProcess($m.Subject, "Route as $($rule.Key) [$($rule.Authority)] -> $($rule.Destination)")) {
        # Mark processed: categorize + mark read so the next run skips it.
        Update-MgUserMessage -UserId $MailboxUpn -MessageId $m.Id -IsRead:$true `
            -Categories @("Triaged:$($rule.Key)") -ErrorAction SilentlyContinue | Out-Null
    }

    [pscustomobject]@{
        Received   = $m.ReceivedDateTime
        From       = $from
        Subject    = $m.Subject
        Class      = $rule.Key
        Authority  = $rule.Authority
        Destination= $rule.Destination
        Execution  = $rule.Execution
        Approver   = $rule.Approver
        TeamRole   = $rule.TeamRole
        Action     = $action
    }
}

$report | Sort-Object Authority, Class | Format-Table -AutoSize
$report | Export-Csv -Path $ReportPath -NoTypeInformation -Encoding UTF8
Write-HelpDeskLog -Level INFO -Message "Triage complete. $($report.Count) message(s). Report: $ReportPath"
