<#
.SYNOPSIS
    UIAO Spec 2 — D1.6: Worker Type Taxonomy
.DESCRIPTION
    Generates the canonical Worker Type Classification Taxonomy that drives
    provisioning rules, license assignment, access scope, and retention
    policies across the Joiner-Mover-Leaver lifecycle.

    This deliverable produces:
    1. Canonical Worker Type Definitions — standardized classification of
       every worker category (Employee, Contractor, Intern, Vendor, etc.)
       with provisioning behavior, license tier, and retention rules
    2. Current-State Audit — discovers existing employeeType values in AD,
       normalizes variants, and maps them to canonical types
    3. Dynamic Group Rules — Entra ID dynamic membership rule expressions
       for each worker type (for license assignment and policy targeting)
    4. Lifecycle Rules per Type — Joiner pre-provisioning lead time,
       Mover conversion rules, Leaver retention/deletion timeline
    5. License Mapping — which M365 license SKU maps to each worker type
    6. Access Scope — Conditional Access policy inclusions/exclusions,
       app access, data classification clearance per type

    Can optionally consume D1.1 HR Attribute Discovery JSON to pre-populate
    the current-state audit with real employeeType distribution data.

    Outputs: JSON rules spec + CSV taxonomy + Markdown reference doc

    Ref: UIAO_136 Spec 2, Phase 1, Deliverable D1.6
         Feeds: D2.1 (Provisioning Architecture), D3.4 (Attribute Mapping)
         Related: ADR-003 (API-driven provisioning), ADR-048 (OrgPath)
.PARAMETER OutputPath
    Directory for output files. Defaults to .\output
.PARAMETER D1InputFile
    Optional path to D1.1 HR Attribute Discovery JSON for current-state
    employeeType distribution analysis.
.PARAMETER DomainController
    Optional DC for live AD query of employeeType values.
.PARAMETER SkipADQuery
    Skip live AD query (use D1.1 data only or generate spec-only output).
.EXAMPLE
    .\Spec2-D1.6-New-WorkerTypeTaxonomy.ps1
    .\Spec2-D1.6-New-WorkerTypeTaxonomy.ps1 -D1InputFile .\output\D1.1_HRAttributeDiscovery.json
.NOTES
    No AD connectivity required for specification output.
    AD connectivity optional for current-state audit.
#>

