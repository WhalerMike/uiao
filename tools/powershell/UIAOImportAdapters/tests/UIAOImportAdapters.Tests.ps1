# Pester tests for UIAOImportAdapters (canon UIAO_182, ADR-094).
#
# Fully offline: fixtures are written to $TestDrive; the only external
# dependency is a stdlib Python interpreter (json + hashlib) for the canonical
# integrity seal, which the tools/powershell Pester CI runner provides.

BeforeAll {
    $modulePath = Join-Path $PSScriptRoot '..' 'UIAOImportAdapters.psm1' | Resolve-Path
    Import-Module $modulePath -Force

    # Independent re-implementation of the canonical seal, used to assert the
    # module's content_hash equals uiao.ir.models.core.canonical_hash(data).
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

    function New-AzureMigrateCsv {
        param([string]$Path)
        @(
            [pscustomobject]@{ Machine = 'WEB01'; 'Operating system' = 'Windows Server 2019'; 'Azure VM readiness' = 'Ready'; Cores = '4' }
            [pscustomobject]@{ Machine = 'DB01'; 'Operating system' = 'Windows Server 2016'; 'Azure VM readiness' = 'Conditionally ready'; Cores = '8' }
        ) | Export-Csv -LiteralPath $Path -NoTypeInformation
    }

    function New-ScubaJson {
        param([string]$Path)
        $obj = @{
            Results = @(
                @{ 'Control ID' = 'MS.AAD.1.1v1'; Requirement = 'Legacy auth blocked'; Result = 'Pass'; Baseline = 'AAD' }
                @{ 'Control ID' = 'MS.AAD.3.1v1'; Requirement = 'MFA enforced'; Result = 'Fail'; Baseline = 'AAD' }
            )
        }
        ($obj | ConvertTo-Json -Depth 10) | Set-Content -LiteralPath $Path -Encoding UTF8
    }
}

Describe 'Module surface' {
    It 'exports exactly the six UIAO_182 roster functions' {
        $exported = @((Get-Command -Module UIAOImportAdapters).Name)
        $exported.Count | Should -Be 6
        $roster = @(
            'Import-UIAOADReconReport',
            'Import-UIAOAzureMigrateReport',
            'Import-UIAODefenderFindings',
            'Import-UIAOGPOAnalyticsReport',
            'Import-UIAOSCuBAReport',
            'Merge-UIAOAssessmentSources'
        )
        foreach ($fn in $roster) { $exported | Should -Contain $fn }
    }
}

Describe 'Import-UIAOAzureMigrateReport' {
    BeforeAll {
        $csv = Join-Path $TestDrive 'azuremigrate.csv'
        New-AzureMigrateCsv -Path $csv
        $Script:Result = Import-UIAOAzureMigrateReport -ReportPath $csv
    }

    It 'targets the ComputerInventory schema' {
        $Result.target_schema | Should -Be 'ComputerInventory'
        $Result.data.target_schema | Should -Be 'ComputerInventory'
    }

    It 'normalizes each source row into a record' {
        $Result.data.record_count | Should -Be 2
        $Result.data.records[0].name | Should -Be 'WEB01'
        $Result.data.records[0].operating_system | Should -Be 'Windows Server 2019'
        $Result.data.records[0].readiness | Should -Be 'Ready'
    }

    It 'preserves the original columns under source_fields' {
        $Result.data.records[1].source_fields.Machine | Should -Be 'DB01'
        $Result.data.records[1].source_fields.Cores | Should -Be '8'
    }

    It 'stamps a complete provenance envelope' {
        $Result.provenance.source | Should -Be 'AzureMigrate'
        $Result.provenance.version | Should -Be 'unknown'
        $Result.provenance.timestamp | Should -Match '^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$'
        $Result.provenance.content_hash | Should -Match '^[0-9a-f]{64}$'
        $Result.provenance.import_module | Should -Be 'UIAOImportAdapters'
    }

    It 'seals data with the canonical content_hash (matches Python canonical_hash)' {
        $expected = Get-ExpectedHash -DataObject $Result.data
        $Result.provenance.content_hash | Should -Be $expected
    }

    It 'records a supplied SourceVersion in provenance' {
        $csv2 = Join-Path $TestDrive 'azuremigrate2.csv'
        New-AzureMigrateCsv -Path $csv2
        $r = Import-UIAOAzureMigrateReport -ReportPath $csv2 -SourceVersion '2024.05'
        $r.provenance.version | Should -Be '2024.05'
    }
}

Describe 'Import-UIAOSCuBAReport (JSON with wrapped array)' {
    BeforeAll {
        $json = Join-Path $TestDrive 'scuba.json'
        New-ScubaJson -Path $json
        $Script:Result = Import-UIAOSCuBAReport -ReportPath $json
    }

    It 'extracts the wrapped Results array and targets ConformanceEvidence' {
        $Result.target_schema | Should -Be 'ConformanceEvidence'
        $Result.data.record_count | Should -Be 2
        $Result.data.records[0].control_id | Should -Be 'MS.AAD.1.1v1'
        $Result.data.records[1].result | Should -Be 'Fail'
    }

    It 'seals data with the canonical content_hash' {
        (Get-ExpectedHash -DataObject $Result.data) | Should -Be $Result.provenance.content_hash
    }
}

