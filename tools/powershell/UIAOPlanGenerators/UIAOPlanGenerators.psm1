# UIAOPlanGenerators — assessment-to-plan derivation (canon UIAO_183, ADR-094).
#
# Consumer at the end of the assessment-to-plan toolchain (ADR-094 Decision 1).
# Derives draft migration plans deterministically from the normalized,
# provenance-anchored artifacts emitted by the two producers (UIAOImportAdapters
# / UIAO_182 and UIAOIdentityAssessment / UIAO_181). It NEVER reads live tenant
# or directory state (ADR-094 Decision 2) — its determinism depends on consuming
# only reviewable producer artifacts.
#
# Core algorithm (ADR-094 Decision 3, UIAO_007 §3.1): decommissioning /
# migration order is computed from the OrgPath cross-plane dependency graph by
# deterministic topological sort, NOT an architect's manual reading. A cycle or
# a cross-domain service dependency is flagged as a blocker that makes the plan
# not approvable until an architect resolves it. A sequence that contradicts a
# recorded dependency is a generator defect, not a judgment call.
#
# Doctrine (UIAO_183 §Non-functional contract / §Drift and provenance anchoring):
#   - Plans are draft-for-approval, never auto-applied.
#   - Each plan cites the assessment artifact it derives from (derived_from) and
#     is sealed with a content_hash byte-identical to
#     uiao.ir.models.core.canonical_hash, so a plan whose cited assessment no
#     longer resolves or whose envelope is incomplete is a DRIFT-PROVENANCE
#     finding, per src/uiao/governance/drift.py.
#   - The sealed plan data contains no timestamp, so the same assessment yields
#     the same plan hash (reproducible plans).
#
# Self-contained per the tools/powershell convention; the Python canonical
# hasher is authoritative for the seal.
#
# Exports (UIAO_183 §Function roster):
#   New-UIAOComputerModernizationPlan   ComputerInventory  -> per-device plan
#   New-UIAOGPOMigrationPlan            GPOMigrationTracker -> GPO->Intune plan
#   New-UIAOIdentityMigrationPlan       identity inventory -> wave roadmap
#   New-UIAODNSMigrationPlan            DNS zones+deps     -> ordered sequence
#   New-UIAOPKIMigrationPlan            CA hierarchy       -> ordered sequence
#   Export-UIAOMasterPlan              plan set           -> master plan + DC order

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Script:ModuleVersion = '1.0.0'
$Script:MaxInputBytes = 200MB


# ---------------------------------------------------------------------------
# Private helpers (seal / validation — mirror the producer modules)
# ---------------------------------------------------------------------------

function Resolve-UIAOPython {
    if ($env:UIAO_PYTHON) { return $env:UIAO_PYTHON }
    foreach ($candidate in @('python3', 'python')) {
        if (Get-Command $candidate -ErrorAction SilentlyContinue) { return $candidate }
    }
    throw "No Python interpreter found (looked for python3, python). Set `$env:UIAO_PYTHON to the interpreter path."
}

function Get-UIAOCanonicalHash {
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

function Get-UIAODependsOn {
    # Extract a dependency id list from a record, handling array-valued or
    # delimited-string 'depends_on' fields.
    [CmdletBinding()]
    [OutputType([string[]])]
    param(
        [Parameter(Mandatory = $true, Position = 0)]$Row,
        [Parameter(Mandatory = $true, Position = 1)][string[]]$Aliases
    )
    foreach ($alias in $Aliases) {
        $prop = $Row.PSObject.Properties | Where-Object { $_.Name -ieq $alias } | Select-Object -First 1
        if ($prop -and $null -ne $prop.Value) {
            $v = $prop.Value
            if (($v -is [System.Collections.IEnumerable]) -and ($v -isnot [string])) {
                return @($v | ForEach-Object { "$_".Trim() } | Where-Object { $_ -ne '' })
            }
            $s = "$v".Trim()
            if ($s -ne '') {
                return @(($s -split '[,;]') | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne '' })
            }
        }
    }
    return @()
}

