# Pester 5.x tests for OrgTreeValidation.psm1.
#
# Coverage scope:
#   - Test-OrgPathFormat            (offline regex; fully covered)
#   - Test-OrgPathHierarchy         (offline lookup; fully covered)
#   - Compare-OrgTreeSnapshots      (offline diff; fully covered via fixtures)
#   - Canonical regex parity        (the literal in the .psm1 must match
#                                    the Python source-of-truth in
#                                    src/uiao/modernization/orgtree/codebook.py)
#   - Get-OrgTreeValidationReport   (tenant-scope; covered via Graph SDK
#                                    mocks defined in BeforeAll below)
#   - Test-DynamicGroupAlignment    (tenant-scope; covered via mocks)
#   - Export-OrgTreeSnapshot        (tenant-scope; covered via mocks)
#
# The tenant-scope cmdlets call Microsoft.Graph cmdlets (Connect-MgGraph,
# Get-MgUser, Get-MgGroup). Microsoft.Graph is intentionally NOT installed
# in CI — we stub the three cmdlets in the global scope of this test
# session so Pester's Mock can substitute behavior per test. When the
# real Microsoft.Graph module is loaded in production, the global stubs
# are shadowed and the real cmdlets win.

# Discovery-time variables. Pester evaluates `It -Skip:<expr>` at
# discovery, *before* any BeforeAll runs. Variables set inside
# BeforeAll are not visible to -Skip; variables set at file top-level
# are.
#
# `$SkipTenantScope` gates the tenant-scope tests below. CI runs without
# Microsoft.Graph installed (it's a 100+ MB module that would dominate
# the lane runtime), so the tenant-scope tests `-Skip` automatically
# and Pester reports them as Skipped, not Failed. A developer with
# Microsoft.Graph installed locally (`Install-Module Microsoft.Graph`)
# runs the full suite end-to-end.
$SkipTenantScope = $null -eq (Get-Module -ListAvailable Microsoft.Graph -ErrorAction SilentlyContinue)

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
# Get-OrgTreeValidationReport (Function 3) — mocked Microsoft.Graph
# ---------------------------------------------------------------------------
#
# The cmdlet calls Connect-MgGraph + Get-MgUser. We synthesize user objects
# with the OnPremisesExtensionAttributes.ExtensionAttribute1 shape that the
# real Graph SDK returns, then assert the cmdlet's counting / classification
# logic against known inputs.

