#requires -Modules Pester
<#
    Pester 5 tests for the Help Desk / Cloud Services kit.

    No Microsoft Graph module is needed: the routing tests exercise the module's
    pure functions, and the -WhatIf test reads Invoke-RequestTriage.ps1's syntax
    tree, so the gate is checked without connecting to a tenant.
#>

BeforeAll {
    # Repo layout: scripts/tests/ beside the module and scripts.
    # Kit zip layout: tests/ beside lib/ (module) and scripts/.
    $root = Split-Path $PSScriptRoot -Parent
    if (Test-Path (Join-Path $root 'lib\HelpDeskEntra.psm1')) {
        $modulePath        = Join-Path $root 'lib\HelpDeskEntra.psm1'
        $script:ScriptsDir = Join-Path $root 'scripts'
    } else {
        $modulePath        = Join-Path $root 'HelpDeskEntra.psm1'
        $script:ScriptsDir = $root
    }
    Import-Module $modulePath -Force
    $script:Table = Get-RequestRoutingTable
    function Get-Rule([string]$Key) { $script:Table | Where-Object Key -eq $Key }
}

Describe 'Routing table shape' {
    It 'has unique keys' {
        $dupes = $script:Table | Group-Object Key | Where-Object Count -gt 1
        $dupes | Should -BeNullOrEmpty
    }

    It 'gives every row a Verification of IdentityProof or None' {
        $script:Table | Where-Object { $_.Verification -notin 'IdentityProof', 'None' } | Should -BeNullOrEmpty
    }

    It 'never routes Help Desk work through Application or Hybrid Identity Administrator' {
        $script:Table | Where-Object { $_.PimRole -in 'Application Administrator', 'Hybrid Identity Administrator' } |
            Should -BeNullOrEmpty
    }
}

Describe 'Execution matches what the Entra ID spoke documents' {
    It 'MFA reset is a manual Help Desk task (the spoke has no method reset)' {
        (Get-Rule 'MfaReset').Execution | Should -Be 'Manual'
    }

    It 'device enable/disable/delete is out of scope (device team)' {
        $r = Get-Rule 'DeviceManagement'
        $r.Execution   | Should -Be 'OutOfScope'
        $r.Destination | Should -Be 'Escalate'
    }

    It 'enterprise app access is manual until the spoke action is piloted' {
        (Get-Rule 'EnterpriseAppAccess').Execution | Should -Be 'Manual'
    }

    It 'directory audit-log reads are manual (the spoke only looks up sign-ins)' {
        (Get-Rule 'AuditLogRetrieval').Execution  | Should -Be 'Manual'
        (Get-Rule 'SignInLogRetrieval').Execution | Should -Be 'Spoke'
    }

    It 'ImmutableID repair is escalate-only for the Help Desk' {
        $r = Get-Rule 'ImmutableIdRepair'
        $r.TeamRole | Should -Be 'TriageEscalateOnly'
        $r.PimRole  | Should -BeNullOrEmpty
    }

    It 'group creation is escalate-only for the Help Desk (Identity Engineering executes)' {
        $r = Get-Rule 'GroupCreation'
        $r.TeamRole | Should -Be 'TriageEscalateOnly'
        $r.PimRole  | Should -BeNullOrEmpty
    }

    It 'app registration requests are out of scope for the Help Desk' {
        $r = Resolve-RequestRoute -Text 'Please register an app for the new portal'
        $r.Key      | Should -Be 'ServicePrincipalChange'
        $r.TeamRole | Should -Be 'OutOfScope'
    }

    It 'password, MFA and Temporary Access Pass rows require identity verification' {
        foreach ($k in 'PasswordReset', 'PasswordResetCloudOnly', 'PasswordResetSynced', 'MfaReset', 'TemporaryAccessPass') {
            (Get-Rule $k).Verification | Should -Be 'IdentityProof' -Because $k
        }
    }
}

