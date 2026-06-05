@{
    RootModule        = 'UIAOIdentityAssessment.psm1'
    ModuleVersion     = '1.0.0'
    GUID              = 'c4f2e3d5-6b7a-48c9-0d1e-2f3a4b5c6d7e'
    Author            = 'Michael Stratton'
    CompanyName       = 'UIAO'
    Copyright         = '(c) UIAO. All rights reserved.'
    Description       = 'Hybrid identity assessment (canon UIAO_181, ADR-094). Producer in the assessment-to-plan toolchain: inventories Entra ID via Microsoft Graph and reconciles it against on-prem AD, emitting sealed UIAO-schema identity assessment artifacts. Cloud-aware Graph endpoint resolution (fail-closed); every exporter supports offline -SnapshotPath normalization.'

    # Uses cloud-aware Graph resolution and modern JSON cmdlets; targets the
    # PowerShell 7 runtime used by the tools/powershell Pester CI. Live reads
    # additionally require the Microsoft.Graph SDK (offline -SnapshotPath does not).
    PowerShellVersion = '7.0'

    FunctionsToExport = @(
        'Export-UIAOEntraUsers',
        'Export-UIAOEntraGroups',
        'Export-UIAOEntraApps',
        'Export-UIAOConditionalAccess',
        'Compare-UIAOIdentitySources',
        'Invoke-UIAOIdentityAssessment'
    )

    CmdletsToExport   = @()
    VariablesToExport = @()
    AliasesToExport   = @()

    PrivateData       = @{
        PSData = @{
            Tags         = @('UIAO', 'Identity', 'Entra', 'Graph', 'Reconciliation', 'ADR-094', 'UIAO-181')
            ProjectUri   = 'https://github.com/WhalerMike/uiao'
            ReleaseNotes = 'Initial UIAOIdentityAssessment release per UIAO_181 / ADR-094 (Workstream B, Gap 3). Four Entra exporters, AD-vs-Entra reconciliation (DRIFT-IDENTITY), and a master orchestrator. Cloud-aware Graph endpoint resolution mirrors uiao.adapters._graph_clouds (commercial serves GCC-Moderate; unknown clouds fail closed). Output sealed with the canonical content_hash for DRIFT-PROVENANCE classification.'
        }
    }
}
