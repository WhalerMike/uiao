# UIAOImportAdapters — assessment-to-plan toolchain PRODUCER (ADR-094, UIAO_182).
#
# Ingestion adapters that normalize heterogeneous third-party assessment
# exports into one canonical UIAO assessment shape, so downstream
# correlation / drift detection / plan generation (UIAOPlanGenerators,
# UIAO_183) operate over a single schema rather than vendor formats.
#
# Design invariants (ADR-094 §Decision 4, UIAO_182 §Non-functional contract):
#   * Read-only, file-based. No live tenant/API reads (that is
#     UIAOIdentityAssessment, UIAO_181). Every function consumes a
#     pre-produced report file and emits a normalized JSON artifact.
#   * Every artifact carries a provenance envelope { source, timestamp,
#     version, content_hash } so it is canon-anchored evidence and a
#     DRIFT-PROVENANCE finding when its seal breaks (UIAO_150 §Principle 2,
#     src/uiao/governance/drift.py::classify_provenance_drift).
#   * content_hash is the SHA-256 of the *canonical JSON* of the artifact's
#     `data` object, byte-for-byte identical to
#     src/uiao/ir/models/core.py::canonical_hash (sorted keys, (',',':')
#     separators, ensure_ascii=False, UTF-8). It is reimplemented natively
#     here so the module stays offline and self-contained (no Python at
#     runtime); tests/ pin the equivalence against Python-computed hashes.
#
# Authored per the OrgPathTools / OrgTreeValidation pattern: .psd1 + .psm1
# + Pester tests. Authenticode signing is a maintainer release step (see
# README.md) — SI-7 / SA-10.

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Script:ArtifactSchemaVersion = 'v1'

# ─────────────────────────────────────────────────────────────────────────
# Canonical JSON + content hash (mirror of src/uiao/ir/models/core.py)
# ─────────────────────────────────────────────────────────────────────────

function ConvertTo-UIAOCanonicalJson {
    <#
    .SYNOPSIS
        Serialize an object to canonical JSON identical to Python's
        json.dumps(sort_keys=True, separators=(',',':'), ensure_ascii=False).
    .DESCRIPTION
        Object keys are sorted by ordinal (code-point) order; no insignificant
        whitespace; non-ASCII characters are emitted raw (UTF-8), matching
        ensure_ascii=False. Handles hashtables / ordered dictionaries /
        PSCustomObject (objects), arrays/lists, strings, integers, booleans,
        and null. This is the offline equivalent of canonical_json() in
        src/uiao/ir/models/core.py — keep the two in lockstep.
    #>
    [CmdletBinding()]
    [OutputType([string])]
    param(
        [Parameter(Mandatory = $false, Position = 0)]
        [AllowNull()]
        $InputObject
    )

    if ($null -eq $InputObject) { return 'null' }

    # Booleans before numerics (a [bool] must not fall through to integer).
    if ($InputObject -is [bool]) { return $(if ($InputObject) { 'true' } else { 'false' }) }

    if ($InputObject -is [string]) { return (ConvertTo-UIAOJsonString $InputObject) }

    if ($InputObject -is [int] -or $InputObject -is [long] -or $InputObject -is [int16] -or
        $InputObject -is [byte] -or $InputObject -is [uint32] -or $InputObject -is [uint64]) {
        return [string][long]$InputObject
    }

    if ($InputObject -is [double] -or $InputObject -is [single] -or $InputObject -is [decimal]) {
        $d = [double]$InputObject
        if ([double]::IsNaN($d) -or [double]::IsInfinity($d)) {
            throw "Non-finite number cannot be canonicalized: $d"
        }
        # Whole-valued floats serialize as integers (assessment counts/scores).
        if ([math]::Truncate($d) -eq $d -and [math]::Abs($d) -lt 1e15) {
            return [string][long]$d
        }
        return $d.ToString('R', [System.Globalization.CultureInfo]::InvariantCulture)
    }

    if ($InputObject -is [System.Collections.IDictionary]) {
        $keys = @($InputObject.Keys | ForEach-Object { [string]$_ })
        $arr = [string[]]$keys
        [System.Array]::Sort($arr, [System.StringComparer]::Ordinal)
        $parts = foreach ($k in $arr) {
            (ConvertTo-UIAOJsonString $k) + ':' + (ConvertTo-UIAOCanonicalJson $InputObject[$k])
        }
        return '{' + ($parts -join ',') + '}'
    }

    if ($InputObject -is [System.Management.Automation.PSCustomObject]) {
        $names = @($InputObject.PSObject.Properties.Name | ForEach-Object { [string]$_ })
        $arr = [string[]]$names
        [System.Array]::Sort($arr, [System.StringComparer]::Ordinal)
        $parts = foreach ($k in $arr) {
            (ConvertTo-UIAOJsonString $k) + ':' + (ConvertTo-UIAOCanonicalJson $InputObject.$k)
        }
        return '{' + ($parts -join ',') + '}'
    }

    # Enumerables (arrays/lists) — strings already handled above.
    if ($InputObject -is [System.Collections.IEnumerable]) {
        $parts = foreach ($item in $InputObject) { ConvertTo-UIAOCanonicalJson $item }
        return '[' + ($parts -join ',') + ']'
    }

    # Fallback: treat as string.
    return (ConvertTo-UIAOJsonString ([string]$InputObject))
}

