@{
    RootModule        = 'UIAOPlanGenerators.psm1'
    ModuleVersion     = '1.0.0'
    GUID              = 'd5a3f4e6-7c8b-49d0-1e2f-3a4b5c6d7e8f'
    Author            = 'Michael Stratton'
    CompanyName       = 'UIAO'
    Copyright         = '(c) UIAO. All rights reserved.'
    Description       = 'Assessment-to-plan derivation (canon UIAO_183, ADR-094). Consumer in the assessment-to-plan toolchain: derives draft migration plans (per-device, GPO, identity waves, DNS, PKI) and a master plan from the normalized producer artifacts. Decommissioning / migration order is computed deterministically from the OrgPath cross-plane dependency graph (topological sort with cycle + cross-domain blocker detection), never from manual reading.'

    # Pure derivation over producer artifacts; no live reads. Targets the
    # PowerShell 7 runtime used by the tools/powershell Pester CI.
    PowerShellVersion = '7.0'

    FunctionsToExport = @(
        'New-UIAOComputerModernizationPlan',
        'New-UIAOGPOMigrationPlan',
        'New-UIAOIdentityMigrationPlan',
        'New-UIAODNSMigrationPlan',
        'New-UIAOPKIMigrationPlan',
        'Export-UIAOMasterPlan'
    )

    CmdletsToExport   = @()
    VariablesToExport = @()
    AliasesToExport   = @()

    PrivateData       = @{
        PSData = @{
            Tags         = @('UIAO', 'Migration', 'Plan', 'OrgPath', 'Topology', 'ADR-094', 'UIAO-183')
            ProjectUri   = 'https://github.com/WhalerMike/uiao'
            ReleaseNotes = 'Initial UIAOPlanGenerators release per UIAO_183 / ADR-094 (Workstream B, Gap 3). Five plan generators plus Export-UIAOMasterPlan. Decommissioning order is computed by deterministic topological sort of the OrgPath dependency graph; cycles and cross-domain dependencies are flagged as blockers that make a plan not approvable. Each plan cites its source assessment (derived_from) and is sealed with the canonical content_hash; the sealed plan data omits timestamps so identical assessments yield identical plan hashes.'
        }
    }
}
