@{
    RootModule        = 'UIAOImportAdapters.psm1'
    ModuleVersion     = '0.1.0'
    GUID              = 'b2e7d4a1-6c3f-4e8a-9d2b-1f5a7c0e93d4'
    Author            = 'Michael Stratton'
    CompanyName       = 'UIAO'
    Copyright         = '(c) UIAO. All rights reserved.'
    Description       = 'Assessment-to-plan toolchain PRODUCER (ADR-094 / UIAO_182). Read-only, file-based ingestion adapters that normalize third-party assessment exports (Azure Migrate, Intune GPO Analytics, Defender for Identity, CISA ScubaGear, ADRecon) into one canonical UIAO assessment shape with a content-hash-sealed provenance envelope.'
    PowerShellVersion = '5.1'

    FunctionsToExport = @(
        'ConvertTo-UIAOCanonicalJson',
        'Get-UIAOContentHash',
        'New-UIAOAssessmentArtifact',
        'Import-UIAOAzureMigrateReport',
        'Import-UIAOGPOAnalyticsReport',
        'Import-UIAODefenderFindings',
        'Import-UIAOSCuBAReport',
        'Import-UIAOADReconReport',
        'Merge-UIAOAssessmentSources'
    )

    CmdletsToExport   = @()
    VariablesToExport = @()
    AliasesToExport   = @()

    PrivateData       = @{
        PSData = @{
            Tags         = @('UIAO', 'Assessment', 'Producer', 'ADR-094', 'UIAO_182')
            ProjectUri   = 'https://github.com/WhalerMike/uiao'
            ReleaseNotes = 'Initial implementation of the UIAO_182 producer roster per ADR-094. Offline, file-based; emits content-hash-sealed UIAO assessment artifacts.'
        }
    }
}
