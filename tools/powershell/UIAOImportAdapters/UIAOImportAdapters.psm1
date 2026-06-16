# UIAOImportAdapters — assessment ingestion adapters (canon: UIAO_182, ADR-094).
#
# Producer in the assessment-to-plan toolchain (ADR-094 Decision 1). Ingests
# already-produced third-party assessment artifacts (Azure Migrate, Intune GPO
# Analytics, Defender for Identity, CISA ScubaGear, ADRecon) and normalizes
# them into UIAO-schema JSON wrapped in a provenance envelope, so downstream
# correlation / drift / plan generation operate over one canonical shape.
#
# Doctrine (UIAO_182 §Non-functional contract, ADR-094 Decision 4):
#   - Read-only ingestion of file artifacts. No live tenant/directory reads
#     (that is UIAOIdentityAssessment / UIAO_181). No plan derivation (that is
#     UIAOPlanGenerators / UIAO_183).
#   - Output carries a provenance envelope (source / version / timestamp) plus
#     a content_hash sealing the normalized data. The seal is computed by the
#     canonical Python hasher so it is byte-identical to
#     `uiao.ir.models.core.canonical_hash` — i.e. an imported artifact whose
#     envelope is incomplete or whose hash no longer matches its data is a
#     DRIFT-PROVENANCE finding by definition (UIAO_150 §Principle 2), directly
#     classifiable by `src/uiao/governance/drift.py::classify_provenance_drift`.
#   - Input validation / sanitization is a documented control surface (SI-10).
#
# Following the established tools/powershell pattern (OrgPathTools /
# OrgTreeValidation): the .psm1 is the operator-facing layer; the Python
# canonical hasher is authoritative for the integrity seal.
#
# Exports (UIAO_182 §Function roster):
#   Import-UIAOAzureMigrateReport   Azure Migrate export    -> ComputerInventory
#   Import-UIAOGPOAnalyticsReport   Intune GPO Analytics    -> GPOMigrationTracker
#   Import-UIAODefenderFindings     Defender Secure Score   -> SecurityAssessment
#   Import-UIAOSCuBAReport          ScubaGear output        -> ConformanceEvidence
#   Import-UIAOADReconReport        ADRecon output          -> ComputerInventory
#   Merge-UIAOAssessmentSources     normalized sources      -> correlated bundle

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Script:ModuleVersion = '1.0.0'

# Safety cap for a single source artifact (SI-10). Imported reports are small
# relative to this; anything larger is rejected rather than read into memory.
$Script:MaxInputBytes = 200MB


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

function Resolve-UIAOPython {
    <#
    .SYNOPSIS
        Internal: resolve the Python interpreter used for the canonical seal.
    .NOTES
        Honors $env:UIAO_PYTHON, else prefers 'python3' then 'python'. Only
        the standard library is used (json, hashlib); the full uiao package
        is NOT imported, so no editable install is required to compute seals.
    #>
    if ($env:UIAO_PYTHON) { return $env:UIAO_PYTHON }
    foreach ($candidate in @('python3', 'python')) {
        if (Get-Command $candidate -ErrorAction SilentlyContinue) { return $candidate }
    }
    throw "No Python interpreter found (looked for python3, python). Set `$env:UIAO_PYTHON to the interpreter path."
}


function Get-UIAOCanonicalHash {
    <#
    .SYNOPSIS
        Internal: SHA-256 over canonical JSON, byte-identical to
        uiao.ir.models.core.canonical_hash.
    .DESCRIPTION
        Pipes any valid JSON serialization of the data to a stdlib-only Python
        canonicalizer that re-serializes with sort_keys=True,
        separators=(',',':'), ensure_ascii=False and hashes the UTF-8 bytes.
        Because Python re-canonicalizes, the intermediate PowerShell JSON only
        needs to be parseable — whitespace and key order do not affect the seal.
    .PARAMETER Json
        A valid JSON string (the data payload to seal).
    #>
    [CmdletBinding()]
    [OutputType([string])]
    param(
        [Parameter(Mandatory = $true)]
        [ValidateNotNullOrEmpty()]
        [string]$Json
    )
    $py = Resolve-UIAOPython
    $pyScript = @'
import sys, json, hashlib
data = json.load(sys.stdin)
canon = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
sys.stdout.write(hashlib.sha256(canon.encode("utf-8")).hexdigest())
'@
    $result = $Json | & $py '-c' $pyScript
    if ($LASTEXITCODE -ne 0) {
        throw "Canonical-hash helper (python) exited $LASTEXITCODE"
    }
    return (($result -join '').Trim())
}


