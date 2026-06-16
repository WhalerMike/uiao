# UIAOIdentityAssessment — hybrid identity assessment (canon UIAO_181, ADR-094).
#
# Producer in the assessment-to-plan toolchain (ADR-094 Decision 1). Inventories
# Entra ID via Microsoft Graph and reconciles it against on-prem AD, emitting
# sealed UIAO-schema identity assessment artifacts that UIAOPlanGenerators
# consumes.
#
# Doctrine (UIAO_181 §Non-functional contract / §Graph endpoint resolution):
#   - Read-only inventory of Entra identity objects + AD-vs-Entra reconciliation.
#   - Live Graph reads resolve their endpoint via the cloud-aware resolver
#     (the PowerShell analogue of uiao.adapters._graph_clouds.resolve_graph_base):
#     default cloud 'commercial' serves GCC-Moderate (ADR-033); unknown clouds
#     fail closed.
#   - Every exporter accepts -SnapshotPath for offline normalization of a
#     pre-captured Graph response (the analogue of OrgPathTools -PrincipalSnapshot),
#     so the module is testable without a live tenant or the Microsoft.Graph SDK.
#   - Output carries a provenance envelope (tenant id, Graph API version, capture
#     timestamp) sealed with a content_hash byte-identical to
#     uiao.ir.models.core.canonical_hash, so a broken/unattributed envelope is a
#     DRIFT-PROVENANCE finding and reconciliation inconsistencies are
#     DRIFT-IDENTITY, per src/uiao/governance/drift.py.
#
# Self-contained per the tools/powershell convention (OrgPathTools /
# OrgTreeValidation / UIAOImportAdapters): the private seal/validation helpers
# mirror UIAOImportAdapters; the Python canonical hasher is authoritative.
#
# Exports (UIAO_181 §Function roster):
#   Export-UIAOEntraUsers           Entra user inventory       -> EntraUserInventory
#   Export-UIAOEntraGroups          Entra groups + membership  -> EntraGroupInventory
#   Export-UIAOEntraApps            App regs + service princ.  -> EntraAppInventory
#   Export-UIAOConditionalAccess    Conditional Access policy  -> ConditionalAccessInventory
#   Compare-UIAOIdentitySources     AD-vs-Entra reconciliation -> IdentityReconciliation
#   Invoke-UIAOIdentityAssessment   Master orchestrator        -> IdentityAssessmentBundle

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Script:ModuleVersion = '1.0.0'
$Script:MaxInputBytes = 200MB
$Script:DefaultGraphApiVersion = 'v1.0'

# Sovereign-cloud Graph endpoints, mirroring
# uiao.adapters._graph_clouds.GRAPH_ENDPOINTS. 'commercial' also serves
# GCC-Moderate (ADR-033) — a tenancy designation on commercial infrastructure,
# not a separate endpoint.
$Script:GraphEndpoints = @{
    'commercial' = 'https://graph.microsoft.com'
    'gcc-high'   = 'https://graph.microsoft.us'
    'dod'        = 'https://dod-graph.microsoft.us'
}
$Script:DefaultCloud = 'commercial'


# ---------------------------------------------------------------------------
# Private helpers (seal / validation — mirror UIAOImportAdapters)
# ---------------------------------------------------------------------------

function Resolve-UIAOPython {
    if ($env:UIAO_PYTHON) { return $env:UIAO_PYTHON }
    foreach ($candidate in @('python3', 'python')) {
        if (Get-Command $candidate -ErrorAction SilentlyContinue) { return $candidate }
    }
    throw "No Python interpreter found (looked for python3, python). Set `$env:UIAO_PYTHON to the interpreter path."
}

function Get-UIAOCanonicalHash {
    # SHA-256 over canonical JSON, byte-identical to
    # uiao.ir.models.core.canonical_hash. Python re-canonicalizes, so the
    # PowerShell JSON only needs to be parseable.
    [CmdletBinding()]
    [OutputType([string])]
    param(
        [Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string]$Json
    )
    $py = Resolve-UIAOPython
    $pyScript = @'
import sys, json, hashlib
data = json.load(sys.stdin)
canon = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
sys.stdout.write(hashlib.sha256(canon.encode("utf-8")).hexdigest())
'@
    $result = $Json | & $py '-c' $pyScript
    if ($LASTEXITCODE -ne 0) { throw "Canonical-hash helper (python) exited $LASTEXITCODE" }
    return (($result -join '').Trim())
}

