# Pester tests for UIAO.OrgPath — Hybrid-C+Path derived-OrgPath tooling
# (ADR-127). Pure functions run offline; the Graph write paths are
# exercised against mocked Update-MgUser / Update-MgDevice.

BeforeAll {
    $modulePath = Join-Path $PSScriptRoot '..' 'UIAO.OrgPath.psm1' | Resolve-Path
    Import-Module $modulePath -Force

    # The Microsoft.Graph SDK is not installed in CI. Define global stubs
    # so Pester has a command to mock; the module resolves them at call
    # time. Removed in AfterAll.
    function global:Update-MgUser {
        param($UserId, $BodyParameter)
    }
    function global:Update-MgDevice {
        param($DeviceId, $BodyParameter)
    }
}

AfterAll {
    Remove-Item -Path function:global:Update-MgUser -ErrorAction SilentlyContinue
    Remove-Item -Path function:global:Update-MgDevice -ErrorAction SilentlyContinue
}


Describe 'New-OrgPath — derived path composition' {
    It 'composes the full three-segment path in canonical order' {
        New-OrgPath -Region NCR -Department IT -Division CyberOps |
            Should -Be 'Region=NCR|Department=IT|Division=CyberOps|'
    }

    It 'always ends in the trailing delimiter (round-trip contract)' {
        # Every populated combination ends in "|" — no exceptions.
        (New-OrgPath -Region NCR) | Should -Match '\|$'
        (New-OrgPath -Region NCR -Department IT) | Should -Match '\|$'
        (New-OrgPath -Region NCR -Department IT -Division CyberOps) | Should -Match '\|$'
    }

    It 'terminates every segment, not just the last' {
        $path = New-OrgPath -Region NCR -Department IT -Division CyberOps
        ($path.ToCharArray() | Where-Object { $_ -eq '|' }).Count | Should -Be 3
    }

    It 'returns empty string when no facet is populated' {
        New-OrgPath | Should -Be ''
    }

    It 'truncates at the first unpopulated facet (contiguous-prefix rule)' {
        # Division without Department is governance-layer drift, not a path.
        New-OrgPath -Region NCR -Division CyberOps | Should -Be 'Region=NCR|'
    }

    It 'rejects facet values containing the delimiter' {
        { New-OrgPath -Region 'NCR|X' } | Should -Throw "*must not contain*"
    }

    It 'rejects facet values containing the segment separator' {
        { New-OrgPath -Region 'NCR=X' } | Should -Throw "*must not contain*"
    }
}


Describe 'Prefix collision regression — the trailing-delimiter fix' {
    # The reason ADR-127 mandates the trailing delimiter: without it,
    # "Division=East" prefix-matches "Division=Eastern|..." and
    # "Division=Easton|...". With it, the match is exact-at-every-depth.
    It '"Division=East|" does NOT prefix-match "Division=Eastern|"' {
        $prefix = Get-OrgPathPrefix -Prefix 'Division=East'
        'Division=Eastern|'.StartsWith($prefix) | Should -Be $false
    }

    It '"Division=East|" does NOT prefix-match "Division=Easton|"' {
        $prefix = Get-OrgPathPrefix -Prefix 'Division=East'
        'Division=Easton|'.StartsWith($prefix) | Should -Be $false
    }

    It '"Division=East|" DOES prefix-match the exact subtree' {
        $prefix = Get-OrgPathPrefix -Prefix 'Division=East'
        'Division=East|'.StartsWith($prefix) | Should -Be $true
    }

    It 'derived paths from New-OrgPath are collision-free at branch level' {
        $east = New-OrgPath -Region NCR -Department Ops -Division East
        $eastern = New-OrgPath -Region NCR -Department Ops -Division Eastern
        $prefix = Get-OrgPathPrefix -Prefix 'Region=NCR|Department=Ops|Division=East'
        $east.StartsWith($prefix) | Should -Be $true
        $eastern.StartsWith($prefix) | Should -Be $false
    }
}


Describe 'Get-OrgPathPrefix — normalization and idempotency' {
    It 'appends the trailing delimiter when missing' {
        Get-OrgPathPrefix -Prefix 'Division=East' | Should -Be 'Division=East|'
    }

    It 'is idempotent — never doubles the delimiter' {
        $once = Get-OrgPathPrefix -Prefix 'Division=East'
        $twice = Get-OrgPathPrefix -Prefix $once
        $twice | Should -Be 'Division=East|'
        Get-OrgPathPrefix -Prefix (Get-OrgPathPrefix -Prefix $twice) |
            Should -Be 'Division=East|'
    }

    It 'normalizes multi-segment prefixes' {
        Get-OrgPathPrefix -Prefix 'Region=NCR|Department=IT' |
            Should -Be 'Region=NCR|Department=IT|'
    }

    It 'leaves an already-terminated multi-segment prefix unchanged' {
        Get-OrgPathPrefix -Prefix 'Region=NCR|Department=IT|' |
            Should -Be 'Region=NCR|Department=IT|'
    }
}


