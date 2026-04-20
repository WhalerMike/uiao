---
document_id: MOD_F
title: "Appendix F — Migration Runbook (OU to Entra)"
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

# Appendix F — Migration Runbook (OU to Entra)

Purpose

This appendix provides a deterministic, step-by-step runbook for migrating from a legacy OU-based Active Directory structure to the Entra ID OrgTree model. Every phase, step, validation checkpoint, and rollback procedure is fully specified.

Scope

Covers the end-to-end migration lifecycle from initial discovery through final decommission of legacy OU dependencies. All migration activities operate within or target the M365 GCC-Moderate boundary.

Canonical Structure

The migration consists of eight sequential phases. Each phase has prerequisites, numbered steps, validation criteria, a rollback procedure, an estimated duration, and an owner. No phase may begin until its predecessor's validation criteria are satisfied.

Technical Scaffolding

Phase 1: Discovery

Prerequisites: Read access to legacy AD environment; Microsoft Graph PowerShell SDK installed; Entra ID Global Reader role.

Estimated Duration: 3–5 business days. Owner: Identity Engineer.

Steps:

Export all OUs from legacy AD with full distinguished name paths.

Export all user objects with OU membership, department, title, manager, and employeeId.

Export all security groups with membership lists.

Export all Group Policy Objects (GPOs) linked to OUs.

Generate a discovery report with counts: total OUs, total users, total groups, total GPOs.

PowerShell Commands:

# Connect to Microsoft Graph Connect-MgGraph -TenantId $TenantId -Scopes "User.Read.All","Group.Read.All"  # Export existing Entra ID users for baseline $EntraUsers = Get-MgUser -All -Property "Id,DisplayName,UserPrincipalName,Department,JobTitle,EmployeeId" `     -Filter "userType eq 'Member'" $EntraUsers | Export-Csv -Path "$OutputPath\entra-users-baseline.csv" -NoTypeInformation  # Export existing groups for baseline $EntraGroups = Get-MgGroup -All -Property "Id,DisplayName,GroupTypes,MembershipRule" $EntraGroups | Export-Csv -Path "$OutputPath\entra-groups-baseline.csv" -NoTypeInformation  # Count summary Write-Verbose "Total Entra Users: $($EntraUsers.Count)" Write-Verbose "Total Entra Groups: $($EntraGroups.Count)"  # Legacy AD export (run on domain-joined machine) $LegacyOUs = Get-ADOrganizationalUnit -Filter * -Properties CanonicalName $LegacyOUs | Export-Csv -Path "$OutputPath\legacy-ous.csv" -NoTypeInformation

Validation Criteria: Discovery report contains non-zero counts for all object types; all exports are complete CSV files with expected columns.

Rollback Procedure: Discovery is read-only; no rollback required.

Phase 2: OrgPath Mapping

Prerequisites: Phase 1 discovery report completed; OrgPath Codebook (Appendix A) finalized.

Estimated Duration: 5–7 business days. Owner: Governance Steward.

Steps:

For each legacy OU, identify the corresponding OrgPath code from Appendix A.

Create a mapping table: Legacy OU Distinguished Name → OrgPath Code.

Identify unmappable OUs (OUs with no OrgPath equivalent) and flag for governance review.

Validate that every user's OU maps to a valid OrgPath.

Generate a mapping report with coverage statistics.

# Create mapping hashtable $OUtoOrgPath = @{     "OU=Finance,OU=Departments,DC=org,DC=local"       = "ORG-FIN"     "OU=AP,OU=Finance,OU=Departments,DC=org,DC=local" = "ORG-FIN-AP"     "OU=HR,OU=Departments,DC=org,DC=local"             = "ORG-HR"     "OU=IT,OU=Departments,DC=org,DC=local"             = "ORG-IT"     "OU=Security,OU=IT,OU=Departments,DC=org,DC=local" = "ORG-IT-SEC" }  # Validate all users have a mapping $UnmappedUsers = $LegacyUsers | Where-Object {     -not $OUtoOrgPath.ContainsKey($_.DistinguishedName -replace "CN=.*?,","") } Write-Verbose "Unmapped users: $($UnmappedUsers.Count)"  # Validate OrgPath codes against regex $OrgPathRegex = "^ORG(-[A-Z]{2,6}){0,4}$" $InvalidMappings = $OUtoOrgPath.Values | Where-Object { $_ -notmatch $OrgPathRegex } Write-Verbose "Invalid OrgPath mappings: $($InvalidMappings.Count)"  # Export mapping $OUtoOrgPath.GetEnumerator() | Select-Object @{N="LegacyOU";E={$_.Key}}, @{N="OrgPath";E={$_.Value}} |     Export-Csv -Path "$OutputPath\ou-orgpath-mapping.csv" -NoTypeInformation