function Assert-UIAOInputPath {
    <#
    .SYNOPSIS
        Internal (SI-10): validate a source path before reading it.
    .DESCRIPTION
        Rejects null/empty paths, non-existent files, and files over the size
        cap. Returns the resolved absolute path. This is the documented input
        validation control surface for the module.
    #>
    [CmdletBinding()]
    [OutputType([string])]
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )
    if ([string]::IsNullOrWhiteSpace($Path)) {
        throw "Report path is null or empty."
    }
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Report file not found: $Path"
    }
    $item = Get-Item -LiteralPath $Path
    if ($item.Length -gt $Script:MaxInputBytes) {
        $mb = [math]::Round($item.Length / 1MB, 1)
        throw "Report file exceeds the $([int]($Script:MaxInputBytes / 1MB)) MB safety cap: $Path ($mb MB)"
    }
    return $item.FullName
}


function Read-UIAOSourceData {
    <#
    .SYNOPSIS
        Internal: load a .json or .csv source artifact into objects.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )
    $ext = [System.IO.Path]::GetExtension($Path).ToLowerInvariant()
    switch ($ext) {
        '.json' {
            $raw = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
            if ([string]::IsNullOrWhiteSpace($raw)) { throw "Source file is empty: $Path" }
            try {
                return ($raw | ConvertFrom-Json)
            }
            catch {
                throw "Source file is not valid JSON: $Path ($($_.Exception.Message))"
            }
        }
        '.csv' {
            return @(Import-Csv -LiteralPath $Path)
        }
        default {
            throw "Unsupported source extension '$ext' (expected .json or .csv): $Path"
        }
    }
}


function Get-UIAORows {
    <#
    .SYNOPSIS
        Internal: coerce a loaded source object into an array of record rows.
    .DESCRIPTION
        Handles three shapes: a top-level array; an object wrapping a known
        array property (e.g. ScubaGear 'Results', Graph 'value'); or a single
        object treated as one row.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [AllowNull()]
        $Data,

        [Parameter(Mandatory = $false)]
        [string[]]$PreferredArrayKeys = @()
    )
    if ($null -eq $Data) { return @() }
    if (($Data -is [System.Collections.IEnumerable]) -and ($Data -isnot [string])) {
        return @($Data)
    }
    foreach ($key in $PreferredArrayKeys) {
        $prop = $Data.PSObject.Properties | Where-Object { $_.Name -ieq $key } | Select-Object -First 1
        if ($prop -and $prop.Value) {
            return @($prop.Value)
        }
    }
    return @($Data)
}


function Get-UIAOFieldValue {
    <#
    .SYNOPSIS
        Internal: first non-empty value among a set of case-insensitive field
        aliases on a row. Returns a string, or $null when none match.
    #>
    [CmdletBinding()]
    [OutputType([string])]
    param(
        [Parameter(Mandatory = $true, Position = 0)]
        $Row,

        [Parameter(Mandatory = $true, Position = 1)]
        [string[]]$Aliases
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
    <#
    .SYNOPSIS
        Internal: capture every original column of a row (values as strings)
        so normalization is lossless and traceable to the source artifact.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        $Row
    )
    $fields = [ordered]@{}
    foreach ($prop in ($Row.PSObject.Properties | Sort-Object Name)) {
        $fields[$prop.Name] = if ($null -eq $prop.Value) { $null } else { "$($prop.Value)" }
    }
    return $fields
}


function New-UIAOImportEnvelope {
    <#
    .SYNOPSIS
        Internal: wrap normalized records in a sealed provenance envelope.
    .DESCRIPTION
        Builds the data payload, seals it with the canonical content_hash, and
        returns an envelope whose provenance carries source / version /
        timestamp / content_hash (the fields drift.py requires to classify a
        DRIFT-PROVENANCE finding).
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)] [string]$SourceTool,
        [Parameter(Mandatory = $false)][string]$SourceVersion,
        [Parameter(Mandatory = $true)] [string]$TargetSchema,
        [Parameter(Mandatory = $true)] [string]$SourceFile,
        [Parameter(Mandatory = $true)] [AllowEmptyCollection()][object[]]$Records
    )
    $recordArray = @($Records)
    $data = [ordered]@{
        target_schema = $TargetSchema
        record_count  = $recordArray.Count
        records       = $recordArray
    }
    $dataJson = $data | ConvertTo-Json -Depth 30
    $contentHash = Get-UIAOCanonicalHash -Json $dataJson

    return [ordered]@{
        schema        = 'uiao.import.v1'
        target_schema = $TargetSchema
        provenance    = [ordered]@{
            source                = $SourceTool
            version               = if ([string]::IsNullOrWhiteSpace($SourceVersion)) { 'unknown' } else { $SourceVersion }
            timestamp             = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
            content_hash          = $contentHash
            actor                 = "UIAOImportAdapters/$Script:ModuleVersion"
            source_file           = $SourceFile
            import_module         = 'UIAOImportAdapters'
            import_module_version = $Script:ModuleVersion
        }
        data          = $data
    }
}