function ConvertTo-UIAOJsonString {
    <#
    .SYNOPSIS
        JSON-escape a string exactly as Python json.dumps(ensure_ascii=False).
    .DESCRIPTION
        Escapes " and \ and the short control forms (\b \f \n \r \t); other
        control characters below U+0020 become \u00XX (lowercase). All other
        characters, including non-ASCII, are emitted raw.
    #>
    [CmdletBinding()]
    [OutputType([string])]
    param([Parameter(Mandatory = $true)][AllowEmptyString()][string]$Value)

    $sb = [System.Text.StringBuilder]::new($Value.Length + 2)
    [void]$sb.Append('"')
    foreach ($ch in $Value.ToCharArray()) {
        $code = [int]$ch
        switch ($ch) {
            '"' { [void]$sb.Append('\"'); continue }
            '\' { [void]$sb.Append('\\'); continue }
            "`b" { [void]$sb.Append('\b'); continue }
            "`f" { [void]$sb.Append('\f'); continue }
            "`n" { [void]$sb.Append('\n'); continue }
            "`r" { [void]$sb.Append('\r'); continue }
            "`t" { [void]$sb.Append('\t'); continue }
            default {
                if ($code -lt 0x20) {
                    [void]$sb.Append('\u')
                    [void]$sb.Append($code.ToString('x4', [System.Globalization.CultureInfo]::InvariantCulture))
                }
                else {
                    [void]$sb.Append($ch)
                }
            }
        }
    }
    [void]$sb.Append('"')
    return $sb.ToString()
}

function Get-UIAOContentHash {
    <#
    .SYNOPSIS
        SHA-256 hex of the canonical JSON of an object.
    .DESCRIPTION
        Equivalent to src/uiao/ir/models/core.py::canonical_hash. Use on the
        artifact `data` object so the seal matches the hash the Python
        DRIFT-PROVENANCE classifier recomputes from actual_state.
    .EXAMPLE
        Get-UIAOContentHash @{ b = 2; a = 1 }
    #>
    [CmdletBinding()]
    [OutputType([string])]
    param(
        [Parameter(Mandatory = $true, Position = 0)]
        [AllowNull()]
        $Data
    )
    $json = ConvertTo-UIAOCanonicalJson $Data
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($json)
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $hash = $sha.ComputeHash($bytes)
    }
    finally {
        $sha.Dispose()
    }
    return -join ($hash | ForEach-Object { $_.ToString('x2') })
}

# ─────────────────────────────────────────────────────────────────────────
# Provenance envelope + artifact wrapper
# ─────────────────────────────────────────────────────────────────────────