function Assert-UIAOInputPath {
    # SI-10 input validation: reject null/missing/oversize paths.
    [CmdletBinding()]
    [OutputType([string])]
    param([Parameter(Mandatory = $true)][string]$Path)
    if ([string]::IsNullOrWhiteSpace($Path)) { throw "Input path is null or empty." }
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "Input file not found: $Path" }
    $item = Get-Item -LiteralPath $Path
    if ($item.Length -gt $Script:MaxInputBytes) {
        $mb = [math]::Round($item.Length / 1MB, 1)
        throw "Input file exceeds the $([int]($Script:MaxInputBytes / 1MB)) MB safety cap: $Path ($mb MB)"
    }
    return $item.FullName
}

function Read-UIAOSourceData {
    [CmdletBinding()]
    param([Parameter(Mandatory = $true)][string]$Path)
    $ext = [System.IO.Path]::GetExtension($Path).ToLowerInvariant()
    switch ($ext) {
        '.json' {
            $raw = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
            if ([string]::IsNullOrWhiteSpace($raw)) { throw "Source file is empty: $Path" }
            try { return ($raw | ConvertFrom-Json) }
            catch { throw "Source file is not valid JSON: $Path ($($_.Exception.Message))" }
        }
        '.csv' { return @(Import-Csv -LiteralPath $Path) }
        default { throw "Unsupported source extension '$ext' (expected .json or .csv): $Path" }
    }
}

function Get-UIAORows {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][AllowNull()]$Data,
        [Parameter(Mandatory = $false)][string[]]$PreferredArrayKeys = @()
    )
    if ($null -eq $Data) { return @() }
    if (($Data -is [System.Collections.IEnumerable]) -and ($Data -isnot [string])) { return @($Data) }
    foreach ($key in $PreferredArrayKeys) {
        $prop = $Data.PSObject.Properties | Where-Object { $_.Name -ieq $key } | Select-Object -First 1
        if ($prop -and $prop.Value) { return @($prop.Value) }
    }
    return @($Data)
}

function Get-UIAOFieldValue {
    [CmdletBinding()]
    [OutputType([string])]
    param(
        [Parameter(Mandatory = $true, Position = 0)]$Row,
        [Parameter(Mandatory = $true, Position = 1)][string[]]$Aliases
    )
    foreach ($alias in $Aliases) {
        $prop = $Row.PSObject.Properties | Where-Object { $_.Name -ieq $alias } | Select-Object -First 1
        if ($prop -and ($null -ne $prop.Value) -and ("$($prop.Value)".Trim() -ne '')) {
            return "$($prop.Value)"
        }
    }
    return $null
}

function ConvertTo-UIAOSourceFields {
    [CmdletBinding()]
    param([Parameter(Mandatory = $true)]$Row)
    $fields = [ordered]@{}
    foreach ($prop in ($Row.PSObject.Properties | Sort-Object Name)) {
        $fields[$prop.Name] = if ($null -eq $prop.Value) { $null } else { "$($prop.Value)" }
    }
    return $fields
}

function Resolve-UIAOGraphBase {
    <#
    .SYNOPSIS
        Resolve the Graph base URL (cloud-aware, fail-closed) — the PowerShell
        analogue of uiao.adapters._graph_clouds.resolve_graph_base.
    #>
    [CmdletBinding()]
    [OutputType([string])]
    param(
        [Parameter(Mandatory = $false)][string]$Cloud = $Script:DefaultCloud,
        [Parameter(Mandatory = $false)][string]$GraphApiVersion = $Script:DefaultGraphApiVersion,
        [Parameter(Mandatory = $false)][string]$Explicit
    )
    if (-not [string]::IsNullOrWhiteSpace($Explicit)) { return $Explicit }
    if (-not $Script:GraphEndpoints.ContainsKey($Cloud)) {
        $supported = ($Script:GraphEndpoints.Keys | Sort-Object) -join ', '
        throw "UIAOIdentityAssessment: unknown cloud '$Cloud'. Supported clouds: $supported. Set -Cloud or pass an explicit -GraphEndpoint."
    }
    return "$($Script:GraphEndpoints[$Cloud])/$GraphApiVersion"
}

