<#
.SYNOPSIS
    Shared library for the Intune + Azure Arc modernization toolkit
    (manual path and UIAO/OrgPath-governed path).

.DESCRIPTION
    Central home for: the Connect helpers (Microsoft Graph + Azure Az), the
    modernization-domain spine (the single table that maps every domain to its
    script, actuation rung, and target plane), the critical-permission / risk
    reference lists, the governance seam that makes the SAME scripts work on
    both the manual and the governed path, and shared logging.

    THE TWO PATHS, ONE TOOLKIT
    --------------------------
    Every state-changing function takes an optional governance seam:

        -OrgPath      the organizational path the governed object belongs to
        -ApprovalRef  the change reference that authorizes the write
        -ActuationRung  L0..L4 (see the ladder below)

    * MANUAL path  — call the scripts with `-WhatIf` to preview, then without
      it to execute. No OrgPath, no ApprovalRef. The team owns the decision.
    * GOVERNED path — supply -OrgPath + -ApprovalRef. Writes above the
      configured actuation ceiling are refused unless an approval reference is
      present. This is the swappable seam: the governance layer changes, the
      execution layer does not. (Mirrors the "Access Authority Map" seam in the
      Help Desk kit.)

    THE ACTUATION MATURITY LADDER (canon: ADR-092)
    ----------------------------------------------
        L0 Record   desired state recorded in canon only
        L1 Observe  actual state collected, drift detected (read-only)
        L2 Advise   the corrective change-set is generated and surfaced; no writes
        L3 Gated    a human approves; UIAO executes through the provider API
                    (dry-run default; writes require explicit per-change approval)
        L4 Auto     the loop closes without a human (federal default ceiling: L3)

    UIAO governs (holds desired state, observes actual, classifies drift,
    reconciles toward intent); the provider remains the data plane (it
    authenticates, routes, stores at runtime). These scripts make change-making
    API calls into provider MANAGEMENT surfaces only — never into the runtime
    auth/request path.

    NOTE ON ENVIRONMENT
    -------------------
    Written to be correct against current Microsoft Graph PowerShell and the Az
    modules, but this is a *reference implementation* for review and adaptation
    — it has not been run against a live tenant. Anything that must be supplied
    locally is marked  # CONFIGURE: .
#>

# --- Microsoft Graph delegated scopes, grouped by operation (least privilege) ---
$script:GraphScopeSets = @{
    DeviceRead   = @('Device.Read.All', 'DeviceManagementManagedDevices.Read.All', 'Directory.Read.All')
    DeviceWrite  = @('DeviceManagementConfiguration.ReadWrite.All', 'DeviceManagementManagedDevices.ReadWrite.All')
    CaRead       = @('Policy.Read.All', 'Application.Read.All')
    CaWrite      = @('Policy.ReadWrite.ConditionalAccess', 'Policy.Read.All')
    OrgRead      = @('Organization.Read.All', 'Directory.Read.All')
}

# --- Actuation ladder (ADR-092). The federal default write ceiling is L3. ---
$script:ActuationLadder = [ordered]@{
    L0 = 'Record  — desired state in canon only'
    L1 = 'Observe — collect actual state, detect drift (read-only)'
    L2 = 'Advise  — generate the corrective change-set, surface it (no writes)'
    L3 = 'Gated   — human approves, UIAO executes via provider API (dry-run default)'
    L4 = 'Auto    — loop closes without a human (above the federal L3 ceiling)'
}
function Get-ActuationLadder { $script:ActuationLadder }