Validation Criteria: 100% of active users have a valid OrgPath mapping; zero invalid OrgPath codes; unmappable OUs documented with resolution plan.

Rollback Procedure: Mapping is a planning artifact; discard mapping file and restart.

Phase 3: Attribute Provisioning

Prerequisites: Phase 2 mapping complete; Entra ID User Administrator role; Attribute Mapping Table (Appendix C) reviewed.

Estimated Duration: 3–5 business days. Owner: Identity Engineer.

Steps:

For each user, write the OrgPath value to extensionAttribute1.

Write role code to extensionAttribute2 based on role mapping.

Write lifecycle state ACTIVE to extensionAttribute3.

Write migration status IN-PROGRESS to extensionAttribute4.

Validate all attribute writes completed successfully.

# Provision OrgPath for each user foreach ($Mapping in $UserOrgPathMappings) {     try {         $UserParams = @{             UserId = $Mapping.EntraUserId             OnPremisesExtensionAttributes = @{                 extensionAttribute1 = $Mapping.OrgPath                 extensionAttribute3 = "ACTIVE"                 extensionAttribute4 = "IN-PROGRESS"             }         }         Update-MgUser @UserParams         Write-Verbose "Updated user $($Mapping.EntraUserId) with OrgPath $($Mapping.OrgPath)"     }     catch {         Write-Error "Failed to update user $($Mapping.EntraUserId): $_"     } }  # Verify provisioning $ProvisionedUsers = Get-MgUser -All -Property "Id,OnPremisesExtensionAttributes" |     Where-Object { $_.OnPremisesExtensionAttributes.ExtensionAttribute1 -match "^ORG" } Write-Verbose "Provisioned users: $($ProvisionedUsers.Count)"  # Identify failures $UnprovisionedUsers = Get-MgUser -All -Property "Id,OnPremisesExtensionAttributes" |     Where-Object { [string]::IsNullOrEmpty($_.OnPremisesExtensionAttributes.ExtensionAttribute1) } Write-Verbose "Unprovisioned users: $($UnprovisionedUsers.Count)"  # Update migration status for successful provisions foreach ($User in $ProvisionedUsers) {     Update-MgUser -UserId $User.Id -OnPremisesExtensionAttributes @{         extensionAttribute4 = "COMPLETED"     } }

Validation Criteria: All users have non-null extensionAttribute1 matching regex; zero provisioning errors; extensionAttribute4 = COMPLETED for all provisioned users.

Rollback Procedure: Set extensionAttribute1 through extensionAttribute4 to null for all affected users.

Phase 4: Dynamic Group Deployment

Prerequisites: Phase 3 complete; Dynamic Group Library (Appendix B) finalized; Groups Administrator role.

Estimated Duration: 2–3 business days. Owner: Identity Engineer.

Steps:

Create each dynamic group per Appendix B definitions.

Set membership rules exactly as specified in the library.

Wait for dynamic membership processing (up to 24 hours).

Validate group membership counts against expected user populations.

Update migration status.

# Create a dynamic security group $GroupParams = @{     DisplayName     = "OrgTree-FIN-All"     Description     = "All Finance Division members including subdepartments"     MailEnabled     = $false     MailNickname    = "OrgTree-FIN-All"     SecurityEnabled = $true     GroupTypes      = @("DynamicMembership")     MembershipRule  = '(user.extensionAttribute1 -eq "ORG-FIN") or (user.extensionAttribute1 -startsWith "ORG-FIN-")'     MembershipRuleProcessingState = "On" } New-MgGroup -BodyParameter $GroupParams  # Verify group creation $CreatedGroup = Get-MgGroup -Filter "displayName eq 'OrgTree-FIN-All'" Write-Verbose "Group created: $($CreatedGroup.DisplayName), Id: $($CreatedGroup.Id)"  # Check membership after processing delay $Members = Get-MgGroupMember -GroupId $CreatedGroup.Id -All Write-Verbose "OrgTree-FIN-All membership count: $($Members.Count)"  # Validate membership rule matches canonical definition $CanonicalRule = '(user.extensionAttribute1 -eq "ORG-FIN") or (user.extensionAttribute1 -startsWith "ORG-FIN-")' if ($CreatedGroup.MembershipRule -ne $CanonicalRule) {     Write-Error "Membership rule drift detected for OrgTree-FIN-All" }