function New-UIAOIdentityEnvelope {
    <#
    .SYNOPSIS
        Wrap normalized identity records in a sealed provenance envelope.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)] [string]$SourceTool,
        [Parameter(Mandatory = $true)] [string]$TargetSchema,
        [Parameter(Mandatory = $false)][string]$TenantId,
        [Parameter(Mandatory = $false)][string]$GraphApiVersion,
        [Parameter(Mandatory = $false)][string]$GraphEndpoint,
        [Parameter(Mandatory = $true)] [string]$SourceRef,
        [Parameter(Mandatory = $true)] [AllowEmptyCollection()][object[]]$Records
    )
    $recordArray = @($Records)
    $data = [ordered]@{
        target_schema = $TargetSchema
        record_count  = $recordArray.Count
        records       = $recordArray
    }
    $contentHash = Get-UIAOCanonicalHash -Json ($data | ConvertTo-Json -Depth 30)
    return [ordered]@{
        schema        = 'uiao.identity.v1'
        target_schema = $TargetSchema
        provenance    = [ordered]@{
            source                = $SourceTool
            version               = if ([string]::IsNullOrWhiteSpace($GraphApiVersion)) { $Script:ModuleVersion } else { $GraphApiVersion }
            timestamp             = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
            content_hash          = $contentHash
            actor                 = "UIAOIdentityAssessment/$Script:ModuleVersion"
            tenant_id             = if ([string]::IsNullOrWhiteSpace($TenantId)) { 'unknown' } else { $TenantId }
            graph_api_version     = if ([string]::IsNullOrWhiteSpace($GraphApiVersion)) { $null } else { $GraphApiVersion }
            graph_endpoint        = $GraphEndpoint
            source_ref            = $SourceRef
            import_module         = 'UIAOIdentityAssessment'
            import_module_version = $Script:ModuleVersion
        }
        data          = $data
    }
}

function Write-UIAOEnvelopeOutput {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)] $Envelope,
        [Parameter(Mandatory = $false)][string]$OutputPath
    )
    if (-not [string]::IsNullOrWhiteSpace($OutputPath)) {
        $json = $Envelope | ConvertTo-Json -Depth 40
        $dir = Split-Path -Parent $OutputPath
        if ($dir -and -not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
        [System.IO.File]::WriteAllText($OutputPath, $json, [System.Text.UTF8Encoding]::new($false))
    }
    return $Envelope
}

function Get-UIAOGraphRows {
    <#
    .SYNOPSIS
        Internal: resolve exporter input rows from -SnapshotPath (offline) or a
        live Graph command (guarded). Returns @{ Rows; SourceRef }.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $false)][string]$SnapshotPath,
        [Parameter(Mandatory = $false)][string]$TenantId,
        [Parameter(Mandatory = $true)] [string]$LiveCommand,
        [Parameter(Mandatory = $false)][scriptblock]$LiveReader,
        [Parameter(Mandatory = $false)][string[]]$PreferredArrayKeys = @('value'),
        [Parameter(Mandatory = $true)] [string]$LiveRefSuffix
    )
    if (-not [string]::IsNullOrWhiteSpace($SnapshotPath)) {
        $full = Assert-UIAOInputPath -Path $SnapshotPath
        $loaded = Read-UIAOSourceData -Path $full
        return @{ Rows = (Get-UIAORows -Data $loaded -PreferredArrayKeys $PreferredArrayKeys); SourceRef = (Split-Path -Leaf $full) }
    }
    if ([string]::IsNullOrWhiteSpace($TenantId)) {
        throw "Provide -SnapshotPath for offline normalization, or -TenantId for a live Graph read."
    }
    if (-not (Get-Command $LiveCommand -ErrorAction SilentlyContinue)) {
        throw "Microsoft.Graph PowerShell SDK ($LiveCommand) not available. Install Microsoft.Graph, or pass -SnapshotPath for offline use."
    }
    $rows = & $LiveReader
    return @{ Rows = @($rows); SourceRef = "graph:$TenantId/$LiveRefSuffix" }
}


# ---------------------------------------------------------------------------
# Public functions — Entra exporters (UIAO_181 §Function roster)
# ---------------------------------------------------------------------------

