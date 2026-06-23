<#
.SYNOPSIS
    Shared library for the Help Desk / Cloud Services Entra ID operations toolkit.

.DESCRIPTION
    Central home for: the Connect helper, the Task Authority & Routing Matrix
    (the single source of truth that drives both the human runbook and the
    Invoke-RequestTriage classifier), the critical-permission reference list
    used for risk tiering, and shared logging.

    DESIGN PRINCIPLE
    ----------------
    The Cloud Services Team (3 x GS-12/GS-13) EXECUTES approved work; it is NOT
    an approval gate for routine tasks. Approval + responsibility sit with the
    requester's MANAGER (or the relevant owner), scaled to the authority the
    task requires. Intake is triaged into ServiceNow (A0/A1) or SAM (A2/A3);
    out-of-scope items escalate out. The team only ever touches fully-approved
    work, and never approves Admin Consent.

    This file is the place to extend the model: when the agency returns more
    accurate approval paths, or you discover new task types, edit the
    $script:RequestRoutingTable below. No other file should need to change.

    NOTE ON ENVIRONMENT
    -------------------
    These scripts are written to be correct against current Microsoft Graph
    PowerShell, but they are a *reference implementation* for review and
    adaptation — they have not been run against a live tenant. Anything that
    must be supplied locally is marked  # CONFIGURE: .
#>

# Microsoft Graph delegated scopes, grouped by the operation that needs them.
# Request only what a given script uses (least privilege).
$script:GraphScopeSets = @{
    InventoryRead   = @('Application.Read.All', 'Directory.Read.All', 'AppRoleAssignment.Read.All')
    OwnerWrite      = @('Application.ReadWrite.All', 'Directory.Read.All')
    GroupWrite      = @('Group.ReadWrite.All', 'GroupMember.Read.All', 'Application.ReadWrite.All')
    HybridUserWrite = @('User.ReadWrite.All', 'Directory.Read.All')
    PimGroups       = @('PrivilegedAccess.ReadWrite.AzureADGroup', 'RoleManagement.ReadWrite.Directory', 'Group.ReadWrite.All')
    MailTriage      = @('Mail.ReadWrite', 'User.Read')   # ReadWrite so processed mail can be marked/categorized
}

function Connect-HelpDeskGraph {
    <#
    .SYNOPSIS  Connect to Microsoft Graph with the named scope set.
    .EXAMPLE   Connect-HelpDeskGraph -ScopeSet InventoryRead
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [ValidateSet('InventoryRead','OwnerWrite','GroupWrite','HybridUserWrite','PimGroups','MailTriage')]
        [string]$ScopeSet,

        # CONFIGURE: your tenant id (GUID or *.onmicrosoft.com). Optional if you
        # only belong to one tenant.
        [string]$TenantId
    )
    if (-not (Get-Module Microsoft.Graph.Authentication -ListAvailable)) {
        throw "Microsoft.Graph PowerShell SDK not found. Install with: Install-Module Microsoft.Graph -Scope CurrentUser"
    }
    $scopes = $script:GraphScopeSets[$ScopeSet]
    $params = @{ Scopes = $scopes; NoWelcome = $true }
    if ($TenantId) { $params.TenantId = $TenantId }
    Connect-MgGraph @params
    Write-HelpDeskLog -Level INFO -Message "Connected to Graph as '$((Get-MgContext).Account)' with scopes: $($scopes -join ', ')"
}

function Write-HelpDeskLog {
    <#  Minimal structured logger -> console + optional transcript file.  #>
    [CmdletBinding()]
    param(
        [ValidateSet('INFO','WARN','ERROR','ACTION')] [string]$Level = 'INFO',
        [Parameter(Mandatory)][string]$Message,
        [string]$LogPath = $env:HELPDESK_LOG   # CONFIGURE (optional): set $env:HELPDESK_LOG to capture a file log
    )
    # Caller supplies the timestamp source; in a script use (Get-Date). Avoided here
    # so the module stays side-effect free at import time.
    $stamp = (Get-Date).ToString('s')
    $line  = "{0} [{1}] {2}" -f $stamp, $Level, $Message
    switch ($Level) {
        'ERROR'  { Write-Host $line -ForegroundColor Red }
        'WARN'   { Write-Host $line -ForegroundColor Yellow }
        'ACTION' { Write-Host $line -ForegroundColor Cyan }
        default  { Write-Host $line }
    }
    if ($LogPath) { Add-Content -Path $LogPath -Value $line }
}