function New-UIAOAssessmentArtifact {
    <#
    .SYNOPSIS
        Wrap a normalized data object in a UIAO assessment artifact with a
        provenance envelope and content-hash seal.
    .PARAMETER Target
        Normalized target schema name (e.g. 'ComputerInventory').
    .PARAMETER Data
        The normalized data object (hashtable / array).
    .PARAMETER SourceTool
        Provenance source — the originating assessment tool.
    .PARAMETER SourceVersion
        Provenance version — the source tool / export version.
    .PARAMETER Timestamp
        ISO-8601 UTC import timestamp. Defaults to now; pass an explicit
        value for deterministic output (tests, reproducible runs).
    .PARAMETER Actor
        Optional actor attribution (defaults to the calling function).
    #>
    [CmdletBinding()]
    [OutputType([System.Collections.Specialized.OrderedDictionary])]
    param(
        [Parameter(Mandatory = $true)][string]$Target,
        [Parameter(Mandatory = $true)][AllowNull()]$Data,
        [Parameter(Mandatory = $true)][string]$SourceTool,
        [Parameter(Mandatory = $true)][string]$SourceVersion,
        [Parameter(Mandatory = $false)][string]$Timestamp,
        [Parameter(Mandatory = $false)][string]$Actor
    )
    $ts = if ($Timestamp) { $Timestamp } else { [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ") }
    $provenance = [ordered]@{
        source       = $SourceTool
        timestamp    = $ts
        version      = $SourceVersion
        content_hash = (Get-UIAOContentHash $Data)
    }
    if ($Actor) { $provenance['actor'] = $Actor }

    return [ordered]@{
        schema     = "uiao.assessment/$Target/$Script:ArtifactSchemaVersion"
        provenance = $provenance
        data       = $Data
    }
}

function Write-UIAOArtifact {
    <#
    .SYNOPSIS
        Internal: serialize an artifact to canonical JSON (UTF-8, no BOM).
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]$Artifact,
        [Parameter(Mandatory = $true)][string]$OutputPath
    )
    $json = ConvertTo-UIAOCanonicalJson $Artifact
    $dir = Split-Path -Parent $OutputPath
    if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    [System.IO.File]::WriteAllText($OutputPath, $json, [System.Text.UTF8Encoding]::new($false))
}

function Read-UIAOReport {
    <#
    .SYNOPSIS
        Internal: read a report file as objects. .json -> ConvertFrom-Json;
        .csv -> Import-Csv. Returns the parsed content.
    #>
    [CmdletBinding()]
    param([Parameter(Mandatory = $true)][string]$ReportPath)
    if (-not (Test-Path -LiteralPath $ReportPath)) {
        throw "Report not found: $ReportPath"
    }
    $ext = [System.IO.Path]::GetExtension($ReportPath).ToLowerInvariant()
    switch ($ext) {
        '.json' { return (Get-Content -LiteralPath $ReportPath -Raw -Encoding UTF8 | ConvertFrom-Json) }
        '.csv' { return (Import-Csv -LiteralPath $ReportPath) }
        default { throw "Unsupported report extension '$ext' (expected .json or .csv): $ReportPath" }
    }
}

function Get-UIAOField {
    <#
    .SYNOPSIS
        Internal: first non-empty property among candidate names on a record.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]$Record,
        [Parameter(Mandatory = $true)][string[]]$Names,
        [Parameter(Mandatory = $false)]$Default = ''
    )
    foreach ($n in $Names) {
        $prop = $Record.PSObject.Properties[$n]
        if ($prop -and $null -ne $prop.Value -and "$($prop.Value)".Trim() -ne '') {
            return $prop.Value
        }
    }
    return $Default
}

function Resolve-UIAORecords {
    <#
    .SYNOPSIS
        Internal: coerce parsed report content into an array of records.
        A JSON object with a single array property unwraps to that array;
        a bare array stays as-is; a single object becomes a one-element array.
    #>
    [CmdletBinding()]
    param([Parameter(Mandatory = $true)][AllowNull()]$Content, [string[]]$PreferKeys)
    if ($null -eq $Content) { return @() }
    if ($Content -is [System.Collections.IEnumerable] -and $Content -isnot [string] -and
        $Content -isnot [System.Management.Automation.PSCustomObject]) {
        return @($Content)
    }
    if ($Content -is [System.Management.Automation.PSCustomObject]) {
        foreach ($k in $PreferKeys) {
            $p = $Content.PSObject.Properties[$k]
            if ($p -and $p.Value -is [System.Collections.IEnumerable] -and $p.Value -isnot [string]) {
                return @($p.Value)
            }
        }
        # Fall back to the first array-valued property.
        foreach ($p in $Content.PSObject.Properties) {
            if ($p.Value -is [System.Collections.IEnumerable] -and $p.Value -isnot [string]) {
                return @($p.Value)
            }
        }
        return @($Content)
    }
    return @($Content)
}

