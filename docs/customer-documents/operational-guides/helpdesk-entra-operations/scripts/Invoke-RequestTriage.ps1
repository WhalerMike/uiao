#requires -Modules Microsoft.Graph.Authentication, Microsoft.Graph.Mail
<#
.SYNOPSIS
    Triage the Help Desk shared mailbox: classify each incoming request by the
    authority it requires, then route it to ServiceNow (A0/A1) or SAM (A2/A3),
    or escalate (OOS). Nothing reaches the Cloud Services Team as actionable
    work until it has been approved in the destination system.

.DESCRIPTION
    This is the operational expression of the Task Authority & Routing Matrix
    (defined in HelpDeskEntra.psm1). For each unread message in the shared
    mailbox's Inbox folder (not Junk, Sent Items or any other folder):

      1. HARD RULE - any mail from microsoft.com or one of its subdomains is
         force-classified as a Microsoft Security Notification: authority A3,
         TriageEscalateOnly. It is NEVER actioned directly and NEVER allowed to
         fall through to a lower-authority rule. The sender check only routes;
         it is not proof a message is genuine (Microsoft sends from several
         addresses, and look-alikes exist). The proof is the matching event in
         the Entra audit log.

      2. Otherwise the subject+body is classified by Resolve-RequestRoute.

      3. Inside the ShouldProcess gate, the message is routed to the matched
         destination via a pluggable connector (New-ServiceNowWorkItem /
         New-SamAccessRequest), then categorized/marked read so it is not
         re-processed. The connectors are scaffolded with the canonical REST
         shapes but must be pointed at your instances ( # CONFIGURE: ).

      4. A triage row is emitted to the report, including the Verification the
         task needs (IdentityProof = verify the person before acting).

    SAFETY: -WhatIf is honored. With -WhatIf no connector is called, no work
    item is created and no mail state changes; the report shows what would
    have been routed.

    PERMISSIONS: delegated Mail.ReadWrite.Shared, and the signed-in operator
    needs Full Access (or folder permission) on the shared mailbox.

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

# Module sits in ..\lib\ in the kit zip and beside the scripts in the repo.
$modulePath = @((Join-Path $PSScriptRoot '..\lib\HelpDeskEntra.psm1'), (Join-Path $PSScriptRoot 'HelpDeskEntra.psm1')) |
    Where-Object { Test-Path $_ } | Select-Object -First 1
Import-Module $modulePath -Force

# --- Connector configuration -------------------------------------------------
# CONFIGURE: point these at your real ServiceNow and SAM (SailPoint) endpoints.
# Stored here as a single block so there is one place to wire up integrations.
$Connectors = @{
    ServiceNow = @{
        InstanceUrl = 'https://YOURINSTANCE.servicenowservices.com'   # CONFIGURE
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
    [Diagnostics.CodeAnalysis.SuppressMessageAttribute('PSUseDeclaredVarsMoreThanAssignments', 'body', Justification = 'Scaffolded ServiceNow REST shape; Invoke-RestMethod is intentionally commented pending endpoint configuration.')]
    [Diagnostics.CodeAnalysis.SuppressMessageAttribute('PSUseDeclaredVarsMoreThanAssignments', 'uri', Justification = 'Scaffolded ServiceNow REST shape; Invoke-RestMethod is intentionally commented pending endpoint configuration.')]
    param([pscustomobject]$Request, [pscustomobject]$Rule)
    # Canonical ServiceNow Table API call. Left as a guarded scaffold because
    # it writes to your ITSM system of record.
    $cfg = $Connectors.ServiceNow
    $table = if ($Rule.Authority -eq 'A0') { 'incident' } else { $cfg.Table }
    $body = @{
        short_description = "[$($Rule.Key)] $($Request.Subject)"
        description       = "Requester: $($Request.From)`nAuthority: $($Rule.Authority)`nApprover: $($Rule.Approver)`nTeam role: $($Rule.TeamRole)`nVerification: $($Rule.Verification)`n`n$($Request.BodyPreview)"
        u_required_approver = $Rule.Approver       # CONFIGURE: map to your approval field
        u_authority_tier    = $Rule.Authority
    } | ConvertTo-Json
    $uri = "$($cfg.InstanceUrl)/api/now/table/$table"
    Write-HelpDeskLog -Level ACTION -Message "ServiceNow -> $table : $($Rule.Key) ($($Rule.Authority)); approver=$($Rule.Approver)"
    # if ($cfg.Credential) { Invoke-RestMethod -Method POST -Uri $uri -Body $body -ContentType 'application/json' -Credential $cfg.Credential }
    return "ServiceNow:$table (stub)"
}

function New-SamAccessRequest {
    [Diagnostics.CodeAnalysis.SuppressMessageAttribute('PSUseDeclaredVarsMoreThanAssignments', 'cfg', Justification = 'Scaffolded SAM connector; $Request is part of the uniform pluggable connector signature.')]
    [Diagnostics.CodeAnalysis.SuppressMessageAttribute('PSReviewUnusedParameter', 'Request', Justification = 'Scaffolded SAM connector; $Request is part of the uniform pluggable connector signature.')]
    param([pscustomobject]$Request, [pscustomobject]$Rule)
    # SailPoint ISC access-request scaffold. A2/A3 items flow through SAM
    # approval first; on approval SAM raises a ServiceNow RITM back to the team.
    $cfg = $Connectors.SAM
    Write-HelpDeskLog -Level ACTION -Message "SAM (SailPoint) access request: $($Rule.Key) ($($Rule.Authority)); approver=$($Rule.Approver)"
    # $token = Get-SamToken @cfg ; Invoke-RestMethod -Method POST -Uri "$($cfg.BaseUrl)/v3/access-requests" -Headers @{Authorization="Bearer $token"} -Body (...)
    return "SAM:access-request (stub)"
}

function Send-ToEscalationQueue {
    [Diagnostics.CodeAnalysis.SuppressMessageAttribute('PSReviewUnusedParameter', 'Request', Justification = 'Scaffolded connector; $Request is part of the uniform pluggable connector signature.')]
    param([pscustomobject]$Request, [pscustomobject]$Rule)
    Write-HelpDeskLog -Level WARN -Message "ESCALATE (out of Help Desk scope): $($Rule.Key) -> $($Rule.Approver)"
    return "Escalate:$($Rule.Approver) (stub)"
}

# --- Classification ----------------------------------------------------------
function Get-MessageClassification {
    param([Parameter(Mandatory)]$Message)

    $fromAddr = $Message.From.EmailAddress.Address
    # HARD RULE: anything from microsoft.com or a subdomain (e.g.
    # accountprotection.microsoft.com) is a security notification and must be
    # triaged, never actioned directly.
    if ($fromAddr -imatch '@([a-z0-9-]+\.)*microsoft\.com$') {
        return (Get-RequestRoutingTable | Where-Object Key -eq 'MicrosoftSecurityNotification')
    }
    $text = "$($Message.Subject) `n $($Message.BodyPreview)"
    return Resolve-RequestRoute -Text $text
}

# --- Main --------------------------------------------------------------------
Connect-HelpDeskGraph -ScopeSet MailTriage -TenantId $TenantId

Write-HelpDeskLog -Level INFO -Message "Reading up to $MaxMessages unread Inbox messages from $MailboxUpn"
$messages = Get-MgUserMailFolderMessage -UserId $MailboxUpn -MailFolderId 'Inbox' -Filter 'isRead eq false' -Top $MaxMessages `
            -Property 'id,subject,from,bodyPreview,receivedDateTime' -ErrorAction Stop

$report = foreach ($m in $messages) {
    $rule = Get-MessageClassification -Message $m
    $from = $m.From.EmailAddress.Address
    $request = [pscustomobject]@{ From = $from; Subject = $m.Subject; BodyPreview = $m.BodyPreview }

    # Every side effect - the work item in ServiceNow/SAM and the mail-state
    # change - sits inside the ShouldProcess gate, so -WhatIf creates nothing.
    $action = "WhatIf: would route to $($rule.Destination)"
    if ($PSCmdlet.ShouldProcess($m.Subject, "Route as $($rule.Key) [$($rule.Authority)] -> $($rule.Destination)")) {
        $action = switch ($rule.Destination) {
            'ServiceNow' { New-ServiceNowWorkItem -Request $request -Rule $rule }
            'SAM'        { New-SamAccessRequest   -Request $request -Rule $rule }
            'Escalate'   { Send-ToEscalationQueue -Request $request -Rule $rule }
        }
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
        Verification = $rule.Verification
        Action     = $action
    }
}

$report | Sort-Object Authority, Class | Format-Table -AutoSize
$report | Export-Csv -Path $ReportPath -NoTypeInformation -Encoding UTF8
Write-HelpDeskLog -Level INFO -Message "Triage complete. $($report.Count) message(s). Report: $ReportPath"
