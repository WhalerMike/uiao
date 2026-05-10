# OrgTreeValidation — PowerShell module wrapping UIAO_159.
#
# Companion to canon UIAO_150–UIAO_176. Python is the canonical
# implementation of OrgTree validation logic; this module is the M365
# admin-facing UX layer. Six exported functions:
#
#   1. Test-OrgPathFormat            — pure regex check (UIAO_151)
#   2. Test-OrgPathHierarchy         — parent-in-codebook check
#   3. Get-OrgTreeValidationReport   — Graph PowerShell SDK tenant scan
#   4. Test-DynamicGroupAlignment    — tenant groups vs UIAO_152 library
#   5. Export-OrgTreeSnapshot        — Graph PowerShell SDK snapshot dump
#   6. Compare-OrgTreeSnapshots      — offline JSON snapshot diff
#
# Plus one umbrella verb that delegates to the Python CLI:
#
#   Invoke-UiaoOrgTreeValidate       — shells out to `uiao orgtree validate all`
#
# Functions 3-5 require Microsoft.Graph PowerShell SDK
# (Install-Module Microsoft.Graph). Functions 1, 2, 6 are pure pwsh
# and need no external module.

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Canonical regex sourced from UIAO_151 §regex / codebook.py:CANONICAL_REGEX.
# Pester test in tests/OrgTreeValidation.Tests.ps1 verifies this literal
# matches the value embedded in src/uiao/modernization/orgtree/codebook.py.
$Script:CanonicalOrgPathPattern = '^ORG(-[A-Z0-9]{2,6}){0,4}$'


function Test-OrgPathFormat {
    <#
    .SYNOPSIS
        Validates an OrgPath string against the canonical regex (UIAO_151).
    .DESCRIPTION
        Returns $true if the OrgPath matches ^ORG(-[A-Z0-9]{2,6}){0,4}$;
        $false otherwise. Pure offline check; no tenant access required.
    .PARAMETER OrgPath
        The OrgPath string to validate (e.g., "ORG-FIN-AP").
    .EXAMPLE
        Test-OrgPathFormat -OrgPath "ORG-FIN-AP"
    .NOTES
        Canon: UIAO_151 §regex. Equivalent Python: `uiao orgtree validate codebook`.
    #>
    [CmdletBinding()]
    [OutputType([bool])]
    param(
        [Parameter(Mandatory = $true)]
        [ValidateNotNullOrEmpty()]
        [string]$OrgPath
    )
    # -cmatch is case-SENSITIVE; required to match Python's re.compile()
    # default behavior on the same regex. PowerShell's -match is
    # case-insensitive by default, which would silently accept lowercase
    # segments and drift away from the Python source-of-truth in
    # src/uiao/modernization/orgtree/codebook.py:CANONICAL_REGEX.
    return [bool]($OrgPath -cmatch $Script:CanonicalOrgPathPattern)
}


function Test-OrgPathHierarchy {
    <#
    .SYNOPSIS
        Validates that a child OrgPath has a registered parent in the codebook.
    .DESCRIPTION
        For ORG (the root), returns $true. Otherwise, computes the parent
        path by stripping the trailing segment and checks that it exists as
        a key in the supplied codebook hashtable.
    .PARAMETER ChildPath
        The OrgPath to validate.
    .PARAMETER Codebook
        Hashtable whose keys are valid OrgPath codes.
    .EXAMPLE
        $cb = @{ "ORG" = $true; "ORG-FIN" = $true }
        Test-OrgPathHierarchy -ChildPath "ORG-FIN-AP" -Codebook $cb   # -> $false (ORG-FIN-AP requires ORG-FIN-AP key OR parent only — see Notes)
    .NOTES
        Hierarchy validity is "the *parent* exists", not "the path itself
        exists". A leaf code's existence is checked separately by callers
        (see Get-OrgTreeValidationReport which checks `$Codebook.ContainsKey($OrgPath)`).
    #>
    [CmdletBinding()]
    [OutputType([bool])]
    param(
        [Parameter(Mandatory = $true)]
        [ValidateNotNullOrEmpty()]
        [string]$ChildPath,

        [Parameter(Mandatory = $true)]
        [hashtable]$Codebook
    )
    if ($ChildPath -eq 'ORG') {
        return $true
    }
    $segments = $ChildPath -split '-'
    if ($segments.Count -lt 2) {
        return $false
    }
    $parentPath = ($segments[0..($segments.Count - 2)]) -join '-'
    return $Codebook.ContainsKey($parentPath)
}