# ─────────────────────────────────────────────────────────────────────────
# Producer functions (UIAO_182 §Function roster)
# ─────────────────────────────────────────────────────────────────────────

function Import-UIAOAzureMigrateReport {
    <#
    .SYNOPSIS
        Normalize an Azure Migrate assessment export into a UIAO
        ComputerInventory artifact.
    .DESCRIPTION
        Read-only. Accepts an Azure Migrate machines export as JSON (array
        or { machines: [...] }) or CSV. Maps common machine fields onto the
        canonical ComputerInventory shape: { computers: [ { name, fqdn, os,
        cores, memoryMB, ipAddresses[], source } ], count }.
    .PARAMETER ReportPath
        Path to the Azure Migrate export (.json or .csv).
    .PARAMETER OutputPath
        Optional path to write the normalized artifact (canonical JSON).
    .PARAMETER SourceVersion
        Export/tool version recorded in provenance (default 'unknown').
    .PARAMETER Timestamp
        Optional ISO-8601 UTC timestamp for deterministic output.
    .EXAMPLE
        Import-UIAOAzureMigrateReport -ReportPath .\migrate.json -OutputPath .\computers.json
    #>
    [CmdletBinding()]
    [OutputType([System.Collections.Specialized.OrderedDictionary])]
    param(
        [Parameter(Mandatory = $true)][string]$ReportPath,
        [Parameter(Mandatory = $false)][string]$OutputPath,
        [Parameter(Mandatory = $false)][string]$SourceVersion = 'unknown',
        [Parameter(Mandatory = $false)][string]$Timestamp
    )
    $records = Resolve-UIAORecords (Read-UIAOReport $ReportPath) -PreferKeys @('machines', 'value', 'Machines')
    $computers = foreach ($r in $records) {
        $ips = Get-UIAOField $r @('IPAddresses', 'ipAddresses', 'IPAddress', 'PrivateIPAddress') ''
        # @(...) around the whole if guarantees an array even for a single
        # element — PowerShell unwraps a 1-element array out of an if-expression.
        $ipList = @(
            if ($ips -is [System.Collections.IEnumerable] -and $ips -isnot [string]) {
                $ips | ForEach-Object { [string]$_ }
            }
            elseif ("$ips".Trim()) {
                "$ips".Split(@(';', ','), [StringSplitOptions]::RemoveEmptyEntries) | ForEach-Object { $_.Trim() }
            }
        )
        [ordered]@{
            name         = [string](Get-UIAOField $r @('MachineName', 'ServerName', 'DisplayName', 'Name', 'ComputerName'))
            fqdn         = [string](Get-UIAOField $r @('FQDN', 'Fqdn', 'FullyQualifiedDomainName'))
            os           = [string](Get-UIAOField $r @('OperatingSystem', 'OSName', 'OS'))
            cores        = [long](Get-UIAOField $r @('Cores', 'NumberOfCores', 'vCPUs') 0)
            memoryMB     = [long](Get-UIAOField $r @('MemoryInMB', 'MemoryMB', 'MemoryInMb') 0)
            ipAddresses  = $ipList
            source       = 'AzureMigrate'
        }
    }
    $computers = @($computers)
    $data = [ordered]@{ computers = $computers; count = $computers.Count }
    $artifact = New-UIAOAssessmentArtifact -Target 'ComputerInventory' -Data $data `
        -SourceTool 'Azure Migrate' -SourceVersion $SourceVersion -Timestamp $Timestamp `
        -Actor 'UIAOImportAdapters/Import-UIAOAzureMigrateReport'
    if ($OutputPath) { Write-UIAOArtifact -Artifact $artifact -OutputPath $OutputPath }
    return $artifact
}

