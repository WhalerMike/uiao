@{
    RootModule        = 'UIAOImportAdapters.psm1'
    ModuleVersion     = '1.0.0'
    GUID              = 'b3e1d2c4-5a6f-47b8-9c0d-1e2f3a4b5c6d'
    Author            = 'Michael Stratton'
    CompanyName       = 'UIAO'
    Copyright         = '(c) UIAO. All rights reserved.'
    Description       = 'Assessment ingestion adapters (canon UIAO_182, ADR-094). Producer in the assessment-to-plan toolchain: normalizes third-party assessment output (Azure Migrate, Intune GPO Analytics, Defender for Identity, CISA ScubaGear, ADRecon) into sealed UIAO-schema envelopes for downstream correlation, drift detection, and plan generation.'

    # Uses ConvertFrom-Json -Depth and modern array serialization; targets the
    # PowerShell 7 runtime used by the tools/powershell Pester CI.
    PowerShellVersion = '7.0'

    FunctionsToExport = @(
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
            Tags         = @('UIAO', 'Assessment', 'Import', 'Provenance', 'ADR-094', 'UIAO-182')
            ProjectUri   = 'https://github.com/WhalerMike/uiao'
            ReleaseNotes = 'Initial UIAOImportAdapters release per UIAO_182 / ADR-094 (Workstream B, Gap 3). Six functions: five normalizing importers plus Merge-UIAOAssessmentSources. Output is sealed with the canonical content_hash so imported artifacts are DRIFT-PROVENANCE-classifiable by src/uiao/governance/drift.py.'
        }
    }
}