function Export-UIAOEntraUsers {
    <#
    .SYNOPSIS
        Inventory Entra ID users into a sealed UIAO EntraUserInventory envelope.
    .DESCRIPTION
        With -SnapshotPath, normalizes a pre-captured Graph response offline.
        With -TenantId, performs a live read via Get-MgUser (requires the
        Microsoft.Graph SDK and an established Graph session).
    .PARAMETER TenantId
        Target tenant id (recorded in provenance; required for a live read).
    .PARAMETER OutputPath
        Optional output path for the normalized envelope JSON.
    .PARAMETER SnapshotPath
        Path to a pre-captured Graph user response (.json/.csv) for offline use.
    .PARAMETER Cloud
        Sovereign cloud for endpoint resolution ('commercial' (default, serves
        GCC-Moderate), 'gcc-high', 'dod'). Unknown clouds fail closed.
    .PARAMETER GraphApiVersion
        Graph API version segment (default 'v1.0'), recorded in provenance.
    .PARAMETER GraphEndpoint
        Explicit Graph base URL override (skips cloud lookup).
    .EXAMPLE
        Export-UIAOEntraUsers -TenantId $tid -OutputPath users.json
    .EXAMPLE
        Export-UIAOEntraUsers -SnapshotPath graph-users.json -OutputPath users.json
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $false)][string]$TenantId,
        [Parameter(Mandatory = $false)][string]$OutputPath,
        [Parameter(Mandatory = $false)][string]$SnapshotPath,
        [Parameter(Mandatory = $false)][string]$Cloud = $Script:DefaultCloud,
        [Parameter(Mandatory = $false)][string]$GraphApiVersion = $Script:DefaultGraphApiVersion,
        [Parameter(Mandatory = $false)][string]$GraphEndpoint
    )
    $endpoint = Resolve-UIAOGraphBase -Cloud $Cloud -GraphApiVersion $GraphApiVersion -Explicit $GraphEndpoint
    $src = Get-UIAOGraphRows -SnapshotPath $SnapshotPath -TenantId $TenantId -LiveCommand 'Get-MgUser' -LiveRefSuffix 'users' `
        -LiveReader { Get-MgUser -All -Property 'id,userPrincipalName,displayName,accountEnabled,mail,userType,onPremisesSyncEnabled,onPremisesSamAccountName' }
    $records = foreach ($row in $src.Rows) {
        [ordered]@{
            id                       = Get-UIAOFieldValue $row @('id', 'Id', 'objectId')
            user_principal_name      = Get-UIAOFieldValue $row @('userPrincipalName', 'UserPrincipalName', 'upn')
            display_name             = Get-UIAOFieldValue $row @('displayName', 'DisplayName')
            enabled                  = Get-UIAOFieldValue $row @('accountEnabled', 'AccountEnabled', 'enabled')
            mail                     = Get-UIAOFieldValue $row @('mail', 'Mail')
            user_type                = Get-UIAOFieldValue $row @('userType', 'UserType')
            on_prem_sync_enabled     = Get-UIAOFieldValue $row @('onPremisesSyncEnabled', 'OnPremisesSyncEnabled')
            on_prem_sam_account_name = Get-UIAOFieldValue $row @('onPremisesSamAccountName', 'OnPremisesSamAccountName', 'samAccountName')
            source_fields            = ConvertTo-UIAOSourceFields $row
        }
    }
    $envelope = New-UIAOIdentityEnvelope -SourceTool 'EntraID' -TargetSchema 'EntraUserInventory' -TenantId $TenantId `
        -GraphApiVersion $GraphApiVersion -GraphEndpoint $endpoint -SourceRef $src.SourceRef -Records @($records)
    return (Write-UIAOEnvelopeOutput -Envelope $envelope -OutputPath $OutputPath)
}

