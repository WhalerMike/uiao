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
    InventoryRead    = @('Application.Read.All', 'Directory.Read.All', 'AppRoleAssignment.Read.All')
    # Group-to-app-role assignment: read the app and the group, write only the
    # assignment. Group.ReadWrite.All / Application.ReadWrite.All are NOT needed.
    AppAssignment    = @('Application.Read.All', 'Group.Read.All', 'AppRoleAssignment.ReadWrite.All')
    # Identity engineering only (see Repair-ImmutableId.ps1). RoleManagement.Read.Directory
    # backs the privileged-target refusal.
    ImmutableIdWrite = @('User.ReadWrite.All', 'Directory.Read.All', 'RoleManagement.Read.Directory')
    # User.ReadBasic.All resolves technician UPNs (Get-MgUser) without reading full profiles.
    PimGroups        = @('PrivilegedAccess.ReadWrite.AzureADGroup', 'RoleManagement.ReadWrite.Directory', 'Group.ReadWrite.All', 'User.ReadBasic.All')
    # Delegated access to a SHARED mailbox needs the .Shared scope; Mail.ReadWrite
    # alone covers only the signed-in user's own mailbox. ReadWrite so processed
    # mail can be marked read and categorized.
    MailTriage       = @('Mail.ReadWrite.Shared', 'User.Read')
}