[CmdletBinding()]
param(
    [string]$OutputPath = ".\output",
    [string]$D1InputFile,
    [string]$DomainController,
    [switch]$SkipADQuery
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $OutputPath)) {
    New-Item -Path $OutputPath -ItemType Directory -Force | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$outPrefix = "UIAO_Spec2_D1.6_WorkerTypeTaxonomy_${timestamp}"

Write-Host "`n================================================================" -ForegroundColor Cyan
Write-Host "  UIAO Spec 2 — D1.6: Worker Type Taxonomy"                     -ForegroundColor Cyan
Write-Host "  Timestamp: $timestamp"                                         -ForegroundColor Cyan
Write-Host "================================================================`n" -ForegroundColor Cyan

# ══════════════════════════════════════════════════════════════
# Section 1: Canonical Worker Type Definitions
# ══════════════════════════════════════════════════════════════
Write-Host "  [1/4] Defining canonical worker type taxonomy..." -ForegroundColor Yellow

$taxonomy = @(
    [ordered]@{
        CanonicalType       = "Employee"
        Code                = "EMP"
        Description         = "Full-time or part-time permanent employee on agency/company payroll"
        HRSourceValues      = @("Employee", "FTE", "Full-Time", "Part-Time", "Regular", "Permanent", "Staff")
        EmployeeTypeValue   = "Employee"
        ProvisioningRules   = [ordered]@{
            JoinerLeadDays       = 7
            JoinerActions        = @("Create Entra ID account (disabled)", "Assign OrgPath", "Add to license group", "Add to department dynamic group", "Generate UPN per D1.5", "Pre-stage mailbox")
            JoinerEnableOn       = "hireDate (employeeHireDate)"
            MoverTriggers        = @("Department change", "Manager change", "Location change", "Title change")
            MoverActions         = @("Recalculate OrgPath", "Dynamic groups auto-cascade", "Update AU membership", "Notify old and new manager")
            LeaverDisableOn      = "terminationDate (employeeLeaveDateTime)"
            LeaverActions        = @("Disable account", "Revoke all sessions", "Remove from groups (except retention)", "Convert mailbox to shared", "Block sign-in", "Trigger access review for delegated access")
            LeaverDeleteAfterDays = 90
            LeaverRetentionPolicy = "Mailbox retained 90 days as shared, then archived. OneDrive retained per org policy (default 30 days)."
        }
        LicenseMapping      = [ordered]@{
            SKU              = "Microsoft 365 E3 or E5"
            AssignmentMethod = "Group-based licensing via dynamic group"
            GroupRule         = '(user.employeeType -eq "Employee")'
        }
        AccessScope         = [ordered]@{
            ConditionalAccess = "Full CA policy set (MFA, compliant device, location-based)"
            AppAccess         = "All productivity apps, LOB apps per role"
            DataClassification = "Up to CUI (Controlled Unclassified Information)"
            GuestAccess       = "Can invite B2B guests (with approval workflow)"
        }
    },
    [ordered]@{
        CanonicalType       = "Contractor"
        Code                = "CTR"
        Description         = "External worker engaged via contract, not on agency/company payroll"
        HRSourceValues      = @("Contractor", "CW", "Contingent Worker", "Contract", "External", "Vendor Employee", "1099")
        EmployeeTypeValue   = "Contractor"
        ProvisioningRules   = [ordered]@{
            JoinerLeadDays       = 3
            JoinerActions        = @("Create Entra ID account (disabled)", "Assign OrgPath", "Add to contractor license group", "Set contract end date as accountExpirationDate", "Generate UPN with contractor domain suffix if applicable")
            JoinerEnableOn       = "contractStartDate or hireDate"
            MoverTriggers        = @("Contract extension", "Department reassignment", "Manager change")
            MoverActions         = @("Extend accountExpirationDate", "Recalculate OrgPath", "Update access review schedule")
            LeaverDisableOn      = "contractEndDate or terminationDate"
            LeaverActions        = @("Disable account immediately", "Revoke all sessions", "Remove all group memberships", "Delete mailbox (no shared conversion)", "Block sign-in")
            LeaverDeleteAfterDays = 30
            LeaverRetentionPolicy = "No mailbox retention. OneDrive content transferred to manager before deletion."
        }
        LicenseMapping      = [ordered]@{
            SKU              = "Microsoft 365 F3 or E3 (per contract terms)"
            AssignmentMethod = "Group-based licensing via dynamic group"
            GroupRule         = '(user.employeeType -eq "Contractor")'
        }
        AccessScope         = [ordered]@{
            ConditionalAccess = "Elevated CA (MFA always, compliant device required, no trusted location bypass)"
            AppAccess         = "Limited to approved apps per contract scope"
            DataClassification = "Up to Controlled (no CUI without explicit approval)"
            GuestAccess       = "Cannot invite B2B guests"
        }
    },
    [ordered]@{
        CanonicalType       = "Intern"
        Code                = "INT"
        Description         = "Temporary worker in training/educational capacity, typically time-bounded"
        HRSourceValues      = @("Intern", "Internship", "Student", "Fellow", "Co-op", "Trainee")
        EmployeeTypeValue   = "Intern"
        ProvisioningRules   = [ordered]@{
            JoinerLeadDays       = 3
            JoinerActions        = @("Create Entra ID account (disabled)", "Assign OrgPath", "Add to intern license group", "Set program end date as accountExpirationDate")
            JoinerEnableOn       = "programStartDate or hireDate"
            MoverTriggers        = @("Conversion to employee", "Department rotation")
            MoverActions         = @("If conversion: change employeeType to Employee, upgrade license group", "If rotation: update OrgPath")
            LeaverDisableOn      = "programEndDate or terminationDate"
            LeaverActions        = @("Disable account", "Revoke sessions", "Remove groups", "Delete mailbox after 14 days")
            LeaverDeleteAfterDays = 14
            LeaverRetentionPolicy = "Minimal retention. OneDrive content transferred to supervisor."
        }
        LicenseMapping      = [ordered]@{
            SKU              = "Microsoft 365 F1 or F3"
            AssignmentMethod = "Group-based licensing via dynamic group"
            GroupRule         = '(user.employeeType -eq "Intern")'
        }
        AccessScope         = [ordered]@{
            ConditionalAccess = "Elevated CA (MFA always, managed device required)"
            AppAccess         = "Teams, Outlook, SharePoint (read-only on sensitive sites)"
            DataClassification = "Public and Internal only"
            GuestAccess       = "Cannot invite B2B guests"
        }
    },
    [ordered]@{
        CanonicalType       = "Vendor"
        Code                = "VND"
        Description         = "External partner or vendor with system access needs, not individually provisioned by HR"
        HRSourceValues      = @("Vendor", "Partner", "Supplier", "Third-Party", "MSP")
        EmployeeTypeValue   = "Vendor"
        ProvisioningRules   = [ordered]@{
            JoinerLeadDays       = 1
            JoinerActions        = @("Prefer B2B Guest invitation over internal account", "If internal account required: create with vendor OrgPath prefix", "Set access review quarterly", "Set account expiration to contract end")
            JoinerEnableOn       = "Sponsor approval"
            MoverTriggers        = @("Contract scope change", "Sponsor change")
            MoverActions         = @("Update sponsor (manager link)", "Adjust app access per new scope")
            LeaverDisableOn      = "contractEndDate or sponsor revocation"
            LeaverActions        = @("Disable immediately", "Revoke all sessions", "Remove all access", "Delete account after 7 days")
            LeaverDeleteAfterDays = 7
            LeaverRetentionPolicy = "No retention. All content owned by sponsoring org unit."
        }
        LicenseMapping      = [ordered]@{
            SKU              = "Entra ID P1 (B2B guest) or Microsoft 365 F1 (if internal account)"
            AssignmentMethod = "Manual or sponsor-approved group"
            GroupRule         = '(user.employeeType -eq "Vendor")'
        }
        AccessScope         = [ordered]@{
            ConditionalAccess = "Strictest CA (MFA always, compliant device, limited session lifetime)"
            AppAccess         = "Only explicitly approved applications"
            DataClassification = "Public only (Internal with explicit approval)"
            GuestAccess       = "Cannot invite B2B guests"
        }
    },
    [ordered]@{
        CanonicalType       = "Volunteer"
        Code                = "VOL"
        Description         = "Unpaid volunteer with limited system access"
        HRSourceValues      = @("Volunteer", "Vol", "Community Service")
        EmployeeTypeValue   = "Volunteer"
        ProvisioningRules   = [ordered]@{
            JoinerLeadDays       = 1
            JoinerActions        = @("Create Entra ID account with minimal access", "Add to volunteer group", "Set program end date")
            JoinerEnableOn       = "programStartDate"
            MoverTriggers        = @("Program change")
            MoverActions         = @("Update OrgPath program segment")
            LeaverDisableOn      = "programEndDate"
            LeaverActions        = @("Disable and delete after 7 days")
            LeaverDeleteAfterDays = 7
            LeaverRetentionPolicy = "No retention."
        }
        LicenseMapping      = [ordered]@{
            SKU              = "Microsoft 365 F1 or Entra ID Free"
            AssignmentMethod = "Group-based licensing"
            GroupRule         = '(user.employeeType -eq "Volunteer")'
        }
        AccessScope         = [ordered]@{
            ConditionalAccess = "MFA required, managed device preferred"
            AppAccess         = "Teams, Outlook (limited)"
            DataClassification = "Public only"
            GuestAccess       = "Cannot invite B2B guests"
        }
    },
    [ordered]@{
        CanonicalType       = "ServiceAccount"
        Code                = "SVC"
        Description         = "Non-human identity for system-to-system integration (should migrate to Workload Identity per ADR-004)"
        HRSourceValues      = @("Service", "System", "Application", "Bot", "API", "Integration")
        EmployeeTypeValue   = "ServiceAccount"
        ProvisioningRules   = [ordered]@{
            JoinerLeadDays       = 0
            JoinerActions        = @("NOT provisioned via HR flow", "Created via IT request with owner assignment", "Must have documented business justification", "Must have expiration date")
            JoinerEnableOn       = "IT approval"
            MoverTriggers        = @("Owner change", "Application decommission")
            MoverActions         = @("Update owner (managedBy)", "Re-certify business justification")
            LeaverDisableOn      = "Application decommission or owner departure"
            LeaverActions        = @("Disable", "Revoke credentials", "Remove SPNs", "Delete after validation period")
            LeaverDeleteAfterDays = 30
            LeaverRetentionPolicy = "No mailbox. Audit logs retained per compliance policy."
        }
        LicenseMapping      = [ordered]@{
            SKU              = "No user license (Workload Identity Premium if needed)"
            AssignmentMethod = "Manual"
            GroupRule         = '(user.employeeType -eq "ServiceAccount")'
        }
        AccessScope         = [ordered]@{
            ConditionalAccess = "Workload Identity CA policies (IP restriction, token lifetime)"
            AppAccess         = "Only the specific application(s) documented in justification"
            DataClassification = "Per application classification"
            GuestAccess       = "N/A"
        }
    }
)

Write-Host "    Defined $($taxonomy.Count) canonical worker types" -ForegroundColor Green

# ══════════════════════════════════════════════════════════════
# Section 2: Current-State Audit
# ══════════════════════════════════════════════════════════════
Write-Host "  [2/4] Auditing current employeeType distribution..." -ForegroundColor Yellow

$currentStateAudit = $null
$adEmployeeTypes = @()

# Try D1.1 data first
if ($D1InputFile -and (Test-Path $D1InputFile)) {
    $d1Data = Get-Content $D1InputFile -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($d1Data.WorkerTypeDistribution) {
        $adEmployeeTypes = $d1Data.WorkerTypeDistribution | ForEach-Object {
            [ordered]@{ Value = $_.WorkerType; Count = $_.Count }
        }
        Write-Host "    Loaded employeeType distribution from D1.1" -ForegroundColor Green
    }
}

# Live AD query if no D1.1 data and not skipped
if ($adEmployeeTypes.Count -eq 0 -and -not $SkipADQuery) {
    try {
        Import-Module ActiveDirectory -ErrorAction Stop
        $adParams = @{}
        if ($DomainController) { $adParams['Server'] = $DomainController }

        $users = Get-ADUser -Filter "objectClass -eq 'user' -and objectCategory -eq 'person'" `
            -Properties employeeType @adParams

        $adEmployeeTypes = $users |
            ForEach-Object { if ($_.employeeType) { $_.employeeType } else { "(not set)" } } |
            Group-Object |
            Sort-Object Count -Descending |
            ForEach-Object { [ordered]@{ Value = $_.Name; Count = $_.Count } }

        Write-Host "    Queried $($users.Count) AD users" -ForegroundColor Green
    } catch {
        Write-Host "    AD query failed: $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

# Build normalization mapping
$normalizationMap = [System.Collections.Generic.List[object]]::new()

foreach ($etEntry in $adEmployeeTypes) {
    $value = $etEntry.Value
    $matched = $false

    foreach ($wt in $taxonomy) {
        foreach ($sourceVal in $wt.HRSourceValues) {
            if ($value -eq $sourceVal -or $value -like "*$sourceVal*") {
                $normalizationMap.Add([ordered]@{
                    CurrentValue    = $value
                    Count           = $etEntry.Count
                    CanonicalType   = $wt.CanonicalType
                    Code            = $wt.Code
                    Confidence      = if ($value -eq $sourceVal) { "Exact" } else { "Partial" }
                    Action          = "Map '$value' -> '$($wt.EmployeeTypeValue)'"
                })
                $matched = $true
                break
            }
        }
        if ($matched) { break }
    }

    if (-not $matched) {
        $normalizationMap.Add([ordered]@{
            CurrentValue    = $value
            Count           = $etEntry.Count
            CanonicalType   = $null
            Code            = $null
            Confidence      = "None"
            Action          = "MANUAL REVIEW — no matching canonical type"
        })
    }
}

$unmapped = @($normalizationMap | Where-Object { $_.Confidence -eq 'None' })
if ($unmapped.Count -gt 0) {
    Write-Host "    Unmapped employeeType values: $($unmapped.Count)" -ForegroundColor Yellow
    foreach ($u in $unmapped) {
        Write-Host "      ! '$($u.CurrentValue)' ($($u.Count) users)" -ForegroundColor Yellow
    }
} else {
    Write-Host "    All employeeType values mapped to canonical types" -ForegroundColor Green
}

$currentStateAudit = [ordered]@{
    DistinctValues   = $adEmployeeTypes.Count
    TotalUsers       = ($adEmployeeTypes | Measure-Object -Property Count -Sum).Sum
    Distribution     = @($adEmployeeTypes)
    NormalizationMap = @($normalizationMap)
    UnmappedCount    = $unmapped.Count
    NotSetCount      = ($adEmployeeTypes | Where-Object { $_.Value -eq '(not set)' } | Select-Object -ExpandProperty Count -First 1)
}

# ══════════════════════════════════════════════════════════════
# Section 3: Dynamic Group Rules
# ══════════════════════════════════════════════════════════════
Write-Host "  [3/4] Generating dynamic group rules..." -ForegroundColor Yellow

$dynamicGroups = $taxonomy | ForEach-Object {
    [ordered]@{
        GroupName       = "UIAO-License-$($_.CanonicalType)"
        GroupType       = "DynamicMembership"
        MembershipRule  = "(user.employeeType -eq `"$($_.EmployeeTypeValue)`")"
        Purpose         = "License assignment and policy targeting for $($_.CanonicalType) workers"
        LicenseSKU      = $_.LicenseMapping.SKU
        WorkerType      = $_.CanonicalType
    }
}

