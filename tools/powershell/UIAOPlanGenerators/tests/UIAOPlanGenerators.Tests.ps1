# Pester tests for UIAOPlanGenerators (canon UIAO_183, ADR-094).
#
# Fully offline: fixtures are normalized assessment envelopes written to
# $TestDrive. The only external dependency is a stdlib Python interpreter
# (json + hashlib) for the canonical integrity seal.

BeforeAll {
    $modulePath = Join-Path $PSScriptRoot '..' 'UIAOPlanGenerators.psm1' | Resolve-Path
    Import-Module $modulePath -Force

    $Script:Py = if ($env:UIAO_PYTHON) { $env:UIAO_PYTHON }
    elseif (Get-Command python3 -ErrorAction SilentlyContinue) { 'python3' }
    else { 'python' }

    function Get-ExpectedHash {
        param([Parameter(Mandatory = $true)] $DataObject)
        $json = $DataObject | ConvertTo-Json -Depth 40
        $pyScript = @'
import sys, json, hashlib
data = json.load(sys.stdin)
canon = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
sys.stdout.write(hashlib.sha256(canon.encode("utf-8")).hexdigest())
'@
        return (($json | & $Script:Py '-c' $pyScript) -join '').Trim()
    }

    # Write a normalized assessment envelope (the shape the generators consume).
    function Write-Assessment {
        param([string]$Path, [string]$Schema, [object[]]$Records, [string]$Source = 'TestProducer')
        $env = @{
            target_schema = $Schema
            provenance    = @{ source = $Source; version = '1.0'; timestamp = '2026-06-05T00:00:00Z'; content_hash = 'seed-hash' }
            data          = @{ records = $Records }
        }
        ($env | ConvertTo-Json -Depth 12) | Set-Content -LiteralPath $Path -Encoding UTF8
    }
}

Describe 'Module surface' {
    It 'exports exactly the six UIAO_183 roster functions' {
        $exported = @((Get-Command -Module UIAOPlanGenerators).Name)
        $exported.Count | Should -Be 6
        foreach ($fn in @(
                'Export-UIAOMasterPlan', 'New-UIAOComputerModernizationPlan', 'New-UIAODNSMigrationPlan',
                'New-UIAOGPOMigrationPlan', 'New-UIAOIdentityMigrationPlan', 'New-UIAOPKIMigrationPlan')) {
            $exported | Should -Contain $fn
        }
    }
}

Describe 'New-UIAOComputerModernizationPlan' {
    BeforeAll {
        $Script:CompAssessment = Join-Path $TestDrive 'computers.json'
        Write-Assessment -Path $Script:CompAssessment -Schema 'ComputerInventory' -Source 'AzureMigrate' -Records @(
            @{ name = 'PC1'; operating_system = 'Windows 10'; readiness = 'Ready' }
            @{ name = 'PC2'; operating_system = 'Windows 11'; readiness = 'Ready' }
            @{ name = 'PC3'; operating_system = 'Windows 10'; readiness = 'Not ready' }
            @{ name = 'PC4'; operating_system = 'Windows 10'; readiness = 'Conditionally ready' }
        )
        $Script:Plan = New-UIAOComputerModernizationPlan -AssessmentPath $Script:CompAssessment
    }

    It 'maps OS + readiness to a deterministic action per device' {
        $byName = @{}; foreach ($r in $Plan.data.records) { $byName[$r.name] = $r.action }
        $byName['PC1'] | Should -Be 'in_place_upgrade'
        $byName['PC2'] | Should -Be 'compliant'
        $byName['PC3'] | Should -Be 'replace_hardware'
        $byName['PC4'] | Should -Be 'remediate_then_upgrade'
    }

    It 'honors -TargetOS and records it' {
        $p = New-UIAOComputerModernizationPlan -AssessmentPath $Script:CompAssessment -TargetOS 'Windows 10'
        ($p.data.records | Where-Object { $_.name -eq 'PC1' }).action | Should -Be 'compliant'
        $p.data.target_os | Should -Be 'Windows 10'
    }

    It 'cites the source assessment in derived_from' {
        $Plan.provenance.derived_from.source | Should -Be 'AzureMigrate'
        $Plan.provenance.derived_from.content_hash | Should -Be 'seed-hash'
        $Plan.provenance.derived_from.source_file | Should -Be 'computers.json'
    }

    It 'seals the plan and is reproducible (same assessment -> same hash)' {
        (Get-ExpectedHash -DataObject $Plan.data) | Should -Be $Plan.provenance.content_hash
        $again = New-UIAOComputerModernizationPlan -AssessmentPath $Script:CompAssessment
        $again.provenance.content_hash | Should -Be $Plan.provenance.content_hash
    }
}