Describe 'Get-OrgTreeValidationReport' -Skip:$SkipTenantScope {
    BeforeEach {
        $script:CodebookPath = Join-Path $script:FixtureDir 'codebook.json'
        Mock -ModuleName OrgTreeValidation Connect-MgGraph {}
    }

    It 'returns DriftDetected=$false when every user has a valid registered OrgPath' -Skip:$SkipTenantScope {
        Mock -ModuleName OrgTreeValidation Get-MgUser {
            return @(
                [pscustomobject]@{
                    Id = 'u1'
                    OnPremisesExtensionAttributes = [pscustomobject]@{ ExtensionAttribute1 = 'ORG' }
                }
                [pscustomobject]@{
                    Id = 'u2'
                    OnPremisesExtensionAttributes = [pscustomobject]@{ ExtensionAttribute1 = 'ORG-FIN-AP' }
                }
                [pscustomobject]@{
                    Id = 'u3'
                    OnPremisesExtensionAttributes = [pscustomobject]@{ ExtensionAttribute1 = 'ORG-HR' }
                }
            )
        }
        $report = Get-OrgTreeValidationReport -TenantId 'fake' -CodebookPath $script:CodebookPath
        $report.TotalUsers      | Should -Be 3
        $report.ValidOrgPaths   | Should -Be 3
        $report.InvalidOrgPaths | Should -Be 0
        $report.OrphanedUsers   | Should -Be 0
        $report.DriftDetected   | Should -BeFalse
    }

    It 'classifies users with empty OrgPath as orphaned and flags drift' -Skip:$SkipTenantScope {
        Mock -ModuleName OrgTreeValidation Get-MgUser {
            return @(
                [pscustomobject]@{
                    Id = 'u1'
                    OnPremisesExtensionAttributes = [pscustomobject]@{ ExtensionAttribute1 = 'ORG-FIN' }
                }
                [pscustomobject]@{
                    Id = 'u2'
                    OnPremisesExtensionAttributes = [pscustomobject]@{ ExtensionAttribute1 = '' }
                }
            )
        }
        $report = Get-OrgTreeValidationReport -TenantId 'fake' -CodebookPath $script:CodebookPath
        $report.TotalUsers    | Should -Be 2
        $report.OrphanedUsers | Should -Be 1
        $report.ValidOrgPaths | Should -Be 1
        $report.DriftDetected | Should -BeTrue
    }

    It 'classifies users with an OrgPath not in the codebook as invalid' -Skip:$SkipTenantScope {
        Mock -ModuleName OrgTreeValidation Get-MgUser {
            return @(
                [pscustomobject]@{
                    Id = 'u1'
                    OnPremisesExtensionAttributes = [pscustomobject]@{ ExtensionAttribute1 = 'ORG-NOTREAL' }
                }
            )
        }
        $report = Get-OrgTreeValidationReport -TenantId 'fake' -CodebookPath $script:CodebookPath
        $report.InvalidOrgPaths | Should -Be 1
        $report.ValidOrgPaths   | Should -Be 0
        $report.DriftDetected   | Should -BeTrue
    }

    It 'classifies users with format-violating OrgPaths as invalid' -Skip:$SkipTenantScope {
        Mock -ModuleName OrgTreeValidation Get-MgUser {
            return @(
                [pscustomobject]@{
                    Id = 'u1'
                    OnPremisesExtensionAttributes = [pscustomobject]@{ ExtensionAttribute1 = 'ORG-fin' }
                }
            )
        }
        $report = Get-OrgTreeValidationReport -TenantId 'fake' -CodebookPath $script:CodebookPath
        $report.InvalidOrgPaths | Should -Be 1
        $report.DriftDetected   | Should -BeTrue
    }

    It 'invokes Connect-MgGraph exactly once per call' -Skip:$SkipTenantScope {
        Mock -ModuleName OrgTreeValidation Get-MgUser { return @() }
        Get-OrgTreeValidationReport -TenantId 'fake' -CodebookPath $script:CodebookPath
        Should -Invoke -ModuleName OrgTreeValidation -CommandName Connect-MgGraph -Times 1 -Exactly
    }
}


# ---------------------------------------------------------------------------
# Test-DynamicGroupAlignment (Function 4) — mocked Microsoft.Graph
# ---------------------------------------------------------------------------

Describe 'Test-DynamicGroupAlignment' -Skip:$SkipTenantScope {
    BeforeEach {
        $script:LibraryPath = Join-Path $script:FixtureDir 'group-library.json'
        Mock -ModuleName OrgTreeValidation Connect-MgGraph {}
    }

    It 'reports all groups aligned when tenant rules match the library' -Skip:$SkipTenantScope {
        # Library has 3 groups. Return a matching MembershipRule for each.
        Mock -ModuleName OrgTreeValidation Get-MgGroup {
            param($Filter)
            switch -Wildcard ($Filter) {
                "*OrgTree-FIN-Users*" {
                    return [pscustomobject]@{
                        DisplayName    = 'OrgTree-FIN-Users'
                        MembershipRule = '(user.extensionAttribute1 -startsWith "ORG-FIN")'
                    }
                }
                "*OrgTree-HR-Users*" {
                    return [pscustomobject]@{
                        DisplayName    = 'OrgTree-HR-Users'
                        MembershipRule = '(user.extensionAttribute1 -startsWith "ORG-HR")'
                    }
                }
                "*OrgTree-IT-Users*" {
                    return [pscustomobject]@{
                        DisplayName    = 'OrgTree-IT-Users'
                        MembershipRule = '(user.extensionAttribute1 -startsWith "ORG-IT")'
                    }
                }
            }
        }
        $r = Test-DynamicGroupAlignment -TenantId 'fake' -GroupLibraryPath $script:LibraryPath
        $r.AlignedGroups    | Should -Be 3
        $r.MisalignedGroups | Should -Be 0
        $r.MissingGroups    | Should -Be 0
    }

    It 'reports a misaligned group when the tenant rule differs from the library' -Skip:$SkipTenantScope {
        Mock -ModuleName OrgTreeValidation Get-MgGroup {
            param($Filter)
            if ($Filter -like '*OrgTree-FIN-Users*') {
                return [pscustomobject]@{
                    DisplayName    = 'OrgTree-FIN-Users'
                    MembershipRule = '(user.extensionAttribute1 -eq "ORG-FIN")'   # wrong operator
                }
            }
            return [pscustomobject]@{
                DisplayName    = 'placeholder'
                MembershipRule = ''
            }
        }
        $r = Test-DynamicGroupAlignment -TenantId 'fake' -GroupLibraryPath $script:LibraryPath
        $r.MisalignedGroups | Should -BeGreaterThan 0
        ($r.Details | Where-Object { $_.GroupName -eq 'OrgTree-FIN-Users' -and $_.Status -eq 'Misaligned' }) |
            Should -Not -BeNullOrEmpty
    }

    It 'reports missing groups when Get-MgGroup returns nothing' -Skip:$SkipTenantScope {
        Mock -ModuleName OrgTreeValidation Get-MgGroup { return $null }
        $r = Test-DynamicGroupAlignment -TenantId 'fake' -GroupLibraryPath $script:LibraryPath
        $r.MissingGroups | Should -Be 3
        $r.AlignedGroups | Should -Be 0
    }
}


