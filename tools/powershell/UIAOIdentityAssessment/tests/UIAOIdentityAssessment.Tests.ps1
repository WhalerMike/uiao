# Pester tests for UIAOIdentityAssessment (canon UIAO_181, ADR-094).
#
# Fully offline: every exporter is driven through -SnapshotPath, so no live
# tenant or Microsoft.Graph SDK is required. The only external dependency is a
# stdlib Python interpreter (json + hashlib) for the canonical integrity seal.

BeforeAll {
    $modulePath = Join-Path $PSScriptRoot '..' 'UIAOIdentityAssessment.psm1' | Resolve-Path
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

    function Write-Json {
        param([object]$Object, [string]$Path)
        ($Object | ConvertTo-Json -Depth 12) | Set-Content -LiteralPath $Path -Encoding UTF8
    }

    # Graph-shaped Entra user response (wrapped 'value' array).
    function New-EntraUsersSnapshot {
        param([string]$Path)
        Write-Json -Path $Path -Object @{
            value = @(
                @{ id = '1'; userPrincipalName = 'alice@contoso.com'; displayName = 'Alice'; accountEnabled = $true }
                @{ id = '2'; userPrincipalName = 'bob@contoso.com'; displayName = 'Bob'; accountEnabled = $false }
                @{ id = '3'; userPrincipalName = 'carol@contoso.com'; displayName = 'Carol'; accountEnabled = $false }
                @{ id = '4'; userPrincipalName = 'eve@contoso.com'; displayName = 'Eve'; accountEnabled = $true }
            )
        }
    }

    # An on-prem AD assessment envelope (the shape Compare reads: data.records).
    function New-ADAssessment {
        param([string]$Path)
        Write-Json -Path $Path -Object @{
            target_schema = 'ADUserInventory'
            provenance    = @{ source = 'ADRecon'; version = '1.0'; timestamp = '2026-06-05T00:00:00Z'; content_hash = 'na' }
            data          = @{
                records = @(
                    @{ user_principal_name = 'alice@contoso.com'; enabled = 'true' }
                    @{ user_principal_name = 'bob@contoso.com'; enabled = 'true' }
                    @{ user_principal_name = 'carol@contoso.com'; enabled = 'false' }
                    @{ user_principal_name = 'dave@contoso.com'; enabled = 'true' }
                )
            }
        }
    }
}

Describe 'Module surface' {
    It 'exports exactly the six UIAO_181 roster functions' {
        $exported = @((Get-Command -Module UIAOIdentityAssessment).Name)
        $exported.Count | Should -Be 6
        foreach ($fn in @(
                'Compare-UIAOIdentitySources', 'Export-UIAOConditionalAccess', 'Export-UIAOEntraApps',
                'Export-UIAOEntraGroups', 'Export-UIAOEntraUsers', 'Invoke-UIAOIdentityAssessment')) {
            $exported | Should -Contain $fn
        }
    }
}

Describe 'Export-UIAOEntraUsers (offline snapshot)' {
    BeforeAll {
        $snap = Join-Path $TestDrive 'users.json'
        New-EntraUsersSnapshot -Path $snap
        $Script:Result = Export-UIAOEntraUsers -SnapshotPath $snap -TenantId 'tenant-123'
    }

    It 'normalizes Graph users into EntraUserInventory' {
        $Result.target_schema | Should -Be 'EntraUserInventory'
        $Result.data.record_count | Should -Be 4
        $Result.data.records[0].user_principal_name | Should -Be 'alice@contoso.com'
        $Result.data.records[1].enabled | Should -Be 'False'
    }

    It 'stamps tenant id, graph api version, and a canonical seal in provenance' {
        $Result.provenance.source | Should -Be 'EntraID'
        $Result.provenance.tenant_id | Should -Be 'tenant-123'
        $Result.provenance.version | Should -Be 'v1.0'
        $Result.provenance.graph_endpoint | Should -Be 'https://graph.microsoft.com/v1.0'
        $Result.provenance.content_hash | Should -Match '^[0-9a-f]{64}$'
    }

    It 'seals data with the canonical content_hash' {
        (Get-ExpectedHash -DataObject $Result.data) | Should -Be $Result.provenance.content_hash
    }
}

Describe 'Graph endpoint resolution (fail-closed)' {
    It 'defaults commercial (GCC-Moderate) and resolves gcc-high / dod' {
        $snap = Join-Path $TestDrive 'u-cloud.json'; New-EntraUsersSnapshot -Path $snap
        (Export-UIAOEntraUsers -SnapshotPath $snap).provenance.graph_endpoint |
            Should -Be 'https://graph.microsoft.com/v1.0'
        (Export-UIAOEntraUsers -SnapshotPath $snap -Cloud 'gcc-high').provenance.graph_endpoint |
            Should -Be 'https://graph.microsoft.us/v1.0'
        (Export-UIAOEntraUsers -SnapshotPath $snap -Cloud 'dod').provenance.graph_endpoint |
            Should -Be 'https://dod-graph.microsoft.us/v1.0'
    }

    It 'fails closed on an unknown cloud' {
        $snap = Join-Path $TestDrive 'u-badcloud.json'; New-EntraUsersSnapshot -Path $snap
        { Export-UIAOEntraUsers -SnapshotPath $snap -Cloud 'bogus' } | Should -Throw '*unknown cloud*'
    }
}

