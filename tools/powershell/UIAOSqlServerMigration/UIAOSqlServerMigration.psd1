@{
    RootModule        = 'UIAOSqlServerMigration.psm1'
    ModuleVersion     = '1.0.0'
    GUID              = '95f89c30-29d8-4eee-ae02-031c14d8013d'
    Author            = 'Michael Stratton'
    CompanyName       = 'UIAO'
    Copyright         = '(c) UIAO. All rights reserved.'
    Description       = 'SQL Server identity-transformation automation behind the Implementation Companion runbooks (canon UIAO_135 Transformation #7; ADR-002, ADR-004, ADR-068, ADR-091). Ships the Arc onboarding/validation helpers (Book 04), the CREATE LOGIN ... FROM EXTERNAL PROVIDER script generation with parallel-run validation (Book 05), and the SPN-collision remediation planning plus NTLM-reduction GPO reporting (Book 06). Read-only validation/audit functions run directly; every state-changing function either SupportsShouldProcess (audit-first, defaults to preview) or generates a reviewable script/plan and executes nothing by default. Fully offline-testable via snapshot inputs; no hard-coded credentials, tenants, or endpoints.'

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
        'Get-UIAONtlmGpoReport'
    )

    CmdletsToExport   = @()
    VariablesToExport = @()
    AliasesToExport   = @()

    PrivateData       = @{
        PSData = @{
            Tags         = @('UIAO', 'SQLServer', 'Arc', 'Entra', 'NTLM', 'Kerberos', 'SPN', 'Migration', 'ADR-091', 'ADR-068', 'UIAO-135')
            ProjectUri   = 'https://github.com/WhalerMike/uiao'
            ReleaseNotes = 'Initial UIAOSqlServerMigration release — the shipped automation for the SQL Server Implementation Companion Books 04-06. Arc: Test-UIAOArcAgentStatus / Test-UIAOArcManagedIdentityToken / Test-UIAOArcSqlExtension (read-only validation) and Invoke-UIAOArcOnboarding (idempotent, ShouldProcess, ConfirmImpact High, plans by default). Login migration: New-UIAOEntraLoginMapping (codifies the Windows->Entra mapping from the UIAO_181 reconciliation), New-UIAOEntraLoginScript (dry-run CREATE LOGIN ... FROM EXTERNAL PROVIDER generation; opens no SQL connection), Test-UIAOLoginParallelRun (ADR-091 §1 exit-criteria evaluation). NTLM/Kerberos: New-UIAOSpnRemediationPlan (audit-first setspn plan from Spec3-D1.7) and Get-UIAONtlmGpoReport (read-only NTLM-reduction GPO posture vs the ADR-068 phased plan). Every output is a provenance-sealed envelope (content_hash byte-identical to uiao.ir.models.core.canonical_hash); the sealed data omits timestamps so identical inputs yield identical hashes.'
        }
    }
}