function Connect-ModernizationGraph {
    <#
    .SYNOPSIS  Connect to Microsoft Graph with the named scope set.
    .EXAMPLE   Connect-ModernizationGraph -ScopeSet DeviceRead
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [ValidateSet('DeviceRead','DeviceWrite','CaRead','CaWrite','OrgRead')]
        [string]$ScopeSet,
        # CONFIGURE: tenant id (GUID or *.onmicrosoft.com). Optional if single-tenant.
        [string]$TenantId
    )
    if (-not (Get-Module Microsoft.Graph.Authentication -ListAvailable)) {
        throw "Microsoft.Graph PowerShell SDK not found. Install with: Install-Module Microsoft.Graph -Scope CurrentUser"
    }
    $scopes = $script:GraphScopeSets[$ScopeSet]
    $params = @{ Scopes = $scopes; NoWelcome = $true }
    if ($TenantId) { $params.TenantId = $TenantId }
    Connect-MgGraph @params
    Write-ModernizationLog -Level INFO -Message "Connected to Graph as '$((Get-MgContext).Account)' with scopes: $($scopes -join ', ')"
}

function Connect-ModernizationAzure {
    <#
    .SYNOPSIS  Connect to Azure (Az) and set the subscription context.
    .EXAMPLE   Connect-ModernizationAzure -SubscriptionId $sub
    #>
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$SubscriptionId)   # CONFIGURE: target subscription
    if (-not (Get-Module Az.Accounts -ListAvailable)) {
        throw "Az PowerShell modules not found. Install with: Install-Module Az -Scope CurrentUser"
    }
    if (-not (Get-AzContext)) { Connect-AzAccount | Out-Null }
    Set-AzContext -SubscriptionId $SubscriptionId | Out-Null
    Write-ModernizationLog -Level INFO -Message "Azure context set to subscription $SubscriptionId"
}

function Write-ModernizationLog {
    <#  Minimal structured logger -> console + optional transcript file.  #>
    [CmdletBinding()]
    param(
        [ValidateSet('INFO','WARN','ERROR','ACTION')] [string]$Level = 'INFO',
        [Parameter(Mandatory)][string]$Message,
        [string]$LogPath = $env:MODERNIZATION_LOG   # CONFIGURE (optional): file log
    )
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

function Assert-GovernanceApproval {
    <#
    .SYNOPSIS
        The governance seam. Decides whether a state-changing operation may
        proceed, given the path the caller is on.
    .DESCRIPTION
        MANUAL path:   no -OrgPath / -ApprovalRef supplied. Returns $true; the
                       caller's own -WhatIf / -Confirm is the only guard.
        GOVERNED path: -OrgPath supplied. A write at or above the actuation
                       ceiling (default L3) REQUIRES a non-empty -ApprovalRef,
                       else the operation is refused. Every decision is logged
                       with actor + OrgPath + approval ref for the evidence trail.
    .OUTPUTS  [bool]  $true to proceed, $false to refuse.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$Operation,
        [string]$OrgPath,
        [string]$ApprovalRef,
        [ValidateSet('L0','L1','L2','L3','L4')] [string]$ActuationRung = 'L3',
        # CONFIGURE: lower the ceiling to forbid autonomous (L4) actuation in a
        # federal boundary. Default L3 is the canon federal ceiling (ADR-092).
        [ValidateSet('L1','L2','L3','L4')] [string]$ActuationCeiling = 'L3'
    )
    $rungOrder = @{ L0=0; L1=1; L2=2; L3=3; L4=4 }
    # Governed path detection: OrgPath present => governed.
    if (-not $OrgPath) {
        Write-ModernizationLog -Level WARN -Message "MANUAL path: '$Operation' has no OrgPath/ApprovalRef. Rely on -WhatIf preview and local change control."
        return $true
    }
    if ($rungOrder[$ActuationRung] -gt $rungOrder[$ActuationCeiling]) {
        Write-ModernizationLog -Level ERROR -Message "REFUSED '$Operation' for OrgPath '$OrgPath': rung $ActuationRung exceeds the actuation ceiling $ActuationCeiling. Autonomous actuation is not permitted here."
        return $false
    }
    if ($rungOrder[$ActuationRung] -ge $rungOrder['L3'] -and -not $ApprovalRef) {
        Write-ModernizationLog -Level ERROR -Message "REFUSED '$Operation' for OrgPath '$OrgPath': rung $ActuationRung is a gated actuation and requires -ApprovalRef. None supplied."
        return $false
    }
    Write-ModernizationLog -Level ACTION -Message "GOVERNED '$Operation' | OrgPath=$OrgPath | rung=$ActuationRung | approval=$ApprovalRef"
    return $true
}

