---
document_id: MOD_O
title: "Appendix O — Enforcement Test Harness (Mock Tenant)"
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

# Appendix O — Enforcement Test Harness (Mock Tenant)

Purpose

This appendix defines a mock tenant specification for testing governance enforcement without requiring a live M365 environment. The harness simulates tenant state in-memory, enabling rapid, repeatable testing of all governance rules.

Scope

Covers mock data for 50 users, 15 dynamic groups, 8 administrative units, and 10 role assignments. Includes 10 test scenarios and the harness architecture.

Canonical Structure

The mock tenant is an in-memory data structure (PowerShell hashtable) that simulates Microsoft Graph API responses. The harness intercepts validation function calls and returns mock data instead of calling live APIs.

Technical Scaffolding

Mock Tenant Initialization Script

# Initialize Mock Tenant Data Structure $MockTenant = @{     TenantId = "mock-tenant-00000000-0000-0000-0000-000000000000"     Users = @()     Groups = @()     AdministrativeUnits = @()     RoleAssignments = @() }  # Generate 50 mock users across OrgPaths $OrgPaths = @("ORG","ORG-FIN","ORG-FIN-AP","ORG-FIN-AR","ORG-FIN-BUD",               "ORG-HR","ORG-HR-REC","ORG-HR-BEN","ORG-IT","ORG-IT-SEC",               "ORG-IT-INF","ORG-IT-DEV","ORG-IT-SEC-SOC","ORG-OPS",               "ORG-OPS-LOG","ORG-LEG","ORG-LEG-COM")  for ($i = 1; $i -le 50; $i++) {     $PathIndex = ($i - 1) % $OrgPaths.Count     $MockTenant.Users += [PSCustomObject]@{         Id = "user-$('{0:D4}' -f $i)"         DisplayName = "MockUser$i"         UserPrincipalName = "mockuser$i@mock.onmicrosoft.com"         Department = ($OrgPaths[$PathIndex] -split "-")[1]         EmployeeId = "EMP$('{0:D6}' -f $i)"         AccountEnabled = $true         OnPremisesExtensionAttributes = @{             ExtensionAttribute1 = $OrgPaths[$PathIndex]             ExtensionAttribute2 = if ($i % 10 -eq 0) { "ROLE-MGR" } else { "ROLE-IC" }             ExtensionAttribute3 = "ACTIVE"             ExtensionAttribute4 = "VALIDATED"             ExtensionAttribute5 = $null         }     } }  # Generate 15 mock groups $GroupDefs = @(     @{Name="OrgTree-ORG-AllEmployees"; Rule='user.extensionAttribute1 -match "^ORG"'},     @{Name="OrgTree-FIN-All"; Rule='(user.extensionAttribute1 -eq "ORG-FIN") or (user.extensionAttribute1 -startsWith "ORG-FIN-")'},     @{Name="OrgTree-HR-All"; Rule='(user.extensionAttribute1 -eq "ORG-HR") or (user.extensionAttribute1 -startsWith "ORG-HR-")'},     @{Name="OrgTree-IT-All"; Rule='(user.extensionAttribute1 -eq "ORG-IT") or (user.extensionAttribute1 -startsWith "ORG-IT-")'},     @{Name="OrgTree-OPS-All"; Rule='(user.extensionAttribute1 -eq "ORG-OPS") or (user.extensionAttribute1 -startsWith "ORG-OPS-")'},     @{Name="OrgTree-LEG-All"; Rule='(user.extensionAttribute1 -eq "ORG-LEG") or (user.extensionAttribute1 -startsWith "ORG-LEG-")'}     # Additional groups follow same pattern for departments... )  foreach ($Def in $GroupDefs) {     $MockTenant.Groups += [PSCustomObject]@{         Id = "group-$($Def.Name)"         DisplayName = $Def.Name         MembershipRule = $Def.Rule         GroupTypes = @("DynamicMembership")         SecurityEnabled = $true     } }  Write-Verbose "Mock tenant initialized: $($MockTenant.Users.Count) users, $($MockTenant.Groups.Count) groups"

Test Scenarios

Boundary Rules

The mock tenant simulates M365 GCC-Moderate responses only; it does not simulate out-of-scope services.

Mock data contains no real tenant identifiers, UPNs, or PII.

Drift Considerations

The mock tenant is a testing artifact; drift in mock data is intentional (for testing). Drift in the harness code itself requires Workflow 8.

Governance Alignment

The test harness enables continuous validation of governance rules without tenant risk, supporting Principle 4 (Drift Resistance) through automated testing and Principle 7 (Tenant Agnosticism) through tenant-independent test execution.
