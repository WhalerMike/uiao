# Pester 5.x tests for OrgTreeValidation.psm1.
#
# Coverage scope:
#   - Test-OrgPathFormat            (offline regex; fully covered)
#   - Test-OrgPathHierarchy         (offline lookup; fully covered)
#   - Compare-OrgTreeSnapshots      (offline diff; fully covered via fixtures)
#   - Canonical regex parity        (the literal in the .psm1 must match
#                                    the Python source-of-truth in
#                                    src/uiao/modernization/orgtree/codebook.py)
#   - Get-OrgTreeValidationReport   (DI delegates; no Microsoft.Graph)
#   - Test-DynamicGroupAlignment    (DI delegates; no Microsoft.Graph)
#   - Export-OrgTreeSnapshot        (DI delegates; no Microsoft.Graph)
#
# The three tenant-scope cmdlets accept Microsoft.Graph cmdlets as
# scriptblock parameters with sensible defaults. Tests pass fake
# scriptblocks that return canned tenant responses — no `Mock` magic,
# no `Microsoft.Graph` install. PR #368 (parked) tried Mock; this
# DI-based revival is the working version.

BeforeAll {
    $script:ModuleRoot = (Resolve-Path "$PSScriptRoot/..").Path
    $script:RepoRoot   = (Resolve-Path "$PSScriptRoot/../../../..").Path
    Import-Module "$script:ModuleRoot/OrgTreeValidation.psm1" -Force
    $script:FixtureDir = Join-Path $PSScriptRoot 'fixtures'
}


Describe 'Test-OrgPathFormat' {
    It 'accepts the bare root code' {
        Test-OrgPathFormat -OrgPath 'ORG' | Should -BeTrue
    }

    It 'accepts a one-level child' {
        Test-OrgPathFormat -OrgPath 'ORG-FIN' | Should -BeTrue
    }

    It 'accepts a four-level path (max depth)' {
        Test-OrgPathFormat -OrgPath 'ORG-FIN-AP-USR-EAST' | Should -BeTrue
    }

    It 'rejects a five-level path (over max depth)' {
        Test-OrgPathFormat -OrgPath 'ORG-FIN-AP-USR-EAST-X' | Should -BeFalse
    }

    It 'rejects lowercase segments' {
        Test-OrgPathFormat -OrgPath 'ORG-fin' | Should -BeFalse
    }

    It 'rejects a missing ORG prefix' {
        Test-OrgPathFormat -OrgPath 'FIN-AP' | Should -BeFalse
    }

    It 'rejects a one-character segment (under min length)' {
        Test-OrgPathFormat -OrgPath 'ORG-F' | Should -BeFalse
    }

    It 'rejects a seven-character segment (over max length)' {
        Test-OrgPathFormat -OrgPath 'ORG-FINANCE' | Should -BeFalse
    }
}


Describe 'Test-OrgPathHierarchy' {
    BeforeAll {
        $script:Codebook = @{
            'ORG'          = $true
            'ORG-FIN'      = $true
            'ORG-FIN-AP'   = $true
            'ORG-HR'       = $true
        }
    }

    It 'returns true for the root' {
        Test-OrgPathHierarchy -ChildPath 'ORG' -Codebook $script:Codebook | Should -BeTrue
    }

    It 'returns true when parent is in codebook' {
        Test-OrgPathHierarchy -ChildPath 'ORG-FIN-AP' -Codebook $script:Codebook | Should -BeTrue
    }

    It 'returns true for a one-level child of root' {
        Test-OrgPathHierarchy -ChildPath 'ORG-HR' -Codebook $script:Codebook | Should -BeTrue
    }

    It 'returns false when parent is missing from codebook' {
        Test-OrgPathHierarchy -ChildPath 'ORG-LEGAL-OPS' -Codebook $script:Codebook | Should -BeFalse
    }
}