function Import-UIAOGPOAnalyticsReport {
    <#
    .SYNOPSIS
        Normalize an Intune Group Policy Analytics export into a UIAO
        GPOMigrationTracker artifact.
    .DESCRIPTION
        Read-only. Accepts a GPO Analytics export (JSON array / { value: [...] }
        or CSV). Maps to { gpos: [ { name, id, status, mdmSupportPercent,
        unsupportedSettings, source } ], count }.
    .PARAMETER ReportPath
        Path to the GPO Analytics export (.json or .csv).
    .PARAMETER OutputPath
        Optional path to write the normalized artifact.
    .PARAMETER SourceVersion
        Export/tool version recorded in provenance.
    .PARAMETER Timestamp
        Optional ISO-8601 UTC timestamp for deterministic output.
    #>
    [CmdletBinding()]
    [OutputType([System.Collections.Specialized.OrderedDictionary])]
    param(
        [Parameter(Mandatory = $true)][string]$ReportPath,
        [Parameter(Mandatory = $false)][string]$OutputPath,
        [Parameter(Mandatory = $false)][string]$SourceVersion = 'unknown',
        [Parameter(Mandatory = $false)][string]$Timestamp
    )
    $records = Resolve-UIAORecords (Read-UIAOReport $ReportPath) -PreferKeys @('gpos', 'value', 'groupPolicyObjects')
    $gpos = foreach ($r in $records) {
        $supported = [long](Get-UIAOField $r @('supportedSettings', 'SupportedSettings', 'mdmSupported') 0)
        $total = [long](Get-UIAOField $r @('totalSettings', 'TotalSettings', 'settingsCount') 0)
        $pct = if ($total -gt 0) { [long][math]::Round(100.0 * $supported / $total) } else { 0 }
        [ordered]@{
            name                = [string](Get-UIAOField $r @('groupPolicyName', 'DisplayName', 'Name', 'GPOName'))
            id                  = [string](Get-UIAOField $r @('groupPolicyObjectId', 'Id', 'GUID', 'GPOGuid'))
            status              = [string](Get-UIAOField $r @('migrationReadiness', 'Status', 'State') 'unassessed')
            mdmSupportPercent   = $pct
            unsupportedSettings = [long](Get-UIAOField $r @('unsupportedSettings', 'UnsupportedSettings') 0)
            source              = 'GPOAnalytics'
        }
    }
    $gpos = @($gpos)
    $data = [ordered]@{ gpos = $gpos; count = $gpos.Count }
    $artifact = New-UIAOAssessmentArtifact -Target 'GPOMigrationTracker' -Data $data `
        -SourceTool 'Intune Group Policy Analytics' -SourceVersion $SourceVersion -Timestamp $Timestamp `
        -Actor 'UIAOImportAdapters/Import-UIAOGPOAnalyticsReport'
    if ($OutputPath) { Write-UIAOArtifact -Artifact $artifact -OutputPath $OutputPath }
    return $artifact
}

function Import-UIAODefenderFindings {
    <#
    .SYNOPSIS
        Normalize a Defender for Identity / Secure Score export into a UIAO
        SecurityAssessment overlay artifact.
    .DESCRIPTION
        Read-only. Accepts a findings/secure-score export (JSON array /
        { findings: [...] } or CSV). Maps to { findings: [ { id, title,
        severity, category, recommendation, source } ], score, count }.
    .PARAMETER ReportPath
        Path to the Defender export (.json or .csv).
    .PARAMETER OutputPath
        Optional path to write the normalized artifact.
    .PARAMETER SourceVersion
        Export/tool version recorded in provenance.
    .PARAMETER Timestamp
        Optional ISO-8601 UTC timestamp for deterministic output.
    #>
    [CmdletBinding()]
    [OutputType([System.Collections.Specialized.OrderedDictionary])]
    param(
        [Parameter(Mandatory = $true)][string]$ReportPath,
        [Parameter(Mandatory = $false)][string]$OutputPath,
        [Parameter(Mandatory = $false)][string]$SourceVersion = 'unknown',
        [Parameter(Mandatory = $false)][string]$Timestamp
    )
    $content = Read-UIAOReport $ReportPath
    $records = Resolve-UIAORecords $content -PreferKeys @('findings', 'value', 'recommendations')
    $findings = foreach ($r in $records) {
        [ordered]@{
            id             = [string](Get-UIAOField $r @('id', 'Id', 'findingId', 'controlName'))
            title          = [string](Get-UIAOField $r @('title', 'Title', 'displayName', 'name'))
            severity       = ([string](Get-UIAOField $r @('severity', 'Severity', 'risk') 'unknown')).ToLowerInvariant()
            category       = [string](Get-UIAOField $r @('category', 'Category', 'controlCategory') 'general')
            recommendation = [string](Get-UIAOField $r @('recommendation', 'Recommendation', 'remediation'))
            source         = 'DefenderForIdentity'
        }
    }
    $findings = @($findings)
    $scoreVal = 0
    if ($content -is [System.Management.Automation.PSCustomObject]) {
        $scoreVal = [long](Get-UIAOField $content @('secureScore', 'currentScore', 'score') 0)
    }
    $data = [ordered]@{ findings = $findings; score = $scoreVal; count = $findings.Count }
    $artifact = New-UIAOAssessmentArtifact -Target 'SecurityAssessment' -Data $data `
        -SourceTool 'Microsoft Defender for Identity' -SourceVersion $SourceVersion -Timestamp $Timestamp `
        -Actor 'UIAOImportAdapters/Import-UIAODefenderFindings'
    if ($OutputPath) { Write-UIAOArtifact -Artifact $artifact -OutputPath $OutputPath }
    return $artifact
}

