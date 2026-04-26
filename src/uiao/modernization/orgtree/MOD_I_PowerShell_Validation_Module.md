---
document_id: MOD_I
title: "Appendix I — PowerShell Validation Module"
version: "1.0"
status: DRAFT
classification: CANONICAL
owner: Michael Stratton
created_at: 2026-04-18
updated_at: 2026-04-18
boundary: GCC-Moderate
namespace: MOD
parent_canon: UIAO_008
---

# Appendix I — PowerShell Validation Module

Purpose

This appendix provides a complete PowerShell module for validating OrgTree configuration against the canonical schemas and codebook. The module is the primary validation tool used in migration (Appendix F), enforcement testing (Appendix J), and drift detection (Appendix M).

Scope

Covers six validation functions that operate against any M365 GCC-Moderate tenant via Microsoft Graph API. All functions are tenant-agnostic, using parameterized $TenantId variables.

Canonical Structure

Each function includes comment-based help, parameter validation attributes, try/catch error handling, and Write-Verbose logging. All Graph API calls use the Microsoft Graph PowerShell SDK (Connect-MgGraph).

Technical Scaffolding

Function 1: Test-OrgPathFormat

function Test-OrgPathFormat {     <#     .SYNOPSIS         Validates an OrgPath string against the canonical regex pattern.     .DESCRIPTION         Returns $true if the OrgPath matches ^ORG(-[A-Z]{2,6}){0,8}$, otherwise $false.     .PARAMETER OrgPath         The OrgPath string to validate.     .EXAMPLE         Test-OrgPathFormat -OrgPath "ORG-FIN-AP"     #>     [CmdletBinding()]     [OutputType([bool])]     param(         [Parameter(Mandatory = $true)]         [ValidateNotNullOrEmpty()]         [string]$OrgPath     )      try {         $Pattern = "^ORG(-[A-Z]{2,6}){0,8}$"         $IsValid = $OrgPath -match $Pattern         Write-Verbose "OrgPath '$OrgPath' format valid: $IsValid"         return $IsValid     }     catch {         Write-Error "Error validating OrgPath format: $_"         return $false     } }

Function 2: Test-OrgPathHierarchy

function Test-OrgPathHierarchy {     <#     .SYNOPSIS         Validates that a child OrgPath has a valid parent in the codebook.     .DESCRIPTION         Checks that the parent path of the given OrgPath exists in the         provided codebook hashtable. Returns $true if valid, $false otherwise.     .PARAMETER ChildPath         The OrgPath to validate.     .PARAMETER Codebook         Hashtable of valid OrgPath codes (keys = OrgPath codes).     .EXAMPLE         Test-OrgPathHierarchy -ChildPath "ORG-FIN-AP" -Codebook $CodebookHash     #>     [CmdletBinding()]     [OutputType([bool])]     param(         [Parameter(Mandatory = $true)]         [ValidateNotNullOrEmpty()]         [string]$ChildPath,          [Parameter(Mandatory = $true)]         [hashtable]$Codebook     )      try {         if ($ChildPath -eq "ORG") {             Write-Verbose "Root OrgPath 'ORG' has no parent; hierarchy valid."             return $true         }          $Segments = $ChildPath -split "-"         if ($Segments.Count -lt 2) {             Write-Verbose "OrgPath '$ChildPath' has insufficient segments."             return $false         }          $ParentSegments = $Segments[0..($Segments.Count - 2)]         $ParentPath = $ParentSegments -join "-"          $ParentExists = $Codebook.ContainsKey($ParentPath)         Write-Verbose "Parent '$ParentPath' of '$ChildPath' exists in codebook: $ParentExists"         return $ParentExists     }     catch {         Write-Error "Error validating OrgPath hierarchy: $_"         return $false     } }

Function 3: Get-OrgTreeValidationReport

function Get-OrgTreeValidationReport {     <#     .SYNOPSIS         Runs all OrgTree validations against a tenant and produces a report.     .DESCRIPTION         Connects to the specified tenant, retrieves all users, validates         OrgPath format and hierarchy, and returns a summary report object.     .PARAMETER TenantId         The target tenant identifier.     .PARAMETER CodebookPath         Path to the JSON codebook file.     .EXAMPLE         Get-OrgTreeValidationReport -TenantId $TenantId -CodebookPath "./codebook.json"     #>     [CmdletBinding()]     [OutputType([PSCustomObject])]     param(         [Parameter(Mandatory = $true)]         [ValidateNotNullOrEmpty()]         [string]$TenantId,          [Parameter(Mandatory = $true)]         [ValidateScript({ Test-Path $_ })]         [string]$CodebookPath     )      try {         Write-Verbose "Loading codebook from $CodebookPath"         $CodebookJson = Get-Content -Path $CodebookPath -Raw | ConvertFrom-Json         $Codebook = @{}         foreach ($Entry in $CodebookJson.entries) {             $Codebook[$Entry.code] = $Entry         }          Write-Verbose "Connecting to tenant $TenantId"         Connect-MgGraph -TenantId $TenantId -Scopes "User.Read.All" -NoWelcome          $AllUsers = Get-MgUser -All -Property "Id,DisplayName,OnPremisesExtensionAttributes"         $TotalUsers = $AllUsers.Count         $ValidCount = 0         $InvalidCount = 0         $OrphanedCount = 0         $DriftDetected = $false          foreach ($User in $AllUsers) {             $OrgPath = $User.OnPremisesExtensionAttributes.ExtensionAttribute1             if ([string]::IsNullOrEmpty($OrgPath)) {                 $OrphanedCount++                 $DriftDetected = $true                 continue             }             $FormatValid = Test-OrgPathFormat -OrgPath $OrgPath             $HierarchyValid = Test-OrgPathHierarchy -ChildPath $OrgPath -Codebook $Codebook             if ($FormatValid -and $HierarchyValid -and $Codebook.ContainsKey($OrgPath)) {                 $ValidCount++             }             else {                 $InvalidCount++                 $DriftDetected = $true             }         }          $Report = [PSCustomObject]@{             TotalUsers    = $TotalUsers             ValidOrgPaths = $ValidCount             InvalidOrgPaths = $InvalidCount             OrphanedUsers = $OrphanedCount             DriftDetected = $DriftDetected         }          Write-Verbose "Validation complete. Valid: $ValidCount, Invalid: $InvalidCount, Orphaned: $OrphanedCount"         return $Report     }     catch {         Write-Error "Error generating validation report: $_"         return $null     } }

Function 4: Test-DynamicGroupAlignment

function Test-DynamicGroupAlignment {     <#     .SYNOPSIS         Validates that dynamic groups in the tenant match the canonical library.     .PARAMETER TenantId         The target tenant identifier.     .PARAMETER GroupLibraryPath         Path to the JSON group library file.     #>     [CmdletBinding()]     [OutputType([PSCustomObject])]     param(         [Parameter(Mandatory = $true)]         [ValidateNotNullOrEmpty()]         [string]$TenantId,          [Parameter(Mandatory = $true)]         [ValidateScript({ Test-Path $_ })]         [string]$GroupLibraryPath     )      try {         $Library = Get-Content -Path $GroupLibraryPath -Raw | ConvertFrom-Json         Connect-MgGraph -TenantId $TenantId -Scopes "Group.Read.All" -NoWelcome          $AlignedGroups = 0         $MisalignedGroups = 0         $MissingGroups = 0         $Details = @()          foreach ($Definition in $Library) {             $TenantGroup = Get-MgGroup -Filter "displayName eq '$($Definition.groupName)'" -ErrorAction SilentlyContinue             if (-not $TenantGroup) {                 $MissingGroups++                 $Details += [PSCustomObject]@{ GroupName = $Definition.groupName; Status = "Missing" }                 continue             }             if ($TenantGroup.MembershipRule -eq $Definition.membershipRule) {                 $AlignedGroups++                 $Details += [PSCustomObject]@{ GroupName = $Definition.groupName; Status = "Aligned" }             }             else {                 $MisalignedGroups++                 $Details += [PSCustomObject]@{ GroupName = $Definition.groupName; Status = "Misaligned" }             }         }          return [PSCustomObject]@{             AlignedGroups   = $AlignedGroups             MisalignedGroups = $MisalignedGroups             MissingGroups   = $MissingGroups             Details         = $Details         }     }     catch {         Write-Error "Error testing dynamic group alignment: $_"         return $null     } }

Function 5: Export-OrgTreeSnapshot

function Export-OrgTreeSnapshot {     <#     .SYNOPSIS         Exports the current OrgTree state as a JSON snapshot.     .PARAMETER TenantId         The target tenant identifier.     .PARAMETER OutputPath         File path for the JSON output.     #>     [CmdletBinding()]     param(         [Parameter(Mandatory = $true)]         [string]$TenantId,          [Parameter(Mandatory = $true)]         [string]$OutputPath     )      try {         Connect-MgGraph -TenantId $TenantId -Scopes "User.Read.All","Group.Read.All" -NoWelcome          $Users = Get-MgUser -All -Property "Id,DisplayName,UserPrincipalName,Department,OnPremisesExtensionAttributes"         $Groups = Get-MgGroup -All -Property "Id,DisplayName,MembershipRule,GroupTypes" |             Where-Object { $_.DisplayName -like "OrgTree-*" }          $Snapshot = [PSCustomObject]@{             snapshotDate = (Get-Date -Format "o")             tenantId     = $TenantId             userCount    = $Users.Count             groupCount   = $Groups.Count             users        = $Users | ForEach-Object {                 [PSCustomObject]@{                     id       = $_.Id                     upn      = $_.UserPrincipalName                     orgPath  = $_.OnPremisesExtensionAttributes.ExtensionAttribute1                     department = $_.Department                 }             }             groups       = $Groups | ForEach-Object {                 [PSCustomObject]@{                     id             = $_.Id                     displayName    = $_.DisplayName                     membershipRule = $_.MembershipRule                 }             }         }          $Snapshot | ConvertTo-Json -Depth 5 | Set-Content -Path $OutputPath -Encoding UTF8         Write-Verbose "Snapshot exported to $OutputPath"     }     catch {         Write-Error "Error exporting OrgTree snapshot: $_"     } }

Function 6: Compare-OrgTreeSnapshots

function Compare-OrgTreeSnapshots {     <#     .SYNOPSIS         Compares two OrgTree snapshots and identifies drift entries.     .PARAMETER BaselinePath         Path to the baseline snapshot JSON.     .PARAMETER CurrentPath         Path to the current snapshot JSON.     #>     [CmdletBinding()]     [OutputType([PSCustomObject[]])]     param(         [Parameter(Mandatory = $true)]         [ValidateScript({ Test-Path $_ })]         [string]$BaselinePath,          [Parameter(Mandatory = $true)]         [ValidateScript({ Test-Path $_ })]         [string]$CurrentPath     )      try {         $Baseline = Get-Content -Path $BaselinePath -Raw | ConvertFrom-Json         $Current = Get-Content -Path $CurrentPath -Raw | ConvertFrom-Json         $DriftEntries = @()          $BaselineUserMap = @{}         foreach ($User in $Baseline.users) { $BaselineUserMap[$User.id] = $User }          foreach ($CurrentUser in $Current.users) {             if (-not $BaselineUserMap.ContainsKey($CurrentUser.id)) {                 $DriftEntries += [PSCustomObject]@{                     ObjectId   = $CurrentUser.id                     ObjectType = "User"                     DriftType  = "NewObject"                     Field      = "N/A"                     BaselineValue = $null                     CurrentValue  = $CurrentUser.orgPath                 }                 continue             }             $BaselineUser = $BaselineUserMap[$CurrentUser.id]             if ($BaselineUser.orgPath -ne $CurrentUser.orgPath) {                 $DriftEntries += [PSCustomObject]@{                     ObjectId      = $CurrentUser.id                     ObjectType    = "User"                     DriftType     = "ValueDrift"                     Field         = "orgPath"                     BaselineValue = $BaselineUser.orgPath                     CurrentValue  = $CurrentUser.orgPath                 }             }         }          Write-Verbose "Drift entries found: $($DriftEntries.Count)"         return $DriftEntries     }     catch {         Write-Error "Error comparing snapshots: $_"         return @()     } }

Boundary Rules

All functions use Microsoft Graph PowerShell SDK, which operates within M365 GCC-Moderate.

No function calls Azure Resource Manager, Azure CLI, or any non-M365 API.

Drift Considerations

The validation module itself is a governance artifact; changes to function logic require Workflow 8 (Governance Artifact Update).

Function outputs are the primary input to drift classification (Appendix M).

Governance Alignment

This module implements Principle 4 (Drift Resistance) by providing the tooling to detect deviations. It implements Principle 6 (Two-Brain Execution): these functions are executed by Execution Substrate, with results validated by Copilot.
