@{
    RootModule        = 'OrgTreeValidation.psm1'
    ModuleVersion     = '1.0.0'
    GUID              = '8a4d2f0e-9b5c-4e1d-9d2a-3f5b6c7e8f01'
    Author            = 'UIAO contributors'
    CompanyName       = 'UIAO'
    Copyright         = '(c) UIAO contributors'
    Description       = 'OrgTree validation and Microsoft Graph snapshot helpers (canon UIAO_159).'
    PowerShellVersion = '7.2'
    RequiredModules   = @()
    FunctionsToExport = @(
        'Test-OrgPathFormat',
        'Test-OrgPathHierarchy',
        'Get-OrgTreeValidationReport',
        'Test-DynamicGroupAlignment',
        'Export-OrgTreeSnapshot',
        'Compare-OrgTreeSnapshots',
        'Invoke-UiaoOrgTreeValidate'
    )
    CmdletsToExport   = @()
    VariablesToExport = @()
    AliasesToExport   = @()
    PrivateData       = @{
        PSData = @{
            Tags         = @('UIAO', 'OrgTree', 'GCC-Moderate', 'EntraID', 'Validation')
            ProjectUri   = 'https://github.com/WhalerMike/uiao'
            ReleaseNotes = 'Initial release. Implements UIAO_159 against UIAO_151/UIAO_152/UIAO_154/UIAO_163.'
        }
    }
}