# ---------------------------------------------------------------------------
# THE MODERNIZATION-DOMAIN SPINE (single source of truth)
# ---------------------------------------------------------------------------
# Maps each in-scope domain to its script, its highest actuation rung, the
# target plane, and the canon ADR that governs it. The customer guide renders
# from this same table so the runbook and the code never drift.
$script:ModernizationDomains = @(
    [pscustomobject]@{ Domain='Server onboarding';     Plane='Azure Arc';        Script='Invoke-ArcOnboarding.ps1';            Rung='L3'; Canon='ADR-002 (Arc requires non-domain-joined state)' }
    [pscustomobject]@{ Domain='Server baseline';       Plane='Azure Arc';        Script='Set-ArcPolicyBaseline.ps1';           Rung='L3'; Canon='ADR-002 / Guest Configuration' }
    [pscustomobject]@{ Domain='Endpoint enrollment';   Plane='Intune';           Script='Set-IntuneAutoEnrollment.ps1';        Rung='L3'; Canon='ADR-071 / ADR-080 (Intune-first)' }
    [pscustomobject]@{ Domain='Endpoint posture';      Plane='Intune';           Script='Get-IntuneEnrollmentStatus.ps1';      Rung='L1'; Canon='ADR-071 / UIAO_011' }
    [pscustomobject]@{ Domain='NTLM elimination';      Plane='Identity (AD/LSA)'; Script='Get-NtlmAudit.ps1';                   Rung='L1'; Canon='ADR-068 (Kerberos/NTLM elimination)' }
    [pscustomobject]@{ Domain='NTLM enforcement';      Plane='Identity (AD/LSA)'; Script='Set-NtlmRestriction.ps1';             Rung='L3'; Canon='ADR-068 (Notice 0009, 2027-04-01)' }
    [pscustomobject]@{ Domain='SPN hygiene';           Plane='Identity (AD)';    Script='Repair-Spn.ps1';                      Rung='L3'; Canon='ADR-068 (Kerberos enablement)' }
    [pscustomobject]@{ Domain='SQL hardening';         Plane='Data (SQL)';       Script='Invoke-SqlHardeningAudit.ps1';        Rung='L1'; Canon='ADR-091 (SQL engine auth transformation)' }
    [pscustomobject]@{ Domain='Conditional Access';    Plane='Security (Entra)'; Script='Deploy-ConditionalAccessBaseline.ps1'; Rung='L3'; Canon='ADR-092 (gated actuation)' }
    [pscustomobject]@{ Domain='CA drift';              Plane='Security (Entra)'; Script='Compare-ConditionalAccessDrift.ps1';   Rung='L1'; Canon='ADR-040 (drift engine)' }
    [pscustomobject]@{ Domain='Cross-domain drift';    Plane='All';              Script='Get-ModernizationDriftReport.ps1';     Rung='L1'; Canon='ADR-040 / ADR-092' }
    [pscustomobject]@{ Domain='OrgPath survey';        Plane='All';              Script='Get-OrgPathSurvey.ps1';                Rung='L2'; Canon='UIAO_011 / ADR-092 (retrofit Step 2)' }
)
function Get-ModernizationDomain { $script:ModernizationDomains }

# ---------------------------------------------------------------------------
# ORGPATH SURVEY HELPER (retrofit Step 2 — "derive OrgPath from structure")
# ---------------------------------------------------------------------------
# Advisory only (L2). Converts the structure an estate already has — Arc resource
# tags, an AD OU distinguished name — into a PROPOSED OrgPath. It does NOT write:
# stamping the proposal onto live objects is the existing gated (-OrgPath) write.
# The rules are deliberately simple and meant to be tuned per agency; edit the
# $script:OrgPathRoot and the heuristics below to match local naming.
$script:OrgPathRoot = '/Agency'   # CONFIGURE: your organization root segment