function Export-UIAOEntraGroups {
    <#
    .SYNOPSIS
        Inventory Entra ID groups and memberships into a sealed envelope.
    .PARAMETER IncludeDynamic
        Include the membership rule for dynamic groups (and flag them). Without
        it, dynamic groups are still listed but the rule is omitted.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $false)][string]$TenantId,
        [Parameter(Mandatory = $false)][string]$OutputPath,
        [Parameter(Mandatory = $false)][string]$SnapshotPath,
        [Parameter(Mandatory = $false)][switch]$IncludeDynamic,
        [Parameter(Mandatory = $false)][string]$Cloud = $Script:DefaultCloud,
        [Parameter(Mandatory = $false)][string]$GraphApiVersion = $Script:DefaultGraphApiVersion,
        [Parameter(Mandatory = $false)][string]$GraphEndpoint
    )
    $endpoint = Resolve-UIAOGraphBase -Cloud $Cloud -GraphApiVersion $GraphApiVersion -Explicit $GraphEndpoint
    $src = Get-UIAOGraphRows -SnapshotPath $SnapshotPath -TenantId $TenantId -LiveCommand 'Get-MgGroup' -LiveRefSuffix 'groups' `
        -LiveReader { Get-MgGroup -All -Property 'id,displayName,groupTypes,membershipRule,securityEnabled,mailEnabled' }
    $records = foreach ($row in $src.Rows) {
        $groupTypes = Get-UIAOFieldValue $row @('groupTypes', 'GroupTypes')
        $isDynamic = ($groupTypes -and ($groupTypes -match 'DynamicMembership'))
        $rule = Get-UIAOFieldValue $row @('membershipRule', 'MembershipRule')
        [ordered]@{
            id              = Get-UIAOFieldValue $row @('id', 'Id', 'objectId')
            display_name    = Get-UIAOFieldValue $row @('displayName', 'DisplayName')
            is_dynamic      = [string]$isDynamic
            security_enabled = Get-UIAOFieldValue $row @('securityEnabled', 'SecurityEnabled')
            mail_enabled    = Get-UIAOFieldValue $row @('mailEnabled', 'MailEnabled')
            membership_rule = if ($IncludeDynamic -and $isDynamic) { $rule } else { $null }
            member_count    = Get-UIAOFieldValue $row @('memberCount', 'MemberCount')
            source_fields   = ConvertTo-UIAOSourceFields $row
        }
    }
    $envelope = New-UIAOIdentityEnvelope -SourceTool 'EntraID' -TargetSchema 'EntraGroupInventory' -TenantId $TenantId `
        -GraphApiVersion $GraphApiVersion -GraphEndpoint $endpoint -SourceRef $src.SourceRef -Records @($records)
    return (Write-UIAOEnvelopeOutput -Envelope $envelope -OutputPath $OutputPath)
}

function Export-UIAOEntraApps {
    <#
    .SYNOPSIS
        Inventory Entra app registrations and service principals into a sealed
        envelope.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $false)][string]$TenantId,
        [Parameter(Mandatory = $false)][string]$OutputPath,
        [Parameter(Mandatory = $false)][string]$SnapshotPath,
        [Parameter(Mandatory = $false)][string]$Cloud = $Script:DefaultCloud,
        [Parameter(Mandatory = $false)][string]$GraphApiVersion = $Script:DefaultGraphApiVersion,
        [Parameter(Mandatory = $false)][string]$GraphEndpoint
    )
    $endpoint = Resolve-UIAOGraphBase -Cloud $Cloud -GraphApiVersion $GraphApiVersion -Explicit $GraphEndpoint
    $src = Get-UIAOGraphRows -SnapshotPath $SnapshotPath -TenantId $TenantId -LiveCommand 'Get-MgServicePrincipal' -LiveRefSuffix 'apps' `
        -LiveReader { Get-MgServicePrincipal -All -Property 'id,appId,displayName,servicePrincipalType,accountEnabled' }
    $records = foreach ($row in $src.Rows) {
        [ordered]@{
            id               = Get-UIAOFieldValue $row @('id', 'Id', 'objectId')
            app_id           = Get-UIAOFieldValue $row @('appId', 'AppId')
            display_name     = Get-UIAOFieldValue $row @('displayName', 'DisplayName')
            object_type      = Get-UIAOFieldValue $row @('servicePrincipalType', 'ServicePrincipalType', 'objectType', 'odata.type')
            sign_in_audience = Get-UIAOFieldValue $row @('signInAudience', 'SignInAudience')
            enabled          = Get-UIAOFieldValue $row @('accountEnabled', 'AccountEnabled')
            source_fields    = ConvertTo-UIAOSourceFields $row
        }
    }
    $envelope = New-UIAOIdentityEnvelope -SourceTool 'EntraID' -TargetSchema 'EntraAppInventory' -TenantId $TenantId `
        -GraphApiVersion $GraphApiVersion -GraphEndpoint $endpoint -SourceRef $src.SourceRef -Records @($records)
    return (Write-UIAOEnvelopeOutput -Envelope $envelope -OutputPath $OutputPath)
}