function Get-UIAOTopologicalOrder {
    <#
    .SYNOPSIS
        Deterministic topological sort of a dependency graph (Kahn), returning a
        foundations-first migration order plus cycle / cross-domain blockers.
    .DESCRIPTION
        Records carry an id, optional domain, and a depends_on edge list ("X
        depends_on Y" means Y is a prerequisite of X). Returns @{ Order;
        Blockers; HasCycle }. Order lists prerequisites before dependents
        (migration/establishment order); reverse it for decommissioning order.
        Cycles and known cross-domain edges are reported as blockers.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][object[]]$Records,
        [Parameter(Mandatory = $true)][string[]]$IdAliases,
        [Parameter(Mandatory = $true)][string[]]$DependsOnAliases,
        [Parameter(Mandatory = $false)][string[]]$DomainAliases = @('domain', 'Domain')
    )
    $nodes = [ordered]@{}
    foreach ($r in $Records) {
        $id = Get-UIAOFieldValue $r $IdAliases
        if (-not $id) { continue }
        if (-not $nodes.Contains($id)) {
            $nodes[$id] = @{
                domain = Get-UIAOFieldValue $r $DomainAliases
                deps   = @(Get-UIAODependsOn $r $DependsOnAliases)
            }
        }
    }

    $blockers = @()
    foreach ($id in $nodes.Keys) {
        foreach ($dep in $nodes[$id].deps) {
            if ($nodes.Contains($dep)) {
                $nDomain = $nodes[$id].domain
                $dDomain = $nodes[$dep].domain
                if ($nDomain -and $dDomain -and ($nDomain -ne $dDomain)) {
                    $blockers += [ordered]@{
                        type       = 'cross_domain'
                        node       = $id
                        depends_on = $dep
                        detail     = "$id ($nDomain) depends on $dep ($dDomain) across domains; requires architect resolution"
                    }
                }
            }
        }
    }

    $indeg = @{}
    $dependentsOf = @{}
    foreach ($id in $nodes.Keys) { $indeg[$id] = 0; $dependentsOf[$id] = @() }
    foreach ($id in $nodes.Keys) {
        foreach ($dep in $nodes[$id].deps) {
            if ($nodes.Contains($dep)) {
                $indeg[$id] = $indeg[$id] + 1
                $dependentsOf[$dep] = @($dependentsOf[$dep]) + $id
            }
        }
    }

    $order = @()
    $remaining = @{}
    foreach ($id in $nodes.Keys) { $remaining[$id] = $indeg[$id] }
    while ($remaining.Count -gt 0) {
        $ready = @($remaining.Keys | Where-Object { $remaining[$_] -eq 0 } | Sort-Object)
        if ($ready.Count -eq 0) { break }   # remaining nodes form a cycle
        foreach ($n in $ready) {
            $order += $n
            $remaining.Remove($n)
        }
        foreach ($n in $ready) {
            foreach ($dependent in $dependentsOf[$n]) {
                if ($remaining.Contains($dependent)) { $remaining[$dependent] = $remaining[$dependent] - 1 }
            }
        }
    }

    $hasCycle = $remaining.Count -gt 0
    if ($hasCycle) {
        $cycleNodes = @($remaining.Keys | Sort-Object)
        $blockers += [ordered]@{
            type   = 'cycle'
            nodes  = $cycleNodes
            detail = "Dependency cycle among: $($cycleNodes -join ', '); requires architect resolution"
        }
    }

    return @{ Order = @($order); Blockers = @($blockers); HasCycle = $hasCycle }
}

function Read-UIAOAssessmentEnvelope {
    [CmdletBinding()]
    param([Parameter(Mandatory = $true)][string]$Path)
    $full = Assert-UIAOInputPath -Path $Path
    $raw = Get-Content -LiteralPath $full -Raw -Encoding UTF8
    if ([string]::IsNullOrWhiteSpace($raw)) { throw "Assessment file is empty: $full" }
    try { $envelope = $raw | ConvertFrom-Json }
    catch { throw "Assessment is not valid envelope JSON: $full ($($_.Exception.Message))" }
    $records = if ($envelope.PSObject.Properties.Name -contains 'data' -and $envelope.data.PSObject.Properties.Name -contains 'records') {
        @($envelope.data.records)
    }
    else { @() }
    return @{ Envelope = $envelope; Records = $records; Full = $full; SourceFile = (Split-Path -Leaf $full) }
}

function Get-UIAODerivedFrom {
    [CmdletBinding()]
    param([Parameter(Mandatory = $true)]$Envelope, [Parameter(Mandatory = $true)][string]$SourceFile)
    $p = if ($Envelope.PSObject.Properties.Name -contains 'provenance') { $Envelope.provenance } else { $null }
    return [ordered]@{
        source       = if ($p) { "$($p.source)" } else { $null }
        version      = if ($p) { "$($p.version)" } else { $null }
        content_hash = if ($p) { "$($p.content_hash)" } else { $null }
        source_file  = $SourceFile
    }
}