function Write-UIAOEnvelopeOutput {
    <#
    .SYNOPSIS
        Internal: return the envelope, and write it to -OutputPath when given.
    .NOTES
        Writes UTF-8 without BOM so the file round-trips cleanly through the
        Python IR / OSCAL pipeline.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)] $Envelope,
        [Parameter(Mandatory = $false)][string]$OutputPath
    )
    if (-not [string]::IsNullOrWhiteSpace($OutputPath)) {
        $json = $Envelope | ConvertTo-Json -Depth 40
        $dir = Split-Path -Parent $OutputPath
        if ($dir -and -not (Test-Path -LiteralPath $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
        }
        [System.IO.File]::WriteAllText($OutputPath, $json, [System.Text.UTF8Encoding]::new($false))
    }
    return $Envelope
}


# ---------------------------------------------------------------------------
# Public functions — importers (UIAO_182 §Function roster)
# ---------------------------------------------------------------------------

function Import-UIAOAzureMigrateReport {
    <#
    .SYNOPSIS
        Normalize an Azure Migrate assessment export into UIAO ComputerInventory.
    .DESCRIPTION
        Reads an already-exported Azure Migrate assessment (.json or .csv) and
        emits a sealed UIAO ComputerInventory envelope. Read-only; never reaches
        a live API (UIAO_182 §Inputs and outputs).
    .PARAMETER ReportPath
        Path to the Azure Migrate export file.
    .PARAMETER OutputPath
        Optional path to write the normalized envelope JSON. The envelope is
        also returned for pipeline use.
    .PARAMETER SourceVersion
        Optional version string for the source export (recorded in provenance).
    .EXAMPLE
        Import-UIAOAzureMigrateReport -ReportPath .\assessment.csv -OutputPath .\inventory.json
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string]$ReportPath,
        [Parameter(Mandatory = $false)][string]$OutputPath,
        [Parameter(Mandatory = $false)][string]$SourceVersion
    )
    $full = Assert-UIAOInputPath -Path $ReportPath
    $loaded = Read-UIAOSourceData -Path $full
    $rows = Get-UIAORows -Data $loaded -PreferredArrayKeys @('Machines', 'machines', 'assessedMachines', 'value')
    $records = foreach ($row in $rows) {
        [ordered]@{
            name             = Get-UIAOFieldValue $row @('Machine', 'MachineName', 'Name', 'DisplayName', 'ComputerName')
            operating_system = Get-UIAOFieldValue $row @('Operating system', 'OperatingSystem', 'OS')
            os_version       = Get-UIAOFieldValue $row @('OS version', 'OperatingSystemVersion', 'OSVersion')
            cores            = Get-UIAOFieldValue $row @('Cores', 'NumberOfCores')
            memory_mb        = Get-UIAOFieldValue $row @('Memory(MB)', 'MemoryInMB', 'MemoryMB')
            readiness        = Get-UIAOFieldValue $row @('Azure VM readiness', 'AzureReadiness', 'Readiness')
            source_fields    = ConvertTo-UIAOSourceFields $row
        }
    }
    $envelope = New-UIAOImportEnvelope -SourceTool 'AzureMigrate' -SourceVersion $SourceVersion `
        -TargetSchema 'ComputerInventory' -SourceFile (Split-Path -Leaf $full) -Records @($records)
    return (Write-UIAOEnvelopeOutput -Envelope $envelope -OutputPath $OutputPath)
}


function Import-UIAOGPOAnalyticsReport {
    <#
    .SYNOPSIS
        Normalize an Intune Group Policy Analytics export into a UIAO
        GPOMigrationTracker.
    .PARAMETER ReportPath
        Path to the GPO Analytics export file (.json or .csv).
    .PARAMETER OutputPath
        Optional output path for the normalized envelope JSON.
    .PARAMETER SourceVersion
        Optional source export version (recorded in provenance).
    .EXAMPLE
        Import-UIAOGPOAnalyticsReport -ReportPath .\gpo-analytics.json -OutputPath .\gpo-tracker.json
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string]$ReportPath,
        [Parameter(Mandatory = $false)][string]$OutputPath,
        [Parameter(Mandatory = $false)][string]$SourceVersion
    )
    $full = Assert-UIAOInputPath -Path $ReportPath
    $loaded = Read-UIAOSourceData -Path $full
    $rows = Get-UIAORows -Data $loaded -PreferredArrayKeys @('value', 'results', 'groupPolicySettingMappings', 'settings')
    $records = foreach ($row in $rows) {
        [ordered]@{
            gpo_name        = Get-UIAOFieldValue $row @('GroupPolicyName', 'groupPolicyName', 'PolicyName', 'DisplayName', 'Name')
            setting_name    = Get-UIAOFieldValue $row @('settingName', 'SettingName', 'Setting', 'settingDisplayName')
            setting_category = Get-UIAOFieldValue $row @('settingCategory', 'Category', 'parentId')
            mdm_support     = Get-UIAOFieldValue $row @('mdmSupported', 'MdmSupported', 'MDMSupport', 'isMdmSupported')
            migration_state = Get-UIAOFieldValue $row @('migrationReadiness', 'MigrationReadiness', 'Status', 'state')
            source_fields   = ConvertTo-UIAOSourceFields $row
        }
    }
    $envelope = New-UIAOImportEnvelope -SourceTool 'IntuneGPOAnalytics' -SourceVersion $SourceVersion `
        -TargetSchema 'GPOMigrationTracker' -SourceFile (Split-Path -Leaf $full) -Records @($records)
    return (Write-UIAOEnvelopeOutput -Envelope $envelope -OutputPath $OutputPath)
}


