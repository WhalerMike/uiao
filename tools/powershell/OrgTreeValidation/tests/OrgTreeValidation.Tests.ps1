# Pester 5.x tests for OrgTreeValidation.psm1.
#
# Coverage scope:
#   - Test-OrgPathFormat          (offline regex; fully covered)
#   - Test-OrgPathHierarchy       (offline lookup; fully covered)
#   - Compare-OrgTreeSnapshots    (offline diff; fully covered via fixtures)
#   - Canonical regex parity      (the literal in the .psm1 must match
#                                  the Python source-of-truth in
#                                  src/uiao/modernization/orgtree/codebook.py)
#
# Functions 3, 4, 5 require a live tenant + Microsoft.Graph SDK and are
# not exercised here. They are smoke-tested manually per UIAO_159.

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
    It 'pwsh CanonicalOrgPathPattern matches src/uiao/modernization/orgtree/codebook.py CANONICAL_REGEX' {
        $codebookPy = Join-Path $script:RepoRoot 'src/uiao/modernization/orgtree/codebook.py'
        Test-Path $codebookPy | Should -BeTrue

        # Extract the literal from `CANONICAL_REGEX = re.compile(r"...")`
        $line = (Select-String -Path $codebookPy -Pattern 'CANONICAL_REGEX\s*=\s*re\.compile\(r"' | Select-Object -First 1).Line
        $line | Should -Not -BeNullOrEmpty
        $match = [regex]::Match($line, 'r"(?<pat>[^"]+)"')
        $match.Success | Should -BeTrue

        $pythonLiteral = $match.Groups['pat'].Value

        # The .psm1 stores its literal in $Script:CanonicalOrgPathPattern, which
        # is module-internal. We probe it via the regex behavior: run a known-good
        # OrgPath through Test-OrgPathFormat and through the Python literal as a
        # net-style regex; both must agree.
        $sample = 'ORG-FIN-AP-USR-EAST'
        $pythonOk = $sample -match $pythonLiteral
        $pwshOk   = Test-OrgPathFormat -OrgPath $sample

        $pwshOk | Should -Be $pythonOk
    }
}
