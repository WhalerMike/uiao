@{
    RootModule        = 'UIAO.OrgPath.psm1'
    ModuleVersion     = '1.0.0'
    GUID              = 'a4e1b7d2-3c58-4f9e-8b06-92d47f1c5a80'
    Author            = 'Michael Stratton'
    CompanyName       = 'UIAO'
    Copyright         = '(c) UIAO. All rights reserved.'
    Description       = 'Hybrid-C+Path derived-OrgPath tooling (ADR-127): compose the extensionAttribute15 derived path (trailing "|" always present), normalize subtree prefixes, detect derived-path drift, and write governance facets + derived path to users and devices via Microsoft Graph.'
    PowerShellVersion = '5.1'

    FunctionsToExport = @(
        'New-OrgPath',
        'Get-OrgPathPrefix',
        'Test-OrgPathDrift',
        'Update-OrgAttributes'
    )

    CmdletsToExport   = @()
    VariablesToExport = @()
    AliasesToExport   = @()

    PrivateData       = @{
        PSData = @{
            Tags         = @('UIAO', 'OrgPath', 'HybridCPath', 'ADR-127', 'ADR-078')
            ProjectUri   = 'https://github.com/WhalerMike/uiao'
            ReleaseNotes = 'Initial Hybrid-C+Path release per ADR-127: derived canonical OrgPath on extensionAttribute15 with the trailing-delimiter contract.'
        }
    }
}