Describe 'Test-OrgPathDrift — derived-layer reconciliation' {
    It 'reports no drift when stored path matches the facets' {
        $result = Test-OrgPathDrift -StoredOrgPath 'Region=NCR|Department=IT|' -Region NCR -Department IT
        $result.IsDrifted | Should -Be $false
    }

    It 'flags a stored path missing the trailing delimiter' {
        $result = Test-OrgPathDrift -StoredOrgPath 'Region=NCR|Department=IT' -Region NCR -Department IT
        $result.IsDrifted | Should -Be $true
        $result.Reason | Should -Match 'trailing'
    }

    It 'flags a stale path after a facet move' {
        $result = Test-OrgPathDrift -StoredOrgPath 'Region=NCR|Department=IT|' -Region NCR -Department HR
        $result.IsDrifted | Should -Be $true
        $result.Expected | Should -Be 'Region=NCR|Department=HR|'
        $result.Actual | Should -Be 'Region=NCR|Department=IT|'
    }

    It 'flags an empty slot when facets are populated' {
        $result = Test-OrgPathDrift -StoredOrgPath '' -Region NCR
        $result.IsDrifted | Should -Be $true
        $result.Expected | Should -Be 'Region=NCR|'
    }

    It 'reports no drift for empty slot on unpopulated facets' {
        (Test-OrgPathDrift -StoredOrgPath '').IsDrifted | Should -Be $false
    }
}


Describe 'Update-OrgAttributes — user vs device Graph write paths' {
    BeforeEach {
        Mock Update-MgUser -ModuleName 'UIAO.OrgPath' {}
        Mock Update-MgDevice -ModuleName 'UIAO.OrgPath' {}
    }

    It 'writes users via Update-MgUser with onPremisesExtensionAttributes' {
        $result = Update-OrgAttributes -UserId 'alice@contoso.com' -Region NCR -Department IT -Division CyberOps

        Should -Invoke Update-MgUser -ModuleName 'UIAO.OrgPath' -Times 1 -Exactly -ParameterFilter {
            $UserId -eq 'alice@contoso.com' -and
            $BodyParameter.ContainsKey('onPremisesExtensionAttributes') -and
            -not $BodyParameter.ContainsKey('extensionAttributes')
        }
        Should -Invoke Update-MgDevice -ModuleName 'UIAO.OrgPath' -Times 0 -Exactly
        $result.Property | Should -Be 'onPremisesExtensionAttributes'
        $result.TargetType | Should -Be 'user'
    }

    It 'writes devices via Update-MgDevice with extensionAttributes (NOT onPremisesExtensionAttributes)' {
        $result = Update-OrgAttributes -DeviceId '3f2c8a1e-1111-2222-3333-444455556666' -Region NCR -Department IT

        Should -Invoke Update-MgDevice -ModuleName 'UIAO.OrgPath' -Times 1 -Exactly -ParameterFilter {
            $DeviceId -eq '3f2c8a1e-1111-2222-3333-444455556666' -and
            $BodyParameter.ContainsKey('extensionAttributes') -and
            -not $BodyParameter.ContainsKey('onPremisesExtensionAttributes')
        }
        Should -Invoke Update-MgUser -ModuleName 'UIAO.OrgPath' -Times 0 -Exactly
        $result.Property | Should -Be 'extensionAttributes'
        $result.TargetType | Should -Be 'device'
    }

    It 'stamps governance facets to their slots and the derived path to extensionAttribute15' {
        $result = Update-OrgAttributes -UserId 'alice@contoso.com' -Region NCR -Department IT -Division CyberOps
        $attrs = $result.Attributes
        $attrs['extensionAttribute1'] | Should -Be 'NCR'
        $attrs['extensionAttribute2'] | Should -Be 'IT'
        $attrs['extensionAttribute3'] | Should -Be 'CyberOps'
        $attrs['extensionAttribute15'] | Should -Be 'Region=NCR|Department=IT|Division=CyberOps|'
    }

    It 'derived path in the write body always carries the trailing delimiter' {
        $result = Update-OrgAttributes -DeviceId 'dev-1' -Region NCR
        $result.Attributes['extensionAttribute15'] | Should -Match '\|$'
    }

    It 'sends identical attribute payloads to users and devices — only the property differs' {
        $user = Update-OrgAttributes -UserId 'u1' -Region NCR -Department IT
        $device = Update-OrgAttributes -DeviceId 'd1' -Region NCR -Department IT
        # Same slots, same values...
        ($user.Attributes.Keys | Sort-Object) -join ',' |
            Should -Be (($device.Attributes.Keys | Sort-Object) -join ',')
        $user.Attributes['extensionAttribute15'] | Should -Be $device.Attributes['extensionAttribute15']
        # ...different Graph property per object type.
        $user.Property | Should -Not -Be $device.Property
    }
}
