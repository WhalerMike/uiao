# Pester tests for UIAOSqlServerMigration (canon UIAO_135 #7; ADR-002/004/068/091).
#
# Fully offline: fixtures (Arc status/token/extension snapshots, login audit,
# reconciliation, collision report, GPO report) are written to $TestDrive. The
# only external dependency is a stdlib Python interpreter (json + hashlib) for
# the canonical integrity seal, exactly like the sibling modules.

BeforeAll {
    $modulePath = Join-Path $PSScriptRoot '..' 'UIAOSqlServerMigration.psm1' | Resolve-Path
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

    function New-Jwt {
        # Build an unsigned JWT with the given payload claims (header.payload.sig).
        param([Parameter(Mandatory = $true)][hashtable]$Claims)
        function ToB64Url([string]$s) {
            $b = [Text.Encoding]::UTF8.GetBytes($s)
            return [Convert]::ToBase64String($b).TrimEnd('=').Replace('+', '-').Replace('/', '_')
        }
        $header = ToB64Url('{"alg":"none","typ":"JWT"}')
        $payload = ToB64Url(($Claims | ConvertTo-Json -Compress))
        return "$header.$payload.sig"
    }

    function Write-Json {
        param([string]$Path, $Object)
        ($Object | ConvertTo-Json -Depth 12) | Set-Content -LiteralPath $Path -Encoding UTF8
    }
}

Describe 'Module surface' {
    It 'exports exactly the nine roster functions' {
        $exported = @((Get-Command -Module UIAOSqlServerMigration).Name)
        $exported.Count | Should -Be 9
        foreach ($fn in @(
                'Test-UIAOArcAgentStatus', 'Test-UIAOArcManagedIdentityToken', 'Test-UIAOArcSqlExtension',
                'Invoke-UIAOArcOnboarding', 'New-UIAOEntraLoginMapping', 'New-UIAOEntraLoginScript',
                'Test-UIAOLoginParallelRun', 'New-UIAOSpnRemediationPlan', 'Get-UIAONtlmGpoReport')) {
            $exported | Should -Contain $fn
        }
    }
}

Describe 'Arc — Test-UIAOArcAgentStatus (Book 04 Step 1)' {
    It 'passes when the snapshot reports Connected in the expected cloud' {
        $p = Join-Path $TestDrive 'arc-connected.json'
        Write-Json -Path $p -Object @{ status = 'Connected'; resourceId = '/subscriptions/x/rg/y'; cloud = 'AzureUSGovernment'; agentVersion = '1.40' }
        $r = Test-UIAOArcAgentStatus -SnapshotPath $p -ExpectedCloud 'AzureUSGovernment'
        $r.data.records[0].validation | Should -Be 'pass'
        $r.data.records[0].connected | Should -BeTrue
    }

    It 'fails when not Connected' {
        $p = Join-Path $TestDrive 'arc-disconnected.json'
        Write-Json -Path $p -Object @{ status = 'Disconnected'; resourceId = '/subscriptions/x'; cloud = 'AzureCloud' }
        $r = Test-UIAOArcAgentStatus -SnapshotPath $p
        $r.data.records[0].validation | Should -Be 'fail'
    }

    It 'fails on a cloud mismatch' {
        $p = Join-Path $TestDrive 'arc-wrongcloud.json'
        Write-Json -Path $p -Object @{ status = 'Connected'; resourceId = '/subscriptions/x'; cloud = 'AzureCloud' }
        $r = Test-UIAOArcAgentStatus -SnapshotPath $p -ExpectedCloud 'AzureUSGovernment'
        $r.data.records[0].validation | Should -Be 'fail'
    }

    It 'seals the validation envelope reproducibly' {
        $p = Join-Path $TestDrive 'arc-seal.json'
        Write-Json -Path $p -Object @{ status = 'Connected'; resourceId = '/subscriptions/x'; cloud = 'AzureCloud' }
        $r = Test-UIAOArcAgentStatus -SnapshotPath $p
        (Get-ExpectedHash -DataObject $r.data) | Should -Be $r.provenance.content_hash
    }

    It 'throws when neither -SnapshotPath nor -Live is given' {
        { Test-UIAOArcAgentStatus } | Should -Throw
    }
}