Describe 'Resolve-RequestRoute' {
    It 'routes a password reset to the conservative manual row when sync state is unknown' {
        $r = Resolve-RequestRoute -Text 'Please reset my password'
        $r.Key       | Should -Be 'PasswordReset'
        $r.Execution | Should -Be 'Manual'
    }

    It 'routes a cloud-only password reset to the spoke' {
        $r = Resolve-RequestRoute -Text 'Please reset my password' -TargetSynced $false
        $r.Key       | Should -Be 'PasswordResetCloudOnly'
        $r.Execution | Should -Be 'Spoke'
    }

    It 'routes a synced password reset to a manual task' {
        $r = Resolve-RequestRoute -Text 'Please reset my password' -TargetSynced $true
        $r.Key       | Should -Be 'PasswordResetSynced'
        $r.Execution | Should -Be 'Manual'
    }

    It 'never text-matches the password variants directly' {
        (Get-Rule 'PasswordResetCloudOnly').Match | Should -BeNullOrEmpty
        (Get-Rule 'PasswordResetSynced').Match    | Should -BeNullOrEmpty
    }

    It 'classifies <Text> as <Key>' -ForEach @(
        @{ Text = 'Lost my phone, need my MFA reset';           Key = 'MfaReset' }
        @{ Text = 'I lost every sign-in method, need a temporary access pass'; Key = 'TemporaryAccessPass' }
        @{ Text = 'Please assign an E5 license';                Key = 'LicenseAssignment' }
        @{ Text = 'Need a G3 licence for the new analyst';      Key = 'LicenseAssignment' }
        @{ Text = 'Disable the device LAPTOP-042';              Key = 'DeviceManagement' }
        @{ Text = 'Sync mismatch - duplicate account in Entra'; Key = 'ImmutableIdRepair' }
        @{ Text = 'Pull the sign-in logs for this user';     Key = 'SignInLogRetrieval' }
        @{ Text = 'Need the directory audit log for a change'; Key = 'AuditLogRetrieval' }
        @{ Text = 'Please create a new security group for the app'; Key = 'GroupCreation' }
    ) {
        (Resolve-RequestRoute -Text $Text).Key | Should -Be $Key
    }

    It 'does not treat e3/e5/sku inside other words as a license request' {
        (Resolve-RequestRoute -Text 'Error code e3f2a1 when opening the skunkworks site').Key |
            Should -Not -Be 'LicenseAssignment'
    }

    It 'falls back to Unknown with manual triage' {
        $r = Resolve-RequestRoute -Text 'hello'
        $r.Key       | Should -Be 'Unknown'
        $r.Execution | Should -Be 'Manual'
    }
}

Describe 'Invoke-RequestTriage -WhatIf gate' {
    BeforeAll {
        $path = Join-Path $script:ScriptsDir 'Invoke-RequestTriage.ps1'
        $script:Ast = [System.Management.Automation.Language.Parser]::ParseFile($path, [ref]$null, [ref]$null)

        function Test-InsideShouldProcess($Node) {
            $p = $Node.Parent
            while ($p) {
                if ($p -is [System.Management.Automation.Language.IfStatementAst] -and
                    $p.Clauses[0].Item1.Extent.Text -match 'ShouldProcess') { return $true }
                $p = $p.Parent
            }
            return $false
        }
        function Test-InsideFunction($Node) {
            $p = $Node.Parent
            while ($p) {
                if ($p -is [System.Management.Automation.Language.FunctionDefinitionAst]) { return $true }
                $p = $p.Parent
            }
            return $false
        }

        $script:Calls = $script:Ast.FindAll({ $args[0] -is [System.Management.Automation.Language.CommandAst] }, $true) |
            Where-Object { -not (Test-InsideFunction $_) }
    }

    It 'calls <Name> only inside the ShouldProcess block' -ForEach @(
        @{ Name = 'New-ServiceNowWorkItem' }
        @{ Name = 'New-SamAccessRequest' }
        @{ Name = 'Send-ToEscalationQueue' }
        @{ Name = 'Update-MgUserMessage' }
    ) {
        $hits = @($script:Calls | Where-Object { $_.GetCommandName() -eq $Name })
        $hits.Count | Should -BeGreaterThan 0
        foreach ($h in $hits) { Test-InsideShouldProcess $h | Should -BeTrue -Because "line $($h.Extent.StartLineNumber)" }
    }

    It 'reads only the Inbox folder' {
        $all = @($script:Calls | Where-Object { $_.GetCommandName() -eq 'Get-MgUserMessage' })
        $all.Count | Should -Be 0
        $inbox = @($script:Calls | Where-Object { $_.GetCommandName() -eq 'Get-MgUserMailFolderMessage' })
        $inbox.Count | Should -Be 1
        $inbox[0].Extent.Text | Should -Match "-MailFolderId\s+'Inbox'"
    }
}

Describe 'Scope sets' {
    It 'mail triage uses the shared-mailbox scope' {
        $m = Get-Module HelpDeskEntra
        $sets = & $m { $script:GraphScopeSets }
        $sets.MailTriage    | Should -Contain 'Mail.ReadWrite.Shared'
        $sets.InventoryRead | Should -Not -Contain 'AppRoleAssignment.ReadWrite.All'
        $sets.AppAssignment | Should -Not -Contain 'Group.ReadWrite.All'
        $sets.AppAssignment | Should -Not -Contain 'Application.ReadWrite.All'
        $sets.PimGroups     | Should -Contain 'User.ReadBasic.All'
    }
}