# ---------------------------------------------------------------------------
# CRITICAL / HIGH-RISK Microsoft Graph permissions (from Doc 3 risk table).
# Used by Get-EnterpriseAppInventory to auto-tier applications.
# An app holding ANY of these as an *application* permission => Tier 1.
# ---------------------------------------------------------------------------
$script:CriticalAppPermissions = @(
    'Mail.ReadWrite.All','Mail.Send','Files.ReadWrite.All','User.ReadWrite.All',
    'Directory.ReadWrite.All','RoleManagement.ReadWrite.Directory','Group.ReadWrite.All',
    'Application.ReadWrite.All','AppRoleAssignment.ReadWrite.All','Sites.FullControl.All'
)
$script:HighRiskAppPermissions = @(
    'Calendars.ReadWrite','User.Read.All','Group.Read.All','Mail.Read','Files.Read.All'
)

function Get-CriticalPermissionList { $script:CriticalAppPermissions }
function Get-HighRiskPermissionList { $script:HighRiskAppPermissions }

# ---------------------------------------------------------------------------
# THE TASK AUTHORITY & ROUTING MATRIX  (single source of truth)
# ---------------------------------------------------------------------------
# Each rule maps an incoming request to:
#   Authority   A0  = no approval (team executes; ServiceNow record only)
#               A1  = requester's MANAGER approves        -> ServiceNow
#               A2  = manager + Application Owner          -> SAM -> ServiceNow exec
#               A3  = IGO / Identity Eng (high authority)  -> SAM escalate -> exec
#               OOS = out of scope                         -> escalate out
#   Destination ServiceNow | SAM | Escalate
#   Execution   Spoke | Manual | SAM | EscalateOnly | OutOfScope -- the recommended
#               default execution path. Spoke = ServiceNow Entra ID Spoke action
#               auto-runs via Flow Designer; Manual = SCTASK to Help Desk / Cloud
#               Services for the gaps (OneDrive, ImmutableID, Conditional Access,
#               one-time group->app-role binding). See helpdesk-flow.md §A3.
#   Approver    who owns the decision/responsibility
#   TeamRole    what the Cloud Services Team does (Execute | ExecuteAfterApproval
#                                                   | TriageEscalateOnly | OutOfScope)
#   Match       regex (case-insensitive) tested against subject + body for triage
#
# EXTEND HERE: add rows for new task types; refine Match patterns and Approver
# as the agency returns accurate paths. Order matters — first match wins, so
# keep the most specific / highest-authority rules near the top.
$script:RequestRoutingTable = @(
    [pscustomobject]@{ Key='MicrosoftSecurityNotification'; Authority='A3'; Destination='SAM'; Execution='EscalateOnly'; Approver='IGO (App Owner sponsors)'; TeamRole='TriageEscalateOnly'; PimRole=$null; Match='admin consent|consent request|review permissions|MSSecurity-noreply|enterprise application.*permission' }
    [pscustomobject]@{ Key='AdminConsentRequest'; Authority='A3'; Destination='SAM'; Execution='EscalateOnly'; Approver='IGO (App Owner sponsors)'; TeamRole='TriageEscalateOnly'; PimRole=$null; Match='admin consent|grant consent|oauth (scope|permission)|tenant-wide permission' }
    [pscustomobject]@{ Key='ImmutableIdRepair'; Authority='A3'; Destination='SAM'; Execution='Manual'; Approver='Identity Eng Lead + IGO'; TeamRole='ExecuteAfterApproval'; PimRole='Hybrid Identity Administrator'; Match='immutableid|immutable id|onpremisesimmutableid|sync mismatch|duplicate (cloud )?account|hard match' }
    [pscustomobject]@{ Key='EnterpriseAppAccess'; Authority='A2'; Destination='SAM'; Execution='Spoke'; Approver='Manager + Application Owner'; TeamRole='ExecuteAfterApproval'; PimRole='Application Administrator'; Match='access to .*application|application access|app role|assign.*(group|app)|enterprise app(lication)? access' }
    [pscustomobject]@{ Key='GroupCreation'; Authority='A2'; Destination='SAM'; Execution='Spoke'; Approver='App Owner + Identity Eng'; TeamRole='ExecuteAfterApproval'; PimRole='Groups Administrator'; Match='create (a )?(security )?group|new (security )?group|add (an )?owner|remove (an )?owner' }
    [pscustomobject]@{ Key='DeviceManagement'; Authority='A2'; Destination='ServiceNow'; Execution='Spoke'; Approver='Manager + Device team'; TeamRole='ExecuteAfterApproval'; PimRole=$null; Match='(enable|disable|delete|remove|retire) (the )?device|device (compliance|stale|cleanup)' }
    [pscustomobject]@{ Key='UserLifecycleCreateDisable'; Authority='A2'; Destination='SAM'; Execution='Spoke'; Approver='Manager + HR / Owner (SAM lifecycle)'; TeamRole='ExecuteAfterApproval'; PimRole='User Administrator'; Match='onboard|new hire|create (a )?(new )?user|off-?board|terminat|leaver|joiner|disable (the )?(user|account)|deactivate account' }
    [pscustomobject]@{ Key='AccessCertRevocation'; Authority='A2'; Destination='SAM'; Execution='Spoke'; Approver='SAM certification (App Owner)'; TeamRole='Execute'; PimRole='Application Administrator'; Match='certification|recertif|revoke access|access review' }
    [pscustomobject]@{ Key='MfaReset'; Authority='A1'; Destination='ServiceNow'; Execution='Spoke'; Approver="Requester's manager"; TeamRole='ExecuteAfterApproval'; PimRole='Authentication Administrator'; Match='mfa|multi-?factor|authenticator|fido2|lost (phone|token)|re-?register.*method' }
    [pscustomobject]@{ Key='LicenseAssignment'; Authority='A1'; Destination='ServiceNow'; Execution='Spoke'; Approver="Requester's manager"; TeamRole='ExecuteAfterApproval'; PimRole='User Administrator'; Match='license|e3|e5|assign.*licen|sku' }
    [pscustomobject]@{ Key='UserEnableUpdate'; Authority='A1'; Destination='ServiceNow'; Execution='Spoke'; Approver="Requester's manager"; TeamRole='ExecuteAfterApproval'; PimRole='User Administrator'; Match='enable (the )?(user|account)|unlock (the )?account|update (user|profile|attribute)|assign manager|set manager|change (title|department|display name)' }
    [pscustomobject]@{ Key='OneDriveProvisioning'; Authority='A1'; Destination='ServiceNow'; Execution='Manual'; Approver="Requester's manager"; TeamRole='ExecuteAfterApproval'; PimRole=$null; Match='provision onedrive|create onedrive|onedrive not (created|provisioned)' }
    [pscustomobject]@{ Key='AuditLogRetrieval'; Authority='A0'; Destination='ServiceNow'; Execution='Spoke'; Approver='None'; TeamRole='Execute'; PimRole=$null; Match='sign-?in log|audit log|directory audit|who (signed in|accessed)|access evidence' }
    [pscustomobject]@{ Key='OneDriveClientSide'; Authority='A0'; Destination='ServiceNow'; Execution='Manual'; Approver='None'; TeamRole='Execute'; PimRole=$null; Match='onedrive (sync|not syncing|stuck|error)|kfm|known folder|onedrive cache|reset onedrive' }
    [pscustomobject]@{ Key='PasswordReset'; Authority='A0'; Destination='ServiceNow'; Execution='Spoke'; Approver='None (SSPR/identity-proof)'; TeamRole='Execute'; PimRole='User Administrator'; Match='password reset|reset.*password|forgot password|locked out' }
    [pscustomobject]@{ Key='ConditionalAccess'; Authority='OOS'; Destination='Escalate'; Execution='OutOfScope'; Approver='Security Admin + IGO'; TeamRole='OutOfScope'; PimRole=$null; Match='conditional access|ca policy|blocked by policy|access policy exception' }
    [pscustomobject]@{ Key='DirectoryRoleAssignment'; Authority='OOS'; Destination='Escalate'; Execution='OutOfScope'; Approver='Identity Eng + IGO'; TeamRole='OutOfScope'; PimRole=$null; Match='directory role|admin role|make.*administrator|grant.*role' }
    [pscustomobject]@{ Key='ServicePrincipalChange'; Authority='OOS'; Destination='Escalate'; Execution='OutOfScope'; Approver='App Owner + Identity Eng'; TeamRole='OutOfScope'; PimRole=$null; Match='service principal|app registration|register (an )?app|client secret|certificate credential' }
    [pscustomobject]@{ Key='OrganizationInfo'; Authority='OOS'; Destination='Escalate'; Execution='OutOfScope'; Approver='Identity Eng'; TeamRole='OutOfScope'; PimRole=$null; Match='tenant (info|settings|details)|organization (info|details|settings)' }
)

function Get-RequestRoutingTable { $script:RequestRoutingTable }

function Resolve-RequestRoute {
    <#
    .SYNOPSIS  Classify free text (e.g. an email subject+body) to a routing rule.
    .DESCRIPTION
        First-match-wins against the routing table's Match regexes. Microsoft
        Security mail is force-classified upstream (see Invoke-RequestTriage)
        so it can never fall through to a lower-authority rule.
    .OUTPUTS   The matched routing rule object, or the 'Unknown' fallback.
    #>
    [CmdletBinding()]
    param([Parameter(Mandatory)][AllowEmptyString()][string]$Text)

    foreach ($rule in $script:RequestRoutingTable) {
        if ($Text -imatch $rule.Match) { return $rule }
    }
    return [pscustomobject]@{
        Key='Unknown'; Authority='A1'; Destination='ServiceNow'; Execution='Manual';
        Approver='Manual triage (human review)'; TeamRole='ExecuteAfterApproval';
        PimRole=$null; Match=$null
    }
}

Export-ModuleMember -Function Connect-HelpDeskGraph, Write-HelpDeskLog,
    Get-CriticalPermissionList, Get-HighRiskPermissionList,
    Get-RequestRoutingTable, Resolve-RequestRoute