Describe 'Arc — Test-UIAOArcManagedIdentityToken (Book 04 Step 2)' {
    It 'passes when aud matches the data-plane audience and exp is in the future' {
        $exp = [DateTimeOffset]::UtcNow.AddHours(1).ToUnixTimeSeconds()
        $jwt = New-Jwt -Claims @{ aud = 'https://database.usgovcloudapi.net/'; iss = 'https://sts'; exp = $exp }
        $p = Join-Path $TestDrive 'token-good.json'
        Write-Json -Path $p -Object @{ access_token = $jwt }
        $r = Test-UIAOArcManagedIdentityToken -TokenSnapshotPath $p -Cloud 'AzureUSGovernment'
        $r.data.records[0].validation | Should -Be 'pass'
    }

    It 'fails on an audience mismatch (the common Arc failure)' {
        $exp = [DateTimeOffset]::UtcNow.AddHours(1).ToUnixTimeSeconds()
        $jwt = New-Jwt -Claims @{ aud = 'https://management.usgovcloudapi.net/'; iss = 'https://sts'; exp = $exp }
        $p = Join-Path $TestDrive 'token-wrongaud.json'
        Write-Json -Path $p -Object @{ access_token = $jwt }
        $r = Test-UIAOArcManagedIdentityToken -TokenSnapshotPath $p -Cloud 'AzureUSGovernment'
        $r.data.records[0].validation | Should -Be 'fail'
        ($r.data.records[0].checks | Where-Object { $_.check -eq 'audience_match' }).passed | Should -BeFalse
    }

    It 'fails on an expired token' {
        $exp = [DateTimeOffset]::UtcNow.AddHours(-1).ToUnixTimeSeconds()
        $jwt = New-Jwt -Claims @{ aud = 'https://database.windows.net/'; iss = 'https://sts'; exp = $exp }
        $p = Join-Path $TestDrive 'token-expired.json'
        Write-Json -Path $p -Object @{ access_token = $jwt }
        $r = Test-UIAOArcManagedIdentityToken -TokenSnapshotPath $p
        ($r.data.records[0].checks | Where-Object { $_.check -eq 'not_expired' }).passed | Should -BeFalse
    }

    It 'fails closed on an unknown cloud' {
        { Test-UIAOArcManagedIdentityToken -TokenSnapshotPath (Join-Path $TestDrive 'token-good.json') -Cloud 'Mars' } | Should -Throw
    }
}

Describe 'Arc — Test-UIAOArcSqlExtension (Book 04 Step 3)' {
    It 'passes when provisioning state is Succeeded' {
        $p = Join-Path $TestDrive 'ext-ok.json'
        Write-Json -Path $p -Object @{ provisioningState = 'Succeeded'; type = 'WindowsAgent.SqlServer' }
        $r = Test-UIAOArcSqlExtension -SnapshotPath $p
        $r.data.records[0].validation | Should -Be 'pass'
    }

    It 'fails when provisioning is stuck' {
        $p = Join-Path $TestDrive 'ext-bad.json'
        Write-Json -Path $p -Object @{ provisioningState = 'Creating'; type = 'WindowsAgent.SqlServer' }
        $r = Test-UIAOArcSqlExtension -SnapshotPath $p
        $r.data.records[0].validation | Should -Be 'fail'
    }
}

Describe 'Arc — Invoke-UIAOArcOnboarding (Book 04 Step 1, mutating)' {
    It 'is a no-op when the status snapshot reports already Connected' {
        $s = Join-Path $TestDrive 'onboard-connected.json'
        Write-Json -Path $s -Object @{ status = 'Connected'; resourceId = '/subscriptions/x'; cloud = 'AzureUSGovernment' }
        $r = Invoke-UIAOArcOnboarding -ResourceGroup rg -TenantId t -SubscriptionId s -Location usgovvirginia `
            -Cloud AzureUSGovernment -StatusSnapshotPath $s
        $r.data.records[0].action | Should -Be 'skipped_already_connected'
        $r.data.records[0].executed | Should -BeFalse
    }

    It 'plans (executes nothing) by default and composes the exact command' {
        $r = Invoke-UIAOArcOnboarding -ResourceGroup rg-sql-arc -TenantId tid -SubscriptionId sid `
            -Location usgovvirginia -Cloud AzureUSGovernment -ProxyUrl 'http://proxy:8080'
        $r.data.records[0].executed | Should -BeFalse
        $r.data.records[0].outcome | Should -Be 'planned'
        $r.data.records[0].command_preview | Should -Match 'azcmagent connect'
        $r.data.records[0].command_preview | Should -Match 'rg-sql-arc'
        $r.data.records[0].command_preview | Should -Match 'AzureUSGovernment'
    }

    It 'supports -WhatIf (no execution even with -Execute)' {
        $r = Invoke-UIAOArcOnboarding -ResourceGroup rg -TenantId t -SubscriptionId s -Location loc -Execute -WhatIf
        $r.data.records[0].executed | Should -BeFalse
    }

    It 'declares SupportsShouldProcess' {
        (Get-Command Invoke-UIAOArcOnboarding).Parameters.ContainsKey('WhatIf') | Should -BeTrue
        (Get-Command Invoke-UIAOArcOnboarding).Parameters.ContainsKey('Confirm') | Should -BeTrue
    }
}