function ConvertTo-OrgPathProposal {
    <#
    .SYNOPSIS  Propose an OrgPath for one object from the structure it already has.
    .DESCRIPTION
        Supply EITHER -Tags (a hashtable of Arc/Azure resource tags) OR -OuDn
        (an Active Directory OU distinguished name). Returns a proposal object
        with the derived OrgPath, the owner (if discoverable), and a confidence
        flag so low-confidence rows can be reviewed before they are stamped.
    .OUTPUTS [pscustomobject] Proposed / Owner / Confidence / Basis
    #>
    [CmdletBinding(DefaultParameterSetName = 'Tags')]
    param(
        [Parameter(Mandatory, ParameterSetName = 'Tags')][hashtable]$Tags,
        [Parameter(Mandatory, ParameterSetName = 'Ou')][string]$OuDn,
        [string]$Root = $script:OrgPathRoot
    )
    if ($PSCmdlet.ParameterSetName -eq 'Tags') {
        $workload = $Tags['Workload']; $env = $Tags['Environment']; $owner = $Tags['Owner']
        $segs = @($Root.Trim('/'), 'Infrastructure')
        if ($workload) { $segs += $workload }
        if ($env)      { $segs += $env }
        $conf = if ($workload -and $env) { 'High' } elseif ($workload -or $env) { 'Medium' } else { 'Low' }
        return [pscustomobject]@{ Proposed = '/' + ($segs -join '/'); Owner = $owner; Confidence = $conf; Basis = 'tags' }
    }
    # OU DN -> first non-Workstations OU segment becomes the department.
    $ous  = ([regex]::Matches($OuDn, 'OU=([^,]+)') | ForEach-Object { $_.Groups[1].Value })
    $dept = ($ous | Where-Object { $_ -notmatch '^(Workstations|Computers|Devices|Endpoints)$' } | Select-Object -First 1)
    $segs = @($Root.Trim('/'))
    if ($dept) { $segs += $dept }
    $segs += 'Endpoints'
    $conf = if ($dept) { 'High' } else { 'Low' }
    return [pscustomobject]@{ Proposed = '/' + ($segs -join '/'); Owner = $null; Confidence = $conf; Basis = 'ou' }
}

# ---------------------------------------------------------------------------
# Risk reference lists
# ---------------------------------------------------------------------------
# SQL server-config switches that should be OFF on a hardened instance.
$script:SqlDangerousConfigs = @(
    'xp_cmdshell','Ole Automation Procedures','clr enabled','cross db ownership chaining',
    'remote admin connections','Database Mail XPs','Ad Hoc Distributed Queries','scan for startup procs'
)
function Get-SqlDangerousConfig { $script:SqlDangerousConfigs }

# LmCompatibilityLevel meanings (NTLM hardening, per ADR-068 staging).
$script:LmCompatibilityLevels = [ordered]@{
    0='Send LM & NTLM'; 1='Send LM & NTLM, use NTLMv2 if negotiated'; 2='Send NTLM only';
    3='Send NTLMv2 only'; 4='Send NTLMv2 only, DC refuses LM'; 5='Send NTLMv2 only, DC refuses LM & NTLM'
}
function Get-LmCompatibilityLevel { $script:LmCompatibilityLevels }

Export-ModuleMember -Function `
    Connect-ModernizationGraph, Connect-ModernizationAzure, Write-ModernizationLog, `
    Assert-GovernanceApproval, Get-ActuationLadder, Get-ModernizationDomain, `
    ConvertTo-OrgPathProposal, `
    Get-SqlDangerousConfig, Get-LmCompatibilityLevel