# OrgPath-combined rules (worker type + location)
$combinedGroups = @(
    [ordered]@{
        GroupName       = "UIAO-AllEmployees-US"
        MembershipRule  = '(user.employeeType -eq "Employee") and (user.extensionAttribute1 -startsWith "CORP/US")'
        Purpose         = "All US employees — Conditional Access and compliance targeting"
    },
    [ordered]@{
        GroupName       = "UIAO-AllContractors"
        MembershipRule  = '(user.employeeType -eq "Contractor")'
        Purpose         = "All contractors — elevated CA policy, restricted app access"
    },
    [ordered]@{
        GroupName       = "UIAO-ExternalWorkers"
        MembershipRule  = '(user.employeeType -eq "Contractor") or (user.employeeType -eq "Vendor") or (user.employeeType -eq "Intern")'
        Purpose         = "All non-employee workers — data loss prevention and session controls"
    }
)

Write-Host "    Generated $($dynamicGroups.Count) license groups + $($combinedGroups.Count) combined groups" -ForegroundColor Green

# ══════════════════════════════════════════════════════════════
# Section 4: Markdown Reference Document
# ══════════════════════════════════════════════════════════════
Write-Host "  [4/4] Generating outputs..." -ForegroundColor Yellow

$mdContent = @"
# UIAO Worker Type Classification Taxonomy