function Export-UIAOConditionalAccess {
    <#
    .SYNOPSIS
        Inventory Conditional Access policies into a sealed envelope.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $false)][string]$TenantId,
        [Parameter(Mandatory = $false)][string]$OutputPath,
        [Parameter(Mandatory = $false)][string]$SnapshotPath,
        [Parameter(Mandatory = $false)][string]$Cloud = $Script:DefaultCloud,
        [Parameter(Mandatory = $false)][string]$GraphApiVersion = $Script:DefaultGraphApiVersion,
        [Parameter(Mandatory = $false)][string]$GraphEndpoint
    )
    $endpoint = Resolve-UIAOGraphBase -Cloud $Cloud -GraphApiVersion $GraphApiVersion -Explicit $GraphEndpoint
    $src = Get-UIAOGraphRows -SnapshotPath $SnapshotPath -TenantId $TenantId -LiveCommand 'Get-MgIdentityConditionalAccessPolicy' -LiveRefSuffix 'conditionalAccess' `
        -LiveReader { Get-MgIdentityConditionalAccessPolicy -All }
    $records = foreach ($row in $src.Rows) {
        [ordered]@{
            id            = Get-UIAOFieldValue $row @('id', 'Id')
            display_name  = Get-UIAOFieldValue $row @('displayName', 'DisplayName')
            state         = Get-UIAOFieldValue $row @('state', 'State')
            source_fields = ConvertTo-UIAOSourceFields $row
        }
    }
    $envelope = New-UIAOIdentityEnvelope -SourceTool 'EntraID' -TargetSchema 'ConditionalAccessInventory' -TenantId $TenantId `
        -GraphApiVersion $GraphApiVersion -GraphEndpoint $endpoint -SourceRef $src.SourceRef -Records @($records)
    return (Write-UIAOEnvelopeOutput -Envelope $envelope -OutputPath $OutputPath)
}


# ---------------------------------------------------------------------------
# Reconciliation + orchestrator
# ---------------------------------------------------------------------------

function Get-UIAOMatchKey {
    [CmdletBinding()]
    param([Parameter(Mandatory = $true)]$Record)
    $upn = Get-UIAOFieldValue $Record @('user_principal_name', 'userPrincipalName', 'UserPrincipalName', 'upn', 'mail', 'Mail')
    if ($upn) { return $upn.ToLowerInvariant() }
    $sam = Get-UIAOFieldValue $Record @('on_prem_sam_account_name', 'samAccountName', 'SamAccountName', 'name', 'Name')
    if ($sam) { return $sam.ToLowerInvariant() }
    return $null
}

function Get-UIAOEnabledState {
    [CmdletBinding()]
    param([Parameter(Mandatory = $true)]$Record)
    $v = Get-UIAOFieldValue $Record @('enabled', 'accountEnabled', 'AccountEnabled', 'Enabled')
    if ($null -eq $v) { return $null }
    return ("$v".Trim().ToLowerInvariant() -in @('true', '1', 'yes', 'enabled'))
}