Describe 'Export-UIAOEntraGroups (-IncludeDynamic)' {
    BeforeAll {
        $Script:GroupSnap = Join-Path $TestDrive 'groups.json'
        Write-Json -Path $Script:GroupSnap -Object @{
            value = @(
                @{ id = 'g1'; displayName = 'All-IT'; groupTypes = @('DynamicMembership', 'Unified'); membershipRule = '(user.department -eq "IT")'; securityEnabled = $true }
                @{ id = 'g2'; displayName = 'Static-Sec'; groupTypes = @(); securityEnabled = $true }
            )
        }
    }

    It 'omits the dynamic membership rule by default but flags the dynamic group' {
        $r = Export-UIAOEntraGroups -SnapshotPath $Script:GroupSnap
        $r.data.records[0].is_dynamic | Should -Be 'True'
        $r.data.records[0].membership_rule | Should -BeNullOrEmpty
    }

    It 'includes the membership rule when -IncludeDynamic is set' {
        $r = Export-UIAOEntraGroups -SnapshotPath $Script:GroupSnap -IncludeDynamic
        $r.data.records[0].membership_rule | Should -Be '(user.department -eq "IT")'
    }
}

Describe 'Compare-UIAOIdentitySources (DRIFT-IDENTITY reconciliation)' {
    BeforeAll {
        $snap = Join-Path $TestDrive 'r-users.json'; New-EntraUsersSnapshot -Path $snap
        $Script:EntraEnv = Join-Path $TestDrive 'r-entra.json'
        $null = Export-UIAOEntraUsers -SnapshotPath $snap -TenantId 't' -OutputPath $Script:EntraEnv
        $Script:AdEnv = Join-Path $TestDrive 'r-ad.json'
        New-ADAssessment -Path $Script:AdEnv
        $Script:Recon = Compare-UIAOIdentitySources -ADAssessmentPath $Script:AdEnv -EntraAssessmentPath $Script:EntraEnv
    }

    It 'classifies every principal and counts the drift' {
        $Recon.target_schema | Should -Be 'IdentityReconciliation'
        $Recon.data.counts.matched | Should -Be 2
        $Recon.data.counts.lifecycle_inconsistent | Should -Be 1
        $Recon.data.counts.orphaned_in_ad | Should -Be 1
        $Recon.data.counts.missing_in_ad | Should -Be 1
        $Recon.data.drift_count | Should -Be 3
        $Recon.data.record_count | Should -Be 5
    }

    It 'tags non-matched principals with DRIFT-IDENTITY' {
        $bob = $Recon.data.records | Where-Object { $_.match_key -eq 'bob@contoso.com' }
        $bob.classification | Should -Be 'lifecycle_inconsistent'
        $bob.drift_class | Should -Be 'DRIFT-IDENTITY'

        $eve = $Recon.data.records | Where-Object { $_.match_key -eq 'eve@contoso.com' }
        $eve.classification | Should -Be 'missing_in_ad'

        $alice = $Recon.data.records | Where-Object { $_.match_key -eq 'alice@contoso.com' }
        $alice.classification | Should -Be 'matched'
        $alice.drift_class | Should -BeNullOrEmpty
    }

    It 'seals the reconciliation with the canonical content_hash' {
        (Get-ExpectedHash -DataObject $Recon.data) | Should -Be $Recon.provenance.content_hash
    }
}

Describe 'Invoke-UIAOIdentityAssessment (orchestrator, offline)' {
    It 'produces a bundle with the user inventory and reconciliation artifacts' {
        $snap = Join-Path $TestDrive 'o-users.json'; New-EntraUsersSnapshot -Path $snap
        $adEnv = Join-Path $TestDrive 'o-ad.json'; New-ADAssessment -Path $adEnv

        $bundle = Invoke-UIAOIdentityAssessment -EntraUsersSnapshotPath $snap -ADAssessmentPath $adEnv -Domain 'contoso.com'
        $bundle.schema | Should -Be 'uiao.identity.assessment.v1'
        $bundle.data.artifact_count | Should -Be 2
        $bundle.data.domain | Should -Be 'contoso.com'
        ($bundle.data.artifacts | Where-Object { $_.target_schema -eq 'IdentityReconciliation' }).drift_count | Should -Be 3
        $bundle.reconciliation.data.drift_count | Should -Be 3
    }
}

Describe 'Input validation' {
    It 'throws when neither -SnapshotPath nor -TenantId is given' {
        { Export-UIAOEntraUsers } | Should -Throw '*SnapshotPath*'
    }

    It 'throws on a missing snapshot file' {
        { Export-UIAOEntraUsers -SnapshotPath (Join-Path $TestDrive 'nope.json') } | Should -Throw '*not found*'
    }
}