Describe 'Compare-OrgTreeSnapshots' {
    It 'identifies value drift on an existing user' {
        $drift = Compare-OrgTreeSnapshots `
            -BaselinePath (Join-Path $script:FixtureDir 'snapshot-baseline.json') `
            -CurrentPath (Join-Path $script:FixtureDir 'snapshot-current.json')

        $valueDrift = $drift | Where-Object { $_.DriftType -eq 'ValueDrift' -and $_.ObjectId -eq 'u1' }
        $valueDrift | Should -Not -BeNullOrEmpty
        $valueDrift.BaselineValue | Should -Be 'ORG-FIN-AP'
        $valueDrift.CurrentValue  | Should -Be 'ORG-FIN-AR'
    }

    It 'identifies a newly-added user' {
        $drift = Compare-OrgTreeSnapshots `
            -BaselinePath (Join-Path $script:FixtureDir 'snapshot-baseline.json') `
            -CurrentPath (Join-Path $script:FixtureDir 'snapshot-current.json')

        $newObj = $drift | Where-Object { $_.DriftType -eq 'NewObject' -and $_.ObjectId -eq 'u4' }
        $newObj | Should -Not -BeNullOrEmpty
        $newObj.CurrentValue | Should -Be 'ORG-LEGAL'
    }

    It 'reports no drift when snapshots are identical' {
        $tmp = New-TemporaryFile
        Copy-Item (Join-Path $script:FixtureDir 'snapshot-baseline.json') $tmp -Force
        $drift = Compare-OrgTreeSnapshots `
            -BaselinePath (Join-Path $script:FixtureDir 'snapshot-baseline.json') `
            -CurrentPath $tmp.FullName
        $drift.Count | Should -Be 0
        Remove-Item $tmp -Force -ErrorAction SilentlyContinue
    }
}


Describe 'Canonical regex parity with Python source-of-truth' {
    BeforeAll {
        $codebookPy = Join-Path $script:RepoRoot 'src/uiao/modernization/orgtree/codebook.py'
        Test-Path $codebookPy | Should -BeTrue

        # Extract the literal from `CANONICAL_REGEX = re.compile(r"...")`
        $line = (Select-String -Path $codebookPy -Pattern 'CANONICAL_REGEX\s*=\s*re\.compile\(r"' | Select-Object -First 1).Line
        $line | Should -Not -BeNullOrEmpty
        $patternMatch = [regex]::Match($line, 'r"(?<pat>[^"]+)"')
        $patternMatch.Success | Should -BeTrue

        $script:PythonLiteral = $patternMatch.Groups['pat'].Value
    }

    It 'matches Python on an all-uppercase canonical sample' {
        $sample = 'ORG-FIN-AP-USR-EAST'
        # -cmatch is case-sensitive, mirroring Python's re.compile() default.
        $pythonOk = $sample -cmatch $script:PythonLiteral
        $pwshOk   = Test-OrgPathFormat -OrgPath $sample
        $pwshOk | Should -Be $pythonOk
        $pwshOk | Should -BeTrue
    }

    It 'matches Python on a mixed-case sample (must reject — guards against case-sensitivity drift)' {
        $sample = 'ORG-fin'
        $pythonOk = $sample -cmatch $script:PythonLiteral
        $pwshOk   = Test-OrgPathFormat -OrgPath $sample
        $pwshOk | Should -Be $pythonOk
        $pwshOk | Should -BeFalse
    }

    It 'matches Python on the bare root' {
        $sample = 'ORG'
        $pythonOk = $sample -cmatch $script:PythonLiteral
        $pwshOk   = Test-OrgPathFormat -OrgPath $sample
        $pwshOk | Should -Be $pythonOk
        $pwshOk | Should -BeTrue
    }
}


# ---------------------------------------------------------------------------
# Get-OrgTreeValidationReport — Function 3, DI-tested
# ---------------------------------------------------------------------------

