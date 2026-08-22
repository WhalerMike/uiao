# Pester tests for OrgPathTools — Model C per-facet PowerShell wrapper (ADR-084 §C8).
# Tests run against a fixture codebook (no real Python required).

BeforeAll {
    $modulePath = Join-Path $PSScriptRoot '..' 'OrgPathTools.psm1' | Resolve-Path
    Import-Module $modulePath -Force

    function New-FixtureCodebook {
        return @{
            schema_version = '2.0.0'
            model          = 'C'
            facets         = @{
                region          = @{
                    attribute     = 'extensionAttribute1'
                    kind          = 'enumerated'
                    description   = 'Geographic region'
                    enumeration   = @(
                        @{ value = 'NCR'; description = 'NCR' },
                        @{ value = 'EASTUS'; description = 'East' },
                        @{ value = 'WESTUS'; description = 'West' },
                        @{ value = 'EMEA'; description = 'EMEA' }
                    )
                    deprecated    = @()
                    value_pattern = $null
                    allow_empty   = $false
                }
                department      = @{
                    attribute     = 'extensionAttribute2'
                    kind          = 'enumerated'
                    description   = 'Business unit'
                    enumeration   = @(
                        @{ value = 'IT'; description = 'IT' },
                        @{ value = 'HR'; description = 'HR' },
                        @{ value = 'Finance'; description = 'Finance' },
                        @{ value = 'Legal'; description = 'Legal' }
                    )
                    deprecated    = @()
                    value_pattern = $null
                    allow_empty   = $false
                }
                division        = @{
                    attribute     = 'extensionAttribute3'
                    kind          = 'enumerated'
                    description   = 'Division'
                    enumeration   = @(
                        @{ value = 'CyberOps'; description = 'CyberOps' },
                        @{ value = 'InfraOps'; description = 'InfraOps' },
                        @{ value = 'AppDev'; description = 'AppDev' }
                    )
                    deprecated    = @(
                        @{ value = 'OldCyber'; replaced_by = 'CyberOps' }
                    )
                    value_pattern = $null
                    allow_empty   = $false
                }
                role            = @{
                    attribute     = 'extensionAttribute4'
                    kind          = 'enumerated'
                    description   = 'Role'
                    enumeration   = @(
                        @{ value = 'Analyst'; description = 'Analyst' },
                        @{ value = 'Engineer'; description = 'Engineer' },
                        @{ value = 'Manager'; description = 'Manager' },
                        @{ value = 'Director'; description = 'Director' }
                    )
                    deprecated    = @()
                    value_pattern = $null
                    allow_empty   = $false
                }
                cost_center     = @{
                    attribute     = 'extensionAttribute5'
                    kind          = 'enumerated'
                    description   = 'CostCenter'
                    enumeration   = @(
                        @{ value = 'CC-BAL'; description = 'Baltimore' }
                    )
                    deprecated    = @()
                    value_pattern = $null
                    allow_empty   = $false
                }
                classification  = @{
                    attribute     = 'extensionAttribute6'
                    kind          = 'enumerated'
                    description   = 'Classification'
                    enumeration   = @(
                        @{ value = 'Employee'; description = 'Employee' },
                        @{ value = 'Contractor'; description = 'Contractor' }
                    )
                    deprecated    = @()
                    value_pattern = $null
                    allow_empty   = $false
                }
                hire_date       = @{
                    attribute     = 'extensionAttribute7'
                    kind          = 'typed'
                    description   = 'Hire date'
                    enumeration   = @()
                    deprecated    = @()
                    value_pattern = '^\d{4}-\d{2}-\d{2}$'
                    allow_empty   = $false
                }
                term_date       = @{
                    attribute     = 'extensionAttribute8'
                    kind          = 'typed'
                    description   = 'Term date'
                    enumeration   = @()
                    deprecated    = @()
                    value_pattern = '^\d{4}-\d{2}-\d{2}$'
                    allow_empty   = $true
                }
                clearance_level = @{
                    attribute     = 'extensionAttribute9'
                    kind          = 'enumerated'
                    description   = 'Clearance'
                    enumeration   = @(
                        @{ value = 'None'; description = 'None' },
                        @{ value = 'Secret'; description = 'Secret' },
                        @{ value = 'TopSecret'; description = 'TS' }
                    )
                    deprecated    = @()
                    value_pattern = $null
                    allow_empty   = $false
                }
                account_type    = @{
                    attribute     = 'extensionAttribute10'
                    kind          = 'enumerated'
                    description   = 'Account type'
                    enumeration   = @(
                        @{ value = 'Standard'; description = 'Standard' },
                        @{ value = 'Privileged'; description = 'Privileged' }
                    )
                    deprecated    = @()
                    value_pattern = $null
                    allow_empty   = $false
                }
                reserved_11     = @{
                    attribute     = 'extensionAttribute11'
                    kind          = 'reserved'
                    description   = 'Reserved'
                    enumeration   = @()
                    deprecated    = @()
                    value_pattern = $null
                    allow_empty   = $false
                }
            }
        }
    }
}