Describe 'New-UIAOGPOMigrationPlan' {
    It 'maps MDM support to migration actions' {
        $path = Join-Path $TestDrive 'gpo.json'
        Write-Assessment -Path $path -Schema 'GPOMigrationTracker' -Records @(
            @{ gpo_name = 'G1'; setting_name = 'S1'; mdm_support = 'true' }
            @{ gpo_name = 'G2'; setting_name = 'S2'; mdm_support = 'false' }
            @{ gpo_name = 'G3'; setting_name = 'S3'; mdm_support = 'partial' }
            @{ gpo_name = 'G4'; setting_name = 'S4'; mdm_support = '' }
        )
        $plan = New-UIAOGPOMigrationPlan -AssessmentPath $path
        $byName = @{}; foreach ($r in $plan.data.records) { $byName[$r.gpo_name] = $r.action }
        $byName['G1'] | Should -Be 'migrate_to_intune'
        $byName['G2'] | Should -Be 'no_intune_equivalent'
        $byName['G3'] | Should -Be 'migrate_with_review'
        $byName['G4'] | Should -Be 'manual_review'
    }
}

Describe 'New-UIAOIdentityMigrationPlan' {
    It 'assigns deterministic waves of -WaveSize' {
        $path = Join-Path $TestDrive 'identity.json'
        Write-Assessment -Path $path -Schema 'EntraUserInventory' -Records @(
            @{ user_principal_name = 'e@x' }, @{ user_principal_name = 'a@x' }
            @{ user_principal_name = 'c@x' }, @{ user_principal_name = 'b@x' }
            @{ user_principal_name = 'd@x' }
        )
        $plan = New-UIAOIdentityMigrationPlan -AssessmentPath $path -WaveSize 2
        $plan.data.record_count | Should -Be 5
        $plan.data.wave_count | Should -Be 3
        $byPrincipal = @{}; foreach ($r in $plan.data.records) { $byPrincipal[$r.principal] = $r.wave }
        $byPrincipal['a@x'] | Should -Be 1
        $byPrincipal['b@x'] | Should -Be 1
        $byPrincipal['c@x'] | Should -Be 2
        $byPrincipal['e@x'] | Should -Be 3
    }
}

Describe 'New-UIAODNSMigrationPlan (topological order + blockers)' {
    It 'orders zones prerequisite-first and is approvable when acyclic' {
        $path = Join-Path $TestDrive 'dns.json'
        Write-Assessment -Path $path -Schema 'DNSZones' -Records @(
            @{ zone = 'hr.corp.local'; depends_on = @('corp.local'); domain = 'corp' }
            @{ zone = 'corp.local'; depends_on = @(); domain = 'corp' }
            @{ zone = 'it.corp.local'; depends_on = @('corp.local'); domain = 'corp' }
        )
        $plan = New-UIAODNSMigrationPlan -AssessmentPath $path
        $plan.data.approvable | Should -BeTrue
        $plan.data.records[0].zone | Should -Be 'corp.local'   # prerequisite first
        @($plan.data.records).Count | Should -Be 3
    }

    It 'flags a cross-domain dependency as a blocker (not approvable)' {
        $path = Join-Path $TestDrive 'dns-xdomain.json'
        Write-Assessment -Path $path -Schema 'DNSZones' -Records @(
            @{ zone = 'a.local'; depends_on = @('b.local'); domain = 'A' }
            @{ zone = 'b.local'; depends_on = @(); domain = 'B' }
        )
        $plan = New-UIAODNSMigrationPlan -AssessmentPath $path
        $plan.data.approvable | Should -BeFalse
        ($plan.data.blockers | Where-Object { $_.type -eq 'cross_domain' }) | Should -Not -BeNullOrEmpty
    }

    It 'flags a dependency cycle as a blocker' {
        $path = Join-Path $TestDrive 'dns-cycle.json'
        Write-Assessment -Path $path -Schema 'DNSZones' -Records @(
            @{ zone = 'x'; depends_on = @('y'); domain = 'd' }
            @{ zone = 'y'; depends_on = @('x'); domain = 'd' }
        )
        $plan = New-UIAODNSMigrationPlan -AssessmentPath $path
        $plan.data.approvable | Should -BeFalse
        ($plan.data.blockers | Where-Object { $_.type -eq 'cycle' }) | Should -Not -BeNullOrEmpty
    }
}

Describe 'New-UIAOPKIMigrationPlan' {
    It 'orders the CA hierarchy root-first' {
        $path = Join-Path $TestDrive 'pki.json'
        Write-Assessment -Path $path -Schema 'PKIHierarchy' -Records @(
            @{ ca = 'IssuingCA'; depends_on = @('RootCA'); domain = 'pki' }
            @{ ca = 'RootCA'; depends_on = @(); domain = 'pki' }
        )
        $plan = New-UIAOPKIMigrationPlan -AssessmentPath $path
        $plan.data.records[0].ca | Should -Be 'RootCA'
        $plan.data.records[1].ca | Should -Be 'IssuingCA'
    }
}