function Get-OrgTreeValidationReport {
    <#
    .SYNOPSIS
        Walks a tenant's users and validates each user's OrgPath.
    .DESCRIPTION
        Connects to the specified tenant via Microsoft.Graph PowerShell SDK,
        retrieves all users with `OnPremisesExtensionAttributes`, validates
        each user's OrgPath (ExtensionAttribute1) against the supplied
        codebook, and returns a summary PSCustomObject.

        Requires Microsoft.Graph module and User.Read.All scope.
    .PARAMETER TenantId
        Target tenant identifier.
    .PARAMETER CodebookPath
        Path to a JSON codebook file with shape:
        { "entries": [ { "code": "ORG-FIN" }, ... ] }
    .EXAMPLE
        Get-OrgTreeValidationReport -TenantId $tid -CodebookPath ./codebook.json
    .NOTES
        UIAO_159 Function 3. Tenant-scope work; no Pester unit-coverage.
    #>
    [CmdletBinding()]
    [OutputType([psobject])]
    param(
        [Parameter(Mandatory = $true)]
        [ValidateNotNullOrEmpty()]
        [string]$TenantId,

        [Parameter(Mandatory = $true)]
        [ValidateScript({ Test-Path $_ })]
        [string]$CodebookPath
    )

    $codebookJson = Get-Content -Path $CodebookPath -Raw | ConvertFrom-Json
    $codebook = @{}
    foreach ($entry in $codebookJson.entries) {
        $codebook[$entry.code] = $entry
    }

    Connect-MgGraph -TenantId $TenantId -Scopes 'User.Read.All' -NoWelcome

    $users = @(Get-MgUser -All -Property 'Id,DisplayName,OnPremisesExtensionAttributes')
    $valid = 0; $invalid = 0; $orphaned = 0

    foreach ($user in $users) {
        $orgPath = $user.OnPremisesExtensionAttributes.ExtensionAttribute1
        if ([string]::IsNullOrEmpty($orgPath)) {
            $orphaned++
            continue
        }
        $formatOk = Test-OrgPathFormat -OrgPath $orgPath
        $hierarchyOk = Test-OrgPathHierarchy -ChildPath $orgPath -Codebook $codebook
        if ($formatOk -and $hierarchyOk -and $codebook.ContainsKey($orgPath)) {
            $valid++
        }
        else {
            $invalid++
        }
    }

    return [pscustomobject]@{
        TotalUsers      = $users.Count
        ValidOrgPaths   = $valid
        InvalidOrgPaths = $invalid
        OrphanedUsers   = $orphaned
        DriftDetected   = ($invalid -gt 0 -or $orphaned -gt 0)
    }
}


function Test-DynamicGroupAlignment {
    <#
    .SYNOPSIS
        Compares tenant dynamic groups against the canonical library (UIAO_152).
    .PARAMETER TenantId
        Target tenant identifier.
    .PARAMETER GroupLibraryPath
        JSON path with array of { groupName, membershipRule } entries.
    .NOTES
        UIAO_159 Function 4. Tenant-scope; no Pester unit-coverage.
    #>
    [CmdletBinding()]
    [OutputType([psobject])]
    param(
        [Parameter(Mandatory = $true)]
        [ValidateNotNullOrEmpty()]
        [string]$TenantId,

        [Parameter(Mandatory = $true)]
        [ValidateScript({ Test-Path $_ })]
        [string]$GroupLibraryPath
    )

    $library = Get-Content -Path $GroupLibraryPath -Raw | ConvertFrom-Json
    Connect-MgGraph -TenantId $TenantId -Scopes 'Group.Read.All' -NoWelcome

    $aligned = 0; $misaligned = 0; $missing = 0
    $details = @()

    foreach ($definition in $library) {
        $tenantGroup = Get-MgGroup -Filter "displayName eq '$($definition.groupName)'" -ErrorAction SilentlyContinue
        if (-not $tenantGroup) {
            $missing++
            $details += [pscustomobject]@{ GroupName = $definition.groupName; Status = 'Missing' }
            continue
        }
        if ($tenantGroup.MembershipRule -eq $definition.membershipRule) {
            $aligned++
            $details += [pscustomobject]@{ GroupName = $definition.groupName; Status = 'Aligned' }
        }
        else {
            $misaligned++
            $details += [pscustomobject]@{ GroupName = $definition.groupName; Status = 'Misaligned' }
        }
    }

    return [pscustomobject]@{
        AlignedGroups    = $aligned
        MisalignedGroups = $misaligned
        MissingGroups    = $missing
        Details          = $details
    }
}


