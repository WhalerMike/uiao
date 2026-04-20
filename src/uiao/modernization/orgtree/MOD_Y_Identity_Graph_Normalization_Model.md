---
document_id: MOD_Y
title: "Appendix Y — Identity Graph Normalization Model"
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

# Appendix Y — Identity Graph Normalization Model

Purpose

This appendix defines the normalization rules that ensure identity graph consistency within the OrgTree. Normalization eliminates redundancy, enforces referential integrity, and ensures that every attribute value is derivable from the canonical OrgPath.

Scope

Covers 12 normalization rules, three normalization forms, approved denormalization patterns, and PowerShell/Graph validation queries. Applies to all identity objects within M365 GCC-Moderate.

Canonical Structure

Identity data is normalized to Third Normal Form (3NF) with explicitly documented denormalization exceptions for performance.

Technical Scaffolding

Normalization Rules

Normalization Forms

First Normal Form (1NF): No multi-valued OrgPaths. Each user has exactly one OrgPath. No repeating groups of attributes. All attribute values are atomic.

Second Normal Form (2NF): All non-key attributes are fully functionally dependent on the OrgPath. Department, group membership, and AU membership are all derivable from the OrgPath alone—they depend on the full OrgPath, not a partial key.

Third Normal Form (3NF): No transitive dependencies between non-key attributes. Lifecycle state does not depend on account status indirectly through another attribute; each attribute depends only on the primary key (user identity + OrgPath).

Approved Denormalization Patterns

Validation Queries

# NRM-001: Verify single OrgPath per user $MultiValuedOrgPaths = Get-MgUser -All -Property "Id,OnPremisesExtensionAttributes" |     Where-Object { ($_.OnPremisesExtensionAttributes.ExtensionAttribute1 -split ";").Count -gt 1 }  # NRM-003: Verify manager references are valid $InvalidManagers = Get-MgUser -All -Property "Id,Manager" -ExpandProperty "Manager" |     Where-Object { $_.Manager -eq $null -and $_.OnPremisesExtensionAttributes.ExtensionAttribute1 -ne "ORG" }  # NRM-008: Verify employeeId uniqueness $AllEmployeeIds = Get-MgUser -All -Property "EmployeeId" |     Where-Object { -not [string]::IsNullOrEmpty($_.EmployeeId) } $DuplicateIds = $AllEmployeeIds | Group-Object -Property EmployeeId |     Where-Object { $_.Count -gt 1 }  # NRM-010: Verify lifecycle-accountEnabled consistency $InconsistentState = Get-MgUser -All -Property "Id,AccountEnabled,OnPremisesExtensionAttributes" |     Where-Object {         ($_.OnPremisesExtensionAttributes.ExtensionAttribute3 -eq "ACTIVE" -and $_.AccountEnabled -eq $false) -or         ($_.OnPremisesExtensionAttributes.ExtensionAttribute3 -eq "SUSPENDED" -and $_.AccountEnabled -eq $true)     }

Boundary Rules

All normalization validation queries run against Entra ID via Microsoft Graph within M365 GCC-Moderate.

Denormalization does not extend to external systems or non-M365 data stores.

Drift Considerations

A normalization rule violation is a specific category of drift detectable by the drift detection engine (Appendix M).

Denormalization drift (cached value diverges from source) is detected by rules DDE-010 and similar.

Governance Alignment

Normalization implements Principle 1 (Deterministic State) by ensuring that every attribute has exactly one authoritative source and Principle 2 (Schema Fixity) by defining the structural rules that all identity data must follow.
