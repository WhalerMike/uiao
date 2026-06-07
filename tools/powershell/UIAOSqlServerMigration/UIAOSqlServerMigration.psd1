@{
    RootModule        = 'UIAOSqlServerMigration.psm1'
    ModuleVersion     = '1.1.0'
    GUID              = '95f89c30-29d8-4eee-ae02-031c14d8013d'
    Author            = 'Michael Stratton'
    CompanyName       = 'UIAO'
    Copyright         = '(c) UIAO. All rights reserved.'
    Description       = 'SQL Server identity-transformation automation behind the Implementation Companion runbooks (canon UIAO_135 Transformation #7; ADR-002, ADR-004, ADR-067, ADR-068, ADR-069, ADR-091). Ships the fused Phase-0 estate inventory with the retain/consolidate/retire gate (Book 02), the Arc onboarding/validation helpers (Book 04), the CREATE LOGIN ... FROM EXTERNAL PROVIDER script generation with parallel-run validation (Book 05), the SPN-collision remediation planning plus NTLM-reduction GPO reporting (Book 06), the ADR-067 group classification and group-login emitter (Book 07), the Spec3-D1.9<->D1.8 correlation with ADR-069 app classification and the connection-string plan (Book 08), the ADR-091 §5 CCM-BIR closure record and scheduled-run drift diff (Book 09), and the SQL ADCS-dependency extraction with the dependency-ordered CA-replacement sequence (Book 10). Read-only validation/audit/derivation functions run directly; every state-changing function either SupportsShouldProcess (audit-first, defaults to preview) or generates a reviewable script/plan and executes nothing by default. Fully offline-testable via snapshot inputs; no hard-coded credentials, tenants, or endpoints.'

    # Pure derivation over reviewed artifacts plus guarded live wrappers; targets
    # the PowerShell 7 runtime used by the tools/powershell Pester CI.
    PowerShellVersion = '7.0'

    FunctionsToExport = @(
        'Test-UIAOArcAgentStatus',
        'Test-UIAOArcManagedIdentityToken',
        'Test-UIAOArcSqlExtension',
        'Invoke-UIAOArcOnboarding',
        'New-UIAOEntraLoginMapping',
        'New-UIAOEntraLoginScript',
        'Test-UIAOLoginParallelRun',
        'New-UIAOSpnRemediationPlan',
        'Get-UIAONtlmGpoReport',
        'New-UIAOEstateInventory',
        'New-UIAOEntraGroupClassification',
        'New-UIAOGroupLoginScript',
        'New-UIAOAppConnectionPlan',
        'New-UIAOClosureRecord',
        'Compare-UIAOClosureRun',
        'New-UIAOSqlCertificatePlan'
    )

    CmdletsToExport   = @()
    VariablesToExport = @()
    AliasesToExport   = @()

    PrivateData       = @{
        PSData = @{
            Tags         = @('UIAO', 'SQLServer', 'Arc', 'Entra', 'NTLM', 'Kerberos', 'SPN', 'Migration', 'ADR-091', 'ADR-068', 'ADR-067', 'ADR-069', 'UIAO-135')
            ProjectUri   = 'https://github.com/WhalerMike/uiao'
            ReleaseNotes = 'v1.1.0 — extends the roster from Books 04-06 to the full Books 02-10 of the SQL Server Implementation Companion, retiring every [to build] marker. New: New-UIAOEstateInventory (Book 02; fuses Spec3-D1.8 + Spec1-D1.5 + Find-DbaInstance into one deduplicated estate inventory and applies the ADR-091 §1 retain/consolidate/retire gate), New-UIAOEntraGroupClassification + New-UIAOGroupLoginScript (Book 07; ADR-067 four-type classification and the access-backing group-login emitter), New-UIAOAppConnectionPlan (Book 08; Spec3-D1.9<->D1.8 correlation, ADR-069 four-class classification, and the dry-run connection-string transformation), New-UIAOClosureRecord + Compare-UIAOClosureRun (Book 09; the ADR-091 §5 CCM-BIR per-instance closure record and the scheduled-run drift diff that flags mixed-mode/new-login/Arc-offline as compliance violations), and New-UIAOSqlCertificatePlan (Book 10; SQL''s three ADCS dependencies and the dependency-ordered CA-replacement / CBA-issuance sequence). All additions are pure derivation over reviewed discovery output — read-only, offline-testable, and changing nothing. Prior (v1.0.0) Books 04-06 roster unchanged. Every output is a provenance-sealed envelope (content_hash byte-identical to uiao.ir.models.core.canonical_hash); the sealed data omits timestamps so identical inputs yield identical hashes.'
        }
    }
}