Describe 'Get-OrgTreeValidationReport' {
    BeforeAll {
        $script:CodebookPath = Join-Path $script:FixtureDir 'codebook.json'
    }

    It 'returns DriftDetected=$false when every user has a valid registered OrgPath' {
        $report = Get-OrgTreeValidationReport `
            -TenantId 'fake' -CodebookPath $script:CodebookPath `
            -ConnectGraph {} `
            -GetUser {
                @(
                    [pscustomobject]@{ Id = 'u1'; OnPremisesExtensionAttributes = [pscustomobject]@{ ExtensionAttribute1 = 'ORG' } }
                    [pscustomobject]@{ Id = 'u2'; OnPremisesExtensionAttributes = [pscustomobject]@{ ExtensionAttribute1 = 'ORG-FIN-AP' } }
                    [pscustomobject]@{ Id = 'u3'; OnPremisesExtensionAttributes = [pscustomobject]@{ ExtensionAttribute1 = 'ORG-HR' } }
                )
            }
        $report.TotalUsers      | Should -Be 3
        $report.ValidOrgPaths   | Should -Be 3
        $report.InvalidOrgPaths | Should -Be 0
        $report.OrphanedUsers   | Should -Be 0
        $report.DriftDetected   | Should -BeFalse
    }

    It 'classifies users with empty OrgPath as orphaned and flags drift' {
        $report = Get-OrgTreeValidationReport `
            -TenantId 'fake' -CodebookPath $script:CodebookPath `
            -ConnectGraph {} `
            -GetUser {
                @(
                    [pscustomobject]@{ Id = 'u1'; OnPremisesExtensionAttributes = [pscustomobject]@{ ExtensionAttribute1 = 'ORG-FIN' } }
                    [pscustomobject]@{ Id = 'u2'; OnPremisesExtensionAttributes = [pscustomobject]@{ ExtensionAttribute1 = '' } }
                )
            }
        $report.TotalUsers    | Should -Be 2
        $report.OrphanedUsers | Should -Be 1
        $report.ValidOrgPaths | Should -Be 1
        $report.DriftDetected | Should -BeTrue
    }

    It 'classifies users with an OrgPath not in the codebook as invalid' {
        $report = Get-OrgTreeValidationReport `
            -TenantId 'fake' -CodebookPath $script:CodebookPath `
            -ConnectGraph {} `
            -GetUser {
                @([pscustomobject]@{ Id = 'u1'; OnPremisesExtensionAttributes = [pscustomobject]@{ ExtensionAttribute1 = 'ORG-NOTREAL' } })
            }
        $report.InvalidOrgPaths | Should -Be 1
        $report.ValidOrgPaths   | Should -Be 0
        $report.DriftDetected   | Should -BeTrue
    }

    It 'classifies users with format-violating OrgPaths as invalid' {
        $report = Get-OrgTreeValidationReport `
            -TenantId 'fake' -CodebookPath $script:CodebookPath `
            -ConnectGraph {} `
            -GetUser {
                @([pscustomobject]@{ Id = 'u1'; OnPremisesExtensionAttributes = [pscustomobject]@{ ExtensionAttribute1 = 'ORG-fin' } })
            }
        $report.InvalidOrgPaths | Should -Be 1
        $report.DriftDetected   | Should -BeTrue
    }

    It 'invokes the ConnectGraph delegate exactly once' {
        $script:connectCount = 0
        Get-OrgTreeValidationReport `
            -TenantId 'fake' -CodebookPath $script:CodebookPath `
            -ConnectGraph { $script:connectCount++ } `
            -GetUser { @() }
        $script:connectCount | Should -Be 1
    }
}


# ---------------------------------------------------------------------------
# Test-DynamicGroupAlignment — Function 4, DI-tested
# ---------------------------------------------------------------------------

Describe 'Test-DynamicGroupAlignment' {
    BeforeAll {
        $script:LibraryPath = Join-Path $script:FixtureDir 'group-library.json'
    }

    It 'reports all groups aligned when tenant rules match the library' {
        $r = Test-DynamicGroupAlignment `
            -TenantId 'fake' -GroupLibraryPath $script:LibraryPath `
            -ConnectGraph {} `
            -GetGroup {
                param($DisplayName)
                # Mirror the canonical rule the library declares for each name.
                switch ($DisplayName) {
                    'OrgTree-FIN-Users' { [pscustomobject]@{ DisplayName=$DisplayName; MembershipRule='(user.extensionAttribute1 -startsWith "ORG-FIN")' } }
                    'OrgTree-HR-Users'  { [pscustomobject]@{ DisplayName=$DisplayName; MembershipRule='(user.extensionAttribute1 -startsWith "ORG-HR")'  } }
                    'OrgTree-IT-Users'  { [pscustomobject]@{ DisplayName=$DisplayName; MembershipRule='(user.extensionAttribute1 -startsWith "ORG-IT")'  } }
                }
            }
        $r.AlignedGroups    | Should -Be 3
        $r.MisalignedGroups | Should -Be 0
        $r.MissingGroups    | Should -Be 0
    }

    It 'reports a misaligned group when the tenant rule differs from the library' {
        $r = Test-DynamicGroupAlignment `
            -TenantId 'fake' -GroupLibraryPath $script:LibraryPath `
            -ConnectGraph {} `
            -GetGroup {
                param($DisplayName)
                if ($DisplayName -eq 'OrgTree-FIN-Users') {
                    [pscustomobject]@{ DisplayName=$DisplayName; MembershipRule='(user.extensionAttribute1 -eq "ORG-FIN")' }  # wrong operator
                }
                else {
                    [pscustomobject]@{ DisplayName=$DisplayName; MembershipRule='' }  # other groups misaligned too; one is enough
                }
            }
        $r.MisalignedGroups | Should -BeGreaterThan 0
        ($r.Details | Where-Object { $_.GroupName -eq 'OrgTree-FIN-Users' -and $_.Status -eq 'Misaligned' }) |
            Should -Not -BeNullOrEmpty
    }

    It 'reports missing groups when GetGroup returns $null for every name' {
        $r = Test-DynamicGroupAlignment `
            -TenantId 'fake' -GroupLibraryPath $script:LibraryPath `
            -ConnectGraph {} `
            -GetGroup { $null }
        $r.MissingGroups | Should -Be 3
        $r.AlignedGroups | Should -Be 0
    }
}


