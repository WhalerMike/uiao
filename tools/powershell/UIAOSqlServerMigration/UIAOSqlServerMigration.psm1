# UIAOSqlServerMigration — SQL Server identity-transformation automation
# (canon: UIAO_135 Transformation #7; ADR-002, ADR-004, ADR-068, ADR-091).
#
# The shipped automation behind the "Implementation Companion" runbooks for the
# SQL Server identity transformation:
#   - Book 02 (estate discovery & the consolidation gate) — the fused Phase-0
#     estate inventory with the ADR-091 §1 retain/consolidate/retire gate
#   - Book 04 (Arc deployment & the managed identity) — onboarding + validation
#   - Book 05 (login migration to Entra) — CREATE LOGIN ... FROM EXTERNAL PROVIDER
#     script generation from the audit, with parallel-run validation
#   - Book 06 (NTLM/Kerberos remediation) — SPN-collision remediation planning
#     and NTLM-reduction Group Policy reporting
#   - Book 07 (groups, AUs & the CA perimeter) — ADR-067 group classification and
#     the group-login emitter
#   - Book 08 (the application chain) — the Spec3-D1.9<->D1.8 correlation, ADR-069
#     app classification, and the connection-string migration plan
#   - Book 09 (continuous monitoring) — the ADR-091 §5 CCM-BIR closure record and
#     the scheduled-run drift diff
#   - Book 10 (certificate discovery) — SQL's three ADCS dependencies and the
#     dependency-ordered CA-replacement (CBA-issuance) bridge
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
#   Estate discovery (Book 02):
#     New-UIAOEstateInventory          fused Phase-0 inventory + retain/consolidate/retire gate
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
#   Groups / AUs (Book 07):
#     New-UIAOEntraGroupClassification ADR-067 four-type group classification
#     New-UIAOGroupLoginScript         CREATE LOGIN for access-backing groups (dry-run)
#   Application chain (Book 08):
#     New-UIAOAppConnectionPlan        D1.9<->D1.8 correlation + ADR-069 + conn-string plan
#   Continuous monitoring (Book 09):
#     New-UIAOClosureRecord            ADR-091 §5 CCM-BIR per-instance closure record
#     Compare-UIAOClosureRun           scheduled-run drift diff (compliance violations)
#   Certificates (Book 10):
#     New-UIAOSqlCertificatePlan       SQL ADCS dependencies + CA-replacement sequence

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Script:ModuleVersion = '1.1.0'

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
# Shared helpers for the Books 02/07/08/09/10 derivations
# ---------------------------------------------------------------------------

function Get-UIAOArrayProp {
    # StrictMode-safe read of a named array property; returns @() when the
    # property is absent or null (ConvertFrom-Json objects throw on a missing
    # member under Set-StrictMode -Version Latest, so every nested-array read
    # goes through here, mirroring the Accounts read in New-UIAOSpnRemediationPlan).
    [CmdletBinding()]
    [OutputType([object[]])]
    param(
        [Parameter(Mandatory = $true)][AllowNull()]$Row,
        [Parameter(Mandatory = $true)][string[]]$Names
    )
    if ($null -eq $Row) { return @() }
    foreach ($n in $Names) {
        $p = $Row.PSObject.Properties | Where-Object { $_.Name -ieq $n } | Select-Object -First 1
        if ($p -and ($null -ne $p.Value)) { return @($p.Value) }
    }
    return @()
}

function ConvertTo-UIAOBool {
    # Coerce a JSON/CSV-sourced truthy value to [bool]. Absent/empty is $false.
    [CmdletBinding()]
    [OutputType([bool])]
    param([Parameter(Mandatory = $false)][AllowNull()]$Value)
    if ($null -eq $Value) { return $false }
    if ($Value -is [bool]) { return $Value }
    return ("$Value".Trim() -match '(?i)^(true|1|yes|y|enabled)$')
}