function Import-UIAOSCuBAReport {
    <#
    .SYNOPSIS
        Normalize a CISA ScubaGear compliance export into UIAO conformance
        evidence.
    .DESCRIPTION
        Read-only. Accepts ScubaGear output as JSON. Supports both a combined
        results object with a Results/TestResults array and a flat array of
        policy results. Maps to { policies: [ { policyId, control, result,
        product, requirement, source } ], summary { pass, fail, warn }, count }.
        RequirementMet is interpreted per UIAO_002 §4.6: Pass/true -> pass,
        Warning -> warn, else fail.
    .PARAMETER ReportPath
        Path to the ScubaGear export (.json).
    .PARAMETER OutputPath
        Optional path to write the normalized artifact.
    .PARAMETER SourceVersion
        ScubaGear version recorded in provenance.
    .PARAMETER Timestamp
        Optional ISO-8601 UTC timestamp for deterministic output.
    #>
    [CmdletBinding()]
    [OutputType([System.Collections.Specialized.OrderedDictionary])]
    param(
        [Parameter(Mandatory = $true)][string]$ReportPath,
        [Parameter(Mandatory = $false)][string]$OutputPath,
        [Parameter(Mandatory = $false)][string]$SourceVersion = 'unknown',
        [Parameter(Mandatory = $false)][string]$Timestamp
    )
    $records = Resolve-UIAORecords (Read-UIAOReport $ReportPath) -PreferKeys @('Results', 'TestResults', 'results', 'policies')
    $pass = 0; $fail = 0; $warn = 0
    $policies = foreach ($r in $records) {
        $raw = "$(Get-UIAOField $r @('RequirementMet', 'Result', 'result', 'Status'))".Trim()
        $result = switch -Regex ($raw) {
            '^(?i)(pass|true)$' { 'pass'; break }
            '^(?i)(warn|warning)$' { 'warn'; break }
            default { 'fail' }
        }
        switch ($result) { 'pass' { $pass++ } 'warn' { $warn++ } default { $fail++ } }
        [ordered]@{
            policyId    = [string](Get-UIAOField $r @('PolicyId', 'policyId', 'Control', 'Id'))
            control     = [string](Get-UIAOField $r @('Control', 'ControlId', 'control'))
            result      = $result
            product     = [string](Get-UIAOField $r @('Product', 'product', 'Baseline'))
            requirement = [string](Get-UIAOField $r @('Requirement', 'requirement', 'Criticality'))
            source      = 'ScubaGear'
        }
    }
    $policies = @($policies)
    $data = [ordered]@{
        policies = $policies
        summary  = [ordered]@{ pass = $pass; fail = $fail; warn = $warn }
        count    = $policies.Count
    }
    $artifact = New-UIAOAssessmentArtifact -Target 'ConformanceEvidence' -Data $data `
        -SourceTool 'CISA ScubaGear' -SourceVersion $SourceVersion -Timestamp $Timestamp `
        -Actor 'UIAOImportAdapters/Import-UIAOSCuBAReport'
    if ($OutputPath) { Write-UIAOArtifact -Artifact $artifact -OutputPath $OutputPath }
    return $artifact
}