Describe 'Export-UIAOMasterPlan' {
    BeforeAll {
        $comp = Join-Path $TestDrive 'm-comp.json'
        Write-Assessment -Path $comp -Schema 'ComputerInventory' -Records @(@{ name = 'PC1'; operating_system = 'Windows 10'; readiness = 'Ready' })
        $Script:CompPlan = Join-Path $TestDrive 'm-comp-plan.json'
        $null = New-UIAOComputerModernizationPlan -AssessmentPath $comp -OutputPath $Script:CompPlan

        $dns = Join-Path $TestDrive 'm-dns.json'
        Write-Assessment -Path $dns -Schema 'DNSZones' -Records @(
            @{ zone = 'corp.local'; depends_on = @(); domain = 'corp' }
            @{ zone = 'hr.corp.local'; depends_on = @('corp.local'); domain = 'corp' }
        )
        $Script:DnsPlan = Join-Path $TestDrive 'm-dns-plan.json'
        $null = New-UIAODNSMigrationPlan -AssessmentPath $dns -OutputPath $Script:DnsPlan

        $Script:ServerDeps = Join-Path $TestDrive 'm-servers.json'
        Write-Assessment -Path $Script:ServerDeps -Schema 'ServerDependencyRegistry' -Records @(
            @{ host = 'DC1'; depends_on = @(); domain = 'corp' }
            @{ host = 'APP1'; depends_on = @('DC1'); domain = 'corp' }
        )
    }

    It 'assembles components and computes the DC decommissioning order (reverse topo)' {
        $master = Export-UIAOMasterPlan -PlanPaths $Script:CompPlan, $Script:DnsPlan -ServerDependencyPath $Script:ServerDeps
        $master.plan_type | Should -Be 'MasterModernizationPlan'
        $master.data.component_plan_count | Should -Be 2
        $master.data.approvable | Should -BeTrue

        # Migration order is DC1 then APP1; decommissioning reverses it:
        # APP1 (the dependent) is decommissioned first, DC1 last.
        $order = @($master.data.dc_decommission_order)
        ($order | Where-Object { $_.host -eq 'APP1' }).decommission_rank | Should -Be 1
        ($order | Where-Object { $_.host -eq 'DC1' }).decommission_rank | Should -Be 2
    }

    It 'aggregates component blockers and marks the master not approvable' {
        $xdns = Join-Path $TestDrive 'm-xdns.json'
        Write-Assessment -Path $xdns -Schema 'DNSZones' -Records @(
            @{ zone = 'a.local'; depends_on = @('b.local'); domain = 'A' }
            @{ zone = 'b.local'; depends_on = @(); domain = 'B' }
        )
        $xPlan = Join-Path $TestDrive 'm-xdns-plan.json'
        $null = New-UIAODNSMigrationPlan -AssessmentPath $xdns -OutputPath $xPlan

        $master = Export-UIAOMasterPlan -PlanPaths $xPlan
        $master.data.approvable | Should -BeFalse
        $master.data.blocker_count | Should -BeGreaterThan 0
    }

    It 'renders a markdown master plan to -OutputPath' {
        $md = Join-Path $TestDrive 'master.md'
        $null = Export-UIAOMasterPlan -PlanPaths $Script:CompPlan, $Script:DnsPlan -ServerDependencyPath $Script:ServerDeps -Format markdown -OutputPath $md
        Test-Path -LiteralPath $md | Should -BeTrue
        $text = Get-Content -LiteralPath $md -Raw
        $text | Should -Match 'UIAO Master Modernization Plan'
        $text | Should -Match 'decommissioning order'
    }

    It 'seals the master plan with the canonical content_hash' {
        $master = Export-UIAOMasterPlan -PlanPaths $Script:CompPlan, $Script:DnsPlan -ServerDependencyPath $Script:ServerDeps
        (Get-ExpectedHash -DataObject $master.data) | Should -Be $master.provenance.content_hash
    }
}

Describe 'Input validation' {
    It 'throws on a missing assessment file' {
        { New-UIAOComputerModernizationPlan -AssessmentPath (Join-Path $TestDrive 'nope.json') } | Should -Throw '*not found*'
    }

    It 'throws on an empty assessment file' {
        $empty = Join-Path $TestDrive 'empty.json'
        '' | Set-Content -LiteralPath $empty -Encoding UTF8
        { New-UIAODNSMigrationPlan -AssessmentPath $empty } | Should -Throw '*empty*'
    }
}
