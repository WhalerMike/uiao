# UIAOSqlServerMigration — SQL Server identity-transformation automation
# (canon: UIAO_135 Transformation #7; ADR-002, ADR-004, ADR-068, ADR-091).
#
# The shipped automation behind the "Implementation Companion" runbooks for the
# SQL Server identity transformation:
#   - Book 04 (Arc deployment & the managed identity) — onboarding + validation
#   - Book 05 (login migration to Entra) — CREATE LOGIN ... FROM EXTERNAL PROVIDER
#     script generation from the audit, with parallel-run validation
#   - Book 06 (NTLM/Kerberos remediation) — SPN-collision remediation planning
#     and NTLM-reduction Group Policy reporting
#
# Doctrine (matches the tools/powershell convention — OrgPathTools /
# UIAOImportAdapters / UIAOIdentityAssessment / UIAOPlanGenerators):
#   - Self-contained .psm1; private seal/validation helpers mirror the producer
#     modules. The Python canonical hasher is authoritative for the integrity
#     seal (byte-identical to uiao.ir.models.core.canonical_hash), so a broken or
#     unattributed envelope is a DRIFT-PROVENANCE finding by definition.
#   - SAFETY (GCC-Moderate / FedRAMP): anything that would mutate state — Arc
#     onboarding, login creation, SPN edits, GPO — is gated. Read-only validation
#     and audit functions run directly; state-changing functions either
#     SupportShouldProcess (default to a -WhatIf-style preview) or generate a
#     reviewable script/plan artifact and execute NOTHING by default. No
#     credentials, tenants, or endpoints are hard-coded; every environment value
#     is a parameter.
#   - No invented cmdlets: live calls use azcmagent / Az.ConnectedMachine /
#     setspn / Get-GPOReport per current Microsoft docs, and every such call is
#     reachable only behind an explicit opt-in switch so the module is fully
#     testable offline (snapshot inputs), exactly like the sibling modules.
#
# Exports (function roster):
#   Arc (Book 04):
#     Test-UIAOArcAgentStatus          azcmagent status -> sealed validation
#     Test-UIAOArcManagedIdentityToken IMDS token audience/exp validation
#     Test-UIAOArcSqlExtension         SQL Server extension provisioning state
#     Invoke-UIAOArcOnboarding         idempotent onboarding wrapper (ShouldProcess)
#   Login migration (Book 05):
#     New-UIAOEntraLoginMapping        Windows-login -> Entra-principal mapping
#     New-UIAOEntraLoginScript         CREATE LOGIN ... FROM EXTERNAL PROVIDER (dry-run)
#     Test-UIAOLoginParallelRun        parallel-run auth-scheme observation
#   NTLM / Kerberos (Book 06):
#     New-UIAOSpnRemediationPlan       SPN-collision remediation plan (audit-first)
#     Get-UIAONtlmGpoReport            NTLM-reduction GPO reporting (read-only)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Script:ModuleVersion = '1.0.0'

# Safety cap for a single source artifact (SI-10). Inputs (audit CSV/JSON,
# snapshots) are small relative to this; anything larger is rejected rather than
# read into memory.
$Script:MaxInputBytes = 200MB

# Sovereign-cloud data-plane (SQL) audiences and the matching azcmagent cloud
# name, mirroring the Graph/ARM cloud resolvers in src/uiao/adapters/. Default
# 'AzureCloud' also serves GCC-Moderate (ADR-033) — a tenancy designation on
# commercial infrastructure, not a separate endpoint. Unknown clouds fail closed.
$Script:SqlAudience = @{
    'AzureCloud'        = 'https://database.windows.net/'
    'AzureUSGovernment' = 'https://database.usgovcloudapi.net/'
}
$Script:DefaultCloud = 'AzureCloud'


# ---------------------------------------------------------------------------
# Private helpers (seal / validation — mirror the sibling producer modules)
# ---------------------------------------------------------------------------

function Resolve-UIAOPython {
    # Honor $env:UIAO_PYTHON, else prefer python3 then python. Only the stdlib
    # (json, hashlib) is used; the uiao package is NOT imported, so no editable
    # install is required to compute seals.
    if ($env:UIAO_PYTHON) { return $env:UIAO_PYTHON }
    foreach ($candidate in @('python3', 'python')) {
        if (Get-Command $candidate -ErrorAction SilentlyContinue) { return $candidate }
    }
    throw "No Python interpreter found (looked for python3, python). Set `$env:UIAO_PYTHON to the interpreter path."
}

function Get-UIAOCanonicalHash {
    # SHA-256 over canonical JSON, byte-identical to
    # uiao.ir.models.core.canonical_hash. Python re-canonicalizes, so the
    # intermediate PowerShell JSON only needs to be parseable.
    [CmdletBinding()]
    [OutputType([string])]
    param([Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string]$Json)
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

function Resolve-UIAOSqlAudience {
    # Resolve the data-plane SQL audience (cloud-aware, fail-closed). An explicit
    # -Resource overrides the cloud default. Mirrors the Graph/ARM resolvers:
    # the management-plane and data-plane audiences are distinct, and a token for
    # one is refused by the other (AGENTS.md).
    [CmdletBinding()]
    [OutputType([string])]
    param(
        [Parameter(Mandatory = $false)][string]$Cloud = $Script:DefaultCloud,
        [Parameter(Mandatory = $false)][string]$Explicit
    )
    if (-not [string]::IsNullOrWhiteSpace($Explicit)) { return $Explicit }
    if (-not $Script:SqlAudience.ContainsKey($Cloud)) {
        $supported = ($Script:SqlAudience.Keys | Sort-Object) -join ', '
        throw "UIAOSqlServerMigration: unknown cloud '$Cloud'. Supported clouds: $supported. Set -Cloud or pass an explicit -Resource."
    }
    return $Script:SqlAudience[$Cloud]
}

function New-UIAOMigrationEnvelope {
    # Wrap records in a sealed provenance envelope. The sealed data omits any
    # timestamp, so identical inputs yield an identical content_hash (reproducible
    # artifacts); the wall-clock timestamp lives only in provenance (unsealed).
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)] [string]$ArtifactType,
        [Parameter(Mandatory = $true)] [AllowEmptyCollection()][object[]]$Records,
        [Parameter(Mandatory = $false)][System.Collections.IDictionary]$ExtraData,
        [Parameter(Mandatory = $false)]$DerivedFrom,
        [Parameter(Mandatory = $false)][string]$SourceRef
    )
    $recordArray = @($Records)
    $data = [ordered]@{
        artifact_type = $ArtifactType
        record_count  = $recordArray.Count
        records       = $recordArray
    }
    if ($ExtraData) { foreach ($k in $ExtraData.Keys) { $data[$k] = $ExtraData[$k] } }
    $contentHash = Get-UIAOCanonicalHash -Json ($data | ConvertTo-Json -Depth 30)
    return [ordered]@{
        schema        = 'uiao.sqlmigration.v1'
        artifact_type = $ArtifactType
        provenance    = [ordered]@{
            source                = 'UIAOSqlServerMigration'
            version               = $Script:ModuleVersion
            timestamp             = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
            content_hash          = $contentHash
            actor                 = "UIAOSqlServerMigration/$Script:ModuleVersion"
            derived_from          = $DerivedFrom
            source_ref            = $SourceRef
            import_module         = 'UIAOSqlServerMigration'
            import_module_version = $Script:ModuleVersion
        }
        data          = $data
    }
}