Validation Criteria: All groups from Appendix B exist in tenant; membership rules match canonical definitions exactly; membership counts are non-zero for populated OrgPaths.

Rollback Procedure: Delete all groups with OrgTree- prefix created during this phase.

Phase 5: AU Deployment

Prerequisites: Phase 4 complete; Delegation Matrix (Appendix D) finalized; Privileged Role Administrator role.

Estimated Duration: 2–3 business days. Owner: Security Steward.

Steps:

Create each Administrative Unit per Appendix D registry.

Configure dynamic membership rules.

Set restricted management flag where specified.

Create scoped role assignments per Appendix D role matrix.

Validate AU membership and role assignment accuracy.

# Create Administrative Unit $AUParams = @{     DisplayName = "AU-FIN"     Description = "Administrative Unit for Finance Division (ORG-FIN)"     MembershipType = "Dynamic"     MembershipRule = '(user.extensionAttribute1 -eq "ORG-FIN") or (user.extensionAttribute1 -startsWith "ORG-FIN-")'     MembershipRuleProcessingState = "On" } $NewAU = New-MgDirectoryAdministrativeUnit -BodyParameter $AUParams Write-Verbose "AU created: $($NewAU.DisplayName), Id: $($NewAU.Id)"  # Assign scoped role $RoleDefinition = Get-MgRoleManagementDirectoryRoleDefinition -Filter "displayName eq 'User Administrator'" $AssigneeGroup = Get-MgGroup -Filter "displayName eq 'OrgTree-FIN-Admins'"  $RoleAssignment = @{     RoleDefinitionId = $RoleDefinition.Id     PrincipalId      = $AssigneeGroup.Id     DirectoryScopeId = "/administrativeUnits/$($NewAU.Id)" } New-MgRoleManagementDirectoryRoleAssignment -BodyParameter $RoleAssignment  # Validate $AUMembers = Get-MgDirectoryAdministrativeUnitMember -AdministrativeUnitId $NewAU.Id -All Write-Verbose "AU-FIN member count: $($AUMembers.Count)"

Validation Criteria: All AUs from Appendix D exist with correct membership rules; all role assignments from matrix are active; restricted management flags are set correctly.

Rollback Procedure: Remove role assignments, then delete AUs in reverse creation order.

Phase 6: Validation

Prerequisites: Phases 3–5 complete; PowerShell Validation Module (Appendix I) available.

Estimated Duration: 2–3 business days. Owner: Governance Steward.

Steps:

Run Test-OrgPathFormat against all users.

Run Test-OrgPathHierarchy against all users.

Run Test-DynamicGroupAlignment against all groups.

Run Get-OrgTreeValidationReport for full status.

Review and remediate any failures before proceeding.

# Import validation module Import-Module "$ModulePath\OrgTreeValidation\OrgTreeValidation.psm1"  # Full validation report $Report = Get-OrgTreeValidationReport -TenantId $TenantId -CodebookPath "$CodebookPath\orgpath-codebook.json" Write-Verbose "Total Users: $($Report.TotalUsers)" Write-Verbose "Valid OrgPaths: $($Report.ValidOrgPaths)" Write-Verbose "Invalid OrgPaths: $($Report.InvalidOrgPaths)" Write-Verbose "Orphaned Users: $($Report.OrphanedUsers)" Write-Verbose "Drift Detected: $($Report.DriftDetected)"  # Export snapshot as baseline Export-OrgTreeSnapshot -TenantId $TenantId -OutputPath "$OutputPath\baseline-snapshot.json"  # Group alignment check $GroupReport = Test-DynamicGroupAlignment -TenantId $TenantId -GroupLibraryPath "$LibraryPath\dynamic-groups.json" Write-Verbose "Aligned Groups: $($GroupReport.AlignedGroups)" Write-Verbose "Misaligned Groups: $($GroupReport.MisalignedGroups)"