function Import-UIAOADReconReport {
    <#
    .SYNOPSIS
        Normalize an ADRecon export into a UIAO ComputerInventory artifact.
    .DESCRIPTION
        Read-only. ADRecon emits one CSV per object class; this adapter
        ingests the Computers CSV (or an equivalent JSON array) and maps to
        the canonical ComputerInventory shape: { computers: [ { name, fqdn,
        os, operatingSystemVersion, enabled, lastLogon, source } ], count }.
        Pass the ADRecon "Computers.csv" (or a JSON conversion of it).
    .PARAMETER ReportPath
        Path to the ADRecon Computers export (.csv or .json).
    .PARAMETER OutputPath
        Optional path to write the normalized artifact.
    .PARAMETER SourceVersion
        ADRecon version recorded in provenance.
    .PARAMETER Timestamp
        Optional ISO-8601 UTC timestamp for deterministic output.
    #>
    [CmdletBinding()]
    [OutputType([System.Collections.Specialized.OrderedDictionary])]
    param(
        [Parameter(Mandatory = $true)][string]$ReportPath,
        [Parameter(Mandatory = $false)][string]$OutputPath,
        [Parameter(Mandatory = $false)][string]$SourceVersion = 'unknown',
        [Parameter(Mandatory = $false)][string]$Timestamp
    )
    $records = Resolve-UIAORecords (Read-UIAOReport $ReportPath) -PreferKeys @('Computers', 'computers', 'value')
    $computers = foreach ($r in $records) {
        $enabledRaw = "$(Get-UIAOField $r @('Enabled', 'enabled') 'true')".Trim()
        [ordered]@{
            name                   = [string](Get-UIAOField $r @('Name', 'ComputerName', 'CN', 'SamAccountName'))
            fqdn                   = [string](Get-UIAOField $r @('DNSHostName', 'dNSHostName', 'FQDN'))
            os                     = [string](Get-UIAOField $r @('OperatingSystem', 'operatingSystem'))
            operatingSystemVersion = [string](Get-UIAOField $r @('OperatingSystemVersion', 'operatingSystemVersion'))
            enabled                = ($enabledRaw -match '^(?i)(true|yes|1)$')
            lastLogon              = [string](Get-UIAOField $r @('LastLogonDate', 'lastLogonTimestamp', 'LastLogon'))
            source                 = 'ADRecon'
        }
    }
    $computers = @($computers)
    $data = [ordered]@{ computers = $computers; count = $computers.Count }
    $artifact = New-UIAOAssessmentArtifact -Target 'ComputerInventory' -Data $data `
        -SourceTool 'ADRecon' -SourceVersion $SourceVersion -Timestamp $Timestamp `
        -Actor 'UIAOImportAdapters/Import-UIAOADReconReport'
    if ($OutputPath) { Write-UIAOArtifact -Artifact $artifact -OutputPath $OutputPath }
    return $artifact
}