function Import-UIAODefenderFindings {
    <#
    .SYNOPSIS
        Normalize a Defender for Identity Secure Score export into a UIAO
        SecurityAssessment overlay.
    .PARAMETER ReportPath
        Path to the Defender Secure Score export file (.json or .csv).
    .PARAMETER OutputPath
        Optional output path for the normalized envelope JSON.
    .PARAMETER SourceVersion
        Optional source export version (recorded in provenance).
    .EXAMPLE
        Import-UIAODefenderFindings -ReportPath .\secure-score.json -OutputPath .\security.json
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string]$ReportPath,
        [Parameter(Mandatory = $false)][string]$OutputPath,
        [Parameter(Mandatory = $false)][string]$SourceVersion
    )
    $full = Assert-UIAOInputPath -Path $ReportPath
    $loaded = Read-UIAOSourceData -Path $full
    $rows = Get-UIAORows -Data $loaded -PreferredArrayKeys @('value', 'controlScores', 'findings', 'results')
    $records = foreach ($row in $rows) {
        [ordered]@{
            control_name  = Get-UIAOFieldValue $row @('controlName', 'ControlName', 'control', 'Name', 'title')
            category      = Get-UIAOFieldValue $row @('controlCategory', 'category', 'Category')
            score         = Get-UIAOFieldValue $row @('score', 'Score', 'currentScore')
            max_score     = Get-UIAOFieldValue $row @('maxScore', 'MaxScore', 'max')
            status        = Get-UIAOFieldValue $row @('implementationStatus', 'status', 'Status', 'state')
            source_fields = ConvertTo-UIAOSourceFields $row
        }
    }
    $envelope = New-UIAOImportEnvelope -SourceTool 'DefenderForIdentity' -SourceVersion $SourceVersion `
        -TargetSchema 'SecurityAssessment' -SourceFile (Split-Path -Leaf $full) -Records @($records)
    return (Write-UIAOEnvelopeOutput -Envelope $envelope -OutputPath $OutputPath)
}


function Import-UIAOSCuBAReport {
    <#
    .SYNOPSIS
        Normalize CISA ScubaGear compliance output into UIAO conformance
        evidence.
    .PARAMETER ReportPath
        Path to the ScubaGear results file (.json or .csv).
    .PARAMETER OutputPath
        Optional output path for the normalized envelope JSON.
    .PARAMETER SourceVersion
        Optional ScubaGear version (recorded in provenance).
    .EXAMPLE
        Import-UIAOSCuBAReport -ReportPath .\ScubaResults.json -OutputPath .\conformance.json
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string]$ReportPath,
        [Parameter(Mandatory = $false)][string]$OutputPath,
        [Parameter(Mandatory = $false)][string]$SourceVersion
    )
    $full = Assert-UIAOInputPath -Path $ReportPath
    $loaded = Read-UIAOSourceData -Path $full
    $rows = Get-UIAORows -Data $loaded -PreferredArrayKeys @('Results', 'results', 'Findings', 'findings', 'value')
    $records = foreach ($row in $rows) {
        [ordered]@{
            baseline      = Get-UIAOFieldValue $row @('Baseline', 'baseline', 'Product', 'ProductName')
            control_id    = Get-UIAOFieldValue $row @('Control ID', 'ControlID', 'controlId', 'Control')
            requirement   = Get-UIAOFieldValue $row @('Requirement', 'requirement', 'Description')
            result        = Get-UIAOFieldValue $row @('Result', 'result', 'Passed', 'Status')
            details       = Get-UIAOFieldValue $row @('Details', 'details', 'Reason', 'ReportDetails')
            source_fields = ConvertTo-UIAOSourceFields $row
        }
    }
    $envelope = New-UIAOImportEnvelope -SourceTool 'ScubaGear' -SourceVersion $SourceVersion `
        -TargetSchema 'ConformanceEvidence' -SourceFile (Split-Path -Leaf $full) -Records @($records)
    return (Write-UIAOEnvelopeOutput -Envelope $envelope -OutputPath $OutputPath)
}