function New-UIAOPlanEnvelope {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)] [string]$PlanType,
        [Parameter(Mandatory = $false)]$DerivedFrom,
        [Parameter(Mandatory = $true)] [AllowEmptyCollection()][object[]]$Records,
        [Parameter(Mandatory = $false)][System.Collections.IDictionary]$ExtraData,
        [Parameter(Mandatory = $false)][AllowEmptyCollection()][object[]]$Blockers = @()
    )
    $blockerArray = @($Blockers)
    $data = [ordered]@{
        plan_type     = $PlanType
        record_count  = @($Records).Count
        blocker_count = $blockerArray.Count
        approvable    = ($blockerArray.Count -eq 0)
        blockers      = $blockerArray
        records       = @($Records)
    }
    if ($ExtraData) { foreach ($k in $ExtraData.Keys) { $data[$k] = $ExtraData[$k] } }
    $contentHash = Get-UIAOCanonicalHash -Json ($data | ConvertTo-Json -Depth 30)
    return [ordered]@{
        schema        = 'uiao.plan.v1'
        plan_type     = $PlanType
        provenance    = [ordered]@{
            source                = 'UIAOPlanGenerators'
            version               = $Script:ModuleVersion
            timestamp             = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
            content_hash          = $contentHash
            actor                 = "UIAOPlanGenerators/$Script:ModuleVersion"
            derived_from          = $DerivedFrom
            approvable            = ($blockerArray.Count -eq 0)
            import_module         = 'UIAOPlanGenerators'
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


# ---------------------------------------------------------------------------
# Public functions — plan generators (UIAO_183 §Function roster)
# ---------------------------------------------------------------------------

function New-UIAOComputerModernizationPlan {
    <#
    .SYNOPSIS
        Derive a per-device modernization plan from a ComputerInventory assessment.
    .PARAMETER AssessmentPath
        Path to a normalized ComputerInventory envelope (from UIAOImportAdapters).
    .PARAMETER OutputPath
        Optional output path for the plan JSON.
    .PARAMETER TargetOS
        Target operating system (default 'Windows 11').
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string]$AssessmentPath,
        [Parameter(Mandatory = $false)][string]$OutputPath,
        [Parameter(Mandatory = $false)][string]$TargetOS = 'Windows 11'
    )
    $a = Read-UIAOAssessmentEnvelope -Path $AssessmentPath
    $records = foreach ($r in $a.Records) {
        $os = Get-UIAOFieldValue $r @('operating_system', 'os', 'OperatingSystem')
        $readiness = Get-UIAOFieldValue $r @('readiness', 'Readiness', 'AzureReadiness')
        $action =
        if ($os -and ($os -match [regex]::Escape($TargetOS))) { 'compliant' }
        elseif ($readiness -and ($readiness -match '(?i)not\s*ready|unsupported|not\s*suitable')) { 'replace_hardware' }
        elseif ($readiness -and ($readiness -match '(?i)conditional')) { 'remediate_then_upgrade' }
        elseif ($readiness -and ($readiness -match '(?i)ready|suitable')) { 'in_place_upgrade' }
        else { 'assess' }
        [ordered]@{
            name       = Get-UIAOFieldValue $r @('name', 'Name', 'machine')
            current_os = $os
            target_os  = $TargetOS
            readiness  = $readiness
            action     = $action
        }
    }
    $envelope = New-UIAOPlanEnvelope -PlanType 'ComputerModernizationPlan' -Records @($records) `
        -DerivedFrom (Get-UIAODerivedFrom -Envelope $a.Envelope -SourceFile $a.SourceFile) `
        -ExtraData ([ordered]@{ target_os = $TargetOS })
    return (Write-UIAOEnvelopeOutput -Envelope $envelope -OutputPath $OutputPath)
}

