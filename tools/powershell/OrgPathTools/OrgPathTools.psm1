# OrgPathTools — Model C per-facet OrgPath PowerShell wrapper (ADR-084 §C8).
#
# Canonical Model C entry point per ADR-084: Test-OrgPathFacets.
# Operator-friendly wrapper that shells out to the Python loader for
# codebook semantics — the loader is the canonical validator
# (src/uiao/modernization/orgtree/codebook.py); this module is the
# operator-facing UX layer.
#
# Per ADR-084 §C8 the Model A `Test-OrgPath` single-string function is
# NOT restored here. For the Model A surface, see the prior
# `OrgTreeValidation` module — it remains operational for
# grandfathered Model A tenants but is not the canonical entry point
# for Model C.
#
# Exports:
#
#   Test-OrgPathFacets       — per-facet validation of all 10 named
#                              slots on one Entra principal
#   Get-OrgPathCodebook      — return the loaded Codebook as a hashtable
#   Test-OrgPathFacetValue   — pure-function: validate one (facet, value)
#                              tuple against the loaded codebook
#
# Functions calling Microsoft Graph require Microsoft.Graph PowerShell
# SDK. Functions that operate on the codebook only are offline.

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Canonical attribute slot binding per ADR-078 (10 named + 5 reserved).
# Sourced from src/uiao/modernization/orgtree/codebook.py; tests in
# tests/OrgPathTools.Tests.ps1 verify these match the Python loader.
$Script:CanonicalSlotMap = [ordered]@{
    'extensionAttribute1'  = 'region'
    'extensionAttribute2'  = 'department'
    'extensionAttribute3'  = 'division'
    'extensionAttribute4'  = 'role'
    'extensionAttribute5'  = 'cost_center'
    'extensionAttribute6'  = 'classification'
    'extensionAttribute7'  = 'hire_date'
    'extensionAttribute8'  = 'term_date'
    'extensionAttribute9'  = 'clearance_level'
    'extensionAttribute10' = 'account_type'
}

# Default path to the Python interpreter for loader shell-outs.
$Script:PythonExe = if ($env:UIAO_PYTHON) { $env:UIAO_PYTHON } else { 'python' }


function Invoke-CodebookLoader {
    <#
    .SYNOPSIS
        Internal: shell out to the Python codebook loader and return parsed JSON.
    .NOTES
        Per ADR-084 §C8 the Python loader is the canonical validator.
        This helper invokes a small Python one-liner that loads the
        default codebook and prints its facet declarations as JSON.
        Tests inject a fixture-loader path via $env:UIAO_PYTHON or
        Get-OrgPathCodebook -PythonScript override.
    #>
    [CmdletBinding()]
    [OutputType([hashtable])]
    param(
        [Parameter(Mandatory = $false)]
        [string]$PythonScript
    )
    $script = if ($PythonScript) { $PythonScript } else {
        @'
import json
from uiao.modernization.orgtree.codebook import default_codebook

cb = default_codebook()
print(json.dumps({
    'schema_version': cb.schema_version,
    'model': cb.model,
    'facets': {
        name: {
            'attribute': f.attribute,
            'kind': f.kind,
            'description': f.description,
            'enumeration': [{'value': v.value, 'description': v.description} for v in f.enumeration.values()],
            'deprecated': [{'value': d.value, 'replaced_by': d.replaced_by} for d in f.deprecated.values()],
            'value_pattern': f.value_pattern,
            'allow_empty': f.allow_empty,
        }
        for name, f in cb.facets.items()
    }
}))
'@
    }
    $jsonText = & $Script:PythonExe '-c' $script
    if ($LASTEXITCODE -ne 0) {
        throw "Python codebook loader exited $LASTEXITCODE"
    }
    return ($jsonText -join "`n") | ConvertFrom-Json -AsHashtable
}