function Import-UIAOADReconReport {
    <#
    .SYNOPSIS
        Normalize ADRecon output (computers / identity) into UIAO
        ComputerInventory.
    .DESCRIPTION
        Consumes ADRecon's CSV export folder files (e.g. Computers.csv) or a
        JSON export. Excel (.xlsx) is intentionally not parsed — export ADRecon
        to CSV, which it produces alongside the workbook.
    .PARAMETER ReportPath
        Path to an ADRecon CSV or JSON export file.
    .PARAMETER OutputPath
        Optional output path for the normalized envelope JSON.
    .PARAMETER SourceVersion
        Optional ADRecon version (recorded in provenance).
    .EXAMPLE
        Import-UIAOADReconReport -ReportPath .\ADRecon-Computers.csv -OutputPath .\inventory.json
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string]$ReportPath,
        [Parameter(Mandatory = $false)][string]$OutputPath,
        [Parameter(Mandatory = $false)][string]$SourceVersion
    )
    $full = Assert-UIAOInputPath -Path $ReportPath
    $loaded = Read-UIAOSourceData -Path $full
    $rows = Get-UIAORows -Data $loaded -PreferredArrayKeys @('Computers', 'computers', 'value')
    $records = foreach ($row in $rows) {
        [ordered]@{
            name             = Get-UIAOFieldValue $row @('Name', 'DNSHostName', 'SamAccountName', 'ComputerName')
            operating_system = Get-UIAOFieldValue $row @('OperatingSystem', 'OS')
            os_version       = Get-UIAOFieldValue $row @('OperatingSystemVersion', 'OSVersion')
            ip_address       = Get-UIAOFieldValue $row @('IPv4Address', 'IPAddress', 'IPv6Address')
            last_logon       = Get-UIAOFieldValue $row @('LastLogonDate', 'lastLogonTimestamp', 'LastLogon')
            enabled          = Get-UIAOFieldValue $row @('Enabled')
            source_fields    = ConvertTo-UIAOSourceFields $row
        }
    }
    $envelope = New-UIAOImportEnvelope -SourceTool 'ADRecon' -SourceVersion $SourceVersion `
        -TargetSchema 'ComputerInventory' -SourceFile (Split-Path -Leaf $full) -Records @($records)
    return (Write-UIAOEnvelopeOutput -Envelope $envelope -OutputPath $OutputPath)
}


function Merge-UIAOAssessmentSources {
    <#
    .SYNOPSIS
        Correlate multiple normalized assessment envelopes into one sealed bundle.
    .DESCRIPTION
        Reads envelopes produced by the Import-UIAO* functions, verifies each
        one's provenance completeness and integrity seal (SI-7), groups records
        by target schema, and emits a sealed correlated bundle. A source whose
        envelope is incomplete or whose content_hash no longer matches its data
        is reported with integrity_ok = $false — a DRIFT-PROVENANCE condition by
        definition (UIAO_182 §Drift and provenance anchoring).
    .PARAMETER SourcePaths
        Paths to normalized assessment envelope files.
    .PARAMETER OutputPath
        Optional output path for the bundle JSON.
    .PARAMETER MergeStrategy
        'Union' (default) keeps every record; 'Distinct' de-duplicates
        structurally identical records within each target schema.
    .EXAMPLE
        Merge-UIAOAssessmentSources -SourcePaths a.json,b.json -OutputPath bundle.json -MergeStrategy Distinct
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string[]]$SourcePaths,
        [Parameter(Mandatory = $false)][string]$OutputPath,
        [Parameter(Mandatory = $false)][ValidateSet('Union', 'Distinct')][string]$MergeStrategy = 'Union'
    )
    $sourceSummaries = @()
    $recordsBySchema = [ordered]@{}

    foreach ($path in $SourcePaths) {
        $full = Assert-UIAOInputPath -Path $path
        $raw = Get-Content -LiteralPath $full -Raw -Encoding UTF8
        try {
            $envelope = $raw | ConvertFrom-Json
        }
        catch {
            throw "Source is not a valid envelope JSON: $full ($($_.Exception.Message))"
        }

        $prov = $envelope.provenance
        $missing = @()
        foreach ($field in @('source', 'version', 'timestamp', 'content_hash')) {
            $has = $prov -and ($prov.PSObject.Properties.Name -contains $field) -and (-not [string]::IsNullOrWhiteSpace("$($prov.$field)"))
            if (-not $has) { $missing += $field }
        }

        $integrityOk = $false
        if ($envelope.PSObject.Properties.Name -contains 'data') {
            $dataJson = $envelope.data | ConvertTo-Json -Depth 30
            $recomputed = Get-UIAOCanonicalHash -Json $dataJson
            $integrityOk = ($missing -notcontains 'content_hash') -and ($recomputed -eq "$($prov.content_hash)")
        }

        $schema = if ($envelope.PSObject.Properties.Name -contains 'target_schema') { "$($envelope.target_schema)" } else { 'Unknown' }
        if (-not $recordsBySchema.Contains($schema)) { $recordsBySchema[$schema] = @() }
        $recs = @($envelope.data.records)
        $recordsBySchema[$schema] += $recs

        $sourceSummaries += [ordered]@{
            source_file       = (Split-Path -Leaf $full)
            source            = "$($prov.source)"
            version           = "$($prov.version)"
            target_schema     = $schema
            record_count      = $recs.Count
            envelope_complete = ($missing.Count -eq 0)
            missing_fields    = $missing
            integrity_ok      = $integrityOk
        }
    }

    if ($MergeStrategy -eq 'Distinct') {
        foreach ($schema in @($recordsBySchema.Keys)) {
            $seen = [System.Collections.Generic.HashSet[string]]::new()
            $deduped = @()
            foreach ($record in @($recordsBySchema[$schema])) {
                $key = $record | ConvertTo-Json -Depth 30 -Compress
                if ($seen.Add($key)) { $deduped += $record }
            }
            $recordsBySchema[$schema] = $deduped
        }
    }

    $totalRecords = 0
    foreach ($schema in $recordsBySchema.Keys) { $totalRecords += @($recordsBySchema[$schema]).Count }

    $mergedData = [ordered]@{
        records_by_schema = $recordsBySchema
        total_records     = $totalRecords
    }
    $mergedJson = $mergedData | ConvertTo-Json -Depth 40
    $contentHash = Get-UIAOCanonicalHash -Json $mergedJson

    $bundle = [ordered]@{
        schema     = 'uiao.import.bundle.v1'
        provenance = [ordered]@{
            source                = 'UIAOImportAdapters.Merge'
            version               = $Script:ModuleVersion
            timestamp             = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
            content_hash          = $contentHash
            actor                 = "UIAOImportAdapters/$Script:ModuleVersion"
            merge_strategy        = $MergeStrategy
            source_count          = @($SourcePaths).Count
            import_module         = 'UIAOImportAdapters'
            import_module_version = $Script:ModuleVersion
        }
        sources    = @($sourceSummaries)
        data       = $mergedData
    }
    return (Write-UIAOEnvelopeOutput -Envelope $bundle -OutputPath $OutputPath)
}


Export-ModuleMember -Function `
    'Import-UIAOAzureMigrateReport', `
    'Import-UIAOGPOAnalyticsReport', `
    'Import-UIAODefenderFindings', `
    'Import-UIAOSCuBAReport', `
    'Import-UIAOADReconReport', `
    'Merge-UIAOAssessmentSources'