function New-UIAOGPOMigrationPlan {
    <#
    .SYNOPSIS
        Derive a GPO-to-Intune migration plan from a GPOMigrationTracker assessment.
    .PARAMETER AnalyticsReport
        Optional path to a supplementary GPO Analytics envelope (reserved for
        future enrichment; recorded in provenance when supplied).
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string]$AssessmentPath,
        [Parameter(Mandatory = $false)][string]$OutputPath,
        [Parameter(Mandatory = $false)][string]$AnalyticsReport
    )
    $a = Read-UIAOAssessmentEnvelope -Path $AssessmentPath
    $records = foreach ($r in $a.Records) {
        $mdm = Get-UIAOFieldValue $r @('mdm_support', 'mdmSupported', 'MdmSupported')
        $action =
        if ($mdm -and ($mdm -match '(?i)^(true|full|supported|yes)$')) { 'migrate_to_intune' }
        elseif ($mdm -and ($mdm -match '(?i)partial|limited')) { 'migrate_with_review' }
        elseif ($mdm -and ($mdm -match '(?i)^(false|none|unsupported|no)$')) { 'no_intune_equivalent' }
        else { 'manual_review' }
        [ordered]@{
            gpo_name     = Get-UIAOFieldValue $r @('gpo_name', 'GroupPolicyName', 'PolicyName')
            setting_name = Get-UIAOFieldValue $r @('setting_name', 'settingName')
            mdm_support  = $mdm
            action       = $action
        }
    }
    $extra = [ordered]@{}
    if (-not [string]::IsNullOrWhiteSpace($AnalyticsReport)) { $extra['analytics_report'] = (Split-Path -Leaf $AnalyticsReport) }
    $envelope = New-UIAOPlanEnvelope -PlanType 'GPOMigrationPlan' -Records @($records) `
        -DerivedFrom (Get-UIAODerivedFrom -Envelope $a.Envelope -SourceFile $a.SourceFile) `
        -ExtraData $extra
    return (Write-UIAOEnvelopeOutput -Envelope $envelope -OutputPath $OutputPath)
}

function New-UIAOIdentityMigrationPlan {
    <#
    .SYNOPSIS
        Derive a wave-based identity migration roadmap from an identity inventory.
    .PARAMETER WaveSize
        Number of principals per wave (default 100). Principals are ordered
        deterministically (by UPN) before wave assignment.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string]$AssessmentPath,
        [Parameter(Mandatory = $false)][string]$OutputPath,
        [Parameter(Mandatory = $false)][ValidateRange(1, 100000)][int]$WaveSize = 100
    )
    $a = Read-UIAOAssessmentEnvelope -Path $AssessmentPath
    $principals = foreach ($r in $a.Records) {
        $key = Get-UIAOFieldValue $r @('user_principal_name', 'userPrincipalName', 'id', 'name')
        if ($key) { @{ key = $key; record = $r } }
    }
    $sorted = @($principals | Sort-Object { $_.key })
    $records = @()
    for ($i = 0; $i -lt $sorted.Count; $i++) {
        $records += [ordered]@{
            principal = $sorted[$i].key
            wave      = [int][math]::Floor($i / $WaveSize) + 1
        }
    }
    $waveCount = if ($sorted.Count -gt 0) { [int][math]::Ceiling($sorted.Count / $WaveSize) } else { 0 }
    $envelope = New-UIAOPlanEnvelope -PlanType 'IdentityMigrationPlan' -Records @($records) `
        -DerivedFrom (Get-UIAODerivedFrom -Envelope $a.Envelope -SourceFile $a.SourceFile) `
        -ExtraData ([ordered]@{ wave_size = $WaveSize; wave_count = $waveCount })
    return (Write-UIAOEnvelopeOutput -Envelope $envelope -OutputPath $OutputPath)
}

function New-UIAODNSMigrationPlan {
    <#
    .SYNOPSIS
        Derive a dependency-ordered DNS zone migration sequence.
    .DESCRIPTION
        Zones carry depends_on edges; the migration sequence is the deterministic
        topological order (prerequisite zones first). Cycles and cross-domain
        dependencies are flagged as blockers that make the plan not approvable.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string]$AssessmentPath,
        [Parameter(Mandatory = $false)][string]$OutputPath
    )
    $a = Read-UIAOAssessmentEnvelope -Path $AssessmentPath
    $topo = Get-UIAOTopologicalOrder -Records $a.Records `
        -IdAliases @('zone', 'name', 'id', 'zone_name') `
        -DependsOnAliases @('depends_on', 'dependencies', 'depends') `
        -DomainAliases @('domain', 'zone_domain', 'Domain')
    $records = @()
    $seq = 1
    foreach ($zone in $topo.Order) {
        $records += [ordered]@{ sequence = $seq; zone = $zone; action = 'migrate_zone' }
        $seq++
    }
    $envelope = New-UIAOPlanEnvelope -PlanType 'DNSMigrationPlan' -Records @($records) -Blockers @($topo.Blockers) `
        -DerivedFrom (Get-UIAODerivedFrom -Envelope $a.Envelope -SourceFile $a.SourceFile)
    return (Write-UIAOEnvelopeOutput -Envelope $envelope -OutputPath $OutputPath)
}