function Get-UIAOInstanceKey {
    # Normalize a SQL instance identity to a stable join key. A default instance
    # ('MSSQLSERVER' / blank) keys on the host alone, so the same instance found
    # by different instruments deduplicates.
    [CmdletBinding()]
    [OutputType([string])]
    param([Parameter(Mandatory = $false)][AllowNull()][string]$Server, [Parameter(Mandatory = $false)][AllowNull()][string]$Instance)
    $s = if ($Server) { $Server.Trim().ToLowerInvariant() } else { '' }
    if ($s.Contains('\')) { $s = $s.Split('\')[0] }   # SERVER\INST in the host field
    $i = if ($Instance) { $Instance.Trim().ToLowerInvariant() } else { '' }
    if ([string]::IsNullOrWhiteSpace($i) -or $i -in @('mssqlserver', 'default')) { return $s }
    return "$s\$i"
}


# ===========================================================================
# Book 02 — Estate discovery & the consolidation gate (ADR-091 §1)
# ===========================================================================

function New-UIAOEstateInventory {
    <#
    .SYNOPSIS
        Fuse the shipped discovery instruments into one deduplicated estate
        inventory and apply the ADR-091 §1 retain / consolidate / retire gate
        (Book 02). Read-only derivation — the Phase-0 instrument.
    .DESCRIPTION
        Resolves the Book 02 [to build] marker: the fused Phase-0 estate-discovery
        instrument. No single instrument finds every instance, so this consumes
        the outputs the shipped scripts already produce and merges them into the
        estate *denominator* every later book operates on:

          -AuthAuditPath     Spec3-D1.8 discovery output (instances enumerated
                             via registry/AD; the InstanceAudits[] / records).
          -SpnInventoryPath  Spec1-D1.5 MSSQLSvc SPN trail (Kerberos-configured
                             hosts otherwise off the radar). Optional.
          -FindInstancePath  A Find-DbaInstance export (network/Browser sweep).
                             Optional.

        Each instance is keyed on host\instance (default instances key on host),
        so the same instance seen by multiple instruments deduplicates while the
        `discovered_by` set records coverage. The three rationalization lenses
        resolve to one classification per instance:
          - retire     — zombie: last access older than -ZombieThresholdDays.
          - consolidate— pre-2022 engine (cannot accept Entra logins in place;
                         the surviving workload moves to a SQL 2022 target).
          - retain     — supported engine (SQL 2022+), enters auth migration.
          - review     — insufficient signal (version/last-access unknown); never
                         silently defaulted to retain.

        Pure derivation over reviewed discovery output — it reads no live host or
        directory and changes nothing. Consolidation *execution* stays review-
        required and lives in the program's migration plan, not here.
    .PARAMETER AuthAuditPath
        Path to a Spec3-D1.8 discovery output (.json or .csv).
    .PARAMETER SpnInventoryPath
        Optional path to a Spec1-D1.5 MSSQLSvc SPN inventory (.json or .csv).
    .PARAMETER FindInstancePath
        Optional path to a Find-DbaInstance export (.csv or .json).
    .PARAMETER ZombieThresholdDays
        Last-access age (days) at/above which an instance with a last-access
        signal is classified 'retire'. Default 400.
    .PARAMETER OutputPath
        Optional path for the sealed estate-inventory envelope JSON.
    .NOTES
        Canon: ADR-091 §1, UIAO_135 §3.2. Book 02. Read-only derivation.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string]$AuthAuditPath,
        [Parameter(Mandatory = $false)][string]$SpnInventoryPath,
        [Parameter(Mandatory = $false)][string]$FindInstancePath,
        [Parameter(Mandatory = $false)][ValidateRange(1, 100000)][int]$ZombieThresholdDays = 400,
        [Parameter(Mandatory = $false)][string]$OutputPath
    )
    $estate = @{}        # key -> [ordered] record
    $derived = @()

    function Merge-Estate {
        param($Key, $Server, $Instance, $Source, [hashtable]$Fields)
        if ([string]::IsNullOrWhiteSpace($Key)) { return }
        if (-not $estate.ContainsKey($Key)) {
            $estate[$Key] = [ordered]@{
                instance_key        = $Key
                server_name         = $Server
                instance_name       = $Instance
                port                = $null
                sql_version_major   = $null
                sql_edition         = $null
                authentication_mode = $null
                service_account     = $null
                last_access_days    = $null
                discovered_by       = @()
            }
        }
        $rec = $estate[$Key]
        if (-not ($rec.discovered_by -contains $Source)) { $rec.discovered_by = @($rec.discovered_by + $Source) }
        foreach ($f in $Fields.Keys) {
            if (($null -eq $rec[$f]) -or ("$($rec[$f])" -eq '')) {
                if (($null -ne $Fields[$f]) -and ("$($Fields[$f])" -ne '')) { $rec[$f] = $Fields[$f] }
            }
        }
    }

    # --- Source 1: Spec3-D1.8 (authoritative instance enumeration) -------------
    $auditFull = Assert-UIAOInputPath -Path $AuthAuditPath
    $auditData = Read-UIAOSourceData -Path $auditFull
    foreach ($r in (Get-UIAORows -Data $auditData -PreferredArrayKeys @('InstanceAudits', 'records', 'Instances'))) {
        $server = Get-UIAOFieldValue $r @('ServerName', 'server_name', 'ComputerName', 'HostName')
        $inst = Get-UIAOFieldValue $r @('InstanceName', 'instance_name', 'Instance')
        $verRaw = Get-UIAOFieldValue $r @('SQLVersionMajor', 'sql_version_major', 'VersionMajor')
        $ver = $null; if ($verRaw) { $tmp = 0; if ([int]::TryParse("$verRaw", [ref]$tmp)) { $ver = $tmp } }
        Merge-Estate -Key (Get-UIAOInstanceKey -Server $server -Instance $inst) -Server $server -Instance $inst -Source 'Spec3-D1.8' -Fields @{
            port                = Get-UIAOFieldValue $r @('Port', 'port')
            sql_version_major   = $ver
            sql_edition         = Get-UIAOFieldValue $r @('SQLEdition', 'sql_edition', 'Edition')
            authentication_mode = Get-UIAOFieldValue $r @('AuthenticationMode', 'authentication_mode', 'LoginMode')
            service_account     = Get-UIAOFieldValue $r @('ServiceAccountName', 'service_account', 'ServiceAccount')
            last_access_days    = Get-UIAOFieldValue $r @('LastAccessDays', 'last_access_days')
        }
    }
    $derived += [ordered]@{ source = 'Spec3-D1.8-Get-SQLServerAuthAudit'; source_file = (Split-Path -Leaf $auditFull) }

    # --- Source 2: Spec1-D1.5 SPN trail (optional) -----------------------------
    if (-not [string]::IsNullOrWhiteSpace($SpnInventoryPath)) {
        $spnFull = Assert-UIAOInputPath -Path $SpnInventoryPath
        $spnData = Read-UIAOSourceData -Path $spnFull
        foreach ($r in (Get-UIAORows -Data $spnData -PreferredArrayKeys @('SPNs', 'records', 'Orphans'))) {
            $spnHost = Get-UIAOFieldValue $r @('HostName', 'ServerName', 'Host', 'ComputerName')
            $spn = Get-UIAOFieldValue $r @('SPN', 'spn', 'ServicePrincipalName')
            if (-not $spnHost -and $spn -and $spn.Contains('/')) {
                # MSSQLSvc/host[:port] — pull the host (and dynamic-port instance, if any).
                $hp = $spn.Split('/')[-1]
                $spnHost = $hp.Split(':')[0]
            }
            if (-not $spnHost) { continue }
            Merge-Estate -Key (Get-UIAOInstanceKey -Server $spnHost -Instance $null) -Server $spnHost -Instance $null -Source 'Spec1-D1.5' -Fields @{}
        }
        $derived += [ordered]@{ source = 'Spec1-D1.5-Get-KerberosSPNInventory'; source_file = (Split-Path -Leaf $spnFull) }
    }

    # --- Source 3: Find-DbaInstance network sweep (optional) -------------------
    if (-not [string]::IsNullOrWhiteSpace($FindInstancePath)) {
        $fiFull = Assert-UIAOInputPath -Path $FindInstancePath
        $fiData = Read-UIAOSourceData -Path $fiFull
        foreach ($r in (Get-UIAORows -Data $fiData -PreferredArrayKeys @('records', 'Instances'))) {
            $server = Get-UIAOFieldValue $r @('ComputerName', 'computer_name', 'ServerName', 'SqlInstance')
            $inst = Get-UIAOFieldValue $r @('InstanceName', 'instance_name')
            if (-not $server) { continue }
            Merge-Estate -Key (Get-UIAOInstanceKey -Server $server -Instance $inst) -Server $server -Instance $inst -Source 'Find-DbaInstance' -Fields @{
                port = Get-UIAOFieldValue $r @('Port', 'TCPPort', 'port')
            }
        }
        $derived += [ordered]@{ source = 'Find-DbaInstance'; source_file = (Split-Path -Leaf $fiFull) }
    }

    # --- Classify (the gate) ---------------------------------------------------
    $records = foreach ($key in ($estate.Keys | Sort-Object)) {
        $rec = $estate[$key]
        $basis = @()
        $lastAccess = $null
        if ($null -ne $rec.last_access_days -and "$($rec.last_access_days)" -ne '') {
            $t = 0; if ([int]::TryParse("$($rec.last_access_days)", [ref]$t)) { $lastAccess = $t }
        }
        $ver = $rec.sql_version_major

        $classification = 'review'
        if (($null -ne $lastAccess) -and ($lastAccess -ge $ZombieThresholdDays)) {
            $classification = 'retire'; $basis += "no access in >= $ZombieThresholdDays days (zombie)"
        }
        elseif ($null -ne $ver -and $ver -lt 16) {
            $classification = 'consolidate'; $basis += "pre-2022 engine (v$ver) cannot accept Entra logins in place — move surviving workload to a SQL 2022 target"
        }
        elseif ($null -ne $ver -and $ver -ge 16) {
            $classification = 'retain'; $basis += "supported engine (v$ver) — enters the authentication migration (Book 03+)"
        }
        else {
            $basis += 'insufficient signal (engine version and last-access unknown) — classify manually before the gate'
        }

        $rec.classification = $classification
        $rec.classification_basis = @($basis)
        $rec.enters_auth_migration = ($classification -eq 'retain')
        $rec
    }
    $records = @($records)

    $counts = [ordered]@{
        retain      = @($records | Where-Object { $_.classification -eq 'retain' }).Count
        consolidate = @($records | Where-Object { $_.classification -eq 'consolidate' }).Count
        retire      = @($records | Where-Object { $_.classification -eq 'retire' }).Count
        review      = @($records | Where-Object { $_.classification -eq 'review' }).Count
    }
    $coverage = [ordered]@{}
    foreach ($s in @('Spec3-D1.8', 'Spec1-D1.5', 'Find-DbaInstance')) {
        $coverage[$s] = @($records | Where-Object { $_.discovered_by -contains $s }).Count
    }
    $envelope = New-UIAOMigrationEnvelope -ArtifactType 'EstateInventory' -Records $records `
        -SourceRef "audit:$(Split-Path -Leaf $auditFull)" -DerivedFrom $derived `
        -ExtraData ([ordered]@{
            gate                = 'ADR-091 §1 retain/consolidate/retire'
            denominator         = $records.Count
            classification      = $counts
            source_coverage     = $coverage
            zombie_threshold_days = $ZombieThresholdDays
            consolidation_execution = 'review_required'
        })
    return (Write-UIAOEnvelopeOutput -Envelope $envelope -OutputPath $OutputPath)
}