# ---------------------------------------------------------------------------
# Export-OrgTreeSnapshot — Function 5, DI-tested
# ---------------------------------------------------------------------------

Describe 'Export-OrgTreeSnapshot' {
    BeforeEach {
        $script:OutFile = Join-Path ([System.IO.Path]::GetTempPath()) ("orgtree-snap-$([guid]::NewGuid()).json")
    }

    AfterEach {
        if (Test-Path $script:OutFile) { Remove-Item $script:OutFile -Force -ErrorAction SilentlyContinue }
    }

    It 'writes a JSON snapshot with the expected top-level fields and OrgTree-* filter' {
        Export-OrgTreeSnapshot `
            -TenantId 'fake' -OutputPath $script:OutFile `
            -ConnectGraph {} `
            -GetUser {
                @(
                    [pscustomobject]@{
                        Id                = 'u1'
                        UserPrincipalName = 'alice@example.gov'
                        Department        = 'Finance'
                        OnPremisesExtensionAttributes = [pscustomobject]@{ ExtensionAttribute1 = 'ORG-FIN-AP' }
                    }
                )
            } `
            -GetGroup {
                @(
                    [pscustomobject]@{ Id = 'g1'; DisplayName = 'OrgTree-FIN-Users';    MembershipRule = '(user.extensionAttribute1 -startsWith "ORG-FIN")' }
                    [pscustomobject]@{ Id = 'g2'; DisplayName = 'NotAnOrgTreeGroup';     MembershipRule = '' }  # filtered out
                )
            }
        Test-Path $script:OutFile | Should -BeTrue
        $snapshot = Get-Content -Path $script:OutFile -Raw | ConvertFrom-Json
        $snapshot.tenantId            | Should -Be 'fake'
        $snapshot.userCount           | Should -Be 1
        $snapshot.groupCount          | Should -Be 1   # OrgTree-* filter trimmed the other
        $snapshot.users[0].orgPath    | Should -Be 'ORG-FIN-AP'
        $snapshot.groups[0].displayName | Should -Be 'OrgTree-FIN-Users'
    }

    It 'invokes the ConnectGraph delegate exactly once' {
        $script:connectCount = 0
        Export-OrgTreeSnapshot `
            -TenantId 'fake' -OutputPath $script:OutFile `
            -ConnectGraph { $script:connectCount++ } `
            -GetUser { @() } `
            -GetGroup { @() }
        $script:connectCount | Should -Be 1
    }
}