function Export-OrgTreeSnapshot {
    <#
    .SYNOPSIS
        Snapshots the current OrgTree state to a JSON file.
    .PARAMETER TenantId
        Target tenant identifier.
    .PARAMETER OutputPath
        Destination JSON file path.
    .NOTES
        UIAO_159 Function 5. Tenant-scope; no Pester unit-coverage.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$TenantId,

        [Parameter(Mandatory = $true)]
        [string]$OutputPath
    )

    Connect-MgGraph -TenantId $TenantId -Scopes 'User.Read.All', 'Group.Read.All' -NoWelcome

    $users = @(Get-MgUser -All -Property 'Id,DisplayName,UserPrincipalName,Department,OnPremisesExtensionAttributes')
    $groups = @(Get-MgGroup -All -Property 'Id,DisplayName,MembershipRule,GroupTypes' |
            Where-Object { $_.DisplayName -like 'OrgTree-*' })

    $snapshot = [pscustomobject]@{
        snapshotDate = (Get-Date -Format 'o')
        tenantId     = $TenantId
        userCount    = $users.Count
        groupCount   = $groups.Count
        users        = $users | ForEach-Object {
            [pscustomobject]@{
                id         = $_.Id
                upn        = $_.UserPrincipalName
                orgPath    = $_.OnPremisesExtensionAttributes.ExtensionAttribute1
                department = $_.Department
            }
        }
        groups       = $groups | ForEach-Object {
            [pscustomobject]@{
                id             = $_.Id
                displayName    = $_.DisplayName
                membershipRule = $_.MembershipRule
            }
        }
    }

    $snapshot | ConvertTo-Json -Depth 5 | Set-Content -Path $OutputPath -Encoding UTF8
}


function Compare-OrgTreeSnapshots {
    <#
    .SYNOPSIS
        Diffs two OrgTree snapshots; emits drift entries.
    .PARAMETER BaselinePath
        Baseline snapshot JSON.
    .PARAMETER CurrentPath
        Current snapshot JSON.
    .OUTPUTS
        Array of drift PSCustomObjects: ObjectId, ObjectType, DriftType,
        Field, BaselineValue, CurrentValue.
    .NOTES
        UIAO_159 Function 6. Pure offline diff; Pester-tested.
    #>
    [CmdletBinding()]
    [OutputType([psobject[]])]
    param(
        [Parameter(Mandatory = $true)]
        [ValidateScript({ Test-Path $_ })]
        [string]$BaselinePath,

        [Parameter(Mandatory = $true)]
        [ValidateScript({ Test-Path $_ })]
        [string]$CurrentPath
    )

    $baseline = Get-Content -Path $BaselinePath -Raw | ConvertFrom-Json
    $current = Get-Content -Path $CurrentPath -Raw | ConvertFrom-Json

    $drift = @()
    $baselineMap = @{}
    foreach ($u in $baseline.users) { $baselineMap[$u.id] = $u }

    foreach ($cu in $current.users) {
        if (-not $baselineMap.ContainsKey($cu.id)) {
            $drift += [pscustomobject]@{
                ObjectId      = $cu.id
                ObjectType    = 'User'
                DriftType     = 'NewObject'
                Field         = 'N/A'
                BaselineValue = $null
                CurrentValue  = $cu.orgPath
            }
            continue
        }
        $bu = $baselineMap[$cu.id]
        if ($bu.orgPath -ne $cu.orgPath) {
            $drift += [pscustomobject]@{
                ObjectId      = $cu.id
                ObjectType    = 'User'
                DriftType     = 'ValueDrift'
                Field         = 'orgPath'
                BaselineValue = $bu.orgPath
                CurrentValue  = $cu.orgPath
            }
        }
    }

    return $drift
}


function Invoke-UiaoOrgTreeValidate {
    <#
    .SYNOPSIS
        Shells out to `uiao orgtree validate all` and surfaces the result.
    .DESCRIPTION
        Locates the uiao Python CLI on PATH, runs the aggregate
        validation, and returns a PSCustomObject with the captured
        stdout/exit code. The Python CLI is the canonical implementation
        of Functions 1-4's offline checks (codebook, dynamic groups,
        admin units, device planes, policy targets, drift-engine config).
    .PARAMETER UiaoPath
        Override the path to the uiao executable. Defaults to "uiao" on PATH.
    .EXAMPLE
        Invoke-UiaoOrgTreeValidate
    .NOTES
        Bridge between the M365-admin-UX (PowerShell, this module) and
        the canonical implementation (Python, src/uiao/modernization/orgtree).
    #>
    [CmdletBinding()]
    [OutputType([psobject])]
    param(
        [string]$UiaoPath = 'uiao'
    )

    $proc = Start-Process -FilePath $UiaoPath -ArgumentList 'orgtree', 'validate', 'all' `
        -NoNewWindow -PassThru -Wait `
        -RedirectStandardOutput ([System.IO.Path]::GetTempFileName()) `
        -RedirectStandardError ([System.IO.Path]::GetTempFileName())

    return [pscustomobject]@{
        ExitCode = $proc.ExitCode
        Passed   = ($proc.ExitCode -eq 0)
    }
}


Export-ModuleMember -Function @(
    'Test-OrgPathFormat',
    'Test-OrgPathHierarchy',
    'Get-OrgTreeValidationReport',
    'Test-DynamicGroupAlignment',
    'Export-OrgTreeSnapshot',
    'Compare-OrgTreeSnapshots',
    'Invoke-UiaoOrgTreeValidate'
)