# ===========================================================================
# Book 07 — Groups, AUs & the CA perimeter (ADR-067, ADR-036)
# ===========================================================================

function New-UIAOEntraGroupClassification {
    <#
    .SYNOPSIS
        Classify each exported Entra/AD group into exactly one of the ADR-067
        canonical group types and attach its transformation pattern (Book 07).
        Read-only derivation.
    .DESCRIPTION
        Resolves the Book 07 [to build] marker (classifier side). Consumes an
        Export-UIAOEntraGroups envelope (UIAOIdentityAssessment) and assigns each
        group exactly one ADR-067 type from its observable shape
        (groupTypes / mail_enabled / security_enabled / membership_rule):

          - orgtree_dynamic_group  — dynamic membership (a rule, or groupTypes
                                      contains DynamicMembership) → ADR-036.
          - mail_enabled_split     — mail-enabled security group → two-object
                                      pattern (M365 Group for mail + assigned
                                      security group for access, correlated by
                                      OrgPath).
          - distribution_m365_group— mail-only distribution list → M365 Group,
                                      securityEnabled:false (never access control).
          - assigned_security_group— security-only group → assigned Entra security
                                      group, flattened (record nesting in audit).
          - m365_unified           — already a Unified M365 group (no access action).
          - review                 — insufficient signal; classified manually.

        Each record carries the type, its target_state, the transformation, the
        provisioning adapter, and `becomes_sql_login` (the access-backing types a
        SQL login is created for in Book 05/07). Pure derivation — reads no live
        directory and writes nothing but the sealed classification.
    .PARAMETER GroupExportPath
        Path to an Export-UIAOEntraGroups envelope (.json) or a group list (.csv).
    .PARAMETER OutputPath
        Optional path for the sealed classification envelope JSON.
    .NOTES
        Canon: ADR-067, ADR-036, UIAO_135 §3.2. Book 07. Read-only derivation.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string]$GroupExportPath,
        [Parameter(Mandatory = $false)][string]$OutputPath
    )
    $full = Assert-UIAOInputPath -Path $GroupExportPath
    $data = Read-UIAOSourceData -Path $full
    # Export-UIAOEntraGroups is a sealed envelope (.data.records); a raw .csv is a
    # bare row set. Unwrap the envelope when present, else read the rows directly.
    $rows = if (($data.PSObject.Properties.Name -contains 'data') -and $data.data -and ($data.data.PSObject.Properties.Name -contains 'records')) {
        Get-UIAORows -Data $data.data.records
    }
    else {
        Get-UIAORows -Data $data -PreferredArrayKeys @('records', 'groups', 'Groups')
    }

    $records = foreach ($r in $rows) {
        $name = Get-UIAOFieldValue $r @('display_name', 'displayName', 'DisplayName', 'name', 'GroupName')
        if ([string]::IsNullOrWhiteSpace($name)) { continue }
        $mail = Get-UIAOFieldValue $r @('mail', 'Mail')
        $mailEnabled = ConvertTo-UIAOBool (Get-UIAOFieldValue $r @('mail_enabled', 'mailEnabled', 'MailEnabled'))
        $secEnabled = ConvertTo-UIAOBool (Get-UIAOFieldValue $r @('security_enabled', 'securityEnabled', 'SecurityEnabled'))
        $rule = Get-UIAOFieldValue $r @('membership_rule', 'membershipRule', 'MembershipRule')
        $gtJoined = ((Get-UIAOArrayProp -Row $r -Names @('groupTypes', 'GroupTypes', 'group_types')) | ForEach-Object { "$_" }) -join ','

        $type = 'review'; $target = $null; $transform = 'Insufficient signal (no groupTypes / mail / security flags) — classify manually.'; $adapter = 'n/a'
        $requiresSplit = $false; $flatten = $false; $dynamic = $false; $becomesLogin = $false
        if ($gtJoined -match '(?i)Unified') {
            $type = 'm365_unified'; $target = 'Microsoft 365 Group (already Unified)'
            $transform = 'No access-group action; governed via M365 Group lifecycle (mail/Teams/SharePoint).'
        }
        elseif ($rule -or ($gtJoined -match '(?i)Dynamic')) {
            $type = 'orgtree_dynamic_group'; $target = 'OrgTree-* dynamic group (ADR-036)'; $dynamic = $true; $becomesLogin = $true
            $transform = 'Provision via the entra-dynamic-groups adapter (UIAO_152); membership derives from the OrgPath rule.'
            $adapter = 'entra-dynamic-groups (UIAO_152)'
        }
        elseif ($mailEnabled -and $secEnabled) {
            $type = 'mail_enabled_split'; $target = 'Two-object: M365 Group (mail) + assigned security group (access), correlated by OrgPath'; $requiresSplit = $true; $becomesLogin = $true
            $transform = 'Split into a mail object and an access object; correlate via the OrgPath extension attribute (ADR-067).'
            $adapter = 'manual split + entra-dynamic-groups (UIAO_152)'
        }
        elseif ($mailEnabled) {
            $type = 'distribution_m365_group'; $target = 'Microsoft 365 Group, securityEnabled:false'
            $transform = 'Mail-only distribution surface; never used for access control (ADR-067).'
        }
        elseif ($secEnabled) {
            $type = 'assigned_security_group'; $target = 'Assigned Entra security group (flattened)'; $flatten = $true; $becomesLogin = $true
            $transform = 'Direct membership; flatten any nesting and record the transitive chain in the migration audit (ADR-067).'
            $adapter = 'entra-admin-units (UIAO_154) for DBA AU scoping'
        }

        [ordered]@{
            display_name       = $name
            group_type         = $type
            target_state       = $target
            transformation     = $transform
            provisioning_adapter = $adapter
            mail               = $mail
            security_enabled   = $secEnabled
            mail_enabled       = $mailEnabled
            dynamic            = $dynamic
            requires_split     = $requiresSplit
            flatten_required   = $flatten
            becomes_sql_login  = $becomesLogin
        }
    }
    $records = @($records)

    $typeCounts = [ordered]@{}
    foreach ($t in @('assigned_security_group', 'orgtree_dynamic_group', 'distribution_m365_group', 'mail_enabled_split', 'm365_unified', 'review')) {
        $typeCounts[$t] = @($records | Where-Object { $_.group_type -eq $t }).Count
    }
    $envelope = New-UIAOMigrationEnvelope -ArtifactType 'EntraGroupClassification' -Records $records `
        -SourceRef "group_export:$(Split-Path -Leaf $full)" `
        -DerivedFrom ([ordered]@{ source = 'UIAOIdentityAssessment.Export-UIAOEntraGroups'; source_file = (Split-Path -Leaf $full) }) `
        -ExtraData ([ordered]@{ taxonomy = 'ADR-067 four-type'; type_counts = $typeCounts; review_required = (@($records | Where-Object { $_.group_type -eq 'review' }).Count -gt 0) })
    return (Write-UIAOEnvelopeOutput -Envelope $envelope -OutputPath $OutputPath)
}

function New-UIAOGroupLoginScript {
    <#
    .SYNOPSIS
        Generate idempotent CREATE LOGIN ... FROM EXTERNAL PROVIDER T-SQL for the
        access-backing groups in an ADR-067 classification. DRY-RUN ONLY — writes
        a reviewable .sql file and opens no SQL connection (Book 07).
    .DESCRIPTION
        Resolves the Book 07 [to build] marker (group-login-emitter side). Consumes
        a New-UIAOEntraGroupClassification envelope and emits one idempotent
        `IF NOT EXISTS (...) CREATE LOGIN [<group>] FROM EXTERNAL PROVIDER;` per
        group whose ADR-067 type backs access (`becomes_sql_login` = true:
        assigned security, OrgTree dynamic, and the access side of a mail-enabled
        split). Mail-only distribution / Unified M365 groups and `review` groups
        are NOT emitted as runnable T-SQL — they appear only as commented-out
        lines so a mail group can never become a SQL login. The group name is
        bracket-quoted with embedded `]` doubled. Like Book 05's login emitter it
        never opens a SQL connection; the script is the deliverable.
    .PARAMETER ClassificationPath
        Path to a New-UIAOEntraGroupClassification envelope JSON.
    .PARAMETER OutputPath
        Path for the generated .sql script (recommended). When omitted the T-SQL
        is returned as a string.
    .NOTES
        Canon: ADR-067, ADR-091, UIAO_135 §3.2. Book 07. Generates a script;
        executes nothing — review-required before any change window.
    #>
    [CmdletBinding()]
    [OutputType([string])]
    param(
        [Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string]$ClassificationPath,
        [Parameter(Mandatory = $false)][string]$OutputPath
    )
    $full = Assert-UIAOInputPath -Path $ClassificationPath
    $env = Read-UIAOSourceData -Path $full
    $rows = Get-UIAORows -Data $env.data.records

    $lines = @()
    $lines += '-- Generated by UIAOSqlServerMigration (Book 07). DRY-RUN ARTIFACT — review before executing.'
    $lines += '-- Idempotent CREATE LOGIN ... FROM EXTERNAL PROVIDER for access-backing Entra groups (ADR-067).'
    $lines += "-- Source classification: $(Split-Path -Leaf $full)"
    $lines += '-- Group-based logins are the target: they remove per-user login churn (Book 07).'
    $lines += ''

    $emitted = 0; $skipped = 0
    foreach ($r in $rows) {
        $name = Get-UIAOFieldValue $r @('display_name', 'DisplayName', 'name')
        $type = Get-UIAOFieldValue $r @('group_type', 'GroupType')
        $isLogin = ConvertTo-UIAOBool (Get-UIAOFieldValue $r @('becomes_sql_login', 'BecomesSqlLogin'))
        if ([string]::IsNullOrWhiteSpace($name)) { continue }
        if (-not $isLogin) {
            $skipped++
            $lines += "-- skipped ($type): '$name' does not back SQL access — no login emitted."
            continue
        }
        $safe = $name.Replace(']', ']]')
        $lines += "IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE name = N'$($name.Replace("'", "''"))')"
        $lines += "    CREATE LOGIN [$safe] FROM EXTERNAL PROVIDER;"
        $lines += 'GO'
        $emitted++
    }
    $lines += ''
    $lines += "-- Summary: $emitted group login(s) generated, $skipped non-access group(s) skipped."
    $text = ($lines -join "`n") + "`n"

    Write-UIAOTextOutput -Text $text -OutputPath $OutputPath
    return $text
}


# ===========================================================================
# Book 08 — The application chain & connection-string migration (ADR-069)
# ===========================================================================

function New-UIAOAppConnectionPlan {
    <#
    .SYNOPSIS
        Correlate the Spec3-D1.9 LDAP-bind inventory with the Spec3-D1.8 SQL
        audit, classify each app by the ADR-069 four-class taxonomy, and emit the
        review-required connection-string migration plan (Book 08). Read-only
        derivation.
    .DESCRIPTION
        Resolves the Book 08 [to build] marker: the D1.9 <-> D1.8 correlation plus
        the ADR-069 class emitter. Consumes:

          -LdapBindInventoryPath  Spec3-D1.9 output — the LDAP-bind accounts and
                                  their source applications.
          -AuthAuditPath          Spec3-D1.8 output (optional) — to correlate a
                                  bind account to the SQL login(s) it maps to, so
                                  the plan names the exact instances affected.
          -CapabilityMap          optional app -> capability hashtable/JSON
                                  ({ oidc; saml; reverse_proxy; vendor_locked }),
                                  the observable signals ADR-069 classifies on.

        Each app is assigned exactly one ADR-069 class, preferring the cleanest
        end-state (OIDC > SAML > App Proxy > Domain Services):
          - Class 3 — OIDC                  (oidc/oauth capable)
          - Class 2 — SAML                  (SAML 2.0 capable)
          - Class 1 — Entra App Proxy       (legacy web app behind a reverse proxy)
          - Class 4 — Entra Domain Services (vendor-locked LDAP bind; carve-out)
          - review                          (no capability signal and no D1.9
                                            MigrationTarget — classified manually)

        For apps correlated to a SQL login the plan also emits the connection-
        string transformation that removes the stored credential — the last mile.
        Every record is mutating + requires_review; the function changes nothing.
    .PARAMETER LdapBindInventoryPath
        Path to a Spec3-D1.9 LDAP-bind inventory (.json or .csv).
    .PARAMETER AuthAuditPath
        Optional path to a Spec3-D1.8 SQL audit for the bind-account correlation.
    .PARAMETER CapabilityMap
        Optional: hashtable, or path to a JSON object, mapping app -> capabilities.
    .PARAMETER OutputPath
        Optional path for the sealed connection-plan envelope JSON.
    .NOTES
        Canon: ADR-069, ADR-051, ADR-004, UIAO_135 §3.2. Book 08. Read-only
        derivation; the connection-string change itself is review-required.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string]$LdapBindInventoryPath,
        [Parameter(Mandatory = $false)][string]$AuthAuditPath,
        [Parameter(Mandatory = $false)]$CapabilityMap,
        [Parameter(Mandatory = $false)][string]$OutputPath
    )
    $full = Assert-UIAOInputPath -Path $LdapBindInventoryPath
    $data = Read-UIAOSourceData -Path $full
    $rows = Get-UIAORows -Data $data -PreferredArrayKeys @('LDAPBindAccounts', 'ldapAccounts', 'records', 'accountGroups')

    # SQL-login lookup from the D1.8 audit (normalized account key -> [instances]).
    $sqlLoginKeys = @{}
    $auditRef = $null
    if (-not [string]::IsNullOrWhiteSpace($AuthAuditPath)) {
        $auditFull = Assert-UIAOInputPath -Path $AuthAuditPath
        $auditData = Read-UIAOSourceData -Path $auditFull
        $auditRef = "audit:$(Split-Path -Leaf $auditFull)"
        foreach ($inst in (Get-UIAORows -Data $auditData -PreferredArrayKeys @('InstanceAudits', 'records', 'Instances'))) {
            $server = Get-UIAOFieldValue $inst @('ServerName', 'server_name', 'ComputerName')
            $instLogins = @()
            foreach ($arr in @('WindowsLogins', 'SQLLogins', 'Logins')) { $instLogins += (Get-UIAOArrayProp -Row $inst -Names @($arr)) }
            foreach ($lg in $instLogins) {
                $ln = Get-UIAOFieldValue $lg @('LoginName', 'login_name', 'name', 'Name')
                $k = ConvertTo-UIAOMatchKey -Name $ln
                if (-not $k) { continue }
                if (-not $sqlLoginKeys.ContainsKey($k)) { $sqlLoginKeys[$k] = @() }
                if ($server -and -not ($sqlLoginKeys[$k] -contains $server)) { $sqlLoginKeys[$k] = @($sqlLoginKeys[$k] + $server) }
            }
        }
    }

    # Capability map (hashtable or JSON-object path) -> key lookup.
    $capLookup = @{}
    if ($CapabilityMap) {
        $cmObj = $CapabilityMap
        if ($CapabilityMap -is [string]) { $cmObj = Read-UIAOSourceData -Path (Assert-UIAOInputPath -Path $CapabilityMap) }
        if ($cmObj -is [System.Collections.IDictionary]) {
            foreach ($k in $cmObj.Keys) {
                $v = $cmObj[$k]
                # Normalize a nested hashtable to a PSCustomObject so Get-UIAOFieldValue
                # (which reads PSObject.Properties) can see its capability keys.
                if ($v -is [System.Collections.IDictionary]) { $v = [pscustomobject]$v }
                $capLookup[(ConvertTo-UIAOMatchKey -Name "$k")] = $v
            }
        }
        else {
            foreach ($p in $cmObj.PSObject.Properties) { $capLookup[(ConvertTo-UIAOMatchKey -Name $p.Name)] = $p.Value }
        }
    }

    $records = foreach ($r in $rows) {
        $app = Get-UIAOFieldValue $r @('SourceApplication', 'source_application', 'Application', 'AppName')
        $acct = Get-UIAOFieldValue $r @('AccountName', 'account_name', 'SamAccountName', 'sam_account_name')
        if ([string]::IsNullOrWhiteSpace($app) -and [string]::IsNullOrWhiteSpace($acct)) { continue }
        $bindType = Get-UIAOFieldValue $r @('BindType', 'bind_type')
        $migTarget = Get-UIAOFieldValue $r @('MigrationTarget', 'migration_target')

        # Capability signals.
        $capKey = ConvertTo-UIAOMatchKey -Name $app
        $cap = if ($capKey -and $capLookup.ContainsKey($capKey)) { $capLookup[$capKey] } else { $null }
        $oidc = $false; $saml = $false; $proxy = $false; $locked = $false
        if ($cap) {
            $oidc = ConvertTo-UIAOBool (Get-UIAOFieldValue $cap @('oidc', 'oauth', 'OIDC'))
            $saml = ConvertTo-UIAOBool (Get-UIAOFieldValue $cap @('saml', 'SAML'))
            $proxy = ConvertTo-UIAOBool (Get-UIAOFieldValue $cap @('reverse_proxy', 'app_proxy', 'proxy'))
            $locked = ConvertTo-UIAOBool (Get-UIAOFieldValue $cap @('vendor_locked', 'locked', 'unmigratable'))
        }

        $class = 'review'; $target = $null
        if ($oidc) { $class = 'Class 3 — OIDC'; $target = 'Entra OIDC application (Microsoft identity platform)' }
        elseif ($saml) { $class = 'Class 2 — SAML'; $target = 'Entra SAML SSO federation' }
        elseif ($proxy) { $class = 'Class 1 — App Proxy'; $target = 'Entra ID Application Proxy (modernized ingress, legacy app preserved)' }
        elseif ($locked) { $class = 'Class 4 — Entra Domain Services'; $target = 'Entra Domain Services (carve-out; on-prem AD trust not preserved)' }
        elseif ($migTarget) {
            switch -regex ($migTarget) {
                '(?i)oidc|oauth' { $class = 'Class 3 — OIDC'; $target = $migTarget; break }
                '(?i)saml' { $class = 'Class 2 — SAML'; $target = $migTarget; break }
                '(?i)proxy' { $class = 'Class 1 — App Proxy'; $target = $migTarget; break }
                '(?i)domain services|ds' { $class = 'Class 4 — Entra Domain Services'; $target = $migTarget; break }
                default { $class = 'review'; $target = $migTarget }
            }
        }

        # SQL correlation + connection-string transformation (the last mile).
        $k = ConvertTo-UIAOMatchKey -Name $acct
        $sqlInstances = @()
        if ($k -and $sqlLoginKeys.ContainsKey($k)) { $sqlInstances = @($sqlLoginKeys[$k]) }
        $connPattern = $null
        if ($sqlInstances.Count -gt 0) {
            $connPattern = 'Replace the stored SQL/Windows credential with Entra: set "Authentication=Active Directory Managed Identity" (service identity) or "Active Directory Default" (interactive), Encrypt=True; remove "User Id="/"Password=". Review-required.'
        }

        [ordered]@{
            source_application   = $app
            bind_account         = $acct
            bind_type            = $bindType
            ldap_class           = $class
            target_state         = $target
            correlated_sql_instances = $sqlInstances
            connection_string_pattern = $connPattern
            mutating             = $true
            requires_review      = $true
        }
    }
    $records = @($records)

    $classCounts = [ordered]@{}
    foreach ($c in @('Class 1 — App Proxy', 'Class 2 — SAML', 'Class 3 — OIDC', 'Class 4 — Entra Domain Services', 'review')) {
        $classCounts[$c] = @($records | Where-Object { $_.ldap_class -eq $c }).Count
    }
    $correlated = @($records | Where-Object { @($_.correlated_sql_instances).Count -gt 0 }).Count
    $envelope = New-UIAOMigrationEnvelope -ArtifactType 'AppConnectionPlan' -Records $records `
        -SourceRef "ldap_bind:$(Split-Path -Leaf $full)" `
        -DerivedFrom ([ordered]@{ source = 'Spec3-D1.9-Get-LDAPBindAccountInventory'; source_file = (Split-Path -Leaf $full); correlated_with = $auditRef }) `
        -ExtraData ([ordered]@{ taxonomy = 'ADR-069 four-class'; class_counts = $classCounts; sql_correlated_count = $correlated; preference_order = 'OIDC > SAML > App Proxy > Domain Services'; enforcement = 'none_by_default' })
    return (Write-UIAOEnvelopeOutput -Envelope $envelope -OutputPath $OutputPath)
}


