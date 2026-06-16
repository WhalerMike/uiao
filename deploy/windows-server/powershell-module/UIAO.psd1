@{
    ModuleVersion     = '1.0.0'
    GUID              = 'C1D2E3F4-A5B6-7890-CDEF-012345678901'
    Author            = 'WhalerMike'
    CompanyName       = 'UIAO'
    Copyright         = '(c) WhalerMike. Apache-2.0.'
    Description       = 'Manage the UIAO governance API Windows Service installation.'
    PowerShellVersion = '5.1'
    RootModule        = 'UIAO.psm1'

    FunctionsToExport = @(
        'Install-UIAO',
        'Uninstall-UIAO',
        'Get-UIAOStatus',
        'Test-UIAOHealth',
        'Update-UIAO'
    )
    CmdletsToExport   = @()
    VariablesToExport = @()
    AliasesToExport   = @()

    PrivateData = @{
        PSData = @{
            Tags         = @('UIAO','governance','OrgPath','identity','IIS','WindowsService')
            ProjectUri   = 'https://github.com/WhalerMike/uiao'
            ReleaseNotes = 'Initial release of the UIAO PowerShell management module.'
        }
    }
}