function Get-OrgPathCodebook {
    <#
    .SYNOPSIS
        Return the loaded per-facet Codebook as a hashtable.
    .DESCRIPTION
        Per ADR-084 §C8 shells out to the Python loader. Returned shape
        mirrors the FastAPI /api/v1/orgpath/codebook response (per
        ADR-084 §C7): facets keyed by name, each with attribute, kind,
        enumeration, deprecated, value_pattern, allow_empty.
    .EXAMPLE
        $cb = Get-OrgPathCodebook
        $cb.facets.region.enumeration | Format-Table
    .NOTES
        Canon: UIAO_151 v4.0. Equivalent Python:
        `uiao.modernization.orgtree.codebook.default_codebook()`.
    #>
    [CmdletBinding()]
    [OutputType([hashtable])]
    param(
        [Parameter(Mandatory = $false)]
        [string]$PythonScript
    )
    Invoke-CodebookLoader -PythonScript $PythonScript
}


function Test-OrgPathFacetValue {
    <#
    .SYNOPSIS
        Validate one (facet, value) tuple against the loaded codebook.
    .DESCRIPTION
        Returns a hashtable with IsValid / IsActive / IsDeprecated /
        ReplacementFor / Reason. Per-facet validation per UIAO_163 v2.0
        Format / Value / Phantom semantics. Pure check (no Graph
        access; only shells to Python for the codebook).
    .PARAMETER Facet
        The facet name (e.g., 'region', 'department').
    .PARAMETER Value
        The value to validate.
    .PARAMETER Codebook
        Optional pre-loaded codebook hashtable. When omitted, the
        function loads via Get-OrgPathCodebook (one shell-out per
        invocation).
    .EXAMPLE
        Test-OrgPathFacetValue -Facet 'region' -Value 'NCR'
    #>
    [CmdletBinding()]
    [OutputType([hashtable])]
    param(
        [Parameter(Mandatory = $true)]
        [ValidateNotNullOrEmpty()]
        [string]$Facet,

        [Parameter(Mandatory = $true)]
        [AllowEmptyString()]
        [string]$Value,

        [Parameter(Mandatory = $false)]
        [hashtable]$Codebook
    )
    $cb = if ($Codebook) { $Codebook } else { Get-OrgPathCodebook }
    if (-not $cb.facets.ContainsKey($Facet)) {
        return @{
            Facet           = $Facet
            Value           = $Value
            IsValid         = $false
            IsActive        = $false
            IsDeprecated    = $false
            ReplacementFor  = $null
            Reason          = "Unknown facet '$Facet' — not declared in the codebook"
        }
    }
    $facetDoc = $cb.facets[$Facet]
    $kind = $facetDoc.kind

    if ($kind -eq 'reserved') {
        $valid = [string]::IsNullOrEmpty($Value)
        return @{
            Facet           = $Facet
            Value           = $Value
            IsValid         = $valid
            IsActive        = $false
            IsDeprecated    = $false
            ReplacementFor  = $null
            Reason          = if ($valid) { 'Reserved slot, null (correct)' } else { "Reserved slot has value '$Value'" }
        }
    }

    if ($kind -eq 'typed') {
        if ([string]::IsNullOrEmpty($Value) -and $facetDoc.allow_empty) {
            return @{
                Facet          = $Facet
                Value          = $Value
                IsValid        = $true
                IsActive       = $true
                IsDeprecated   = $false
                ReplacementFor = $null
                Reason         = 'Empty (allowed)'
            }
        }
        $pattern = $facetDoc.value_pattern
        $match = ($pattern -and ($Value -cmatch $pattern))
        return @{
            Facet          = $Facet
            Value          = $Value
            IsValid        = [bool]$match
            IsActive       = [bool]$match
            IsDeprecated   = $false
            ReplacementFor = $null
            Reason         = if ($match) { "Matches $Facet value_pattern" } else { "'$Value' fails $Facet value_pattern '$pattern'" }
        }
    }

    # Enumerated facet.
    $deprecatedEntry = $facetDoc.deprecated | Where-Object { $_.value -eq $Value } | Select-Object -First 1
    if ($deprecatedEntry) {
        return @{
            Facet          = $Facet
            Value          = $Value
            IsValid        = $false
            IsActive       = $false
            IsDeprecated   = $true
            ReplacementFor = $deprecatedEntry.replaced_by
            Reason         = "'$Value' is deprecated; replaced_by '$($deprecatedEntry.replaced_by)'"
        }
    }
    $activeMatch = $facetDoc.enumeration | Where-Object { $_.value -eq $Value } | Select-Object -First 1
    if ($activeMatch) {
        return @{
            Facet          = $Facet
            Value          = $Value
            IsValid        = $true
            IsActive       = $true
            IsDeprecated   = $false
            ReplacementFor = $null
            Reason         = "Active value in $Facet enumeration"
        }
    }
    return @{
        Facet          = $Facet
        Value          = $Value
        IsValid        = $false
        IsActive       = $false
        IsDeprecated   = $false
        ReplacementFor = $null
        Reason         = "'$Value' not in $Facet enumeration"
    }
}