function Compare-UIAOIdentitySources {
    <#
    .SYNOPSIS
        Reconcile an on-prem AD identity assessment against an Entra inventory,
        classifying inconsistencies as DRIFT-IDENTITY.
    .DESCRIPTION
        Both inputs are sealed assessment envelopes (e.g. an ADRecon import from
        UIAOImportAdapters and an Export-UIAOEntraUsers inventory). Principals are
        joined on a match key (UPN, else SAM account name). Each principal is
        classified: matched / orphaned_in_ad (AD only) / missing_in_ad (Entra
        only) / lifecycle_inconsistent (both, enabled-state mismatch). Every
        non-matched class is a DRIFT-IDENTITY finding (UIAO_181 §Drift and
        provenance anchoring).
    .PARAMETER ADAssessmentPath
        Path to the on-prem AD identity assessment envelope.
    .PARAMETER EntraAssessmentPath
        Path to the Entra identity inventory envelope.
    .PARAMETER OutputPath
        Optional output path for the reconciliation envelope JSON.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string]$ADAssessmentPath,
        [Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string]$EntraAssessmentPath,
        [Parameter(Mandatory = $false)][string]$OutputPath
    )
    $adFull = Assert-UIAOInputPath -Path $ADAssessmentPath
    $entraFull = Assert-UIAOInputPath -Path $EntraAssessmentPath
    $adEnv = Get-Content -LiteralPath $adFull -Raw -Encoding UTF8 | ConvertFrom-Json
    $entraEnv = Get-Content -LiteralPath $entraFull -Raw -Encoding UTF8 | ConvertFrom-Json

    $adByKey = [ordered]@{}
    foreach ($r in @($adEnv.data.records)) {
        $k = Get-UIAOMatchKey -Record $r
        if ($k -and -not $adByKey.Contains($k)) { $adByKey[$k] = $r }
    }
    $entraByKey = [ordered]@{}
    foreach ($r in @($entraEnv.data.records)) {
        $k = Get-UIAOMatchKey -Record $r
        if ($k -and -not $entraByKey.Contains($k)) { $entraByKey[$k] = $r }
    }

    $reconRecords = @()
    $counts = [ordered]@{ matched = 0; orphaned_in_ad = 0; missing_in_ad = 0; lifecycle_inconsistent = 0 }

    foreach ($key in $adByKey.Keys) {
        $adEnabled = Get-UIAOEnabledState -Record $adByKey[$key]
        if ($entraByKey.Contains($key)) {
            $entraEnabled = Get-UIAOEnabledState -Record $entraByKey[$key]
            $inconsistent = ($null -ne $adEnabled) -and ($null -ne $entraEnabled) -and ($adEnabled -ne $entraEnabled)
            $class = if ($inconsistent) { 'lifecycle_inconsistent' } else { 'matched' }
            $counts[$class] = $counts[$class] + 1
            $reconRecords += [ordered]@{
                match_key      = $key
                classification = $class
                ad_enabled     = $adEnabled
                entra_enabled  = $entraEnabled
                drift_class    = if ($inconsistent) { 'DRIFT-IDENTITY' } else { $null }
            }
        }
        else {
            $counts['orphaned_in_ad'] = $counts['orphaned_in_ad'] + 1
            $reconRecords += [ordered]@{
                match_key      = $key
                classification = 'orphaned_in_ad'
                ad_enabled     = $adEnabled
                entra_enabled  = $null
                drift_class    = 'DRIFT-IDENTITY'
            }
        }
    }
    foreach ($key in $entraByKey.Keys) {
        if (-not $adByKey.Contains($key)) {
            $counts['missing_in_ad'] = $counts['missing_in_ad'] + 1
            $reconRecords += [ordered]@{
                match_key      = $key
                classification = 'missing_in_ad'
                ad_enabled     = $null
                entra_enabled  = Get-UIAOEnabledState -Record $entraByKey[$key]
                drift_class    = 'DRIFT-IDENTITY'
            }
        }
    }

    $data = [ordered]@{
        target_schema = 'IdentityReconciliation'
        counts        = $counts
        drift_count   = ($counts['orphaned_in_ad'] + $counts['missing_in_ad'] + $counts['lifecycle_inconsistent'])
        record_count  = @($reconRecords).Count
        records       = @($reconRecords)
    }
    $contentHash = Get-UIAOCanonicalHash -Json ($data | ConvertTo-Json -Depth 30)
    $envelope = [ordered]@{
        schema        = 'uiao.identity.reconciliation.v1'
        target_schema = 'IdentityReconciliation'
        provenance    = [ordered]@{
            source                = 'UIAOIdentityAssessment.Reconcile'
            version               = $Script:ModuleVersion
            timestamp             = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
            content_hash          = $contentHash
            actor                 = "UIAOIdentityAssessment/$Script:ModuleVersion"
            ad_source             = (Split-Path -Leaf $adFull)
            entra_source          = (Split-Path -Leaf $entraFull)
            import_module         = 'UIAOIdentityAssessment'
            import_module_version = $Script:ModuleVersion
        }
        data          = $data
    }
    return (Write-UIAOEnvelopeOutput -Envelope $envelope -OutputPath $OutputPath)
}