Describe 'Output file round-trip' {
    It 'writes a UTF-8 envelope whose seal survives read-back via Merge integrity check' {
        $csv = Join-Path $TestDrive 'rt.csv'
        New-AzureMigrateCsv -Path $csv
        $out = Join-Path $TestDrive 'rt-out.json'
        $null = Import-UIAOAzureMigrateReport -ReportPath $csv -OutputPath $out
        Test-Path -LiteralPath $out | Should -BeTrue

        $bundle = Merge-UIAOAssessmentSources -SourcePaths $out
        $bundle.sources[0].integrity_ok | Should -BeTrue
        $bundle.sources[0].envelope_complete | Should -BeTrue
    }
}

Describe 'Merge-UIAOAssessmentSources' {
    BeforeAll {
        $csv = Join-Path $TestDrive 'm-am.csv'
        New-AzureMigrateCsv -Path $csv
        $json = Join-Path $TestDrive 'm-scuba.json'
        New-ScubaJson -Path $json

        $Script:AmOut = Join-Path $TestDrive 'm-am-out.json'
        $Script:ScOut = Join-Path $TestDrive 'm-sc-out.json'
        $null = Import-UIAOAzureMigrateReport -ReportPath $csv -OutputPath $Script:AmOut
        $null = Import-UIAOSCuBAReport -ReportPath $json -OutputPath $Script:ScOut
    }

    It 'groups records by target schema across sources' {
        $bundle = Merge-UIAOAssessmentSources -SourcePaths $Script:AmOut, $Script:ScOut
        $bundle.schema | Should -Be 'uiao.import.bundle.v1'
        $bundle.provenance.source_count | Should -Be 2
        $bundle.data.records_by_schema.ComputerInventory.Count | Should -Be 2
        $bundle.data.records_by_schema.ConformanceEvidence.Count | Should -Be 2
        $bundle.data.total_records | Should -Be 4
    }

    It 'seals the bundle with the canonical content_hash' {
        $bundle = Merge-UIAOAssessmentSources -SourcePaths $Script:AmOut, $Script:ScOut
        (Get-ExpectedHash -DataObject $bundle.data) | Should -Be $bundle.provenance.content_hash
    }

    It 'Distinct strategy de-duplicates identical records within a schema' {
        # Merging the same source twice: Union keeps 4, Distinct collapses to 2.
        $union = Merge-UIAOAssessmentSources -SourcePaths $Script:AmOut, $Script:AmOut -MergeStrategy Union
        $union.data.records_by_schema.ComputerInventory.Count | Should -Be 4

        $distinct = Merge-UIAOAssessmentSources -SourcePaths $Script:AmOut, $Script:AmOut -MergeStrategy Distinct
        $distinct.data.records_by_schema.ComputerInventory.Count | Should -Be 2
    }

    It 'flags a broken seal (tampered data) as integrity_ok = false' {
        $tampered = Join-Path $TestDrive 'tampered.json'
        $env = Get-Content -LiteralPath $Script:AmOut -Raw | ConvertFrom-Json
        $env.data.records[0].name = 'TAMPERED-VALUE'   # data changed; hash now stale
        ($env | ConvertTo-Json -Depth 40) | Set-Content -LiteralPath $tampered -Encoding UTF8

        $bundle = Merge-UIAOAssessmentSources -SourcePaths $tampered
        $bundle.sources[0].integrity_ok | Should -BeFalse
    }

    It 'flags an incomplete envelope (missing provenance field)' {
        $incomplete = Join-Path $TestDrive 'incomplete.json'
        $env = Get-Content -LiteralPath $Script:AmOut -Raw | ConvertFrom-Json
        $env.provenance.PSObject.Properties.Remove('timestamp')
        ($env | ConvertTo-Json -Depth 40) | Set-Content -LiteralPath $incomplete -Encoding UTF8

        $bundle = Merge-UIAOAssessmentSources -SourcePaths $incomplete
        $bundle.sources[0].envelope_complete | Should -BeFalse
        $bundle.sources[0].missing_fields | Should -Contain 'timestamp'
    }
}

Describe 'Input validation (SI-10)' {
    It 'throws on a missing report file' {
        { Import-UIAOAzureMigrateReport -ReportPath (Join-Path $TestDrive 'does-not-exist.csv') } |
            Should -Throw '*not found*'
    }

    It 'throws on an unsupported extension' {
        $bad = Join-Path $TestDrive 'report.txt'
        'irrelevant' | Set-Content -LiteralPath $bad -Encoding UTF8
        { Import-UIAOADReconReport -ReportPath $bad } | Should -Throw '*Unsupported source extension*'
    }

    It 'throws on an empty JSON file' {
        $empty = Join-Path $TestDrive 'empty.json'
        '' | Set-Content -LiteralPath $empty -Encoding UTF8
        { Import-UIAOSCuBAReport -ReportPath $empty } | Should -Throw '*empty*'
    }
}
