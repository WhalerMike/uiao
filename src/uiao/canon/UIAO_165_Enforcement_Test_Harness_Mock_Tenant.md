---
document_id: UIAO_165
title: "Appendix O — Enforcement Test Harness (Mock Tenant)"
version: "1.0"
status: Draft
owner: Michael Stratton
created_at: "2026-04-18"
updated_at: "2026-04-18"
provenance_flatten:
  prior_id: "MOD_O"
  flattened_at: "2026-05-10"
  flattened_by: "ADR-060"
---

# Appendix O — Enforcement Test Harness (Mock Tenant)

Purpose

This appendix defines a mock tenant specification for testing governance enforcement without requiring a live M365 environment. The harness simulates tenant state in-memory, enabling rapid, repeatable testing of all governance rules.

Scope

Covers mock data for 50 users, 15 dynamic groups, 8 administrative units, and 10 role assignments. Includes 10 test scenarios and the harness architecture.

Canonical Structure

The mock tenant is an in-memory data structure (PowerShell hashtable) that simulates Microsoft Graph API responses. The harness intercepts validation function calls and returns mock data instead of calling live APIs.

Technical Scaffolding

Mock Tenant Initialization Script

# Initialize Mock Tenant Data Structure $MockTenant = @{     TenantId = "mock-tenant-00000000-0000-0000-0000-000000000000"     Users = @()     Groups = @()     AdministrativeUnits = @()     RoleAssignments = @() }  # Generate 50 mock users across governed OrgPath facet combinations. Each triple is a codebook-valid (Region, Department, Division); the derived path on slot 15 is recomputed from them by New-OrgPath, never hand-written. Harness bookkeeping stays in the harness - the fifteen slots are a governed, tenant-wide resource, not scratch space. $OrgNodes = @( @{ Region="NCR"; Department="IT"; Division="CyberOps" }, @{ Region="NCR"; Department="IT"; Division="InfraOps" }, @{ Region="NCR"; Department="IT"; Division="AppDev" }, @{ Region="NCR"; Department="Finance"; Division="GRC" }, @{ Region="NCR"; Department="Finance"; Division="Data" }, @{ Region="EASTUS"; Department="HR"; Division="Service" }, @{ Region="EASTUS"; Department="Legal"; Division="GRC" }, @{ Region="EASTUS"; Department="Operations"; Division="Service" }, @{ Region="WESTUS"; Department="IT"; Division="Cloud" }, @{ Region="WESTUS"; Department="Engineering"; Division="AppDev" } )  for ($i = 1; $i -le 50; $i++) {     $Node = $OrgNodes[($i - 1) % $OrgNodes.Count]     $MockTenant.Users += [PSCustomObject]@{         Id = "user-$('{0:D4}' -f $i)"         DisplayName = "MockUser$i"         UserPrincipalName = "mockuser$i@mock.onmicrosoft.com"         Department = $Node.Department         EmployeeId = "EMP$('{0:D6}' -f $i)"         AccountEnabled = $true         OnPremisesExtensionAttributes = @{             ExtensionAttribute1 = $Node.Region             ExtensionAttribute2 = $Node.Department             ExtensionAttribute3 = $Node.Division             ExtensionAttribute6 = if ($i % 7 -eq 0) { "Contractor" } else { "Employee" }             ExtensionAttribute10 = if ($i % 10 -eq 0) { "Privileged" } else { "Standard" }             ExtensionAttribute15 = New-OrgPath -Region $Node.Region -Department $Node.Department -Division $Node.Division         }     } }  # Generate mock groups. Node-exact and cross-cutting scopes are boolean facet composition; only a subtree scope uses the derived path, anchored at Region= and delimiter-terminated. $GroupDefs = @(     @{Name="OrgTree-All-Governed"; Rule='user.extensionAttribute15 -ne $null'},     @{Name="OrgTree-FIN-All"; Rule='user.extensionAttribute2 -eq "Finance"'},     @{Name="OrgTree-HR-All"; Rule='user.extensionAttribute2 -eq "HR"'},     @{Name="OrgTree-IT-All"; Rule='user.extensionAttribute2 -eq "IT"'},     @{Name="OrgTree-OPS-All"; Rule='user.extensionAttribute2 -eq "Operations"'},     @{Name="OrgTree-LEG-All"; Rule='user.extensionAttribute2 -eq "Legal"'},     @{Name="OrgTree-IT-CyberOps"; Rule='(user.extensionAttribute2 -eq "IT") and (user.extensionAttribute3 -eq "CyberOps")'},     @{Name="OrgTree-Branch-NCR-IT"; Rule='user.extensionAttribute15 -startsWith "Region=NCR|Department=IT|"'},     @{Name="OrgTree-Privileged-All"; Rule='user.extensionAttribute10 -eq "Privileged"'}     # Additional groups follow the same three shapes. )  foreach ($Def in $GroupDefs) {     $MockTenant.Groups += [PSCustomObject]@{         Id = "group-$($Def.Name)"         DisplayName = $Def.Name         MembershipRule = $Def.Rule         GroupTypes = @("DynamicMembership")         SecurityEnabled = $true     } }  Write-Verbose "Mock tenant initialized: $($MockTenant.Users.Count) users, $($MockTenant.Groups.Count) groups"

Test Scenarios

Boundary Rules

The mock tenant simulates M365 GCC-Moderate responses only; it does not simulate out-of-scope services.

Mock data contains no real tenant identifiers, UPNs, or PII.

Drift Considerations

The mock tenant is a testing artifact; drift in mock data is intentional (for testing). Drift in the harness code itself requires Workflow 8.

Governance Alignment

The test harness enables continuous validation of governance rules without tenant risk, supporting Principle 4 (Drift Resistance) through automated testing and Principle 7 (Tenant Agnosticism) through tenant-independent test execution.