function Merge-UIAOAssessmentSources {
    <#
    .SYNOPSIS
        Correlate multiple normalized assessment artifacts into one bundle.
    .DESCRIPTION
        Reads two or more normalized artifacts (as written by the Import-*
        functions) and produces a correlated assessment bundle:
        { sources: [ { schema, provenance } ], computers, gpos, findings,
        policies, ... } merging the per-target payloads. The bundle's own
        provenance seals the merged data; each input's provenance is
        preserved under `sources` for lineage.

        -MergeStrategy 'union' (default) concatenates records across sources.
        -MergeStrategy 'dedupe' additionally removes ComputerInventory
        duplicates by case-insensitive name.
    .PARAMETER SourcePaths
        Paths to normalized artifact JSON files (2+).
    .PARAMETER OutputPath
        Optional path to write the merged bundle.
    .PARAMETER MergeStrategy
        'union' (default) or 'dedupe'.
    .PARAMETER Timestamp
        Optional ISO-8601 UTC timestamp for deterministic output.
    #>
    [CmdletBinding()]
    [OutputType([System.Collections.Specialized.OrderedDictionary])]
    param(
        [Parameter(Mandatory = $true)][string[]]$SourcePaths,
        [Parameter(Mandatory = $false)][string]$OutputPath,
        [Parameter(Mandatory = $false)][ValidateSet('union', 'dedupe')][string]$MergeStrategy = 'union',
        [Parameter(Mandatory = $false)][string]$Timestamp
    )
    if ($SourcePaths.Count -lt 2) {
        throw "Merge-UIAOAssessmentSources requires at least two source paths."
    }
    $sources = [System.Collections.Generic.List[object]]::new()
    $computers = [System.Collections.Generic.List[object]]::new()
    $gpos = [System.Collections.Generic.List[object]]::new()
    $findings = [System.Collections.Generic.List[object]]::new()
    $policies = [System.Collections.Generic.List[object]]::new()

    foreach ($path in $SourcePaths) {
        if (-not (Test-Path -LiteralPath $path)) { throw "Source artifact not found: $path" }
        $art = Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json
        $prov = $art.PSObject.Properties['provenance']
        if ($prov) {
            $sources.Add([ordered]@{
                    schema     = [string]$art.schema
                    source     = [string]$art.provenance.source
                    version    = [string]$art.provenance.version
                    timestamp  = [string]$art.provenance.timestamp
                })
        }
        $d = $art.data
        if ($null -eq $d) { continue }
        foreach ($pair in @(
                @{ key = 'computers'; list = $computers },
                @{ key = 'gpos'; list = $gpos },
                @{ key = 'findings'; list = $findings },
                @{ key = 'policies'; list = $policies })) {
            $p = $d.PSObject.Properties[$pair.key]
            if ($p -and $p.Value) { foreach ($item in @($p.Value)) { $pair.list.Add((ConvertTo-UIAOHashtable $item)) } }
        }
    }

    if ($MergeStrategy -eq 'dedupe' -and $computers.Count -gt 0) {
        $seen = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
        $unique = [System.Collections.Generic.List[object]]::new()
        foreach ($c in $computers) {
            $name = [string]$c['name']
            if ($name -and -not $seen.Add($name)) { continue }
            $unique.Add($c)
        }
        $computers = $unique
    }

    $data = [ordered]@{
        sources   = @($sources)
        computers = @($computers)
        gpos      = @($gpos)
        findings  = @($findings)
        policies  = @($policies)
        strategy  = $MergeStrategy
    }
    $artifact = New-UIAOAssessmentArtifact -Target 'AssessmentBundle' -Data $data `
        -SourceTool 'UIAOImportAdapters/Merge' -SourceVersion $Script:ArtifactSchemaVersion -Timestamp $Timestamp `
        -Actor 'UIAOImportAdapters/Merge-UIAOAssessmentSources'
    if ($OutputPath) { Write-UIAOArtifact -Artifact $artifact -OutputPath $OutputPath }
    return $artifact
}

function ConvertTo-UIAOHashtable {
    <#
    .SYNOPSIS
        Internal: deep-convert a PSCustomObject (from ConvertFrom-Json) into
        ordered hashtables / arrays so it canonicalizes deterministically.
    #>
    [CmdletBinding()]
    param([Parameter(Mandatory = $true)][AllowNull()]$InputObject)
    if ($null -eq $InputObject) { return $null }
    if ($InputObject -is [System.Management.Automation.PSCustomObject]) {
        $h = [ordered]@{}
        foreach ($p in $InputObject.PSObject.Properties) { $h[$p.Name] = ConvertTo-UIAOHashtable $p.Value }
        return $h
    }
    if ($InputObject -is [System.Collections.IDictionary]) {
        $h = [ordered]@{}
        foreach ($k in $InputObject.Keys) { $h[[string]$k] = ConvertTo-UIAOHashtable $InputObject[$k] }
        return $h
    }
    if ($InputObject -is [System.Collections.IEnumerable] -and $InputObject -isnot [string]) {
        return @($InputObject | ForEach-Object { ConvertTo-UIAOHashtable $_ })
    }
    return $InputObject
}

Export-ModuleMember -Function `
    'ConvertTo-UIAOCanonicalJson', `
    'Get-UIAOContentHash', `
    'New-UIAOAssessmentArtifact', `
    'Import-UIAOAzureMigrateReport', `
    'Import-UIAOGPOAnalyticsReport', `
    'Import-UIAODefenderFindings', `
    'Import-UIAOSCuBAReport', `
    'Import-UIAOADReconReport', `
    'Merge-UIAOAssessmentSources'
