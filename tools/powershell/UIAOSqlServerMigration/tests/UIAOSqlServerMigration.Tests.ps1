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
    It 'exports exactly the sixteen roster functions' {
        $exported = @((Get-Command -Module UIAOSqlServerMigration).Name)
        $exported.Count | Should -Be 16
        foreach ($fn in @(
                'Test-UIAOArcAgentStatus', 'Test-UIAOArcManagedIdentityToken', 'Test-UIAOArcSqlExtension',
                'Invoke-UIAOArcOnboarding', 'New-UIAOEntraLoginMapping', 'New-UIAOEntraLoginScript',
                'Test-UIAOLoginParallelRun', 'New-UIAOSpnRemediationPlan', 'Get-UIAONtlmGpoReport',
                'New-UIAOEstateInventory', 'New-UIAOEntraGroupClassification', 'New-UIAOGroupLoginScript',
                'New-UIAOAppConnectionPlan', 'New-UIAOClosureRecord', 'Compare-UIAOClosureRun',
                'New-UIAOSqlCertificatePlan')) {
            $exported | Should -Contain $fn
        }
    }

    It 'matches the manifest FunctionsToExport' {
        $manifest = Import-PowerShellDataFile (Join-Path $PSScriptRoot '..' 'UIAOSqlServerMigration.psd1')
        $exported = @((Get-Command -Module UIAOSqlServerMigration).Name) | Sort-Object
        (@($manifest.FunctionsToExport) | Sort-Object) | Should -Be $exported
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

Describe 'Estate — New-UIAOEstateInventory (Book 02, the gate)' {
    BeforeAll {
        $Script:Audit02 = Join-Path $TestDrive 'd18-discovery.json'
        Write-Json -Path $Script:Audit02 -Object @{
            InstanceAudits = @(
                @{ ServerName = 'SQL01'; InstanceName = 'MSSQLSERVER'; SQLVersionMajor = 16; SQLEdition = 'Enterprise'; AuthenticationMode = 'Mixed' }
                @{ ServerName = 'SQL02'; InstanceName = 'MSSQLSERVER'; SQLVersionMajor = 13; SQLEdition = 'Standard' }
                @{ ServerName = 'SQL03'; InstanceName = 'MSSQLSERVER'; SQLVersionMajor = 16; LastAccessDays = 500 }
                @{ ServerName = 'SQL04'; InstanceName = 'MSSQLSERVER' }
            )
        }
    }

    It 'applies the retain / consolidate / retire / review gate' {
        $r = New-UIAOEstateInventory -AuthAuditPath $Script:Audit02
        $r.data.denominator | Should -Be 4
        $r.data.classification.retain | Should -Be 1
        $r.data.classification.consolidate | Should -Be 1
        $r.data.classification.retire | Should -Be 1
        $r.data.classification.review | Should -Be 1
    }

    It 'lets a zombie (stale last-access) override the supported-version retain' {
        $r = New-UIAOEstateInventory -AuthAuditPath $Script:Audit02
        $sql03 = $r.data.records | Where-Object { $_.instance_key -eq 'sql03' }
        $sql03.classification | Should -Be 'retire'
    }

    It 'only retain instances enter the auth migration' {
        $r = New-UIAOEstateInventory -AuthAuditPath $Script:Audit02
        @($r.data.records | Where-Object { $_.enters_auth_migration }).Count | Should -Be 1
        ($r.data.records | Where-Object { $_.instance_key -eq 'sql01' }).enters_auth_migration | Should -BeTrue
    }

    It 'merges the SPN trail and records source coverage (dedup by host)' {
        $spn = Join-Path $TestDrive 'd15-spn.json'
        Write-Json -Path $spn -Object @{ SPNs = @(
                @{ HostName = 'SQL01'; SPN = 'MSSQLSvc/SQL01.contoso.gov:1433' }
                @{ SPN = 'MSSQLSvc/SQL99:1433' }
            ) }
        $r = New-UIAOEstateInventory -AuthAuditPath $Script:Audit02 -SpnInventoryPath $spn
        $r.data.denominator | Should -Be 5   # SQL99 is new; SQL01 dedups
        $sql01 = $r.data.records | Where-Object { $_.instance_key -eq 'sql01' }
        $sql01.discovered_by | Should -Contain 'Spec3-D1.8'
        $sql01.discovered_by | Should -Contain 'Spec1-D1.5'
        ($r.data.records | Where-Object { $_.instance_key -eq 'sql99' }).discovered_by | Should -Contain 'Spec1-D1.5'
    }

    It 'seals the inventory reproducibly' {
        $r = New-UIAOEstateInventory -AuthAuditPath $Script:Audit02
        (Get-ExpectedHash -DataObject $r.data) | Should -Be $r.provenance.content_hash
    }
}

Describe 'Groups — New-UIAOEntraGroupClassification (Book 07, ADR-067)' {
    BeforeAll {
        $Script:Groups = Join-Path $TestDrive 'groups.json'
        Write-Json -Path $Script:Groups -Object @{
            data = @{ records = @(
                    @{ display_name = 'SQL-DBAs'; security_enabled = $true; mail_enabled = $false }
                    @{ display_name = 'OrgPath-Finance'; security_enabled = $true; mail_enabled = $false; membership_rule = '(user.department -eq "Finance")' }
                    @{ display_name = 'All-Staff-DL'; security_enabled = $false; mail_enabled = $true; mail = 'all@contoso.gov' }
                    @{ display_name = 'AppOwners'; security_enabled = $true; mail_enabled = $true; mail = 'appowners@contoso.gov' }
                    @{ display_name = 'Project-Unified'; groupTypes = @('Unified') }
                ) }
        }
    }

    It 'assigns each group exactly one ADR-067 type' {
        $r = New-UIAOEntraGroupClassification -GroupExportPath $Script:Groups
        $by = @{}; foreach ($x in $r.data.records) { $by[$x.display_name] = $x.group_type }
        $by['SQL-DBAs'] | Should -Be 'assigned_security_group'
        $by['OrgPath-Finance'] | Should -Be 'orgtree_dynamic_group'
        $by['All-Staff-DL'] | Should -Be 'distribution_m365_group'
        $by['AppOwners'] | Should -Be 'mail_enabled_split'
        $by['Project-Unified'] | Should -Be 'm365_unified'
    }

    It 'marks only access-backing groups as becoming SQL logins' {
        $r = New-UIAOEntraGroupClassification -GroupExportPath $Script:Groups
        ($r.data.records | Where-Object { $_.display_name -eq 'SQL-DBAs' }).becomes_sql_login | Should -BeTrue
        ($r.data.records | Where-Object { $_.display_name -eq 'All-Staff-DL' }).becomes_sql_login | Should -BeFalse
        ($r.data.records | Where-Object { $_.display_name -eq 'AppOwners' }).requires_split | Should -BeTrue
    }

    It 'seals reproducibly' {
        $r = New-UIAOEntraGroupClassification -GroupExportPath $Script:Groups
        (Get-ExpectedHash -DataObject $r.data) | Should -Be $r.provenance.content_hash
    }
}

Describe 'Groups — New-UIAOGroupLoginScript (Book 07, dry-run)' {
    BeforeAll {
        $Script:GroupClass = Join-Path $TestDrive 'group-class.json'
        Write-Json -Path $Script:GroupClass -Object @{
            artifact_type = 'EntraGroupClassification'
            data          = @{ records = @(
                    @{ display_name = 'SQL-DBAs'; group_type = 'assigned_security_group'; becomes_sql_login = $true }
                    @{ display_name = 'All-Staff-DL'; group_type = 'distribution_m365_group'; becomes_sql_login = $false }
                ) }
        }
    }

    It 'emits CREATE LOGIN only for access-backing groups' {
        $sql = New-UIAOGroupLoginScript -ClassificationPath $Script:GroupClass
        $sql | Should -Match 'CREATE LOGIN \[SQL-DBAs\] FROM EXTERNAL PROVIDER'
        $sql | Should -Not -Match 'CREATE LOGIN \[All-Staff-DL\]'
        $sql | Should -Match 'skipped \(distribution_m365_group\)'
    }

    It 'opens no SQL connection (no -Server/-Execute surface)' {
        (Get-Command New-UIAOGroupLoginScript).Parameters.Keys | Should -Not -Contain 'Server'
        (Get-Command New-UIAOGroupLoginScript).Parameters.Keys | Should -Not -Contain 'Execute'
    }
}

Describe 'Apps — New-UIAOAppConnectionPlan (Book 08, ADR-069)' {
    BeforeAll {
        $Script:Ldap = Join-Path $TestDrive 'd19-ldap.json'
        Write-Json -Path $Script:Ldap -Object @{
            LDAPBindAccounts = @(
                @{ SourceApplication = 'Billing'; AccountName = 'CONTOSO\svc-billing'; BindType = 'simple'; MigrationTarget = 'OIDC' }
                @{ SourceApplication = 'LegacyHR'; AccountName = 'CONTOSO\svc-hr'; BindType = 'simple' }
            )
        }
        $Script:Audit08 = Join-Path $TestDrive 'd18-for-apps.json'
        Write-Json -Path $Script:Audit08 -Object @{
            InstanceAudits = @(
                @{ ServerName = 'SQL01'; WindowsLogins = @(@{ LoginName = 'CONTOSO\svc-billing' }) }
            )
        }
    }

    It 'classifies by ADR-069, preferring capability signals then D1.9 MigrationTarget' {
        $r = New-UIAOAppConnectionPlan -LdapBindInventoryPath $Script:Ldap -AuthAuditPath $Script:Audit08 `
            -CapabilityMap @{ LegacyHR = @{ vendor_locked = $true } }
        $by = @{}; foreach ($x in $r.data.records) { $by[$x.source_application] = $x.ldap_class }
        $by['Billing'] | Should -Be 'Class 3 — OIDC'
        $by['LegacyHR'] | Should -Be 'Class 4 — Entra Domain Services'
    }

    It 'correlates the bind account to its SQL instances and emits the conn-string pattern' {
        $r = New-UIAOAppConnectionPlan -LdapBindInventoryPath $Script:Ldap -AuthAuditPath $Script:Audit08
        $billing = $r.data.records | Where-Object { $_.source_application -eq 'Billing' }
        $billing.correlated_sql_instances | Should -Contain 'SQL01'
        $billing.connection_string_pattern | Should -Match 'Active Directory Managed Identity'
        $billing.requires_review | Should -BeTrue
    }
}

Describe 'ConMon — New-UIAOClosureRecord (Book 09, ADR-091 §5)' {
    BeforeAll {
        $Script:Audit09 = Join-Path $TestDrive 'd18-closure.json'
        Write-Json -Path $Script:Audit09 -Object @{
            InstanceAudits = @(
                @{ ServerName = 'SQL01'; InstanceName = 'MSSQLSERVER'; AuthenticationMode = 'Windows'; SaDisabled = $true; ArcConnected = $true; EntraIDReady = $true }
                @{ ServerName = 'SQL02'; InstanceName = 'MSSQLSERVER'; AuthenticationMode = 'Mixed'; SaDisabled = $false; ArcConnected = $true; EntraIDReady = $true; SQLLogins = @(@{ LoginName = 'app_svc' }) }
                @{ ServerName = 'SQL03'; InstanceName = 'MSSQLSERVER'; AuthenticationMode = 'Windows'; SaDisabled = $true; ArcConnected = $true; EntraIDReady = $true; SQLLogins = @(@{ LoginName = 'legacy_app' }) }
            )
        }
        $Script:Exceptions = Join-Path $TestDrive 'exceptions.json'
        Write-Json -Path $Script:Exceptions -Object @{ records = @(@{ ServerName = 'SQL03'; InstanceName = 'MSSQLSERVER' }) }
    }

    It 'closes an instance with every ADR-091 §5 field satisfied' {
        $r = New-UIAOClosureRecord -AuditPath $Script:Audit09
        ($r.data.records | Where-Object { $_.instance_key -eq 'sql01' }).verdict | Should -Be 'closed'
    }

    It 'leaves an instance open with the failing fields named' {
        $r = New-UIAOClosureRecord -AuditPath $Script:Audit09
        $sql02 = $r.data.records | Where-Object { $_.instance_key -eq 'sql02' }
        $sql02.verdict | Should -Be 'open'
        $sql02.failing_fields | Should -Contain 'windows_auth_only'
        $sql02.failing_fields | Should -Contain 'sa_disabled'
    }

    It 'tolerates an excepted type-S login (closed_excepted)' {
        $r = New-UIAOClosureRecord -AuditPath $Script:Audit09 -ExceptionRegistryPath $Script:Exceptions
        ($r.data.records | Where-Object { $_.instance_key -eq 'sql03' }).verdict | Should -Be 'closed_excepted'
    }

    It 'reports MFA/Conditional-Access as an external join, not asserted' {
        $r = New-UIAOClosureRecord -AuditPath $Script:Audit09
        ($r.data.records | Where-Object { $_.instance_key -eq 'sql01' }).mfa_conditional_access | Should -Be 'external'
    }
}

Describe 'ConMon — Compare-UIAOClosureRun (Book 09 drift diff)' {
    BeforeAll {
        $Script:Base = Join-Path $TestDrive 'run-base.json'
        Write-Json -Path $Script:Base -Object @{
            InstanceAudits = @(
                @{ ServerName = 'SQL01'; InstanceName = 'MSSQLSERVER'; AuthenticationMode = 'Windows'; ArcConnected = $true }
                @{ ServerName = 'SQL09'; InstanceName = 'MSSQLSERVER'; AuthenticationMode = 'Windows'; ArcConnected = $true }
            )
        }
        $Script:Curr = Join-Path $TestDrive 'run-curr.json'
        Write-Json -Path $Script:Curr -Object @{
            InstanceAudits = @(
                @{ ServerName = 'SQL01'; InstanceName = 'MSSQLSERVER'; AuthenticationMode = 'Mixed'; ArcConnected = $false; SQLLogins = @(@{ LoginName = 'new_sql_login' }) }
                @{ ServerName = 'SQL05'; InstanceName = 'MSSQLSERVER'; AuthenticationMode = 'Windows'; ArcConnected = $true }
            )
        }
    }

    It 'flags mixed-mode, a new SQL-auth login, and Arc offline as violations' {
        $r = Compare-UIAOClosureRun -BaselinePath $Script:Base -CurrentPath $Script:Curr
        $events = @($r.data.records | Where-Object { $_.instance_key -eq 'sql01' } | ForEach-Object { $_.event })
        $events | Should -Contain 'mixed_mode_enabled'
        $events | Should -Contain 'new_sql_auth_login'
        $events | Should -Contain 'arc_agent_offline'
        $r.data.compliance_violation | Should -BeTrue
    }

    It 'reports appeared/disappeared instances as informational (non-violation)' {
        $r = Compare-UIAOClosureRun -BaselinePath $Script:Base -CurrentPath $Script:Curr
        ($r.data.records | Where-Object { $_.instance_key -eq 'sql05' }).event | Should -Be 'instance_appeared'
        ($r.data.records | Where-Object { $_.instance_key -eq 'sql09' }).event | Should -Be 'instance_disappeared'
        ($r.data.records | Where-Object { $_.instance_key -eq 'sql05' }).violation | Should -BeFalse
    }
}

Describe 'Certificates — New-UIAOSqlCertificatePlan (Book 10)' {
    BeforeAll {
        $Script:Cert = Join-Path $TestDrive 'd110-cert.json'
        Write-Json -Path $Script:Cert -Object @{
            Certificates    = @(
                @{ Subject = 'CN=SQL01.contoso.gov'; AuthenticationType = 'ServerAuth'; IsExpired = $false; DaysToExpiry = 30 }
                @{ Subject = 'CN=jdoe'; AuthenticationType = 'Certificate'; IsSmartCard = $true }
                @{ Subject = 'CN=webserver.contoso.gov'; AuthenticationType = 'ServerAuth' }
            )
            CBARequired     = $true
            CBAReadiness    = 'Partial'
            EnterpriseRootCAs = @(@{ CAName = 'Contoso-Root-CA' })
            EnterpriseSubCAs  = @(@{ CAName = 'Contoso-Issuing-CA' })
        }
    }

    It 'extracts SQL''s three ADCS dependency classes, scoped by -SqlHostFilter' {
        $r = New-UIAOSqlCertificatePlan -CertAuditPath $Script:Cert -SqlHostFilter 'SQL01'
        $r.data.dependency_counts.tls_server_cert | Should -Be 1     # only SQL01, webserver filtered out
        $r.data.dependency_counts.certificate_mapped_login | Should -Be 1
        $r.data.dependency_counts.cba_posture | Should -Be 1
    }

    It 'sequences the CA replacement root-first (the CBA-issuance bridge)' {
        $r = New-UIAOSqlCertificatePlan -CertAuditPath $Script:Cert
        $seq = @($r.data.ca_replacement_sequence)
        $seq[0].ca | Should -Be 'Contoso-Root-CA'
        $seq[0].tier | Should -Be 'root'
        $seq[1].tier | Should -Be 'issuing'
        $r.data.analytical | Should -BeTrue
    }

    It 'marks every record review-required' {
        $r = New-UIAOSqlCertificatePlan -CertAuditPath $Script:Cert
        foreach ($x in $r.data.records) { $x.requires_review | Should -BeTrue }
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

    It 'throws on a missing estate audit file' {
        { New-UIAOEstateInventory -AuthAuditPath (Join-Path $TestDrive 'nope.json') } | Should -Throw '*not found*'
    }
}