Validation Criteria: Zero invalid OrgPaths; zero orphaned users; zero misaligned groups; zero drift detected.

Rollback Procedure: If validation fails, return to the phase responsible for the failure (Phase 3, 4, or 5) and re-execute.

Phase 7: Cutover

Prerequisites: Phase 6 validation passes with zero failures.

Estimated Duration: 1 business day. Owner: Governance Steward.

Steps:

Enable drift detection engine monitoring (Appendix M).

Activate SLA tracking for all governance operations.

Set extensionAttribute4 = VALIDATED for all users.

Notify all division administrators of go-live.

Begin telemetry collection (Appendix X).

# Mark all users as validated $AllUsers = Get-MgUser -All -Property "Id" -Filter "userType eq 'Member'" foreach ($User in $AllUsers) {     try {         Update-MgUser -UserId $User.Id -OnPremisesExtensionAttributes @{             extensionAttribute4 = "VALIDATED"         }     }     catch {         Write-Error "Failed to update migration status for $($User.Id): $_"     } }  # Create post-cutover snapshot Export-OrgTreeSnapshot -TenantId $TenantId -OutputPath "$OutputPath\cutover-snapshot.json"  # Compare against baseline $DriftReport = Compare-OrgTreeSnapshots -BaselinePath "$OutputPath\baseline-snapshot.json" `     -CurrentPath "$OutputPath\cutover-snapshot.json" Write-Verbose "Drift entries since baseline: $($DriftReport.Count)"

Validation Criteria: Drift detection engine is active; telemetry is flowing; all users have extensionAttribute4 = VALIDATED.

Rollback Procedure: Disable drift detection; revert extensionAttribute4 to COMPLETED; return to Phase 6.

Phase 8: Decommission

Prerequisites: Phase 7 cutover stable for 30 calendar days with zero critical drift events.

Estimated Duration: 5–10 business days. Owner: Infrastructure Engineer.

Steps:

Verify no active dependencies on legacy OU structure.

Remove legacy OU-based group policies where replaced by Conditional Access.

Archive legacy OU export data for compliance retention.

Document decommission completion in governance log.

Clear extensionAttribute4 (migration tracking no longer needed).

# Final validation before decommission $FinalReport = Get-OrgTreeValidationReport -TenantId $TenantId -CodebookPath "$CodebookPath\orgpath-codebook.json" if ($FinalReport.InvalidOrgPaths -gt 0 -or $FinalReport.DriftDetected -eq $true) {     Write-Error "Cannot decommission: validation failures exist"     return }  # Clear migration tracking attribute $AllUsers = Get-MgUser -All -Property "Id" -Filter "userType eq 'Member'" foreach ($User in $AllUsers) {     Update-MgUser -UserId $User.Id -OnPremisesExtensionAttributes @{         extensionAttribute4 = $null     } }  # Export final decommission snapshot Export-OrgTreeSnapshot -TenantId $TenantId -OutputPath "$OutputPath\decommission-final-snapshot.json" Write-Verbose "Decommission complete. Legacy OU dependencies removed."

Validation Criteria: Zero legacy OU dependencies; all governance operations running via OrgTree; decommission documented.

Rollback Procedure: At this phase, rollback to legacy OU is a full re-implementation project and is outside the scope of this runbook.

Boundary Rules

All migration commands target Entra ID via Microsoft Graph API within M365 GCC-Moderate.

Legacy AD read operations are the only cross-boundary activity permitted (read-only, discovery phase only).

No migration step may provision resources in Azure services outside M365.

Drift Considerations

During migration (Phases 3–6), drift detection is not yet active; manual validation checkpoints serve as drift prevention.

Post-cutover (Phase 7+), the drift detection engine monitors continuously per Appendix M.

Governance Alignment

This runbook implements Principle 6 (Two-Brain Execution): Copilot reviews and validates each phase's plan; Execution Substrate executes the PowerShell commands. It also implements Principle 3 (Provenance Traceability): every phase produces artifacts (exports, reports, snapshots) that create a complete audit trail.