Describe 'Test-OrgPathFacetValue — enumerated facet semantics' {
    It 'returns IsActive=True for a known value' {
        $cb = New-FixtureCodebook
        $result = Test-OrgPathFacetValue -Facet 'region' -Value 'NCR' -Codebook $cb
        $result.IsValid | Should -Be $true
        $result.IsActive | Should -Be $true
        $result.IsDeprecated | Should -Be $false
    }

    It 'returns IsActive=False for an unknown value' {
        $cb = New-FixtureCodebook
        $result = Test-OrgPathFacetValue -Facet 'region' -Value 'MARS' -Codebook $cb
        $result.IsValid | Should -Be $false
        $result.IsActive | Should -Be $false
    }

    It 'returns IsDeprecated=True with replacement_for set' {
        $cb = New-FixtureCodebook
        $result = Test-OrgPathFacetValue -Facet 'division' -Value 'OldCyber' -Codebook $cb
        $result.IsValid | Should -Be $false
        $result.IsDeprecated | Should -Be $true
        $result.ReplacementFor | Should -Be 'CyberOps'
    }
}

Describe 'Test-OrgPathFacetValue — typed facet semantics' {
    It 'accepts ISO 8601 date for hire_date' {
        $cb = New-FixtureCodebook
        $result = Test-OrgPathFacetValue -Facet 'hire_date' -Value '2024-01-15' -Codebook $cb
        $result.IsValid | Should -Be $true
    }

    It 'rejects US-format date for hire_date' {
        $cb = New-FixtureCodebook
        $result = Test-OrgPathFacetValue -Facet 'hire_date' -Value '01/15/2024' -Codebook $cb
        $result.IsValid | Should -Be $false
    }

    It 'accepts empty value for term_date (allow_empty)' {
        $cb = New-FixtureCodebook
        $result = Test-OrgPathFacetValue -Facet 'term_date' -Value '' -Codebook $cb
        $result.IsValid | Should -Be $true
        $result.Reason | Should -Be 'Empty (allowed)'
    }

    It 'rejects empty value for hire_date (no allow_empty)' {
        $cb = New-FixtureCodebook
        $result = Test-OrgPathFacetValue -Facet 'hire_date' -Value '' -Codebook $cb
        $result.IsValid | Should -Be $false
    }
}

Describe 'Test-OrgPathFacetValue — reserved facet semantics' {
    It 'accepts null/empty for reserved facet' {
        $cb = New-FixtureCodebook
        $result = Test-OrgPathFacetValue -Facet 'reserved_11' -Value '' -Codebook $cb
        $result.IsValid | Should -Be $true
    }

    It 'rejects any value on reserved facet' {
        $cb = New-FixtureCodebook
        $result = Test-OrgPathFacetValue -Facet 'reserved_11' -Value 'rogue' -Codebook $cb
        $result.IsValid | Should -Be $false
        $result.Reason | Should -Match 'Reserved'
    }
}