function Connect-HelpDeskGraph {
    <#
    .SYNOPSIS  Connect to Microsoft Graph with the named scope set.
    .EXAMPLE   Connect-HelpDeskGraph -ScopeSet InventoryRead
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [ValidateSet('InventoryRead','AppAssignment','ImmutableIdWrite','PimGroups','MailTriage')]
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
#               A1  = supervisor or requester's MANAGER approves -> ServiceNow
#               A2  = manager + Application Owner          -> SAM -> ServiceNow exec
#               A3  = IGO / Identity Eng (high authority)  -> SAM escalate -> exec
#               OOS = out of scope                         -> escalate out
#   Destination ServiceNow | SAM | Escalate
#   Execution   Spoke | Manual | EscalateOnly | OutOfScope -- the recommended
#               default execution path. Spoke = a ServiceNow Microsoft Entra ID
#               spoke action auto-runs via Flow Designer; Manual = SCTASK to the
#               Help Desk. Spoke is used ONLY where the spoke documents the action:
#               it has no MFA / authentication-method reset, no device enable /
#               disable / delete, resets cloud-only passwords only, and does not
#               document group-to-app-role binding. See helpdesk-flow.qmd.
#   Approver    who owns the decision/responsibility
#   TeamRole    what the Cloud Services Team does (Execute | ExecuteAfterApproval
#                                                   | TriageEscalateOnly | OutOfScope)
#   PimRole     least-privileged role the Help Desk activates for the task ($null =
#               none, or not a Help Desk task)
#   Verification IdentityProof = verify the PERSON before acting (phishing-resistant
#               sign-in or re-proofing; never email, caller ID, a caller-supplied
#               callback number or knowledge questions), then notify the user out of
#               band. Approval is not verification: an A0 reset still needs it.
#               None = no identity check beyond the authenticated request.
#   Match       regex (case-insensitive) tested against subject + body for triage;
#               $null = never text-matched (selected by Resolve-RequestRoute)
#
# Triage cannot see from an email whether the TARGET holds a directory role, is a
# member/owner of a role-assignable group, or sits in a restricted management AU.
# The executor checks that before any credential action; any hit escalates.
#
# EXTEND HERE: add rows for new task types; refine Match patterns and Approver
# as the agency returns accurate paths. Order matters — first match wins, so
# keep the most specific / highest-authority rules near the top.
$script:AppAssignmentRole = 'Help Desk Enterprise App Assignment'   # custom role; see New-HelpDeskPAG.ps1

$script:RequestRoutingTable = @(
    [pscustomobject]@{ Key='MicrosoftSecurityNotification'; Authority='A3'; Destination='SAM'; Execution='EscalateOnly'; Approver='IGO (App Owner sponsors)'; TeamRole='TriageEscalateOnly'; PimRole=$null; Verification='None'; Match='admin consent|consent request|review permissions|MSSecurity-noreply|enterprise application.*permission' }
    [pscustomobject]@{ Key='AdminConsentRequest'; Authority='A3'; Destination='SAM'; Execution='EscalateOnly'; Approver='IGO (App Owner sponsors)'; TeamRole='TriageEscalateOnly'; PimRole=$null; Verification='None'; Match='admin consent|grant consent|oauth (scope|permission)|tenant-wide permission' }
    [pscustomobject]@{ Key='ImmutableIdRepair'; Authority='A3'; Destination='SAM'; Execution='EscalateOnly'; Approver='Identity Eng Lead + IGO (Identity Engineering executes, usually in AD)'; TeamRole='TriageEscalateOnly'; PimRole=$null; Verification='None'; Match='immutableid|immutable id|onpremisesimmutableid|sync mismatch|duplicate (cloud )?account|hard match' }
    [pscustomobject]@{ Key='EnterpriseAppAccess'; Authority='A2'; Destination='SAM'; Execution='Manual'; Approver='Manager + Application Owner'; TeamRole='ExecuteAfterApproval'; PimRole=$script:AppAssignmentRole; Verification='None'; Match='access to .*application|application access|app role|assign.*(group|app)|enterprise app(lication)? access' }
    [pscustomobject]@{ Key='GroupCreation'; Authority='A2'; Destination='SAM'; Execution='Spoke'; Approver='App Owner + Identity Eng'; TeamRole='ExecuteAfterApproval'; PimRole='Groups Administrator'; Verification='None'; Match='create (a )?(security )?group|new (security )?group|add (an )?owner|remove (an )?owner' }
    [pscustomobject]@{ Key='DeviceManagement'; Authority='OOS'; Destination='Escalate'; Execution='OutOfScope'; Approver='Device team (endpoint management)'; TeamRole='OutOfScope'; PimRole=$null; Verification='None'; Match='(enable|disable|delete|remove|retire) (the )?device|device (compliance|stale|cleanup)' }
    [pscustomobject]@{ Key='UserLifecycleCreateDisable'; Authority='A2'; Destination='SAM'; Execution='Spoke'; Approver='Manager + HR / Owner (SAM lifecycle)'; TeamRole='ExecuteAfterApproval'; PimRole='User Administrator'; Verification='None'; Match='onboard|new hire|create (a )?(new )?user|off-?board|terminat|leaver|joiner|disable (the )?(user|account)|deactivate account' }
    [pscustomobject]@{ Key='AccessCertRevocation'; Authority='A2'; Destination='SAM'; Execution='Spoke'; Approver='SAM certification (App Owner)'; TeamRole='Execute'; PimRole=$script:AppAssignmentRole; Verification='None'; Match='certification|recertif|revoke access|access review' }
    [pscustomobject]@{ Key='TemporaryAccessPass'; Authority='A1'; Destination='ServiceNow'; Execution='Manual'; Approver="Help desk supervisor or requester's manager"; TeamRole='ExecuteAfterApproval'; PimRole='Authentication Administrator'; Verification='IdentityProof'; Match='temporary access pass|\btap\b|lost (all|every) (sign-?in )?(method|factor)s?|account recovery' }
    [pscustomobject]@{ Key='MfaReset'; Authority='A1'; Destination='ServiceNow'; Execution='Manual'; Approver="Help desk supervisor or requester's manager"; TeamRole='ExecuteAfterApproval'; PimRole='Authentication Administrator'; Verification='IdentityProof'; Match='mfa|multi-?factor|authenticator|fido2|passkey|lost (phone|token)|re-?register.*method' }
    [pscustomobject]@{ Key='LicenseAssignment'; Authority='A1'; Destination='ServiceNow'; Execution='Spoke'; Approver="Requester's manager"; TeamRole='ExecuteAfterApproval'; PimRole='License Administrator'; Verification='None'; Match='licen[cs]e|\b[eg][35]\b|\bsku\b' }
    [pscustomobject]@{ Key='UserEnableUpdate'; Authority='A1'; Destination='ServiceNow'; Execution='Spoke'; Approver="Requester's manager"; TeamRole='ExecuteAfterApproval'; PimRole='User Administrator'; Verification='None'; Match='enable (the )?(user|account)|unlock (the )?account|update (user|profile|attribute)|assign manager|set manager|change (title|department|display name)' }
    [pscustomobject]@{ Key='OneDriveProvisioning'; Authority='A1'; Destination='ServiceNow'; Execution='Manual'; Approver="Requester's manager (pre-provisioning is a SharePoint Administrator task)"; TeamRole='ExecuteAfterApproval'; PimRole=$null; Verification='None'; Match='provision onedrive|create onedrive|onedrive not (created|provisioned)' }
    [pscustomobject]@{ Key='AuditLogRetrieval'; Authority='A0'; Destination='ServiceNow'; Execution='Spoke'; Approver='None'; TeamRole='Execute'; PimRole='Reports Reader'; Verification='None'; Match='sign-?in log|audit log|directory audit|who (signed in|accessed)|access evidence' }
    [pscustomobject]@{ Key='OneDriveClientSide'; Authority='A0'; Destination='ServiceNow'; Execution='Manual'; Approver='None'; TeamRole='Execute'; PimRole=$null; Verification='None'; Match='onedrive (sync|not syncing|stuck|error)|kfm|known folder|onedrive cache|reset onedrive' }
    # Password reset: text triage cannot tell a cloud-only user from a synced one,
    # so the matched row is the conservative Manual default. Resolve-RequestRoute
    # -TargetSynced selects the cloud-only (Spoke) or synced (Manual) row once the
    # target's onPremisesSyncEnabled is known.
    [pscustomobject]@{ Key='PasswordReset'; Authority='A0'; Destination='ServiceNow'; Execution='Manual'; Approver='None (no approval; identity verification required)'; TeamRole='Execute'; PimRole='Password Administrator'; Verification='IdentityProof'; Match='password reset|reset.*password|forgot password|locked out' }
    [pscustomobject]@{ Key='PasswordResetCloudOnly'; Authority='A0'; Destination='ServiceNow'; Execution='Spoke'; Approver='None (no approval; identity verification required)'; TeamRole='Execute'; PimRole='Password Administrator'; Verification='IdentityProof'; Match=$null }
    [pscustomobject]@{ Key='PasswordResetSynced'; Authority='A0'; Destination='ServiceNow'; Execution='Manual'; Approver='None (no approval; identity verification required); reset in the Entra admin center with password writeback, else in AD'; TeamRole='Execute'; PimRole='Password Administrator'; Verification='IdentityProof'; Match=$null }
    [pscustomobject]@{ Key='ConditionalAccess'; Authority='OOS'; Destination='Escalate'; Execution='OutOfScope'; Approver='Security Admin + IGO'; TeamRole='OutOfScope'; PimRole=$null; Verification='None'; Match='conditional access|ca policy|blocked by policy|access policy exception' }
    [pscustomobject]@{ Key='DirectoryRoleAssignment'; Authority='OOS'; Destination='Escalate'; Execution='OutOfScope'; Approver='Identity Eng + IGO'; TeamRole='OutOfScope'; PimRole=$null; Verification='None'; Match='directory role|admin role|make.*administrator|grant.*role' }
    [pscustomobject]@{ Key='ServicePrincipalChange'; Authority='OOS'; Destination='Escalate'; Execution='OutOfScope'; Approver='App Owner + Identity Eng'; TeamRole='OutOfScope'; PimRole=$null; Verification='None'; Match='service principal|app registration|register (an )?app|client secret|certificate credential' }
    [pscustomobject]@{ Key='OrganizationInfo'; Authority='OOS'; Destination='Escalate'; Execution='OutOfScope'; Approver='Identity Eng'; TeamRole='OutOfScope'; PimRole=$null; Verification='None'; Match='tenant (info|settings|details)|organization (info|details|settings)' }
)

function Get-RequestRoutingTable { $script:RequestRoutingTable }

function Resolve-RequestRoute {
    <#
    .SYNOPSIS  Classify free text (e.g. an email subject+body) to a routing rule.
    .DESCRIPTION
        First-match-wins against the routing table's Match regexes (rows with no
        Match are skipped). Microsoft Security mail is force-classified upstream
        (see Invoke-RequestTriage) so it can never fall through to a
        lower-authority rule.

        -TargetSynced refines a password-reset match once the target's
        onPremisesSyncEnabled is known: $false selects the cloud-only row (the
        spoke's Reset Password covers users created in Entra ID only); $true
        selects the synced row (manual, Entra admin center with writeback).
    .OUTPUTS   The matched routing rule object, or the 'Unknown' fallback.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][AllowEmptyString()][string]$Text,
        [Nullable[bool]]$TargetSynced
    )

    foreach ($rule in $script:RequestRoutingTable) {
        if (-not $rule.Match) { continue }
        if ($Text -imatch $rule.Match) {
            if ($rule.Key -eq 'PasswordReset' -and $null -ne $TargetSynced) {
                $variant = if ($TargetSynced) { 'PasswordResetSynced' } else { 'PasswordResetCloudOnly' }
                return ($script:RequestRoutingTable | Where-Object Key -eq $variant)
            }
            return $rule
        }
    }
    return [pscustomobject]@{
        Key='Unknown'; Authority='A1'; Destination='ServiceNow'; Execution='Manual';
        Approver='Manual triage (human review)'; TeamRole='ExecuteAfterApproval';
        PimRole=$null; Verification='None'; Match=$null
    }
}

function Get-AppAssignmentRoleName { $script:AppAssignmentRole }

Export-ModuleMember -Function Connect-HelpDeskGraph, Write-HelpDeskLog,
    Get-CriticalPermissionList, Get-HighRiskPermissionList,
    Get-RequestRoutingTable, Resolve-RequestRoute, Get-AppAssignmentRoleName