> **Ref:** UIAO_136 Spec 2, D1.6 | ADR-003 (API-driven provisioning) | ADR-048 (OrgPath)
> **Generated:** $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")

---

## Canonical Worker Types

| Code | Type | employeeType Value | License SKU | Leaver Delete (days) |
|------|------|-------------------|-------------|---------------------|
$( ($taxonomy | ForEach-Object { "| $($_.Code) | **$($_.CanonicalType)** | ``$($_.EmployeeTypeValue)`` | $($_.LicenseMapping.SKU) | $($_.ProvisioningRules.LeaverDeleteAfterDays) |" }) -join "`n" )

---

## Joiner-Mover-Leaver Lifecycle Summary

$( ($taxonomy | ForEach-Object {
    @"

### $($_.CanonicalType) ($($_.Code))

$($_.Description)

**Joiner:**
- Lead time: $($_.ProvisioningRules.JoinerLeadDays) days before hire date
- Enable trigger: $($_.ProvisioningRules.JoinerEnableOn)
- Actions: $( ($_.ProvisioningRules.JoinerActions | ForEach-Object { "``$_``" }) -join ', ' )

**Mover triggers:** $( ($_.ProvisioningRules.MoverTriggers -join ', ') )

**Leaver:**
- Disable trigger: $($_.ProvisioningRules.LeaverDisableOn)
- Delete after: $($_.ProvisioningRules.LeaverDeleteAfterDays) days
- Retention: $($_.ProvisioningRules.LeaverRetentionPolicy)

"@
}) -join "" )