Describe 'Test-OrgPathFacetValue — unknown facet handling' {
    It 'returns IsValid=False with explanatory Reason for unknown facet' {
        $cb = New-FixtureCodebook
        $result = Test-OrgPathFacetValue -Facet 'nonexistent' -Value 'x' -Codebook $cb
        $result.IsValid | Should -Be $false
        $result.Reason | Should -Match 'Unknown facet'
    }
}

Describe 'Test-OrgPathFacets — per-principal 10-facet validation (offline via -PrincipalSnapshot)' {
    It 'returns 10 per-facet results for a fully-populated snapshot' {
        $cb = New-FixtureCodebook
        $snapshot = @{
            extensionAttribute1  = 'NCR'
            extensionAttribute2  = 'IT'
            extensionAttribute3  = 'CyberOps'
            extensionAttribute4  = 'Engineer'
            extensionAttribute5  = 'CC-BAL'
            extensionAttribute6  = 'Employee'
            extensionAttribute7  = '2024-01-15'
            extensionAttribute8  = ''
            extensionAttribute9  = 'Secret'
            extensionAttribute10 = 'Standard'
        }
        $results = Test-OrgPathFacets -PrincipalSnapshot $snapshot -Codebook $cb
        $results.Count | Should -Be 10
        ($results | Where-Object { $_.IsValid }).Count | Should -Be 10
    }

    It 'flags per-facet drift independently — one bad facet, nine clean' {
        $cb = New-FixtureCodebook
        $snapshot = @{
            extensionAttribute1  = 'NCR'
            extensionAttribute2  = 'BogusDept'  # orgpath-codebook-allow: negative fixture
            extensionAttribute3  = 'CyberOps'
            extensionAttribute4  = 'Engineer'
            extensionAttribute5  = 'CC-BAL'
            extensionAttribute6  = 'Employee'
            extensionAttribute7  = '2024-01-15'
            extensionAttribute8  = ''
            extensionAttribute9  = 'Secret'
            extensionAttribute10 = 'Standard'
        }
        $results = Test-OrgPathFacets -PrincipalSnapshot $snapshot -Codebook $cb
        $invalid = @($results | Where-Object { -not $_.IsValid })
        $invalid.Count | Should -Be 1
        $invalid[0].Facet | Should -Be 'department'
        $invalid[0].Value | Should -Be 'BogusDept'
    }

    It 'returns one result per canonical slot binding' {
        $cb = New-FixtureCodebook
        $snapshot = @{ extensionAttribute1 = 'NCR' }
        $results = Test-OrgPathFacets -PrincipalSnapshot $snapshot -Codebook $cb
        $slots = $results | ForEach-Object { $_.Slot }
        $slots | Should -Contain 'extensionAttribute1'
        $slots | Should -Contain 'extensionAttribute10'
        $slots.Count | Should -Be 10
    }

    It 'flags Phantom Drift with replacement_for when value is deprecated' {
        $cb = New-FixtureCodebook
        $snapshot = @{
            extensionAttribute3 = 'OldCyber'  # orgpath-codebook-allow: negative fixture
        }
        $results = Test-OrgPathFacets -PrincipalSnapshot $snapshot -Codebook $cb
        $phantom = @($results | Where-Object { $_.IsDeprecated })
        $phantom.Count | Should -Be 1
        $phantom[0].ReplacementFor | Should -Be 'CyberOps'
    }
}

Describe 'OrgPathTools — Model A surface is NOT restored (ADR-084 §C8)' {
    It 'does not export Test-OrgPath single-string function' {
        Get-Command -Module OrgPathTools -Name Test-OrgPath -ErrorAction SilentlyContinue | Should -BeNullOrEmpty
    }
    It 'does not export Test-OrgPathFormat single-regex function' {
        Get-Command -Module OrgPathTools -Name Test-OrgPathFormat -ErrorAction SilentlyContinue | Should -BeNullOrEmpty
    }
}