function New-UIAOPKIMigrationPlan {
    <#
    .SYNOPSIS
        Derive a dependency-ordered PKI / CA migration sequence.
    .DESCRIPTION
        CAs carry depends_on edges (issuing CA depends on its root). The sequence
        is the deterministic topological order (root before issuing). Cycles and
        cross-domain dependencies are flagged as blockers.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string]$AssessmentPath,
        [Parameter(Mandatory = $false)][string]$OutputPath
    )
    $a = Read-UIAOAssessmentEnvelope -Path $AssessmentPath
    $topo = Get-UIAOTopologicalOrder -Records $a.Records `
        -IdAliases @('ca', 'ca_name', 'name', 'id') `
        -DependsOnAliases @('depends_on', 'dependencies', 'issued_by', 'parent') `
        -DomainAliases @('domain', 'Domain')
    $records = @()
    $seq = 1
    foreach ($ca in $topo.Order) {
        $records += [ordered]@{ sequence = $seq; ca = $ca; action = 'migrate_ca' }
        $seq++
    }
    $envelope = New-UIAOPlanEnvelope -PlanType 'PKIMigrationPlan' -Records @($records) -Blockers @($topo.Blockers) `
        -DerivedFrom (Get-UIAODerivedFrom -Envelope $a.Envelope -SourceFile $a.SourceFile)
    return (Write-UIAOEnvelopeOutput -Envelope $envelope -OutputPath $OutputPath)
}