# ===========================================================================
# Book 09 — Continuous monitoring & the CCM-BIR closure record (ADR-091 §5)
# ===========================================================================

function Get-UIAOInstanceLoginNames {
    # Collect the login names of a given type bucket from a D1.8 instance record.
    [CmdletBinding()]
    [OutputType([string[]])]
    param([Parameter(Mandatory = $true)]$Instance, [Parameter(Mandatory = $true)][string[]]$ArrayNames)
    $out = foreach ($lg in (Get-UIAOArrayProp -Row $Instance -Names $ArrayNames)) {
        $n = Get-UIAOFieldValue $lg @('LoginName', 'login_name', 'name', 'Name')
        if ($n) { $n }
    }
    # Unary comma so an empty result returns @() (not unrolled to $null) — the
    # caller relies on .Count.
    $arr = @($out | Sort-Object -Unique)
    return , $arr
}

function New-UIAOClosureRecord {
    <#
    .SYNOPSIS
        Project a Spec3-D1.8 audit run onto the ADR-091 §5 per-instance CCM-BIR
        closure field set and emit a closure record per instance (Book 09).
        Read-only derivation.
    .DESCRIPTION
        Resolves the Book 09 [to build] marker (ingestion side). Ingests one
        scheduled D1.8 deep-audit run and, per instance, evaluates the ADR-091 §5
        closure fields from the audit output:
          - Windows Authentication Only (LoginMode = 1 / AuthenticationMode).
          - zero active type-S (SQL-auth) logins outside the exception registry.
          - zero active type-W/G (Windows) logins.
          - sa disabled.
          - Arc agent enrolled/healthy and the SQL extension / Managed Identity
            active (EntraIDReady).

        Transformation #7 is closed for an instance when all evaluable §5 fields
        are satisfied. The MFA-via-Conditional-Access field is an external join
        (Entra sign-in logs) and is reported as `external` rather than asserted
        from the audit. An instance in the exception registry is marked
        `excepted` (its type-S exception is tolerated) but still tracked. Pure
        derivation over the read-only audit; emits evidence, changes nothing.
    .PARAMETER AuditPath
        Path to a Spec3-D1.8 deep-audit output (.json or .csv).
    .PARAMETER ExceptionRegistryPath
        Optional path to an exception registry (JSON array / object or CSV) whose
        entries name excepted instances (server\instance or server).
    .PARAMETER OutputPath
        Optional path for the sealed closure-record envelope JSON.
    .NOTES
        Canon: ADR-091 §5, ADR-068 Phase C, UIAO_135 Transformation #7. Book 09.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string]$AuditPath,
        [Parameter(Mandatory = $false)][string]$ExceptionRegistryPath,
        [Parameter(Mandatory = $false)][string]$OutputPath
    )
    $full = Assert-UIAOInputPath -Path $AuditPath
    $data = Read-UIAOSourceData -Path $full
    $rows = Get-UIAORows -Data $data -PreferredArrayKeys @('InstanceAudits', 'records', 'Instances')

    # Exception registry -> set of excepted instance keys.
    $excepted = @{}
    $excRef = $null
    if (-not [string]::IsNullOrWhiteSpace($ExceptionRegistryPath)) {
        $excFull = Assert-UIAOInputPath -Path $ExceptionRegistryPath
        $excData = Read-UIAOSourceData -Path $excFull
        $excRef = "exceptions:$(Split-Path -Leaf $excFull)"
        foreach ($e in (Get-UIAORows -Data $excData -PreferredArrayKeys @('records', 'exceptions', 'instances'))) {
            $srv = Get-UIAOFieldValue $e @('ServerName', 'server_name', 'instance', 'Instance', 'instance_key')
            $ins = Get-UIAOFieldValue $e @('InstanceName', 'instance_name')
            $key = if ($srv -and $srv.Contains('\')) { (Get-UIAOInstanceKey -Server $srv.Split('\')[0] -Instance $srv.Split('\')[1]) } else { (Get-UIAOInstanceKey -Server $srv -Instance $ins) }
            if ($key) { $excepted[$key] = $true }
        }
    }

    $records = foreach ($inst in $rows) {
        $server = Get-UIAOFieldValue $inst @('ServerName', 'server_name', 'ComputerName')
        $instance = Get-UIAOFieldValue $inst @('InstanceName', 'instance_name')
        $key = Get-UIAOInstanceKey -Server $server -Instance $instance
        $isExcepted = $excepted.ContainsKey($key)

        $authMode = Get-UIAOFieldValue $inst @('AuthenticationMode', 'authentication_mode', 'LoginMode')
        $windowsOnly = ($authMode -match '(?i)windows') -or ("$authMode".Trim() -eq '1')

        $sqlLogins = Get-UIAOInstanceLoginNames -Instance $inst -ArrayNames @('SQLLogins', 'sql_logins')
        $winLogins = Get-UIAOInstanceLoginNames -Instance $inst -ArrayNames @('WindowsLogins', 'windows_logins')
        # Scalar count overrides if the audit supplied them directly.
        $sqlCountRaw = Get-UIAOFieldValue $inst @('ActiveSqlLoginCount', 'active_sql_login_count')
        $winCountRaw = Get-UIAOFieldValue $inst @('ActiveWindowsLoginCount', 'active_windows_login_count')
        $sqlCount = if ($sqlCountRaw) { [int]$sqlCountRaw } else { $sqlLogins.Count }
        $winCount = if ($winCountRaw) { [int]$winCountRaw } else { $winLogins.Count }

        $saDisabled = ConvertTo-UIAOBool (Get-UIAOFieldValue $inst @('SaDisabled', 'sa_disabled'))
        $arcHealthy = ConvertTo-UIAOBool (Get-UIAOFieldValue $inst @('ArcConnected', 'arc_connected', 'ArcHealthy'))
        $entraReady = ConvertTo-UIAOBool (Get-UIAOFieldValue $inst @('EntraIDReady', 'entra_id_ready', 'EntraReady'))

        $fields = @(
            [ordered]@{ field = 'windows_auth_only'; satisfied = [bool]$windowsOnly; observed = $authMode }
            [ordered]@{ field = 'zero_active_type_s_outside_exception'; satisfied = (($sqlCount -eq 0) -or $isExcepted); observed = $sqlCount }
            [ordered]@{ field = 'zero_active_type_wg'; satisfied = ($winCount -eq 0); observed = $winCount }
            [ordered]@{ field = 'sa_disabled'; satisfied = [bool]$saDisabled; observed = $saDisabled }
            [ordered]@{ field = 'arc_enrolled_healthy'; satisfied = [bool]$arcHealthy; observed = $arcHealthy }
            [ordered]@{ field = 'managed_identity_active'; satisfied = [bool]$entraReady; observed = $entraReady }
        )
        $failing = @($fields | Where-Object { -not $_.satisfied } | ForEach-Object { $_.field })
        $verdict = if ($failing.Count -eq 0) { if ($isExcepted) { 'closed_excepted' } else { 'closed' } } else { 'open' }

        [ordered]@{
            instance_key   = $key
            server_name    = $server
            instance_name  = $instance
            excepted       = $isExcepted
            closure_fields = $fields
            failing_fields = $failing
            mfa_conditional_access = 'external'   # Entra sign-in log join (Step 2 note)
            verdict        = $verdict
        }
    }
    $records = @($records)

    $closed = @($records | Where-Object { $_.verdict -match '^closed' }).Count
    $open = @($records | Where-Object { $_.verdict -eq 'open' }).Count
    $envelope = New-UIAOMigrationEnvelope -ArtifactType 'CcmBirClosureRecord' -Records $records `
        -SourceRef "audit:$(Split-Path -Leaf $full)" `
        -DerivedFrom ([ordered]@{ source = 'Spec3-D1.8-Get-SQLServerAuthAudit'; source_file = (Split-Path -Leaf $full); exceptions = $excRef }) `
        -ExtraData ([ordered]@{ field_set = 'ADR-091 §5'; closed_count = $closed; open_count = $open; mfa_field = 'external join (Entra sign-in logs) — not asserted from the audit'; read_only = $true })
    return (Write-UIAOEnvelopeOutput -Envelope $envelope -OutputPath $OutputPath)
}

function Compare-UIAOClosureRun {
    <#
    .SYNOPSIS
        Diff two scheduled Spec3-D1.8 runs and emit the ADR-091 §5 drift events —
        each a compliance violation, not an advisory (Book 09). Read-only.
    .DESCRIPTION
        Resolves the Book 09 [to build] marker (diff side). Indexes a baseline and
        a current D1.8 run by instance and surfaces each ADR-091 §5 regression:
          - mixed_mode_enabled    — LoginMode 1 -> 2 (Windows-Only -> Mixed Mode).
          - new_sql_auth_login    — a type-S login present now but not in baseline.
          - new_windows_login     — a type-W/G login reintroduced on a previously
                                    Entra-only instance.
          - arc_agent_offline     — Arc/extension healthy in baseline, not now.
        Instances that appeared (a possible discovery gap) or disappeared are
        reported as informational events. Drift is detected mechanically at the
        next scheduled run; the function reads and reports only.
    .PARAMETER BaselinePath
        Path to the prior Spec3-D1.8 run (.json or .csv).
    .PARAMETER CurrentPath
        Path to the current Spec3-D1.8 run (.json or .csv).
    .PARAMETER OutputPath
        Optional path for the sealed drift-event envelope JSON.
    .NOTES
        Canon: ADR-091 §5, ADR-068 Phase C, UIAO_135 Transformation #7. Book 09.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string]$BaselinePath,
        [Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string]$CurrentPath,
        [Parameter(Mandatory = $false)][string]$OutputPath
    )
    function Read-Run {
        param([string]$Path)
        $full = Assert-UIAOInputPath -Path $Path
        $rows = Get-UIAORows -Data (Read-UIAOSourceData -Path $full) -PreferredArrayKeys @('InstanceAudits', 'records', 'Instances')
        $idx = @{}
        foreach ($inst in $rows) {
            $key = Get-UIAOInstanceKey -Server (Get-UIAOFieldValue $inst @('ServerName', 'server_name', 'ComputerName')) -Instance (Get-UIAOFieldValue $inst @('InstanceName', 'instance_name'))
            if (-not $key) { continue }
            $authMode = Get-UIAOFieldValue $inst @('AuthenticationMode', 'authentication_mode', 'LoginMode')
            $idx[$key] = [ordered]@{
                windows_only = ($authMode -match '(?i)windows') -or ("$authMode".Trim() -eq '1')
                sql_logins   = Get-UIAOInstanceLoginNames -Instance $inst -ArrayNames @('SQLLogins', 'sql_logins')
                win_logins   = Get-UIAOInstanceLoginNames -Instance $inst -ArrayNames @('WindowsLogins', 'windows_logins')
                arc_healthy  = ConvertTo-UIAOBool (Get-UIAOFieldValue $inst @('ArcConnected', 'arc_connected', 'EntraIDReady', 'entra_id_ready'))
            }
        }
        return @{ index = $idx; file = (Split-Path -Leaf $full) }
    }
    $base = Read-Run -Path $BaselinePath
    $curr = Read-Run -Path $CurrentPath

    $events = @()
    foreach ($key in ($curr.index.Keys | Sort-Object)) {
        $c = $curr.index[$key]
        if (-not $base.index.ContainsKey($key)) {
            $events += [ordered]@{ instance_key = $key; event = 'instance_appeared'; severity = 'info'; violation = $false; detail = 'present this run, absent in baseline — verify it was in the original audit scope (discovery gap)' }
            continue
        }
        $b = $base.index[$key]
        if ($b.windows_only -and -not $c.windows_only) {
            $events += [ordered]@{ instance_key = $key; event = 'mixed_mode_enabled'; severity = 'high'; violation = $true; detail = 'LoginMode 1 -> 2 (Windows-Only -> Mixed Mode) without authorization' }
        }
        $newSql = @($c.sql_logins | Where-Object { $_ -notin $b.sql_logins })
        foreach ($n in $newSql) {
            $events += [ordered]@{ instance_key = $key; event = 'new_sql_auth_login'; severity = 'high'; violation = $true; detail = "SQL-auth login created: $n" }
        }
        $newWin = @($c.win_logins | Where-Object { $_ -notin $b.win_logins })
        foreach ($n in $newWin) {
            $events += [ordered]@{ instance_key = $key; event = 'new_windows_login'; severity = 'medium'; violation = $true; detail = "Windows-backed login reintroduced: $n" }
        }
        if ($b.arc_healthy -and -not $c.arc_healthy) {
            $events += [ordered]@{ instance_key = $key; event = 'arc_agent_offline'; severity = 'high'; violation = $true; detail = 'Arc agent/extension healthy in baseline, not now — Managed-Identity engine auth interrupted' }
        }
    }
    foreach ($key in ($base.index.Keys | Sort-Object)) {
        if (-not $curr.index.ContainsKey($key)) {
            $events += [ordered]@{ instance_key = $key; event = 'instance_disappeared'; severity = 'info'; violation = $false; detail = 'present in baseline, absent this run — retired or unreachable; confirm intended' }
        }
    }
    $events = @($events)

    $violations = @($events | Where-Object { $_.violation }).Count
    $envelope = New-UIAOMigrationEnvelope -ArtifactType 'ClosureRunDiff' -Records $events `
        -SourceRef "current:$($curr.file)" `
        -DerivedFrom ([ordered]@{ source = 'Spec3-D1.8-Get-SQLServerAuthAudit'; baseline_file = $base.file; current_file = $curr.file }) `
        -ExtraData ([ordered]@{ drift_event_count = $events.Count; violation_count = $violations; compliance_violation = ($violations -gt 0); read_only = $true })
    return (Write-UIAOEnvelopeOutput -Envelope $envelope -OutputPath $OutputPath)
}


# ===========================================================================
# Book 10 — Certificate discovery for SQL Server's ADCS dependencies (UIAO_135 §3.3)
# ===========================================================================

function New-UIAOSqlCertificatePlan {
    <#
    .SYNOPSIS
        Extract SQL Server's three ADCS dependencies from a Spec3-D1.10 audit and
        sequence the dependency-ordered CA-replacement (CBA-issuance) bridge
        (Book 10). Read-only, analytical derivation.
    .DESCRIPTION
        Resolves the Book 10 [to build] marker: the SQL-specific certificate
        extraction and the CBA-issuance bridge. Consumes a Spec3-D1.10
        certificate audit and isolates the three dependencies SQL Server has on
        ADCS:
          - tls_server_cert         — the TLS server certificate that encrypts
                                      SQL connections (scoped to SQL hosts via
                                      -SqlHostFilter when supplied).
          - certificate_mapped_login— a login mapped to a certificate / smart card.
          - cba_posture             — certificate-based auth as the NTLM-
                                      replacement posture (CBA readiness / required).

        It then derives the CA-replacement order from the enterprise CA hierarchy
        (roots before issuing CAs), the same dependency-ordering New-UIAOPKIMigrationPlan
        applies — so the replacement CA is stood up and trusted before any ADCS
        decommission date is set. Analytical only: there is no normative ADCS-
        migration ADR, so every record is requires_review and the function changes
        nothing.
    .PARAMETER CertAuditPath
        Path to a Spec3-D1.10 certificate-based-auth audit (.json or .csv).
    .PARAMETER SqlHostFilter
        Optional regex/substring to scope server-cert dependencies to SQL hosts
        (matched against the certificate subject/host). When omitted, all server-
        auth certificates are surfaced.
    .PARAMETER OutputPath
        Optional path for the sealed certificate-plan envelope JSON.
    .NOTES
        Canon: UIAO_135 §3.3, ADR-068. Book 10. Read-only, analytical — no
        normative ADCS-migration ADR exists; every action is review-required.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string]$CertAuditPath,
        [Parameter(Mandatory = $false)][string]$SqlHostFilter,
        [Parameter(Mandatory = $false)][string]$OutputPath
    )
    $full = Assert-UIAOInputPath -Path $CertAuditPath
    $audit = Read-UIAOSourceData -Path $full

    $certs = @(Get-UIAOArrayProp -Row $audit -Names @('Certificates', 'certificates'))
    if ($certs.Count -eq 0) { $certs = @(Get-UIAORows -Data $audit -PreferredArrayKeys @('Certificates', 'certificates', 'records')) }

    $records = foreach ($c in $certs) {
        $subject = Get-UIAOFieldValue $c @('Subject', 'subject', 'CertificateDN', 'SubjectName')
        $issuer = Get-UIAOFieldValue $c @('Issuer', 'issuer')
        $authType = Get-UIAOFieldValue $c @('AuthenticationType', 'authentication_type')
        $isExpired = ConvertTo-UIAOBool (Get-UIAOFieldValue $c @('IsExpired', 'is_expired', 'HasExpiredCerts'))
        $daysToExpiry = Get-UIAOFieldValue $c @('DaysToExpiry', 'days_to_expiry')
        $smartCard = ConvertTo-UIAOBool (Get-UIAOFieldValue $c @('IsSmartCard', 'SmartCardCapable', 'HasSmartCardLogon'))
        $certBased = ConvertTo-UIAOBool (Get-UIAOFieldValue $c @('CertBasedAuth', 'cert_based_auth'))

        # SQL-host scoping for the server-cert (TLS) dependency.
        $matchesSql = $true
        if (-not [string]::IsNullOrWhiteSpace($SqlHostFilter)) {
            $matchesSql = ("$subject" -match [regex]::Escape($SqlHostFilter)) -or ("$subject" -imatch $SqlHostFilter)
        }

        $dep = $null
        if ($smartCard -or $certBased -or ("$authType" -match '(?i)cert|smart')) {
            $dep = 'certificate_mapped_login'
        }
        elseif ($matchesSql -and ("$authType" -match '(?i)server|tls|ssl' -or [string]::IsNullOrWhiteSpace($authType))) {
            $dep = 'tls_server_cert'
        }
        if (-not $dep) { continue }   # cert not relevant to SQL's three dependencies

        [ordered]@{
            dependency_class = $dep
            subject          = $subject
            issuer           = $issuer
            is_expired       = $isExpired
            days_to_expiry   = $daysToExpiry
            replacement_action = if ($dep -eq 'certificate_mapped_login') { 'Re-issue from the replacement CA; bridge cert-mapped login to Entra CBA where it is the NTLM-replacement posture (review-required).' } else { 'Re-issue the SQL TLS server certificate from the replacement CA before any ADCS decommission date.' }
            requires_review  = $true
        }
    }
    $records = @($records)

    # CBA posture (environment-level NTLM-replacement readiness).
    $cbaRequired = ConvertTo-UIAOBool (Get-UIAOFieldValue $audit @('CBARequired', 'cba_required', 'EntraIDCBARequired'))
    $cbaReadiness = Get-UIAOFieldValue $audit @('CBAReadiness', 'cba_readiness')
    if ($cbaRequired -or $cbaReadiness) {
        $records = @($records + [ordered]@{
                dependency_class = 'cba_posture'
                subject          = '<environment>'
                issuer           = $null
                is_expired       = $false
                days_to_expiry   = $null
                replacement_action = "CBA is the NTLM-replacement posture (readiness: $cbaReadiness). Stand up Entra CBA issuance on the replacement CA before retiring NTLM (ADR-068)."
                requires_review  = $true
            })
    }

    # Dependency-ordered CA-replacement sequence: roots before issuing CAs.
    function Get-CaNames {
        param($Items)
        $names = @($Items | ForEach-Object { if ($_ -is [string]) { $_ } else { "$(Get-UIAOFieldValue $_ @('CAName', 'ca_name', 'Name'))" } } | Where-Object { $_ })
        return , $names
    }
    $roots = Get-CaNames (Get-UIAOArrayProp -Row $audit -Names @('EnterpriseRootCAs', 'enterprise_root_cas'))
    $subs = Get-CaNames (Get-UIAOArrayProp -Row $audit -Names @('EnterpriseSubCAs', 'enterprise_sub_cas'))
    if ($roots.Count -eq 0 -and $subs.Count -eq 0) {
        # Fall back to a flat EnterpriseCAs list (order preserved, roots assumed first by the audit).
        $roots = Get-CaNames (Get-UIAOArrayProp -Row $audit -Names @('EnterpriseCAs', 'enterprise_cas'))
    }
    $sequence = @()
    $order = 1
    foreach ($r in $roots) { $sequence += [ordered]@{ order = $order; ca = $r; tier = 'root'; action = 'replace/trust first (parent of issuing CAs)' }; $order++ }
    foreach ($s in $subs) { $sequence += [ordered]@{ order = $order; ca = $s; tier = 'issuing'; action = 'replace after its root is trusted' }; $order++ }

    $depCounts = [ordered]@{}
    foreach ($d in @('tls_server_cert', 'certificate_mapped_login', 'cba_posture')) {
        $depCounts[$d] = @($records | Where-Object { $_.dependency_class -eq $d }).Count
    }
    $envelope = New-UIAOMigrationEnvelope -ArtifactType 'SqlCertificatePlan' -Records $records `
        -SourceRef "cert_audit:$(Split-Path -Leaf $full)" `
        -DerivedFrom ([ordered]@{ source = 'Spec3-D1.10-Get-CertBasedAuthAudit'; source_file = (Split-Path -Leaf $full) }) `
        -ExtraData ([ordered]@{
            dependency_counts     = $depCounts
            ca_replacement_sequence = $sequence
            analytical            = $true
            normative_adr         = 'none (no ADCS-migration ADR) — plan is review-required'
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
    'Get-UIAONtlmGpoReport', `
    'New-UIAOEstateInventory', `
    'New-UIAOEntraGroupClassification', `
    'New-UIAOGroupLoginScript', `
    'New-UIAOAppConnectionPlan', `
    'New-UIAOClosureRecord', `
    'Compare-UIAOClosureRun', `
    'New-UIAOSqlCertificatePlan'
