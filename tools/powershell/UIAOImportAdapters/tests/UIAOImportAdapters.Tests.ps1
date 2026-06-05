# Pester tests for UIAOImportAdapters (ADR-094 / UIAO_182).
#
# Fully OFFLINE: no Python, no network, no Microsoft.Graph. The canonical-JSON
# equivalence is pinned against ground-truth strings/hashes computed by
# src/uiao/ir/models/core.py::canonical_json / canonical_hash, so these tests
# prove the native PowerShell serializer matches Python WITHOUT running Python.
# Regenerate the baked constants with, e.g.:
#   python -c "import sys;sys.path.insert(0,'src'); \
#     from uiao.ir.models.core import canonical_hash; print(canonical_hash({...}))"

BeforeAll {
    $modulePath = Join-Path $PSScriptRoot '..' 'UIAOImportAdapters.psm1' | Resolve-Path
    Import-Module $modulePath -Force

    function New-JsonFile {
        param([string]$Path, $Object)
        $json = $Object | ConvertTo-Json -Depth 10
        [System.IO.File]::WriteAllText($Path, $json, [System.Text.UTF8Encoding]::new($false))
    }
}

Describe 'Canonical JSON parity with Python canonical_json' {
    It 'serializes a mixed object with ordinal-sorted keys and compact separators' {
        $obj = [ordered]@{ b = 2; a = 'x'; list = @(3, 1, 2); u = 'café' }
        ConvertTo-UIAOCanonicalJson $obj |
            Should -BeExactly '{"a":"x","b":2,"list":[3,1,2],"u":"café"}'
    }

    It 'escapes quotes, backslashes, tabs, null and booleans like Python' {
        $obj = [ordered]@{ q = "he said `"hi`"`tand\left"; z = $null; ok = $true }
        ConvertTo-UIAOCanonicalJson $obj |
            Should -BeExactly '{"ok":true,"q":"he said \"hi\"\tand\\left","z":null}'
    }

    It 'emits null / true / false / integers as bare tokens' {
        ConvertTo-UIAOCanonicalJson $null | Should -BeExactly 'null'
        ConvertTo-UIAOCanonicalJson $true | Should -BeExactly 'true'
        ConvertTo-UIAOCanonicalJson $false | Should -BeExactly 'false'
        ConvertTo-UIAOCanonicalJson 42 | Should -BeExactly '42'
    }

    It 'serializes an empty array and empty object' {
        ConvertTo-UIAOCanonicalJson @() | Should -BeExactly '[]'
        ConvertTo-UIAOCanonicalJson ([ordered]@{}) | Should -BeExactly '{}'
    }
}

Describe 'Content hash parity with Python canonical_hash' {
    # Ground-truth SHA-256 values computed by canonical_hash() in
    # src/uiao/ir/models/core.py (see file header).
    It 'matches Python for a mixed object' {
        $obj = [ordered]@{ b = 2; a = 'x'; list = @(3, 1, 2); u = 'café' }
        Get-UIAOContentHash $obj |
            Should -BeExactly '5390da13cdac367c36e557673d87f2a6bd1e1a02564d907d485e6bbb7f4f9fe2'
    }

    It 'matches Python for an object with escapes / null / bool' {
        $obj = [ordered]@{ q = "he said `"hi`"`tand\left"; z = $null; ok = $true }
        Get-UIAOContentHash $obj |
            Should -BeExactly '2956384585f7f64cd312cf650cc78cd663b8330df543ff2439936502284a7357'
    }

    It 'matches Python for a ComputerInventory data payload' {
        $data = [ordered]@{
            computers = @([ordered]@{ name = 'DC01'; os = 'Windows Server 2019'; source = 'ADRecon' })
            count     = 1
        }
        Get-UIAOContentHash $data |
            Should -BeExactly 'e3606a0a9fa80d40776f646899a20741ad2c303dddd55fccca287669552daae2'
    }

    It 'is insensitive to source key insertion order (ordinal sort)' {
        $a = [ordered]@{ a = 1; b = 2 }
        $b = [ordered]@{ b = 2; a = 1 }
        (Get-UIAOContentHash $a) | Should -BeExactly (Get-UIAOContentHash $b)
    }
}

Describe 'Provenance envelope contract' {
    It 'New-UIAOAssessmentArtifact seals data and fills required fields' {
        $data = [ordered]@{ k = 'v' }
        $art = New-UIAOAssessmentArtifact -Target 'Test' -Data $data `
            -SourceTool 'tool' -SourceVersion '1.0' -Timestamp '2026-06-05T00:00:00Z'
        $art.provenance.source | Should -BeExactly 'tool'
        $art.provenance.version | Should -BeExactly '1.0'
        $art.provenance.timestamp | Should -BeExactly '2026-06-05T00:00:00Z'
        $art.provenance.content_hash | Should -BeExactly (Get-UIAOContentHash $data)
        $art.schema | Should -BeExactly 'uiao.assessment/Test/v1'
    }
}

Describe 'Import-UIAOAzureMigrateReport' {
    It 'normalizes machines to ComputerInventory with a valid seal' {
        $src = Join-Path $TestDrive 'migrate.json'
        New-JsonFile $src @{ machines = @(
                @{ MachineName = 'web01'; OperatingSystem = 'Windows Server 2019'; Cores = 4; MemoryInMB = 8192; IPAddresses = @('10.0.0.1') },
                @{ MachineName = 'db01'; OperatingSystem = 'Windows Server 2022'; Cores = 8; MemoryInMB = 16384 }
            ) }
        $art = Import-UIAOAzureMigrateReport -ReportPath $src -Timestamp '2026-06-05T00:00:00Z'
        $art.data.count | Should -Be 2
        $art.data.computers[0].name | Should -BeExactly 'web01'
        $art.data.computers[0].cores | Should -Be 4
        $art.data.computers[0].ipAddresses[0] | Should -BeExactly '10.0.0.1'
        $art.provenance.source | Should -BeExactly 'Azure Migrate'
        $art.provenance.content_hash | Should -BeExactly (Get-UIAOContentHash $art.data)
    }

    It 'writes a UTF-8 (no BOM) artifact file when -OutputPath is given' {
        $src = Join-Path $TestDrive 'm2.json'
        New-JsonFile $src @{ machines = @(@{ MachineName = 'x'; OperatingSystem = 'Linux' }) }
        $out = Join-Path $TestDrive 'out\m2.json'
        Import-UIAOAzureMigrateReport -ReportPath $src -OutputPath $out -Timestamp '2026-06-05T00:00:00Z' | Out-Null
        Test-Path $out | Should -BeTrue
        $bytes = [System.IO.File]::ReadAllBytes($out)
        # No UTF-8 BOM (EF BB BF)
        ($bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) | Should -BeFalse
        $reloaded = Get-Content $out -Raw | ConvertFrom-Json
        $reloaded.data.computers[0].name | Should -BeExactly 'x'
    }
}

Describe 'Import-UIAOSCuBAReport' {
    It 'interprets RequirementMet (Pass/Warning/else) per UIAO_002 semantics' {
        $src = Join-Path $TestDrive 'scuba.json'
        New-JsonFile $src @{ Results = @(
                @{ PolicyId = 'MS.AAD.1.1v1'; Control = 'IA-2(1)'; RequirementMet = 'Pass' },
                @{ PolicyId = 'MS.AAD.3.1v1'; Control = 'IA-2'; RequirementMet = 'Fail' },
                @{ PolicyId = 'MS.EXO.1.1v1'; Control = 'SC-7'; RequirementMet = 'Warning' }
            ) }
        $art = Import-UIAOSCuBAReport -ReportPath $src -Timestamp '2026-06-05T00:00:00Z'
        $art.data.summary.pass | Should -Be 1
        $art.data.summary.fail | Should -Be 1
        $art.data.summary.warn | Should -Be 1
        ($art.data.policies | Where-Object { $_.policyId -eq 'MS.AAD.1.1v1' }).result | Should -BeExactly 'pass'
    }
}

Describe 'Import-UIAOGPOAnalyticsReport' {
    It 'computes MDM support percent and maps GPO fields' {
        $src = Join-Path $TestDrive 'gpo.json'
        New-JsonFile $src @{ value = @(
                @{ groupPolicyName = 'Baseline'; groupPolicyObjectId = 'g1'; supportedSettings = 8; totalSettings = 10; unsupportedSettings = 2 }
            ) }
        $art = Import-UIAOGPOAnalyticsReport -ReportPath $src -Timestamp '2026-06-05T00:00:00Z'
        $art.data.gpos[0].name | Should -BeExactly 'Baseline'
        $art.data.gpos[0].mdmSupportPercent | Should -Be 80
        $art.data.gpos[0].unsupportedSettings | Should -Be 2
    }
}

Describe 'Import-UIAODefenderFindings' {
    It 'lowercases severity and captures score' {
        $src = Join-Path $TestDrive 'def.json'
        New-JsonFile $src @{ secureScore = 72; findings = @(
                @{ id = 'F1'; title = 'Legacy auth enabled'; severity = 'High'; category = 'Identity'; recommendation = 'Block legacy auth' }
            ) }
        $art = Import-UIAODefenderFindings -ReportPath $src -Timestamp '2026-06-05T00:00:00Z'
        $art.data.score | Should -Be 72
        $art.data.findings[0].severity | Should -BeExactly 'high'
    }
}

Describe 'Import-UIAOADReconReport' {
    It 'ingests a CSV Computers export into ComputerInventory' {
        $src = Join-Path $TestDrive 'computers.csv'
        @'
Name,DNSHostName,OperatingSystem,Enabled,LastLogonDate
DC01,dc01.contoso.local,Windows Server 2019,TRUE,2026-06-01
WS10,ws10.contoso.local,Windows 10,FALSE,2025-01-01
'@ | Set-Content -Path $src -Encoding utf8
        $art = Import-UIAOADReconReport -ReportPath $src -Timestamp '2026-06-05T00:00:00Z'
        $art.data.count | Should -Be 2
        ($art.data.computers | Where-Object { $_.name -eq 'DC01' }).enabled | Should -BeTrue
        ($art.data.computers | Where-Object { $_.name -eq 'WS10' }).enabled | Should -BeFalse
    }
}

Describe 'Merge-UIAOAssessmentSources' {
    BeforeEach {
        $a1 = Join-Path $TestDrive 'a1.json'
        $a2 = Join-Path $TestDrive 'a2.json'
        $m1 = Join-Path $TestDrive 'mi1.json'
        New-JsonFile $m1 @{ machines = @(@{ MachineName = 'DC01'; OperatingSystem = 'WS2019' }) }
        Import-UIAOAzureMigrateReport -ReportPath $m1 -OutputPath $a1 -Timestamp '2026-06-05T00:00:00Z' | Out-Null
        $c1 = Join-Path $TestDrive 'c1.csv'
        @'
Name,OperatingSystem
DC01,WS2019
APP02,WS2022
'@ | Set-Content -Path $c1 -Encoding utf8
        Import-UIAOADReconReport -ReportPath $c1 -OutputPath $a2 -Timestamp '2026-06-05T00:00:00Z' | Out-Null
        $script:A1 = $a1; $script:A2 = $a2
    }

    It 'union concatenates computers across sources' {
        $bundle = Merge-UIAOAssessmentSources -SourcePaths @($script:A1, $script:A2) -Timestamp '2026-06-05T00:00:00Z'
        $bundle.data.computers.Count | Should -Be 3
        $bundle.data.sources.Count | Should -Be 2
        $bundle.provenance.content_hash | Should -BeExactly (Get-UIAOContentHash $bundle.data)
    }

    It 'dedupe removes duplicate computer names case-insensitively' {
        $bundle = Merge-UIAOAssessmentSources -SourcePaths @($script:A1, $script:A2) -MergeStrategy dedupe -Timestamp '2026-06-05T00:00:00Z'
        $bundle.data.computers.Count | Should -Be 2
    }

    It 'requires at least two sources' {
        { Merge-UIAOAssessmentSources -SourcePaths @($script:A1) } | Should -Throw
    }
}

Describe 'Determinism and error handling' {
    It 'produces an identical seal for identical input + timestamp' {
        $src = Join-Path $TestDrive 'det.json'
        New-JsonFile $src @{ machines = @(@{ MachineName = 'n1'; OperatingSystem = 'os' }) }
        $h1 = (Import-UIAOAzureMigrateReport -ReportPath $src -Timestamp '2026-06-05T00:00:00Z').provenance.content_hash
        $h2 = (Import-UIAOAzureMigrateReport -ReportPath $src -Timestamp '2026-06-05T00:00:00Z').provenance.content_hash
        $h1 | Should -BeExactly $h2
    }

    It 'throws on a missing report file' {
        { Import-UIAOAzureMigrateReport -ReportPath (Join-Path $TestDrive 'nope.json') } | Should -Throw
    }

    It 'throws on an unsupported report extension' {
        $bad = Join-Path $TestDrive 'bad.xlsx'
        Set-Content -Path $bad -Value 'x' -Encoding utf8
        { Import-UIAOADReconReport -ReportPath $bad } | Should -Throw
    }
}