function Export-UIAOMasterPlan {
    <#
    .SYNOPSIS
        Assemble component plans into a master plan, and (from a server
        dependency registry) compute the domain-controller decommissioning order.
    .DESCRIPTION
        Reads the component plan envelopes named in -PlanPaths and summarizes
        them (type, record/blocker counts, approvability, derived_from). When
        -ServerDependencyPath is supplied, builds the cross-plane dependency
        graph and emits the deterministic DC decommissioning order — the reverse
        of the migration topological order, so no controller is decommissioned
        before its dependents are migrated (ADR-094 Decision 3). Cross-domain
        edges and cycles propagate as blockers; the master plan is approvable
        only when no component plan and no server-graph blocker remains.
    .PARAMETER PlanPaths
        Paths to component plan envelopes.
    .PARAMETER OutputPath
        Optional output path. With -Format markdown the rendered document is
        written here; otherwise the master-plan JSON envelope is written.
    .PARAMETER Format
        'json' (default) or 'markdown'.
    .PARAMETER ServerDependencyPath
        Optional server dependency registry envelope (records carry host id,
        domain, depends_on) used to compute the DC decommissioning order.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string[]]$PlanPaths,
        [Parameter(Mandatory = $false)][string]$OutputPath,
        [Parameter(Mandatory = $false)][ValidateSet('json', 'markdown')][string]$Format = 'json',
        [Parameter(Mandatory = $false)][string]$ServerDependencyPath
    )
    $componentSummaries = @()
    $aggregateBlockers = @()
    foreach ($path in $PlanPaths) {
        $p = Read-UIAOAssessmentEnvelope -Path $path
        $env = $p.Envelope
        $planType = if ($env.PSObject.Properties.Name -contains 'plan_type') { "$($env.plan_type)" } else { 'UnknownPlan' }
        $blockerCount = if ($env.data.PSObject.Properties.Name -contains 'blocker_count') { [int]$env.data.blocker_count } else { 0 }
        if ($blockerCount -gt 0 -and ($env.data.PSObject.Properties.Name -contains 'blockers')) {
            foreach ($b in @($env.data.blockers)) { $aggregateBlockers += $b }
        }
        $componentSummaries += [ordered]@{
            plan_type    = $planType
            source_file  = $p.SourceFile
            record_count = if ($env.data.PSObject.Properties.Name -contains 'record_count') { [int]$env.data.record_count } else { @($p.Records).Count }
            approvable   = if ($env.data.PSObject.Properties.Name -contains 'approvable') { [bool]$env.data.approvable } else { ($blockerCount -eq 0) }
            content_hash = if ($env.PSObject.Properties.Name -contains 'provenance') { "$($env.provenance.content_hash)" } else { $null }
        }
    }

    $dcDecommissionOrder = @()
    $serverDerivedFrom = $null
    if (-not [string]::IsNullOrWhiteSpace($ServerDependencyPath)) {
        $s = Read-UIAOAssessmentEnvelope -Path $ServerDependencyPath
        $serverDerivedFrom = Get-UIAODerivedFrom -Envelope $s.Envelope -SourceFile $s.SourceFile
        $topo = Get-UIAOTopologicalOrder -Records $s.Records `
            -IdAliases @('host', 'name', 'id', 'server', 'dc') `
            -DependsOnAliases @('depends_on', 'dependencies', 'depends') `
            -DomainAliases @('domain', 'Domain')
        # Decommissioning order is the reverse of the migration (foundations-first)
        # order: dependents are decommissioned before the foundations they rely on.
        $reversed = @($topo.Order)
        [array]::Reverse($reversed)
        $rank = 1
        foreach ($serverHost in $reversed) {
            $dcDecommissionOrder += [ordered]@{ decommission_rank = $rank; host = $serverHost }
            $rank++
        }
        foreach ($b in @($topo.Blockers)) { $aggregateBlockers += $b }
    }

    $extra = [ordered]@{
        component_plans       = @($componentSummaries)
        component_plan_count  = @($componentSummaries).Count
        dc_decommission_order = @($dcDecommissionOrder)
    }
    if ($serverDerivedFrom) { $extra['server_dependency_source'] = $serverDerivedFrom }

    $envelope = New-UIAOPlanEnvelope -PlanType 'MasterModernizationPlan' -Records @() `
        -Blockers @($aggregateBlockers) -ExtraData $extra

    if ($Format -eq 'markdown') {
        $md = ConvertTo-UIAOMasterPlanMarkdown -Envelope $envelope
        if (-not [string]::IsNullOrWhiteSpace($OutputPath)) {
            $dir = Split-Path -Parent $OutputPath
            if ($dir -and -not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
            [System.IO.File]::WriteAllText($OutputPath, $md, [System.Text.UTF8Encoding]::new($false))
        }
        return $envelope
    }
    return (Write-UIAOEnvelopeOutput -Envelope $envelope -OutputPath $OutputPath)
}

function ConvertTo-UIAOMasterPlanMarkdown {
    [CmdletBinding()]
    param([Parameter(Mandatory = $true)]$Envelope)
    $d = $Envelope.data
    $lines = @()
    $lines += '# UIAO Master Modernization Plan'
    $lines += ''
    $lines += "Status: $(if ($d.approvable) { 'Approvable (no blockers)' } else { "BLOCKED ($($d.blocker_count) blocker(s) require architect resolution)" })"
    $lines += "Plan seal (content_hash): ``$($Envelope.provenance.content_hash)``"
    $lines += ''
    $lines += '## Component plans'
    $lines += ''
    $lines += '| Plan | Records | Approvable | Source |'
    $lines += '|---|---|---|---|'
    foreach ($c in @($d.component_plans)) {
        $lines += "| $($c.plan_type) | $($c.record_count) | $($c.approvable) | $($c.source_file) |"
    }
    if (@($d.dc_decommission_order).Count -gt 0) {
        $lines += ''
        $lines += '## Domain controller decommissioning order'
        $lines += ''
        $lines += '| Rank | Host |'
        $lines += '|---|---|'
        foreach ($row in @($d.dc_decommission_order)) {
            $lines += "| $($row.decommission_rank) | $($row.host) |"
        }
    }
    if (@($d.blockers).Count -gt 0) {
        $lines += ''
        $lines += '## Blockers'
        $lines += ''
        foreach ($b in @($d.blockers)) {
            $lines += "- **$($b.type)**: $($b.detail)"
        }
    }
    return (($lines -join "`n") + "`n")
}


Export-ModuleMember -Function `
    'New-UIAOComputerModernizationPlan', `
    'New-UIAOGPOMigrationPlan', `
    'New-UIAOIdentityMigrationPlan', `
    'New-UIAODNSMigrationPlan', `
    'New-UIAOPKIMigrationPlan', `
    'Export-UIAOMasterPlan'