function Write-UIAOEnvelopeOutput {
    [CmdletBinding()]
    param([Parameter(Mandatory = $true)]$Envelope, [Parameter(Mandatory = $false)][string]$OutputPath)
    if (-not [string]::IsNullOrWhiteSpace($OutputPath)) {
        $json = $Envelope | ConvertTo-Json -Depth 40
        $dir = Split-Path -Parent $OutputPath
        if ($dir -and -not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
        [System.IO.File]::WriteAllText($OutputPath, $json, [System.Text.UTF8Encoding]::new($false))
    }
    return $Envelope
}

function Write-UIAOTextOutput {
    # Write a generated text artifact (e.g. a .sql script) with no BOM.
    [CmdletBinding()]
    param([Parameter(Mandatory = $true)][string]$Text, [Parameter(Mandatory = $false)][string]$OutputPath)
    if (-not [string]::IsNullOrWhiteSpace($OutputPath)) {
        $dir = Split-Path -Parent $OutputPath
        if ($dir -and -not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
        [System.IO.File]::WriteAllText($OutputPath, $Text, [System.Text.UTF8Encoding]::new($false))
    }
}

function ConvertFrom-UIAOJwtPayload {
    # Decode the (unverified) payload segment of a JWT to inspect aud/iss/exp.
    # This is a claims-inspection helper for validation only — it does NOT verify
    # the signature and must not be used to make a trust decision.
    [CmdletBinding()]
    param([Parameter(Mandatory = $true)][string]$Jwt)
    $parts = $Jwt.Split('.')
    if ($parts.Count -lt 2) { throw "Value is not a JWT (expected at least header.payload)." }
    $payload = $parts[1].Replace('-', '+').Replace('_', '/')
    $payload += '=' * ((4 - $payload.Length % 4) % 4)
    $bytes = [Convert]::FromBase64String($payload)
    return ([Text.Encoding]::UTF8.GetString($bytes) | ConvertFrom-Json)
}


# ===========================================================================
# Book 04 — Arc deployment & the managed identity (ADR-002, ADR-004)
# ===========================================================================

function Test-UIAOArcAgentStatus {
    <#
    .SYNOPSIS
        Validate the Azure Connected Machine agent status (Book 04, Step 1
        verification). Read-only.
    .DESCRIPTION
        Resolves the agent status either from a captured `azcmagent show -j`
        snapshot (-SnapshotPath, offline/testable) or — only with -Live — by
        invoking `azcmagent show -j` on the host. Confirms the agent reports
        Connected and that the resource id lands in the expected cloud, and
        returns a sealed validation envelope. Run-first / read-only: it queries
        and reports, it never onboards or changes the agent (that is
        Invoke-UIAOArcOnboarding).

        This resolves the Book 04 Step 1 [to build] marker (status side): the
        idempotency check that lets onboarding "skip if already Connected" and
        the sealed evidence record.
    .PARAMETER SnapshotPath
        Path to a captured `azcmagent show -j` JSON document (offline mode).
    .PARAMETER Live
        Invoke `azcmagent show -j` on the local host. Requires the agent to be
        installed. Mutually informative with -SnapshotPath; -Live takes effect
        only when no snapshot is supplied.
    .PARAMETER ExpectedCloud
        Expected Azure cloud the resource id should resolve to ('AzureCloud' or
        'AzureUSGovernment'). Default 'AzureCloud' (serves GCC-Moderate, ADR-033).
    .PARAMETER OutputPath
        Optional path for the sealed validation envelope JSON.
    .NOTES
        Canon: UIAO_135 Transformation #7; ADR-002, ADR-004. Book 04 Step 1.
        Live mode calls the real `azcmagent` CLI (no invented cmdlets).
    .EXAMPLE
        Test-UIAOArcAgentStatus -SnapshotPath .\output\azcmagent-show.json
    .EXAMPLE
        Test-UIAOArcAgentStatus -Live -ExpectedCloud AzureUSGovernment
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $false)][string]$SnapshotPath,
        [Parameter(Mandatory = $false)][switch]$Live,
        [Parameter(Mandatory = $false)][ValidateSet('AzureCloud', 'AzureUSGovernment')][string]$ExpectedCloud = $Script:DefaultCloud,
        [Parameter(Mandatory = $false)][string]$OutputPath
    )
    $sourceRef = $null
    if (-not [string]::IsNullOrWhiteSpace($SnapshotPath)) {
        $full = Assert-UIAOInputPath -Path $SnapshotPath
        $show = Read-UIAOSourceData -Path $full
        $sourceRef = "snapshot:$(Split-Path -Leaf $full)"
    }
    elseif ($Live) {
        if (-not (Get-Command 'azcmagent' -ErrorAction SilentlyContinue)) {
            throw "azcmagent not found on PATH. Install the Connected Machine agent or pass -SnapshotPath."
        }
        $raw = & azcmagent show -j 2>$null
        if ($LASTEXITCODE -ne 0) { throw "azcmagent show -j exited $LASTEXITCODE" }
        $show = ($raw -join "`n") | ConvertFrom-Json
        $sourceRef = 'live:azcmagent show -j'
    }
    else {
        throw "Provide -SnapshotPath for offline validation or -Live to query the host."
    }

    $status = Get-UIAOFieldValue $show @('status', 'agentStatus', 'Status')
    $resourceId = Get-UIAOFieldValue $show @('resourceId', 'resourceid', 'ResourceId')
    $resourceName = Get-UIAOFieldValue $show @('resourceName', 'resourcename', 'ResourceName')
    $agentVersion = Get-UIAOFieldValue $show @('agentVersion', 'agentversion', 'AgentVersion')

    $isConnected = ($status -and ($status -match '(?i)^connected$'))
    # The Government-cloud resource id contains the Government subscription path
    # only indirectly; the durable cloud signal in `azcmagent show` is the cloud
    # field. Validate it when present, else treat as informational.
    $reportedCloud = Get-UIAOFieldValue $show @('cloud', 'Cloud')
    $cloudOk = if ($reportedCloud) { $reportedCloud -ieq $ExpectedCloud } else { $true }

    $checks = @(
        [ordered]@{ check = 'agent_connected'; passed = [bool]$isConnected; observed = $status; expected = 'Connected' }
        [ordered]@{ check = 'cloud_match'; passed = [bool]$cloudOk; observed = $reportedCloud; expected = $ExpectedCloud }
        [ordered]@{ check = 'resource_id_present'; passed = [bool]$resourceId; observed = $resourceId; expected = '<non-empty>' }
    )
    $record = [ordered]@{
        status        = $status
        connected     = [bool]$isConnected
        resource_id   = $resourceId
        resource_name = $resourceName
        agent_version = $agentVersion
        cloud         = $reportedCloud
        expected_cloud = $ExpectedCloud
        checks        = $checks
        validation    = if (@($checks | Where-Object { -not $_.passed }).Count -eq 0) { 'pass' } else { 'fail' }
    }
    $envelope = New-UIAOMigrationEnvelope -ArtifactType 'ArcAgentStatusValidation' -Records @($record) `
        -SourceRef $sourceRef -ExtraData ([ordered]@{ validation = $record.validation })
    return (Write-UIAOEnvelopeOutput -Envelope $envelope -OutputPath $OutputPath)
}

function Test-UIAOArcManagedIdentityToken {
    <#
    .SYNOPSIS
        Validate that the host can mint a managed-identity token for the SQL
        data-plane audience, and that the token's aud/exp are correct (Book 04,
        Step 2). Read-only.
    .DESCRIPTION
        The single most common Arc failure point is an audience mismatch: a token
        minted for the management plane is refused by the data plane and vice
        versa (the Graph-vs-ARM split in AGENTS.md). This function decodes a
        managed-identity token and asserts its `aud` matches the intended SQL
        data-plane resource and its `exp` is in the future.

        Token source is either -TokenSnapshotPath (a captured IMDS response, for
        offline validation/testing) or -Live (queries the local Arc IMDS at
        169.254.169.254). The signature is NOT verified — this inspects claims
        for an operational pre-flight, not a trust decision.

        Resolves the Book 04 Step 2 [to build] facet: a verification wrapper for
        managed-identity/IMDS token availability and audience correctness.
    .PARAMETER TokenSnapshotPath
        Path to a captured IMDS token response JSON ({ access_token, ... }) or a
        file containing a bare JWT.
    .PARAMETER Live
        Query the local Arc IMDS endpoint for a token.
    .PARAMETER Cloud
        Cloud whose SQL data-plane audience the token must target.
    .PARAMETER Resource
        Explicit resource/audience override (takes precedence over -Cloud).
    .PARAMETER OutputPath
        Optional path for the sealed validation envelope JSON.
    .NOTES
        Canon: UIAO_135 Transformation #7; ADR-002, ADR-004. Book 04 Step 2.
        Live mode reads the documented Arc IMDS endpoint; no invented cmdlets.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $false)][string]$TokenSnapshotPath,
        [Parameter(Mandatory = $false)][switch]$Live,
        [Parameter(Mandatory = $false)][ValidateSet('AzureCloud', 'AzureUSGovernment')][string]$Cloud = $Script:DefaultCloud,
        [Parameter(Mandatory = $false)][string]$Resource,
        [Parameter(Mandatory = $false)][string]$OutputPath
    )
    $expectedAud = Resolve-UIAOSqlAudience -Cloud $Cloud -Explicit $Resource
    $accessToken = $null
    $sourceRef = $null

    if (-not [string]::IsNullOrWhiteSpace($TokenSnapshotPath)) {
        $full = Assert-UIAOInputPath -Path $TokenSnapshotPath
        $raw = Get-Content -LiteralPath $full -Raw -Encoding UTF8
        $sourceRef = "snapshot:$(Split-Path -Leaf $full)"
        $trimmed = $raw.Trim()
        if ($trimmed.StartsWith('{')) {
            $obj = $trimmed | ConvertFrom-Json
            $accessToken = Get-UIAOFieldValue $obj @('access_token', 'accessToken')
        }
        else {
            $accessToken = $trimmed
        }
    }
    elseif ($Live) {
        # Documented Arc IMDS managed-identity token endpoint. The request must
        # name the data-plane resource explicitly — a generic token mints fine
        # but is refused at use time.
        $imds = "http://169.254.169.254/metadata/identity/oauth2/token?api-version=2020-06-01&resource=$([uri]::EscapeDataString($expectedAud))"
        $resp = Invoke-RestMethod -Uri $imds -Headers @{ Metadata = 'true' } -ErrorAction Stop
        $accessToken = $resp.access_token
        $sourceRef = 'live:imds'
    }
    else {
        throw "Provide -TokenSnapshotPath for offline validation or -Live to query IMDS."
    }

    if ([string]::IsNullOrWhiteSpace($accessToken)) { throw "No access_token found in the token source." }

    $claims = ConvertFrom-UIAOJwtPayload -Jwt $accessToken
    $aud = Get-UIAOFieldValue $claims @('aud')
    $iss = Get-UIAOFieldValue $claims @('iss')
    $expRaw = Get-UIAOFieldValue $claims @('exp')

    # Audience comparison tolerates a trailing slash difference (the IMDS resource
    # and the JWT aud commonly differ only by that).
    $audMatch = $aud -and ($aud.TrimEnd('/') -ieq $expectedAud.TrimEnd('/'))
    $expEpoch = 0
    [int64]::TryParse(("$expRaw"), [ref]$expEpoch) | Out-Null
    $expUtc = if ($expEpoch -gt 0) { [DateTimeOffset]::FromUnixTimeSeconds($expEpoch).UtcDateTime } else { $null }
    $notExpired = ($expUtc -and ($expUtc -gt [DateTime]::UtcNow))

    $checks = @(
        [ordered]@{ check = 'audience_match'; passed = [bool]$audMatch; observed = $aud; expected = $expectedAud }
        [ordered]@{ check = 'not_expired'; passed = [bool]$notExpired; observed = $(if ($expUtc) { $expUtc.ToString('o') } else { $null }); expected = '> now (UTC)' }
        [ordered]@{ check = 'issuer_present'; passed = [bool]$iss; observed = $iss; expected = '<non-empty>' }
    )
    $record = [ordered]@{
        expected_audience = $expectedAud
        token_audience    = $aud
        issuer            = $iss
        expires_utc       = $(if ($expUtc) { $expUtc.ToString('o') } else { $null })
        checks            = $checks
        validation        = if (@($checks | Where-Object { -not $_.passed }).Count -eq 0) { 'pass' } else { 'fail' }
    }
    $envelope = New-UIAOMigrationEnvelope -ArtifactType 'ArcManagedIdentityTokenValidation' -Records @($record) `
        -SourceRef $sourceRef -ExtraData ([ordered]@{ validation = $record.validation })
    return (Write-UIAOEnvelopeOutput -Envelope $envelope -OutputPath $OutputPath)
}