Describe 'Login — New-UIAOEntraLoginMapping (Book 05 Step 1)' {
    BeforeAll {
        $Script:Audit = Join-Path $TestDrive 'logins.csv'
        @(
            [PSCustomObject]@{ LoginName = 'CONTOSO\jdoe'; Type = 'WINDOWS_LOGIN'; Disabled = 'False' }
            [PSCustomObject]@{ LoginName = 'CONTOSO\appsvc'; Type = 'WINDOWS_LOGIN'; Disabled = 'False' }
            [PSCustomObject]@{ LoginName = 'CONTOSO\nomap'; Type = 'WINDOWS_LOGIN'; Disabled = 'False' }
        ) | Export-Csv -LiteralPath $Script:Audit -NoTypeInformation -Encoding UTF8

        $Script:Recon = Join-Path $TestDrive 'recon.json'
        Write-Json -Path $Script:Recon -Object @{
            target_schema = 'IdentityReconciliation'
            provenance    = @{ source = 'UIAOIdentityAssessment.Reconcile'; content_hash = 'h' }
            data          = @{ records = @(
                    @{ match_key = 'jdoe'; classification = 'matched'; entra_upn = 'jdoe@contoso.gov' }
                ) }
        }
    }

    It 'maps via reconciliation for cleanly matched principals' {
        $r = New-UIAOEntraLoginMapping -LoginAuditPath $Script:Audit -ReconciliationPath $Script:Recon
        $jdoe = $r.data.records | Where-Object { $_.windows_login -eq 'CONTOSO\jdoe' }
        $jdoe.entra_principal | Should -Be 'jdoe@contoso.gov'
        $jdoe.principal_type | Should -Be 'user'
        $jdoe.mapping_source | Should -Be 'reconciliation'
    }

    It 'prefers a group map over reconciliation (group-based logins are the target)' {
        $r = New-UIAOEntraLoginMapping -LoginAuditPath $Script:Audit -ReconciliationPath $Script:Recon `
            -GroupMap @{ 'CONTOSO\appsvc' = 'sql-app-readers' }
        $appsvc = $r.data.records | Where-Object { $_.windows_login -eq 'CONTOSO\appsvc' }
        $appsvc.entra_principal | Should -Be 'sql-app-readers'
        $appsvc.principal_type | Should -Be 'group'
    }

    It 'flags unresolved logins for review (never silently dropped)' {
        $r = New-UIAOEntraLoginMapping -LoginAuditPath $Script:Audit -ReconciliationPath $Script:Recon
        $nomap = $r.data.records | Where-Object { $_.windows_login -eq 'CONTOSO\nomap' }
        $nomap.review_required | Should -BeTrue
        $r.data.approvable | Should -BeFalse
    }
}

Describe 'Login — New-UIAOEntraLoginScript (Book 05 Step 1, dry-run)' {
    BeforeAll {
        $Script:Mapping = Join-Path $TestDrive 'mapping.json'
        Write-Json -Path $Script:Mapping -Object @{
            artifact_type = 'EntraLoginMapping'
            data          = @{ records = @(
                    @{ windows_login = 'CONTOSO\jdoe'; entra_principal = 'jdoe@contoso.gov'; principal_type = 'user'; review_required = $false }
                    @{ windows_login = 'CONTOSO\appsvc'; entra_principal = 'sql-app-readers'; principal_type = 'group'; review_required = $false }
                    @{ windows_login = 'CONTOSO\nomap'; entra_principal = $null; principal_type = 'unresolved'; review_required = $true }
                ) }
        }
    }

    It 'emits idempotent CREATE LOGIN ... FROM EXTERNAL PROVIDER for resolved principals' {
        $out = Join-Path $TestDrive 'create-logins.sql'
        $sql = New-UIAOEntraLoginScript -MappingPath $Script:Mapping -OutputPath $out
        Test-Path -LiteralPath $out | Should -BeTrue
        $sql | Should -Match 'IF NOT EXISTS'
        $sql | Should -Match 'CREATE LOGIN \[jdoe@contoso\.gov\] FROM EXTERNAL PROVIDER'
        $sql | Should -Match 'CREATE LOGIN \[sql-app-readers\] FROM EXTERNAL PROVIDER'
    }

    It 'does NOT emit runnable T-SQL for unresolved mappings' {
        $sql = New-UIAOEntraLoginScript -MappingPath $Script:Mapping
        $sql | Should -Not -Match 'CREATE LOGIN \[\] FROM EXTERNAL PROVIDER'
        $sql | Should -Match 'TODO \(review\)'
    }

    It 'opens no SQL connection — it returns/writes text only' {
        # The function has no -Server/-Execute surface at all.
        (Get-Command New-UIAOEntraLoginScript).Parameters.Keys | Should -Not -Contain 'Server'
        (Get-Command New-UIAOEntraLoginScript).Parameters.Keys | Should -Not -Contain 'Execute'
    }
}

Describe 'Login — Test-UIAOLoginParallelRun (Book 05 Step 3)' {
    It 'is cutover-ready when no NTLM remains and every login also uses AAD' {
        $p = Join-Path $TestDrive 'obs-good.csv'
        @(
            [PSCustomObject]@{ login_name = 'CONTOSO\jdoe'; auth_scheme = 'KERBEROS'; sessions = 2 }
            [PSCustomObject]@{ login_name = 'CONTOSO\jdoe'; auth_scheme = 'AAD'; sessions = 5 }
        ) | Export-Csv -LiteralPath $p -NoTypeInformation -Encoding UTF8
        $r = Test-UIAOLoginParallelRun -ObservationPath $p
        $r.data.cutover_ready | Should -BeTrue
        $r.data.ntlm_rows | Should -Be 0
    }

    It 'is not cutover-ready while NTLM rows remain' {
        $p = Join-Path $TestDrive 'obs-ntlm.csv'
        @(
            [PSCustomObject]@{ login_name = 'CONTOSO\jdoe'; auth_scheme = 'NTLM'; sessions = 1 }
            [PSCustomObject]@{ login_name = 'CONTOSO\jdoe'; auth_scheme = 'AAD'; sessions = 5 }
        ) | Export-Csv -LiteralPath $p -NoTypeInformation -Encoding UTF8
        $r = Test-UIAOLoginParallelRun -ObservationPath $p
        $r.data.cutover_ready | Should -BeFalse
        $r.data.ntlm_rows | Should -Be 1
    }

    It 'is not cutover-ready while a login arrives only on its legacy scheme' {
        $p = Join-Path $TestDrive 'obs-legacy.csv'
        @(
            [PSCustomObject]@{ login_name = 'CONTOSO\legacy'; auth_scheme = 'KERBEROS'; sessions = 3 }
        ) | Export-Csv -LiteralPath $p -NoTypeInformation -Encoding UTF8
        $r = Test-UIAOLoginParallelRun -ObservationPath $p
        $r.data.cutover_ready | Should -BeFalse
        $r.data.logins_only_legacy | Should -Be 1
    }
}

Describe 'NTLM — New-UIAOSpnRemediationPlan (Book 06 Phase 2, audit-first)' {
    BeforeAll {
        $Script:Collision = Join-Path $TestDrive 'collisions.json'
        Write-Json -Path $Script:Collision -Object @{
            Collisions = @(
                @{
                    SPN = 'MSSQLSvc/sqlhost:1433'; ServiceClass = 'MSSQLSvc'; CollisionType = 'ExactDuplicate'; Severity = 'High'
                    Accounts = @(
                        @{ AccountName = 'CONTOSO\svc-sql'; ObjectType = 'user'; Enabled = $true }
                        @{ AccountName = 'CONTOSO\old-sql'; ObjectType = 'user'; Enabled = $false }
                    )
                }
                @{
                    SPN = 'HTTP/web'; ServiceClass = 'HTTP'; CollisionType = 'CrossObjectType'; Severity = 'Critical'
                    Accounts = @(
                        @{ AccountName = 'WEB01$'; ObjectType = 'computer'; Enabled = $true }
                        @{ AccountName = 'CONTOSO\svc-web'; ObjectType = 'user'; Enabled = $true }
                    )
                }
            )
        }
    }

    It 'emits a setspn -D for the disabled (shadowing) account' {
        $r = New-UIAOSpnRemediationPlan -CollisionReportPath $Script:Collision
        $sql = $r.data.records | Where-Object { $_.spn -eq 'MSSQLSvc/sqlhost:1433' }
        ($sql.commands -join ' ') | Should -Match 'setspn -D MSSQLSvc/sqlhost:1433 CONTOSO\\old-sql'
    }

    It 'recommends removing the user-object SPN for a cross-object-type collision' {
        $r = New-UIAOSpnRemediationPlan -CollisionReportPath $Script:Collision
        $web = $r.data.records | Where-Object { $_.spn -eq 'HTTP/web' }
        ($web.commands -join ' ') | Should -Match 'setspn -D HTTP/web CONTOSO\\svc-web'
        ($web.commands -join ' ') | Should -Match 'workload identity'
    }

    It 'marks every action mutating and review-required, and runs no setspn' {
        $r = New-UIAOSpnRemediationPlan -CollisionReportPath $Script:Collision
        foreach ($a in $r.data.records) {
            $a.mutating | Should -BeTrue
            $a.requires_review | Should -BeTrue
        }
        $r.data.enforcement | Should -Be 'none_by_default'
    }

    It 'scopes to a service class with -ServiceClassFilter' {
        $r = New-UIAOSpnRemediationPlan -CollisionReportPath $Script:Collision -ServiceClassFilter 'MSSQLSvc'
        @($r.data.records | Where-Object { $_.service_class -eq 'HTTP' }).Count | Should -Be 0
    }
}

Describe 'NTLM — Get-UIAONtlmGpoReport (Book 06 Phase 2, read-only)' {
    BeforeAll {
        $Script:Gpo = Join-Path $TestDrive 'gpo.json'
        Write-Json -Path $Script:Gpo -Object @{
            records = @(
                @{ gpo_name = 'NTLMv2-Only'; lm_compatibility_level = 5 }
                @{ gpo_name = 'Legacy'; lm_compatibility_level = 2 }
                @{ gpo_name = 'FullBlock'; lm_compatibility_level = 5; restrict_ntlm_incoming = 'DenyAll' }
                @{ gpo_name = 'NoSetting' }
            )
        }
    }

    It 'classifies posture per the ADR-068 phased plan' {
        $r = Get-UIAONtlmGpoReport -GpoReportPath $Script:Gpo
        $by = @{}; foreach ($x in $r.data.records) { $by[$x.gpo_name] = $x.posture }
        $by['NTLMv2-Only'] | Should -Be 'phase_b_ntlmv2_only'
        $by['Legacy'] | Should -Be 'below_target'
        $by['FullBlock'] | Should -Be 'phase_c_full_block'
        $by['NoSetting'] | Should -Be 'unconfigured'
    }

    It 'records the program backstop as a planning date, not a mandate' {
        $r = Get-UIAONtlmGpoReport -GpoReportPath $Script:Gpo
        $r.data.program_backstop | Should -Be '2027-04-01'
        $r.data.read_only | Should -BeTrue
        $r.data.backstop_note | Should -Match 'not an external'
    }
}

Describe 'Input validation' {
    It 'throws on a missing audit file' {
        { New-UIAOEntraLoginMapping -LoginAuditPath (Join-Path $TestDrive 'nope.csv') } | Should -Throw '*not found*'
    }

    It 'throws on an empty collision report' {
        $empty = Join-Path $TestDrive 'empty.json'
        '' | Set-Content -LiteralPath $empty -Encoding UTF8
        { New-UIAOSpnRemediationPlan -CollisionReportPath $empty } | Should -Throw '*empty*'
    }
}