# ---------------------------------------------------------------------------
# Export-OrgTreeSnapshot (Function 5) — mocked Microsoft.Graph + file I/O
# ---------------------------------------------------------------------------

Describe 'Export-OrgTreeSnapshot' -Skip:$SkipTenantScope {
    BeforeEach {
        $script:OutFile = Join-Path ([System.IO.Path]::GetTempPath()) ("orgtree-snap-$([guid]::NewGuid()).json")
        Mock -ModuleName OrgTreeValidation Connect-MgGraph {}
    }

    AfterEach {
        if (Test-Path $script:OutFile) { Remove-Item $script:OutFile -Force -ErrorAction SilentlyContinue }
    }

    It 'writes a JSON snapshot with the expected top-level fields' -Skip:$SkipTenantScope {
        Mock -ModuleName OrgTreeValidation Get-MgUser {
            return @(
                [pscustomobject]@{
                    Id                = 'u1'
                    UserPrincipalName = 'alice@example.gov'
                    Department        = 'Finance'
                    OnPremisesExtensionAttributes = [pscustomobject]@{ ExtensionAttribute1 = 'ORG-FIN-AP' }
                }
            )
        }
        Mock -ModuleName OrgTreeValidation Get-MgGroup {
            return @(
                [pscustomobject]@{
                    Id             = 'g1'
                    DisplayName    = 'OrgTree-FIN-Users'
                    MembershipRule = '(user.extensionAttribute1 -startsWith "ORG-FIN")'
                }
                [pscustomobject]@{
                    Id             = 'g2'
                    DisplayName    = 'NotAnOrgTreeGroup'   # filtered out by Where-Object
                    MembershipRule = ''
                }
            )
        }
        Export-OrgTreeSnapshot -TenantId 'fake' -OutputPath $script:OutFile
        Test-Path $script:OutFile | Should -BeTrue
        $snapshot = Get-Content -Path $script:OutFile -Raw | ConvertFrom-Json
        $snapshot.tenantId   | Should -Be 'fake'
        $snapshot.userCount  | Should -Be 1
        # Only OrgTree-* groups survive the Where-Object filter.
        $snapshot.groupCount | Should -Be 1
        $snapshot.users[0].orgPath | Should -Be 'ORG-FIN-AP'
        $snapshot.groups[0].displayName | Should -Be 'OrgTree-FIN-Users'
    }

    It 'invokes Connect-MgGraph exactly once' -Skip:$SkipTenantScope {
        Mock -ModuleName OrgTreeValidation Get-MgUser { return @() }
        Mock -ModuleName OrgTreeValidation Get-MgGroup { return @() }
        Export-OrgTreeSnapshot -TenantId 'fake' -OutputPath $script:OutFile
        Should -Invoke -ModuleName OrgTreeValidation -CommandName Connect-MgGraph -Times 1 -Exactly
    }
}