function Test-OrgPathFacets {
    <#
    .SYNOPSIS
        Per-facet validation of all 10 named OrgPath slots on one Entra principal.
    .DESCRIPTION
        Canonical Model C entry point per ADR-084 §C8. Reads the 10
        canonical extensionAttribute slots (1–10) from the Entra user
        and validates each per-facet against the loaded codebook.
        Returns an array of hashtables, one per facet, with Facet /
        Slot / Value / IsValid / IsActive / IsDeprecated /
        ReplacementFor / Reason.

        Requires Microsoft.Graph PowerShell SDK. The principal is read
        via Get-MgUser (or supplied via -PrincipalSnapshot for offline
        testing).
    .PARAMETER UserPrincipalName
        UPN of the user to validate. Pass either this OR
        -PrincipalSnapshot.
    .PARAMETER PrincipalSnapshot
        Pre-fetched hashtable mapping extensionAttribute1..10 → value.
        Used for offline testing or when the snapshot was captured by
        the engine's snapshot job.
    .PARAMETER Codebook
        Optional pre-loaded codebook hashtable.
    .EXAMPLE
        Test-OrgPathFacets -UserPrincipalName alice@contoso.com
    .EXAMPLE
        $snap = @{ extensionAttribute1 = 'NCR'; extensionAttribute2 = 'IT' }
        Test-OrgPathFacets -PrincipalSnapshot $snap
    #>
    [CmdletBinding(DefaultParameterSetName = 'ByUPN')]
    [OutputType([hashtable[]])]
    param(
        [Parameter(Mandatory = $true, ParameterSetName = 'ByUPN')]
        [ValidateNotNullOrEmpty()]
        [string]$UserPrincipalName,

        [Parameter(Mandatory = $true, ParameterSetName = 'BySnapshot')]
        [hashtable]$PrincipalSnapshot,

        [Parameter(Mandatory = $false)]
        [hashtable]$Codebook
    )
    $cb = if ($Codebook) { $Codebook } else { Get-OrgPathCodebook }

    # Resolve principal attribute hash.
    $attrs = if ($PSCmdlet.ParameterSetName -eq 'ByUPN') {
        if (-not (Get-Command Get-MgUser -ErrorAction SilentlyContinue)) {
            throw "Microsoft.Graph PowerShell SDK not installed; cannot resolve $UserPrincipalName. Pass -PrincipalSnapshot for offline use."
        }
        $props = @($Script:CanonicalSlotMap.Keys) -join ','
        $user = Get-MgUser -UserId $UserPrincipalName -Property $props
        $h = @{}
        foreach ($slot in $Script:CanonicalSlotMap.Keys) {
            $h[$slot] = $user.OnPremisesExtensionAttributes.$slot
        }
        $h
    }
    else {
        $PrincipalSnapshot
    }

    $results = @()
    foreach ($slot in $Script:CanonicalSlotMap.Keys) {
        $facetName = $Script:CanonicalSlotMap[$slot]
        $value = if ($attrs.ContainsKey($slot)) { $attrs[$slot] } else { '' }
        if ($null -eq $value) { $value = '' }
        $result = Test-OrgPathFacetValue -Facet $facetName -Value $value -Codebook $cb
        $result.Slot = $slot
        $results += $result
    }
    return $results
}


Export-ModuleMember -Function `
    'Get-OrgPathCodebook', `
    'Test-OrgPathFacetValue', `
    'Test-OrgPathFacets'