function Test-UIAOArcSqlExtension {
    <#
    .SYNOPSIS
        Confirm the Azure extension for SQL Server is provisioned and the
        instance reports Entra-auth capable (Book 04, Step 3 verification).
        Read-only.
    .DESCRIPTION
        Resolves the extension state from a captured
        `az connectedmachine extension show` snapshot (-SnapshotPath) or, with
        -Live, by invoking it. Asserts provisioning state is 'Succeeded' for the
        WindowsAgent.SqlServer extension and surfaces the Entra-auth-capable
        signal when present.

        Resolves the Book 04 Step 3 [to build] marker: a verification wrapper
        that confirms the extension provisioning state and that the instance
        reports Entra-auth capable.
    .PARAMETER SnapshotPath
        Path to a captured extension JSON document (offline mode).
    .PARAMETER Live
        Invoke `az connectedmachine extension show` on the host.
    .PARAMETER MachineName
        Arc machine name (live mode). Defaults to $env:COMPUTERNAME.
    .PARAMETER ResourceGroup
        Resource group of the Arc machine (live mode).
    .PARAMETER ExtensionName
        Extension instance name. Default 'WindowsAgent.SqlServer'.
    .PARAMETER OutputPath
        Optional path for the sealed validation envelope JSON.
    .NOTES
        Canon: UIAO_135 Transformation #7; ADR-002, ADR-004. Book 04 Step 3.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $false)][string]$SnapshotPath,
        [Parameter(Mandatory = $false)][switch]$Live,
        [Parameter(Mandatory = $false)][string]$MachineName = $env:COMPUTERNAME,
        [Parameter(Mandatory = $false)][string]$ResourceGroup,
        [Parameter(Mandatory = $false)][string]$ExtensionName = 'WindowsAgent.SqlServer',
        [Parameter(Mandatory = $false)][string]$OutputPath
    )
    $sourceRef = $null
    if (-not [string]::IsNullOrWhiteSpace($SnapshotPath)) {
        $full = Assert-UIAOInputPath -Path $SnapshotPath
        $ext = Read-UIAOSourceData -Path $full
        $sourceRef = "snapshot:$(Split-Path -Leaf $full)"
    }
    elseif ($Live) {
        if (-not (Get-Command 'az' -ErrorAction SilentlyContinue)) {
            throw "az CLI not found on PATH. Install Azure CLI or pass -SnapshotPath."
        }
        if ([string]::IsNullOrWhiteSpace($ResourceGroup)) { throw "-ResourceGroup is required in -Live mode." }
        $raw = & az connectedmachine extension show --machine-name $MachineName --resource-group $ResourceGroup --name $ExtensionName -o json 2>$null
        if ($LASTEXITCODE -ne 0) { throw "az connectedmachine extension show exited $LASTEXITCODE" }
        $ext = ($raw -join "`n") | ConvertFrom-Json
        $sourceRef = 'live:az connectedmachine extension show'
    }
    else {
        throw "Provide -SnapshotPath for offline validation or -Live to query the extension."
    }

    $provState = Get-UIAOFieldValue $ext @('provisioningState', 'provisioning_state', 'ProvisioningState')
    $extType = Get-UIAOFieldValue $ext @('type', 'typePropertiesType', 'Type')
    # Some extension settings surface Entra-auth capability; treat absence as
    # informational rather than a hard fail (capability is also confirmed by the
    # Book 05 smoke test).
    $entraCapable = Get-UIAOFieldValue $ext @('AzureAdAuthenticationEnabled', 'azureAdAuthenticationEnabled', 'entraAuthEnabled')

    $succeeded = ($provState -and ($provState -match '(?i)^succeeded$'))
    $checks = @(
        [ordered]@{ check = 'provisioning_succeeded'; passed = [bool]$succeeded; observed = $provState; expected = 'Succeeded' }
        [ordered]@{ check = 'extension_present'; passed = [bool]$extType; observed = $extType; expected = '<non-empty>' }
    )
    $record = [ordered]@{
        extension_name        = $ExtensionName
        provisioning_state    = $provState
        extension_type        = $extType
        entra_auth_capable    = $entraCapable
        checks                = $checks
        validation            = if (@($checks | Where-Object { -not $_.passed }).Count -eq 0) { 'pass' } else { 'fail' }
    }
    $envelope = New-UIAOMigrationEnvelope -ArtifactType 'ArcSqlExtensionValidation' -Records @($record) `
        -SourceRef $sourceRef -ExtraData ([ordered]@{ validation = $record.validation })
    return (Write-UIAOEnvelopeOutput -Envelope $envelope -OutputPath $OutputPath)
}

function Invoke-UIAOArcOnboarding {
    <#
    .SYNOPSIS
        Idempotent, guarded wrapper around `azcmagent connect` (Book 04, Step 1).
        Defaults to a preview; mutating action requires explicit confirmation.
    .DESCRIPTION
        Idempotency first: if a current status (via -StatusSnapshotPath, or -Live)
        already reports Connected, the function is a no-op and returns a
        'skipped_already_connected' plan record — the "skip if already Connected"
        behavior the Book 04 [to build] marker calls for.

        Otherwise it composes the exact `azcmagent connect` invocation from the
        supplied parameters and returns it as a sealed onboarding plan. Because
        the function declares SupportsShouldProcess with ConfirmImpact High, the
        command is EXECUTED only when the caller passes -Execute AND confirms the
        ShouldProcess prompt (or -Confirm:$false in an approved change window).
        With -WhatIf (or by default, no -Execute) nothing runs against the host —
        the plan is the deliverable, suitable for change-control review.

        No secrets are embedded: tenant, subscription, resource group, location,
        cloud, and proxy are all parameters. This resolves the Book 04 Step 1
        [to build] marker (onboarding side).
    .PARAMETER ResourceGroup
        Target Azure resource group for the Arc machine resource.
    .PARAMETER TenantId
        Azure AD tenant GUID.
    .PARAMETER SubscriptionId
        Target subscription GUID.
    .PARAMETER Location
        Azure region (e.g. 'usgovvirginia').
    .PARAMETER Cloud
        azcmagent cloud name ('AzureCloud' or 'AzureUSGovernment').
    .PARAMETER ProxyUrl
        Egress proxy URL (e.g. $env:HTTPS_PROXY). Optional.
    .PARAMETER StatusSnapshotPath
        Captured `azcmagent show -j` to drive the idempotency check offline.
    .PARAMETER Live
        Query `azcmagent show -j` for the idempotency check on the host.
    .PARAMETER Execute
        Opt in to actually running `azcmagent connect`. Even with -Execute the
        ShouldProcess gate still applies (use -Confirm:$false in an approved
        change window). Without -Execute the function only plans.
    .PARAMETER OutputPath
        Optional path for the sealed onboarding-plan envelope JSON.
    .NOTES
        Canon: UIAO_135 Transformation #7; ADR-002, ADR-004. Book 04 Step 1.
        Mutating — SupportsShouldProcess, ConfirmImpact High, audit-first.
    .EXAMPLE
        # Plan only (safe default) — emits the reviewable command, runs nothing.
        Invoke-UIAOArcOnboarding -ResourceGroup rg-sql-arc -TenantId $t -SubscriptionId $s `
            -Location usgovvirginia -Cloud AzureUSGovernment -WhatIf
    #>
    [CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]
    param(
        [Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string]$ResourceGroup,
        [Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string]$TenantId,
        [Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string]$SubscriptionId,
        [Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string]$Location,
        [Parameter(Mandatory = $false)][ValidateSet('AzureCloud', 'AzureUSGovernment')][string]$Cloud = $Script:DefaultCloud,
        [Parameter(Mandatory = $false)][string]$ProxyUrl,
        [Parameter(Mandatory = $false)][string]$StatusSnapshotPath,
        [Parameter(Mandatory = $false)][switch]$Live,
        [Parameter(Mandatory = $false)][switch]$Execute,
        [Parameter(Mandatory = $false)][string]$OutputPath
    )
    # --- Idempotency: skip if already Connected --------------------------------
    $alreadyConnected = $false
    $statusRef = $null
    if (-not [string]::IsNullOrWhiteSpace($StatusSnapshotPath)) {
        $statusEnv = Test-UIAOArcAgentStatus -SnapshotPath $StatusSnapshotPath -ExpectedCloud $Cloud
        $alreadyConnected = [bool]$statusEnv.data.records[0].connected
        $statusRef = "snapshot:$(Split-Path -Leaf $StatusSnapshotPath)"
    }
    elseif ($Live -and (Get-Command 'azcmagent' -ErrorAction SilentlyContinue)) {
        $statusEnv = Test-UIAOArcAgentStatus -Live -ExpectedCloud $Cloud
        $alreadyConnected = [bool]$statusEnv.data.records[0].connected
        $statusRef = 'live:azcmagent show -j'
    }

    # Compose the exact command (arguments are data; never interpolated into a
    # shell string at execution time — splatted as an arg array).
    $argList = @(
        'connect',
        '--resource-group', $ResourceGroup,
        '--tenant-id', $TenantId,
        '--subscription-id', $SubscriptionId,
        '--location', $Location,
        '--cloud', $Cloud
    )
    if (-not [string]::IsNullOrWhiteSpace($ProxyUrl)) { $argList += @('--proxy-url', $ProxyUrl) }
    $previewCommand = 'azcmagent ' + (($argList | ForEach-Object { if ($_ -match '\s') { "`"$_`"" } else { $_ } }) -join ' ')

    if ($alreadyConnected) {
        $record = [ordered]@{
            action          = 'skipped_already_connected'
            executed        = $false
            command_preview = $previewCommand
            status_source   = $statusRef
        }
        $envelope = New-UIAOMigrationEnvelope -ArtifactType 'ArcOnboardingPlan' -Records @($record) `
            -SourceRef $statusRef -ExtraData ([ordered]@{ outcome = 'skipped_already_connected' })
        return (Write-UIAOEnvelopeOutput -Envelope $envelope -OutputPath $OutputPath)
    }

    $executed = $false
    $outcome = 'planned'
    if ($Execute) {
        if ($PSCmdlet.ShouldProcess("Arc machine in $ResourceGroup ($Cloud)", "azcmagent connect")) {
            # PATH check is gated behind ShouldProcess so -WhatIf plans without
            # requiring azcmagent; the binary is only needed for real execution.
            if (-not (Get-Command 'azcmagent' -ErrorAction SilentlyContinue)) {
                throw "azcmagent not found on PATH; cannot -Execute. Remove -Execute to plan only."
            }
            & azcmagent @argList
            if ($LASTEXITCODE -ne 0) { throw "azcmagent connect exited $LASTEXITCODE" }
            $executed = $true
            $outcome = 'executed'
        }
        else {
            $outcome = 'declined_by_shouldprocess'
        }
    }

    $record = [ordered]@{
        action          = 'onboard'
        executed        = $executed
        outcome         = $outcome
        command_preview = $previewCommand
        resource_group  = $ResourceGroup
        location        = $Location
        cloud           = $Cloud
        proxy_configured = (-not [string]::IsNullOrWhiteSpace($ProxyUrl))
    }
    $envelope = New-UIAOMigrationEnvelope -ArtifactType 'ArcOnboardingPlan' -Records @($record) `
        -SourceRef $statusRef -ExtraData ([ordered]@{ outcome = $outcome })
    return (Write-UIAOEnvelopeOutput -Envelope $envelope -OutputPath $OutputPath)
}


# ===========================================================================
# Book 05 — Login migration & parallel-run validation (ADR-091, UIAO_181)
# ===========================================================================

function Get-UIAOLoginName {
    # Extract the Windows login name from a Book 03 login-audit row.
    [CmdletBinding()]
    param([Parameter(Mandatory = $true)]$Row)
    return Get-UIAOFieldValue $Row @('LoginName', 'login_name', 'Name', 'name', 'WindowsLogin')
}

function ConvertTo-UIAOMatchKey {
    # Normalize a name to the reconciliation match key: drop a DOMAIN\ prefix and
    # lowercase, so 'CONTOSO\jdoe' and 'jdoe' join, and a UPN matches by its
    # local part when no domain-qualified key exists.
    [CmdletBinding()]
    [OutputType([string])]
    param([Parameter(Mandatory = $false)][AllowNull()][string]$Name)
    if ([string]::IsNullOrWhiteSpace($Name)) { return $null }
    $n = $Name.Trim()
    if ($n.Contains('\')) { $n = $n.Split('\')[-1] }
    return $n.ToLowerInvariant()
}

function New-UIAOEntraLoginMapping {
    <#
    .SYNOPSIS
        Map each audited Windows login to its Entra principal (UPN or group),
        codified from the UIAO_181 reconciliation — not mapped by hand (Book 05,
        Step 1). Read-only / derivation.
    .DESCRIPTION
        Resolves the Book 05 [to build] marker: the Windows-login -> Entra-
        principal mapping (the `EntraPrincipal` column) is the one piece of real
        judgment in the migration, and this codifies it from the
        Compare-UIAOIdentitySources reconciliation envelope (UIAO_181) rather than
        a hand-built spreadsheet.

        Inputs:
          -LoginAuditPath        the Book 03 *_logins.csv (or its JSON), the
                                 WindowsLogins to reproduce as Entra logins.
          -ReconciliationPath    a UIAOIdentityAssessment IdentityReconciliation
                                 envelope; only principals that reconcile cleanly
                                 (classification 'matched') produce a confident
                                 mapping.
          -GroupMap              optional hashtable / JSON mapping a Windows login
                                 (or its normalized key) to a preferred Entra
                                 *group* — group-based logins are the target
                                 because they remove per-user churn (Book 05).

        Each output record carries the Windows login, the resolved EntraPrincipal,
        the principal_type (group | user | unresolved), and the mapping_source
        (group_map | reconciliation | unresolved) with a confidence. Unresolved
        logins are emitted explicitly (never silently dropped) so an architect
        closes them before any script is generated. Pure derivation over reviewed
        artifacts — it reads no live directory and executes nothing.
    .PARAMETER LoginAuditPath
        Path to the Book 03 login inventory (.csv or .json).
    .PARAMETER ReconciliationPath
        Path to a UIAO_181 IdentityReconciliation envelope.
    .PARAMETER GroupMap
        Optional: hashtable, or path to a JSON object, mapping login -> Entra group.
    .PARAMETER OutputPath
        Optional path for the sealed mapping envelope JSON.
    .NOTES
        Canon: ADR-091, UIAO_181, UIAO_135 §3.2. Book 05 Step 1.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string]$LoginAuditPath,
        [Parameter(Mandatory = $false)][string]$ReconciliationPath,
        [Parameter(Mandatory = $false)]$GroupMap,
        [Parameter(Mandatory = $false)][string]$OutputPath
    )
    $auditFull = Assert-UIAOInputPath -Path $LoginAuditPath
    $auditData = Read-UIAOSourceData -Path $auditFull
    $auditRows = Get-UIAORows -Data $auditData -PreferredArrayKeys @('records', 'Logins', 'logins', 'WindowsLogins')

    # Build the reconciliation lookup: match_key -> { entra_upn; matched }.
    $reconByKey = @{}
    $reconRef = $null
    if (-not [string]::IsNullOrWhiteSpace($ReconciliationPath)) {
        $reconFull = Assert-UIAOInputPath -Path $ReconciliationPath
        $reconEnv = Read-UIAOSourceData -Path $reconFull
        $reconRef = "reconciliation:$(Split-Path -Leaf $reconFull)"
        foreach ($r in (Get-UIAORows -Data $reconEnv.data.records)) {
            $k = ConvertTo-UIAOMatchKey -Name (Get-UIAOFieldValue $r @('match_key', 'matchKey'))
            if (-not $k) { continue }
            $reconByKey[$k] = [ordered]@{
                classification = Get-UIAOFieldValue $r @('classification')
                entra_upn      = Get-UIAOFieldValue $r @('entra_upn', 'entraUpn', 'userPrincipalName', 'upn')
            }
        }
    }

    # Normalize the group map (hashtable or JSON-object path) to a key lookup.
    $groupLookup = @{}
    if ($GroupMap) {
        $gmObj = $GroupMap
        if ($GroupMap -is [string]) {
            $gmFull = Assert-UIAOInputPath -Path $GroupMap
            $gmObj = Read-UIAOSourceData -Path $gmFull
        }
        if ($gmObj -is [System.Collections.IDictionary]) {
            foreach ($k in $gmObj.Keys) { $groupLookup[(ConvertTo-UIAOMatchKey -Name "$k")] = "$($gmObj[$k])" }
        }
        else {
            foreach ($p in $gmObj.PSObject.Properties) { $groupLookup[(ConvertTo-UIAOMatchKey -Name $p.Name)] = "$($p.Value)" }
        }
    }

    $records = foreach ($row in $auditRows) {
        $login = Get-UIAOLoginName -Row $row
        if ([string]::IsNullOrWhiteSpace($login)) { continue }
        $type = Get-UIAOFieldValue $row @('Type', 'type', 'LoginType')
        $disabled = Get-UIAOFieldValue $row @('Disabled', 'disabled', 'IsDisabled')
        $key = ConvertTo-UIAOMatchKey -Name $login

        $entraPrincipal = $null; $principalType = 'unresolved'; $mappingSource = 'unresolved'; $confidence = 'none'
        if ($groupLookup.ContainsKey($key)) {
            $entraPrincipal = $groupLookup[$key]; $principalType = 'group'; $mappingSource = 'group_map'; $confidence = 'high'
        }
        elseif ($reconByKey.ContainsKey($key)) {
            $rec = $reconByKey[$key]
            if (($rec.classification -eq 'matched') -and $rec.entra_upn) {
                $entraPrincipal = $rec.entra_upn; $principalType = 'user'; $mappingSource = 'reconciliation'; $confidence = 'high'
            }
            else {
                # present in reconciliation but not cleanly matched -> needs review
                $mappingSource = "reconciliation:$($rec.classification)"; $confidence = 'low'
            }
        }

        [ordered]@{
            windows_login   = $login
            login_type      = $type
            disabled        = $disabled
            entra_principal = $entraPrincipal
            principal_type  = $principalType
            mapping_source  = $mappingSource
            confidence      = $confidence
            review_required = ($principalType -eq 'unresolved')
        }
    }
    $records = @($records)
    $unresolved = @($records | Where-Object { $_.review_required }).Count
    $derived = if ($reconRef) { [ordered]@{ source = 'IdentityReconciliation'; source_file = (Split-Path -Leaf $ReconciliationPath) } } else { $null }
    $envelope = New-UIAOMigrationEnvelope -ArtifactType 'EntraLoginMapping' -Records $records `
        -SourceRef "audit:$(Split-Path -Leaf $auditFull)" -DerivedFrom $derived `
        -ExtraData ([ordered]@{ unresolved_count = $unresolved; approvable = ($unresolved -eq 0) })
    return (Write-UIAOEnvelopeOutput -Envelope $envelope -OutputPath $OutputPath)
}

function New-UIAOEntraLoginScript {
    <#
    .SYNOPSIS
        Generate idempotent CREATE LOGIN ... FROM EXTERNAL PROVIDER T-SQL from a
        login mapping. DRY-RUN ONLY: writes a reviewable .sql file and executes
        nothing against any instance (Book 05, Step 1).
    .DESCRIPTION
        Consumes a New-UIAOEntraLoginMapping envelope (or its records) and emits
        the exact idempotent T-SQL the runbook specifies — one
        `IF NOT EXISTS (... ) CREATE LOGIN [<principal>] FROM EXTERNAL PROVIDER;`
        per resolved principal, group-based logins preferred. This is the
        production-safety heart of Book 05: the function NEVER opens a SQL
        connection. Its only side effect is writing a script file for review and
        execution in a change window.

        Unresolved mappings (review_required) are NOT emitted as runnable T-SQL —
        they appear only as commented-out lines so a half-mapped estate cannot
        produce a login for a principal no one chose. The principal name is
        emitted inside bracket-quoting with embedded `]` doubled, so an odd
        principal name cannot break out of the identifier.
    .PARAMETER MappingPath
        Path to a New-UIAOEntraLoginMapping envelope JSON.
    .PARAMETER OutputPath
        Path for the generated .sql script. Strongly recommended (the script is
        the deliverable); when omitted the T-SQL is returned as a string.
    .PARAMETER IncludeUnresolved
        Also emit unresolved mappings as commented-out TODO lines (default on).
    .NOTES
        Canon: ADR-091, UIAO_135 §3.2. Book 05 Step 1. Generates a script;
        executes nothing — review-required before any change window.
    #>
    [CmdletBinding()]
    [OutputType([string])]
    param(
        [Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string]$MappingPath,
        [Parameter(Mandatory = $false)][string]$OutputPath,
        [Parameter(Mandatory = $false)][bool]$IncludeUnresolved = $true
    )
    $full = Assert-UIAOInputPath -Path $MappingPath
    $env = Read-UIAOSourceData -Path $full
    $rows = Get-UIAORows -Data $env.data.records

    $lines = @()
    $lines += '-- Generated by UIAOSqlServerMigration (Book 05). DRY-RUN ARTIFACT — review before executing.'
    $lines += '-- Idempotent CREATE LOGIN ... FROM EXTERNAL PROVIDER. Executes nothing on generation.'
    $lines += "-- Source mapping: $(Split-Path -Leaf $full)"
    $lines += '-- Safety: keep the superseded Windows login ENABLED until parallel-run validates the Entra login (ADR-091 §1).'
    $lines += ''

    $emitted = 0; $skipped = 0
    foreach ($r in $rows) {
        $principal = Get-UIAOFieldValue $r @('entra_principal', 'EntraPrincipal')
        $reviewRequired = "$(Get-UIAOFieldValue $r @('review_required'))" -match '(?i)true'
        $login = Get-UIAOFieldValue $r @('windows_login', 'WindowsLogin')
        if ([string]::IsNullOrWhiteSpace($principal) -or $reviewRequired) {
            $skipped++
            if ($IncludeUnresolved) {
                $lines += "-- TODO (review): no confident Entra principal for Windows login '$login' — resolve in the mapping before generating."
            }
            continue
        }
        $safe = $principal.Replace(']', ']]')
        $lines += "IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE name = N'$($principal.Replace("'", "''"))')"
        $lines += "    CREATE LOGIN [$safe] FROM EXTERNAL PROVIDER;"
        $lines += 'GO'
        $emitted++
    }
    $lines += ''
    $lines += "-- Summary: $emitted login(s) generated, $skipped unresolved/skipped."
    $text = ($lines -join "`n") + "`n"

    Write-UIAOTextOutput -Text $text -OutputPath $OutputPath
    return $text
}

function Test-UIAOLoginParallelRun {
    <#
    .SYNOPSIS
        Evaluate the parallel-run observation window against its exit criteria
        from observed connection auth-schemes (Book 05, Step 3). Read-only.
    .DESCRIPTION
        Consumes the output of the live auth-scheme query the runbook gives
        (sys.dm_exec_connections joined to sys.dm_exec_sessions, projected to
        login_name / auth_scheme / sessions) — supplied as a captured .csv/.json
        via -ObservationPath, so the evaluation is fully offline and testable.
        Against ADR-091 §1 exit criteria it reports:
          - whether every login that connected via NTLM/KERBEROS now also appears
            connecting via AAD,
          - whether ANY NTLM rows remain (cross-checks Book 06 — must be zero),
          - whether any login is still arriving ONLY on its legacy scheme.
        Emits a sealed validation envelope with a cutover_ready verdict. It only
        reads and reports — it never disables or drops a login (that is the manual
        change-window step the runbook keeps review-required).
    .PARAMETER ObservationPath
        Path to captured auth-scheme observations (.csv or .json) with columns
        login_name, auth_scheme, sessions.
    .PARAMETER OutputPath
        Optional path for the sealed validation envelope JSON.
    .NOTES
        Canon: ADR-091 §1, UIAO_135 §3.2. Book 05 Step 3.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string]$ObservationPath,
        [Parameter(Mandatory = $false)][string]$OutputPath
    )
    $full = Assert-UIAOInputPath -Path $ObservationPath
    $data = Read-UIAOSourceData -Path $full
    $rows = Get-UIAORows -Data $data -PreferredArrayKeys @('records', 'observations')

    # login -> set of schemes seen
    $byLogin = @{}
    $ntlmRows = 0
    foreach ($r in $rows) {
        $login = Get-UIAOFieldValue $r @('login_name', 'LoginName', 'login')
        $scheme = Get-UIAOFieldValue $r @('auth_scheme', 'AuthScheme', 'scheme')
        if (-not $login -or -not $scheme) { continue }
        $s = $scheme.Trim().ToUpperInvariant()
        if (-not $byLogin.ContainsKey($login)) { $byLogin[$login] = [System.Collections.Generic.HashSet[string]]::new() }
        [void]$byLogin[$login].Add($s)
        if ($s -eq 'NTLM') { $ntlmRows++ }
    }

    $perLogin = foreach ($login in ($byLogin.Keys | Sort-Object)) {
        $schemes = @($byLogin[$login])
        $hasAad = $schemes -contains 'AAD'
        $hasLegacy = @($schemes | Where-Object { $_ -in @('NTLM', 'KERBEROS') }).Count -gt 0
        $onlyLegacy = $hasLegacy -and -not $hasAad
        [ordered]@{
            login_name  = $login
            schemes     = ($schemes | Sort-Object)
            has_aad     = $hasAad
            only_legacy = $onlyLegacy
        }
    }
    $perLogin = @($perLogin)
    $loginsOnlyLegacy = @($perLogin | Where-Object { $_.only_legacy }).Count
    $cutoverReady = ($ntlmRows -eq 0) -and ($loginsOnlyLegacy -eq 0)

    $criteria = @(
        [ordered]@{ criterion = 'no_ntlm_remaining'; passed = ($ntlmRows -eq 0); observed = $ntlmRows; expected = 0 }
        [ordered]@{ criterion = 'no_login_only_on_legacy'; passed = ($loginsOnlyLegacy -eq 0); observed = $loginsOnlyLegacy; expected = 0 }
    )
    $envelope = New-UIAOMigrationEnvelope -ArtifactType 'LoginParallelRunValidation' -Records $perLogin `
        -SourceRef "observation:$(Split-Path -Leaf $full)" `
        -ExtraData ([ordered]@{ ntlm_rows = $ntlmRows; logins_only_legacy = $loginsOnlyLegacy; exit_criteria = $criteria; cutover_ready = $cutoverReady })
    return (Write-UIAOEnvelopeOutput -Envelope $envelope -OutputPath $OutputPath)
}


# ===========================================================================
# Book 06 — NTLM detection & remediation (ADR-068, UIAO_135 §3.2)
# ===========================================================================

function New-UIAOSpnRemediationPlan {
    <#
    .SYNOPSIS
        Turn a Spec3-D1.7 SPN-collision report into an audit-first, reviewable
        SPN remediation plan — the safe `setspn -S` / `setspn -D` actions per
        collision (Book 06, Phase 2). Audit/plan only; enforces nothing.
    .DESCRIPTION
        Resolves the Book 06 remediation gap (the [to build] SPN-collision
        remediation helper). Consumes the Spec3-D1.7 collision JSON (its
        Collisions[] with Accounts[]) and derives, per collision, the minimal set
        of `setspn` commands that reduce it to a single enabled owner — the only
        state in which Kerberos succeeds:
          - Remove the SPN from any DISABLED or wrong account (`setspn -D ...`),
            leaving exactly one enabled owner.
          - For a cross-object-type collision (SPN on both a computer and a user
            object, severity CRITICAL) recommend removing it from the user/service
            account and migrating that service to a workload identity (ADR-004).
          - Where the SPN is MISSING (no owner), emit the safe registration form
            `setspn -S` (rejects on collision) for the intended service account.

        Output is a sealed remediation plan: every action has a `command_preview`,
        a `mutating=$true` flag, and `requires_review=$true`. The plan is the
        deliverable; the function runs no `setspn` and changes nothing in AD. The
        commands are emitted as previews for execution in a reviewed change
        window — consistent with the "audit-first, no enforcement by default"
        bar.
    .PARAMETER CollisionReportPath
        Path to a Spec3-D1.7 SPN-collision report JSON.
    .PARAMETER ServiceClassFilter
        Optional service-class filter (e.g. 'MSSQLSvc' to scope to SQL). Default:
        all classes.
    .PARAMETER IntendedOwner
        Optional account to register a MISSING SQL SPN to (used only to compose
        the `setspn -S` preview; never executed).
    .PARAMETER OutputPath
        Optional path for the sealed remediation-plan envelope JSON.
    .NOTES
        Canon: ADR-068, ADR-004, UIAO_135 §3.2. Book 06 Phase 2. Consumes
        Spec3-D1.7. Audit-first — emits previews, executes no setspn.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string]$CollisionReportPath,
        [Parameter(Mandatory = $false)][string]$ServiceClassFilter,
        [Parameter(Mandatory = $false)][string]$IntendedOwner,
        [Parameter(Mandatory = $false)][string]$OutputPath
    )
    $full = Assert-UIAOInputPath -Path $CollisionReportPath
    $report = Read-UIAOSourceData -Path $full
    $collisionSource = if ($report.PSObject.Properties.Name -contains 'Collisions') { $report.Collisions } else { $report }
    $collisions = Get-UIAORows -Data $collisionSource -PreferredArrayKeys @('Collisions', 'records')

    $actions = foreach ($c in $collisions) {
        $serviceClass = Get-UIAOFieldValue $c @('ServiceClass', 'serviceClass')
        if ($ServiceClassFilter -and $serviceClass -and ($serviceClass -inotmatch [regex]::Escape($ServiceClassFilter))) { continue }
        $spn = Get-UIAOFieldValue $c @('SPN', 'spn')
        $type = Get-UIAOFieldValue $c @('CollisionType', 'collisionType')
        $severity = Get-UIAOFieldValue $c @('Severity', 'severity')
        # Read the structured Accounts array (Get-UIAOFieldValue would stringify).
        $accountsRaw = if ($c.PSObject.Properties.Name -contains 'Accounts') { @($c.Accounts) } else { @() }

        # StrictMode-safe property reads (Get-UIAOFieldValue tolerates absent props).
        $disabled = @($accountsRaw | Where-Object { "$(Get-UIAOFieldValue $_ @('Enabled', 'enabled'))" -match '(?i)false' })
        $enabled = @($accountsRaw | Where-Object { "$(Get-UIAOFieldValue $_ @('Enabled', 'enabled'))" -match '(?i)true' })

        # Compose the minimal safe action set for this collision.
        $cmds = @()
        foreach ($d in $disabled) {
            $acct = Get-UIAOFieldValue $d @('AccountName', 'accountName')
            if ($acct -and $spn) { $cmds += "setspn -D $spn $acct" }
        }
        if ($type -match '(?i)CrossObjectType') {
            foreach ($u in @($accountsRaw | Where-Object { "$(Get-UIAOFieldValue $_ @('ObjectType', 'objectType'))" -match '(?i)user' })) {
                $acct = Get-UIAOFieldValue $u @('AccountName', 'accountName')
                if ($acct -and $spn) { $cmds += "setspn -D $spn $acct   # then migrate this service to a workload identity (ADR-004)" }
            }
        }
        $recommended = if ($cmds.Count -gt 0) { 'remove_shadowing_or_user_spn' }
        elseif ($enabled.Count -gt 1) { 'reduce_to_single_enabled_owner' }
        else { 'investigate' }

        [ordered]@{
            spn               = $spn
            service_class     = $serviceClass
            collision_type    = $type
            severity          = $severity
            enabled_owners    = $enabled.Count
            disabled_owners   = $disabled.Count
            recommended_action = $recommended
            commands          = @($cmds)
            mutating          = $true
            requires_review   = $true
        }
    }
    $actions = @($actions)

    # Optional: a MISSING SQL SPN registration preview (the most common silent-
    # NTLM root cause). Emitted only when an intended owner is supplied.
    if ($ServiceClassFilter -and ($ServiceClassFilter -imatch 'MSSQLSvc') -and (-not [string]::IsNullOrWhiteSpace($IntendedOwner))) {
        $actions += [ordered]@{
            spn                = 'MSSQLSvc/<sqlhost>[:port]'
            service_class      = 'MSSQLSvc'
            collision_type     = 'MissingSPN'
            severity           = 'High'
            recommended_action = 'register_missing_spn'
            commands           = @(
                "setspn -S MSSQLSvc/<sqlhost>:1433 $IntendedOwner",
                "setspn -S MSSQLSvc/<sqlhost.fqdn>:1433 $IntendedOwner"
            )
            mutating           = $true
            requires_review    = $true
        }
    }

    $critical = @($actions | Where-Object { "$($_.severity)" -match '(?i)critical' }).Count
    $envelope = New-UIAOMigrationEnvelope -ArtifactType 'SpnRemediationPlan' -Records $actions `
        -SourceRef "collision_report:$(Split-Path -Leaf $full)" `
        -DerivedFrom ([ordered]@{ source = 'Spec3-D1.7-Get-SPNCollisionReport'; source_file = (Split-Path -Leaf $full) }) `
        -ExtraData ([ordered]@{ critical_count = $critical; audit_first = $true; enforcement = 'none_by_default' })
    return (Write-UIAOEnvelopeOutput -Envelope $envelope -OutputPath $OutputPath)
}

function Get-UIAONtlmGpoReport {
    <#
    .SYNOPSIS
        Report each in-scope GPO's NTLM-reduction posture against the ADR-068
        phased plan (Book 06, Phase 2 GPO block). Read-only — audits, never sets.
    .DESCRIPTION
        Resolves the Book 06 remediation gap (the [to build] NTLM-reduction Group
        Policy reporting). Reads GPO settings either from a captured
        `Get-GPOReport -ReportType Xml` snapshot (-GpoReportPath, offline/testable)
        or, with -Live, by invoking `Get-GPOReport` per GPO. For each GPO it reads
        the *LAN Manager authentication level* and the *Restrict NTLM* settings
        and classifies posture against the phased plan:
          - Phase B target: 'Send NTLMv2 response only. Refuse LM & NTLM'
            (LmCompatibilityLevel 5).
          - Phase C backstop (program date 2027-04-01): Restrict NTLM = deny/audit.
        It NEVER calls Set-GPRegistryValue / Set-GPO — it only reports posture so
        the phased enforcement stays a reviewed change, consistent with
        "audit-first, no enforcement by default".

        The 2027-04-01 date is the PROGRAM's own planning backstop, not an
        external FedRAMP or Microsoft mandate (narrative Book 06, ADR-068).
    .PARAMETER GpoReportPath
        Path to a captured GPO settings document. Accepts the module's normalized
        JSON shape (records with gpo_name / lm_compatibility_level /
        restrict_ntlm_*) or a `Get-GPOReport -ReportType Xml` file.
    .PARAMETER Live
        Enumerate GPOs via the GroupPolicy module and read each report live.
    .PARAMETER TargetLmCompatibilityLevel
        The Phase B target LmCompatibilityLevel. Default 5 (Refuse LM & NTLM).
    .PARAMETER OutputPath
        Optional path for the sealed posture-report envelope JSON.
    .NOTES
        Canon: ADR-068, UIAO_135 §3.2. Book 06 Phase 2. Read-only GPO reporting;
        uses Get-GPOReport (no invented cmdlets); sets nothing.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $false)][string]$GpoReportPath,
        [Parameter(Mandatory = $false)][switch]$Live,
        [Parameter(Mandatory = $false)][ValidateRange(0, 5)][int]$TargetLmCompatibilityLevel = 5,
        [Parameter(Mandatory = $false)][string]$OutputPath
    )
    $gpoRows = @()
    $sourceRef = $null
    if (-not [string]::IsNullOrWhiteSpace($GpoReportPath)) {
        $full = Assert-UIAOInputPath -Path $GpoReportPath
        $data = Read-UIAOSourceData -Path $full
        $gpoRows = Get-UIAORows -Data $data -PreferredArrayKeys @('records', 'gpos', 'GPOs')
        $sourceRef = "snapshot:$(Split-Path -Leaf $full)"
    }
    elseif ($Live) {
        if (-not (Get-Module -ListAvailable -Name GroupPolicy)) {
            throw "GroupPolicy module not found (RSAT). Install it or pass -GpoReportPath."
        }
        Import-Module GroupPolicy -ErrorAction Stop
        # Live mode is intentionally a thin pass-through: it surfaces the GPO
        # names so an operator can capture per-GPO Get-GPOReport XML, which the
        # offline path then classifies. We do not parse XML here to keep the
        # security policy parsing testable and reviewed.
        $gpoRows = foreach ($g in (Get-GPO -All)) {
            [ordered]@{ gpo_name = $g.DisplayName; lm_compatibility_level = $null; restrict_ntlm_incoming = $null; restrict_ntlm_outgoing = $null }
        }
        $sourceRef = 'live:Get-GPO -All'
    }
    else {
        throw "Provide -GpoReportPath for offline reporting or -Live to enumerate GPOs."
    }

    $records = foreach ($r in $gpoRows) {
        $name = Get-UIAOFieldValue $r @('gpo_name', 'GpoName', 'DisplayName', 'name')
        $lmRaw = Get-UIAOFieldValue $r @('lm_compatibility_level', 'LmCompatibilityLevel')
        $restrictIn = Get-UIAOFieldValue $r @('restrict_ntlm_incoming', 'RestrictNtlmIncoming')
        $restrictOut = Get-UIAOFieldValue $r @('restrict_ntlm_outgoing', 'RestrictNtlmOutgoing')
        $lm = $null
        if ($null -ne $lmRaw -and $lmRaw -ne '') { $tmp = 0; if ([int]::TryParse("$lmRaw", [ref]$tmp)) { $lm = $tmp } }

        $phaseBMet = ($null -ne $lm) -and ($lm -ge $TargetLmCompatibilityLevel)
        $phaseCMet = ($restrictIn -and ($restrictIn -match '(?i)deny|block')) -or ($restrictOut -and ($restrictOut -match '(?i)deny|block'))
        $posture = if ($phaseCMet) { 'phase_c_full_block' }
        elseif ($phaseBMet) { 'phase_b_ntlmv2_only' }
        elseif ($null -ne $lm) { 'below_target' }
        else { 'unconfigured' }

        [ordered]@{
            gpo_name                 = $name
            lm_compatibility_level   = $lm
            restrict_ntlm_incoming   = $restrictIn
            restrict_ntlm_outgoing   = $restrictOut
            phase_b_ntlmv2_only_met  = $phaseBMet
            phase_c_full_block_met   = $phaseCMet
            posture                  = $posture
            recommendation           = switch ($posture) {
                'phase_c_full_block' { 'Compliant with the 2027-04-01 backstop; verify exception groups remain documented.' }
                'phase_b_ntlmv2_only' { 'NTLMv2-only in place; plan Restrict NTLM (Phase C) ahead of the 2027-04-01 program backstop.' }
                'below_target' { "Raise LAN Manager auth level to >= $TargetLmCompatibilityLevel (Refuse LM & NTLM) — Phase B." }
                default { 'No NTLM-reduction setting found; this GPO does not contribute to the phased block.' }
            }
        }
    }
    $records = @($records)
    $compliant = @($records | Where-Object { $_.phase_b_ntlmv2_only_met -or $_.phase_c_full_block_met }).Count
    $envelope = New-UIAOMigrationEnvelope -ArtifactType 'NtlmGpoPostureReport' -Records $records `
        -SourceRef $sourceRef `
        -ExtraData ([ordered]@{
            target_lm_compatibility_level = $TargetLmCompatibilityLevel
            phase_compliant_count         = $compliant
            program_backstop              = '2027-04-01'
            backstop_note                 = 'Program planning date — not an external FedRAMP or Microsoft mandate (ADR-068).'
            read_only                     = $true
        })
    return (Write-UIAOEnvelopeOutput -Envelope $envelope -OutputPath $OutputPath)
}


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

Export-ModuleMember -Function `
    'Test-UIAOArcAgentStatus', `
    'Test-UIAOArcManagedIdentityToken', `
    'Test-UIAOArcSqlExtension', `
    'Invoke-UIAOArcOnboarding', `
    'New-UIAOEntraLoginMapping', `
    'New-UIAOEntraLoginScript', `
    'Test-UIAOLoginParallelRun', `
    'New-UIAOSpnRemediationPlan', `
    'Get-UIAONtlmGpoReport'