---

## Dynamic Group Rules

| Group Name | Membership Rule | Purpose |
|-----------|----------------|---------|
$( ($dynamicGroups | ForEach-Object { "| ``$($_.GroupName)`` | ``$($_.MembershipRule)`` | $($_.Purpose) |" }) -join "`n" )

### Combined Groups

| Group Name | Membership Rule | Purpose |
|-----------|----------------|---------|
$( ($combinedGroups | ForEach-Object { "| ``$($_.GroupName)`` | ``$($_.MembershipRule)`` | $($_.Purpose) |" }) -join "`n" )

---

## Access Scope per Worker Type

| Type | CA Policy | App Access | Data Classification | Guest Rights |
|------|----------|-----------|-------------------|-------------|
$( ($taxonomy | ForEach-Object { "| $($_.CanonicalType) | $($_.AccessScope.ConditionalAccess) | $($_.AccessScope.AppAccess) | $($_.AccessScope.DataClassification) | $($_.AccessScope.GuestAccess) |" }) -join "`n" )

---

## HR Source Value Mapping

| Current Value | Count | Canonical Type | Confidence | Action |
|--------------|-------|---------------|-----------|--------|
$( if ($normalizationMap.Count -gt 0) { ($normalizationMap | ForEach-Object { "| ``$($_.CurrentValue)`` | $($_.Count) | $($_.CanonicalType ?? 'UNMAPPED') | $($_.Confidence) | $($_.Action) |" }) -join "`n" } else { "| *(No AD data available)* | | | | |" } )
"@

