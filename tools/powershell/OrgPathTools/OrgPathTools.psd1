@{
    RootModule        = 'OrgPathTools.psm1'
    ModuleVersion     = '1.0.0'
    GUID              = '7c0f8a4c-0d9e-4b3a-9c6a-5e2d8f4a6c3b'
    Author            = 'Michael Stratton'
    CompanyName       = 'UIAO'
    Copyright         = '(c) UIAO. All rights reserved.'
    Description       = 'Model C per-facet OrgPath PowerShell wrapper (ADR-084 §C8). Operator-facing UX over the canonical Python Codebook loader.'
    PowerShellVersion = '5.1'

    FunctionsToExport = @(
        'Get-OrgPathCodebook',
        'Test-OrgPathFacetValue',
        'Test-OrgPathFacets'
    )

    CmdletsToExport   = @()
    VariablesToExport = @()
    AliasesToExport   = @()

    PrivateData       = @{
        PSData = @{
            Tags         = @('UIAO', 'OrgPath', 'ModelC', 'ADR-078', 'ADR-084')
            ProjectUri   = 'https://github.com/WhalerMike/uiao'
            ReleaseNotes = 'Initial Model C per-facet release per ADR-084 Phase 5 #8.'
        }
    }
}