function Invoke-UIAOIdentityAssessment {
    <#
    .SYNOPSIS
        Orchestrate a hybrid identity assessment: Entra user inventory plus
        optional AD-vs-Entra reconciliation.
    .DESCRIPTION
        Exports the Entra user inventory (live via -TenantId, or offline via
        -EntraUsersSnapshotPath) and, when -ADAssessmentPath is supplied,
        reconciles it. Returns a sealed assessment bundle summarizing the
        produced artifacts.
    .PARAMETER TenantId
        Target tenant id (live read).
    .PARAMETER Domain
        On-prem AD domain (recorded in provenance).
    .PARAMETER OutputPath
        Optional output path for the assessment bundle JSON.
    .PARAMETER EntraUsersSnapshotPath
        Offline Entra users snapshot (skips the live Graph read).
    .PARAMETER ADAssessmentPath
        Optional on-prem AD assessment envelope to reconcile against.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $false)][string]$TenantId,
        [Parameter(Mandatory = $false)][string]$Domain,
        [Parameter(Mandatory = $false)][string]$OutputPath,
        [Parameter(Mandatory = $false)][string]$EntraUsersSnapshotPath,
        [Parameter(Mandatory = $false)][string]$ADAssessmentPath,
        [Parameter(Mandatory = $false)][string]$Cloud = $Script:DefaultCloud,
        [Parameter(Mandatory = $false)][string]$GraphApiVersion = $Script:DefaultGraphApiVersion,
        [Parameter(Mandatory = $false)][string]$GraphEndpoint
    )
    $artifacts = @()

    $entraUsers = Export-UIAOEntraUsers -TenantId $TenantId -SnapshotPath $EntraUsersSnapshotPath `
        -Cloud $Cloud -GraphApiVersion $GraphApiVersion -GraphEndpoint $GraphEndpoint
    $artifacts += [ordered]@{
        target_schema = 'EntraUserInventory'
        record_count  = $entraUsers.data.record_count
        content_hash  = $entraUsers.provenance.content_hash
    }

    $reconciliation = $null
    if (-not [string]::IsNullOrWhiteSpace($ADAssessmentPath)) {
        # Persist the Entra inventory so reconciliation reads a sealed file.
        $entraTmp = [System.IO.Path]::Combine([System.IO.Path]::GetTempPath(), "uiao-entra-users-$([guid]::NewGuid().ToString('N')).json")
        $null = Write-UIAOEnvelopeOutput -Envelope $entraUsers -OutputPath $entraTmp
        try {
            $reconciliation = Compare-UIAOIdentitySources -ADAssessmentPath $ADAssessmentPath -EntraAssessmentPath $entraTmp
        }
        finally {
            if (Test-Path -LiteralPath $entraTmp) { Remove-Item -LiteralPath $entraTmp -Force -ErrorAction SilentlyContinue }
        }
        $artifacts += [ordered]@{
            target_schema = 'IdentityReconciliation'
            record_count  = $reconciliation.data.record_count
            drift_count   = $reconciliation.data.drift_count
            content_hash  = $reconciliation.provenance.content_hash
        }
    }

    $data = [ordered]@{
        target_schema = 'IdentityAssessmentBundle'
        domain        = if ([string]::IsNullOrWhiteSpace($Domain)) { $null } else { $Domain }
        artifacts     = @($artifacts)
        artifact_count = @($artifacts).Count
    }
    $contentHash = Get-UIAOCanonicalHash -Json ($data | ConvertTo-Json -Depth 30)
    $bundle = [ordered]@{
        schema        = 'uiao.identity.assessment.v1'
        target_schema = 'IdentityAssessmentBundle'
        provenance    = [ordered]@{
            source                = 'UIAOIdentityAssessment'
            version               = $Script:ModuleVersion
            timestamp             = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
            content_hash          = $contentHash
            actor                 = "UIAOIdentityAssessment/$Script:ModuleVersion"
            tenant_id             = if ([string]::IsNullOrWhiteSpace($TenantId)) { 'unknown' } else { $TenantId }
            domain                = $Domain
            import_module         = 'UIAOIdentityAssessment'
            import_module_version = $Script:ModuleVersion
        }
        entra_users   = $entraUsers
        reconciliation = $reconciliation
        data          = $data
    }
    return (Write-UIAOEnvelopeOutput -Envelope $bundle -OutputPath $OutputPath)
}


Export-ModuleMember -Function `
    'Export-UIAOEntraUsers', `
    'Export-UIAOEntraGroups', `
    'Export-UIAOEntraApps', `
    'Export-UIAOConditionalAccess', `
    'Compare-UIAOIdentitySources', `
    'Invoke-UIAOIdentityAssessment'