# ── Output Files ──

# JSON
$jsonFile = Join-Path $OutputPath "${outPrefix}.json"
[ordered]@{
    ExportMetadata = [ordered]@{
        Timestamp   = (Get-Date).ToString("o")
        Script      = "UIAO Spec 2 D1.6 — Worker Type Taxonomy"
        Reference   = "UIAO_136, ADR-003, ADR-048"
        D1Source    = if ($D1InputFile) { $D1InputFile } else { "Not provided" }
    }
    Taxonomy           = @($taxonomy)
    CurrentStateAudit  = $currentStateAudit
    DynamicGroups      = @($dynamicGroups)
    CombinedGroups     = @($combinedGroups)
} | ConvertTo-Json -Depth 10 | Out-File -FilePath $jsonFile -Encoding utf8NoBOM
Write-Host "  JSON: $jsonFile" -ForegroundColor Green

# CSV
$csvFile = Join-Path $OutputPath "${outPrefix}.csv"
$taxonomy | ForEach-Object {
    [PSCustomObject]@{
        Code              = $_.Code
        CanonicalType     = $_.CanonicalType
        EmployeeTypeValue = $_.EmployeeTypeValue
        Description       = $_.Description
        JoinerLeadDays    = $_.ProvisioningRules.JoinerLeadDays
        LeaverDeleteDays  = $_.ProvisioningRules.LeaverDeleteAfterDays
        LicenseSKU        = $_.LicenseMapping.SKU
        GroupRule          = $_.LicenseMapping.GroupRule
        HRSourceValues    = ($_.HRSourceValues -join '; ')
        CAPolicy          = $_.AccessScope.ConditionalAccess
        DataClassification = $_.AccessScope.DataClassification
    }
} | Export-Csv -Path $csvFile -NoTypeInformation -Encoding utf8NoBOM
Write-Host "  CSV: $csvFile" -ForegroundColor Green

# Markdown
$mdFile = Join-Path $OutputPath "${outPrefix}.md"
$mdContent | Out-File -FilePath $mdFile -Encoding utf8NoBOM
Write-Host "  Markdown: $mdFile" -ForegroundColor Green

# Console
Write-Host "`n-- Worker Type Taxonomy --" -ForegroundColor Cyan
foreach ($wt in $taxonomy) {
    Write-Host "  [$($wt.Code)] $($wt.CanonicalType.PadRight(15)) License: $($wt.LicenseMapping.SKU)"
}

if ($currentStateAudit) {
    Write-Host "`n-- Current State Audit --" -ForegroundColor Cyan
    Write-Host "  Distinct employeeType values: $($currentStateAudit.DistinctValues)"
    Write-Host "  Unmapped values:              $($currentStateAudit.UnmappedCount)" -ForegroundColor $(if ($currentStateAudit.UnmappedCount -gt 0) { 'Yellow' } else { 'Green' })
    Write-Host "  Not set (empty):              $($currentStateAudit.NotSetCount)" -ForegroundColor $(if ($currentStateAudit.NotSetCount -gt 0) { 'Red' } else { 'Green' })
}

Write-Host "`n-- Complete --`n" -ForegroundColor Cyan
