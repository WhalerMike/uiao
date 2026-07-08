# UIAO.OrgPath — Hybrid-C+Path derived-OrgPath tooling (ADR-127).
#
# The Hybrid-C+Path model layers two things over the 15 extension
# attribute slots:
#
#   - Governance layer (extensionAttribute1-14): the Model C facet
#     decomposition per ADR-078/ADR-121. Validated per-facet by
#     OrgPathTools / the Python drift engine — NOT by this module.
#   - Inheritance layer (extensionAttribute15): a canonical OrgPath
#     string DERIVED from the hierarchy facets (region, department,
#     division), restoring the subtree-prefix targeting Model C
#     removed.
#
# The trailing-delimiter contract: every segment — including the last —
# is terminated by "|", so a -startsWith / `like` prefix such as
# "Division=East|" can never match "Division=Eastern|" or
# "Division=Easton|". New-OrgPath always emits the trailing delimiter;
# Get-OrgPathPrefix normalizes any prefix that is missing it.
#
# SSOT: src/uiao/canon/data/orgpath/codebook.yaml (`hybrid` block).
# The slot map and segment labels below mirror it; the Pester tests
# guard the module against silent divergence.
#
# Exports:
#
#   New-OrgPath          — compose the derived canonical OrgPath
#                          (always ends in "|")
#   Get-OrgPathPrefix    — normalize a subtree prefix for -startsWith /
#                          `like` use (idempotent)
#   Test-OrgPathDrift    — compare a stored derived path against the
#                          value recomputed from governance facets
#   Update-OrgAttributes — write governance facets + derived path to a
#                          user (Update-MgUser,
#                          onPremisesExtensionAttributes) or device
#                          (Update-MgDevice, extensionAttributes)
#
# Update-OrgAttributes requires the Microsoft.Graph PowerShell SDK; the
# other three functions are pure/offline.

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Inheritance-layer contract per codebook.yaml `hybrid` block (ADR-127).
$Script:OrgPathDelimiter = '|'
$Script:OrgPathSlot = 'extensionAttribute15'

# Ordered hierarchy facets composed into the derived path, with their
# path segment labels and governance-layer slots.
$Script:DerivedFromFacets = @(
    @{ Facet = 'region';     Label = 'Region';     Slot = 'extensionAttribute1' },
    @{ Facet = 'department'; Label = 'Department'; Slot = 'extensionAttribute2' },
    @{ Facet = 'division';   Label = 'Division';   Slot = 'extensionAttribute3' }
)


function New-OrgPath {
    <#
    .SYNOPSIS
        Compose the derived canonical OrgPath for the inheritance layer.
    .DESCRIPTION
        Builds the extensionAttribute15 value from the governance-layer
        hierarchy facets in canonical order (Region, Department,
        Division). Every segment — including the last — is terminated
        by "|" (the ADR-127 trailing-delimiter contract), so the output
        ALWAYS ends in "|".

        The derived path is a contiguous hierarchy prefix: composition
        stops at the first unpopulated facet (a Division without a
        Department is not a path, it is drift in the governance layer).
    .PARAMETER Region
        Region facet value (extensionAttribute1).
    .PARAMETER Department
        Department facet value (extensionAttribute2).
    .PARAMETER Division
        Division facet value (extensionAttribute3).
    .EXAMPLE
        New-OrgPath -Region NCR -Department IT -Division CyberOps
        # Region=NCR|Department=IT|Division=CyberOps|
    .EXAMPLE
        New-OrgPath -Region NCR -Department IT
        # Region=NCR|Department=IT|
    .OUTPUTS
        [string] — the derived path, or '' when no facet is populated.
    #>
    [CmdletBinding()]
    [OutputType([string])]
    param(
        [Parameter(Mandatory = $false)]
        [string]$Region,

        [Parameter(Mandatory = $false)]
        [string]$Department,

        [Parameter(Mandatory = $false)]
        [string]$Division
    )
    $values = @{
        region     = $Region
        department = $Department
        division   = $Division
    }
    $path = ''
    foreach ($entry in $Script:DerivedFromFacets) {
        $value = $values[$entry.Facet]
        if ([string]::IsNullOrEmpty($value)) {
            # Contiguous-prefix rule: stop at the first gap.
            break
        }
        if ($value.Contains($Script:OrgPathDelimiter) -or $value.Contains('=')) {
            throw "OrgPath facet value '$value' ($($entry.Facet)) must not contain '$($Script:OrgPathDelimiter)' or '='."
        }
        # Trailing delimiter always present — every segment is terminated.
        $path += '{0}={1}{2}' -f $entry.Label, $value, $Script:OrgPathDelimiter
    }
    return $path
}


function Get-OrgPathPrefix {
    <#
    .SYNOPSIS
        Normalize an OrgPath subtree prefix for -startsWith / `like` use.
    .DESCRIPTION
        Appends the trailing "|" when the prefix is missing it, so
        "Division=East" becomes "Division=East|" and can never match
        "Division=Eastern|" or "Division=Easton|". Idempotent: a prefix
        that already ends in "|" is returned unchanged (the delimiter
        is never doubled).
    .PARAMETER Prefix
        The prefix to normalize (e.g. "Region=NCR|Department=IT" or a
        single segment "Division=East").
    .EXAMPLE
        Get-OrgPathPrefix -Prefix 'Division=East'
        # Division=East|
    .EXAMPLE
        Get-OrgPathPrefix -Prefix 'Division=East|'
        # Division=East|   (unchanged)
    .OUTPUTS
        [string] — the delimiter-terminated prefix.
    #>
    [CmdletBinding()]
    [OutputType([string])]
    param(
        [Parameter(Mandatory = $true, ValueFromPipeline = $true)]
        [ValidateNotNullOrEmpty()]
        [string]$Prefix
    )
    process {
        if ($Prefix.EndsWith($Script:OrgPathDelimiter)) {
            return $Prefix
        }
        return $Prefix + $Script:OrgPathDelimiter
    }
}


function Test-OrgPathDrift {
    <#
    .SYNOPSIS
        Detect drift between a stored derived OrgPath and its recomputed value.
    .DESCRIPTION
        The inheritance layer is derived data: extensionAttribute15 must
        equal New-OrgPath over the governance-layer hierarchy facets at
        all times. This function recomputes the expected value and
        compares. Any divergence — a hand-edited path, a stale path
        after a facet move, a missing trailing delimiter — is drift.
    .PARAMETER StoredOrgPath
        The value currently stored in extensionAttribute15. Empty or
        absent is compared against the recomputed value like any other.
    .PARAMETER Region
        Region facet value currently in extensionAttribute1.
    .PARAMETER Department
        Department facet value currently in extensionAttribute2.
    .PARAMETER Division
        Division facet value currently in extensionAttribute3.
    .EXAMPLE
        Test-OrgPathDrift -StoredOrgPath 'Region=NCR|Department=IT|' -Region NCR -Department IT
        # IsDrifted = $false
    .EXAMPLE
        Test-OrgPathDrift -StoredOrgPath 'Region=NCR|Department=IT' -Region NCR -Department IT
        # IsDrifted = $true (missing trailing delimiter)
    .OUTPUTS
        [hashtable] with IsDrifted / Expected / Actual / Reason.
    #>
    [CmdletBinding()]
    [OutputType([hashtable])]
    param(
        [Parameter(Mandatory = $false)]
        [AllowEmptyString()]
        [string]$StoredOrgPath = '',

        [Parameter(Mandatory = $false)]
        [string]$Region,

        [Parameter(Mandatory = $false)]
        [string]$Department,

        [Parameter(Mandatory = $false)]
        [string]$Division
    )
    $expected = New-OrgPath -Region $Region -Department $Department -Division $Division
    $drifted = -not [string]::Equals($StoredOrgPath, $expected, [System.StringComparison]::Ordinal)
    $reason = if (-not $drifted) {
        'Stored derived path matches the governance-layer facets'
    }
    elseif ($StoredOrgPath -and -not $StoredOrgPath.EndsWith($Script:OrgPathDelimiter)) {
        "Stored path is missing the trailing '$($Script:OrgPathDelimiter)' (ADR-127 trailing-delimiter contract)"
    }
    else {
        'Stored path does not match the value derived from the governance-layer facets'
    }
    return @{
        IsDrifted = $drifted
        Expected  = $expected
        Actual    = $StoredOrgPath
        Reason    = $reason
    }
}


function Update-OrgAttributes {
    [Diagnostics.CodeAnalysis.SuppressMessageAttribute('PSUseSingularNouns', '', Justification = 'Writes the plural attribute set (governance facets + derived path) in one Graph call; the plural is the contract.')]
    <#
    .SYNOPSIS
        Write governance facets and the derived OrgPath to a user or device.
    .DESCRIPTION
        Stamps the hierarchy facet values to their governance-layer
        slots and the recomputed derived OrgPath to extensionAttribute15
        in a single Graph update, keeping the two layers atomic.

        Object types use DIFFERENT Graph properties:

          - Users:   Update-MgUser with `onPremisesExtensionAttributes`
          - Devices: Update-MgDevice with `extensionAttributes` —
            devices do NOT have onPremisesExtensionAttributes; using it
            on a device is a silent no-op at best.

        Requires the Microsoft.Graph PowerShell SDK. Hybrid-synced
        users' onPremisesExtensionAttributes are read-only in the
        cloud — for those, write via the on-prem AD source instead
        (ADR-121 records the trap).
    .PARAMETER UserId
        Object id or UPN of the user to update.
    .PARAMETER DeviceId
        Object id of the device to update.
    .PARAMETER Region
        Region facet value (extensionAttribute1).
    .PARAMETER Department
        Department facet value (extensionAttribute2).
    .PARAMETER Division
        Division facet value (extensionAttribute3).
    .EXAMPLE
        Update-OrgAttributes -UserId alice@contoso.com -Region NCR -Department IT -Division CyberOps
    .EXAMPLE
        Update-OrgAttributes -DeviceId 3f2c8a1e-0000-0000-0000-000000000000 -Region NCR -Department IT
    .OUTPUTS
        [hashtable] describing the write: TargetType / TargetId /
        Property / Attributes (the slot→value map sent to Graph).
    #>
    [CmdletBinding(DefaultParameterSetName = 'User')]
    [OutputType([hashtable])]
    param(
        [Parameter(Mandatory = $true, ParameterSetName = 'User')]
        [ValidateNotNullOrEmpty()]
        [string]$UserId,

        [Parameter(Mandatory = $true, ParameterSetName = 'Device')]
        [ValidateNotNullOrEmpty()]
        [string]$DeviceId,

        [Parameter(Mandatory = $false)]
        [string]$Region,

        [Parameter(Mandatory = $false)]
        [string]$Department,

        [Parameter(Mandatory = $false)]
        [string]$Division
    )
    $values = @{
        region     = $Region
        department = $Department
        division   = $Division
    }

    # Governance layer: facet values to their canonical slots.
    $attributes = @{}
    foreach ($entry in $Script:DerivedFromFacets) {
        $value = $values[$entry.Facet]
        if (-not [string]::IsNullOrEmpty($value)) {
            $attributes[$entry.Slot] = $value
        }
    }
    # Inheritance layer: the derived path, recomputed — never passed in.
    $attributes[$Script:OrgPathSlot] = New-OrgPath -Region $Region -Department $Department -Division $Division

    if ($PSCmdlet.ParameterSetName -eq 'User') {
        if (-not (Get-Command Update-MgUser -ErrorAction SilentlyContinue)) {
            throw 'Microsoft.Graph PowerShell SDK not installed; Update-MgUser is unavailable.'
        }
        # Users carry the slots under onPremisesExtensionAttributes.
        Update-MgUser -UserId $UserId -BodyParameter @{
            onPremisesExtensionAttributes = $attributes
        }
        return @{
            TargetType = 'user'
            TargetId   = $UserId
            Property   = 'onPremisesExtensionAttributes'
            Attributes = $attributes
        }
    }

    if (-not (Get-Command Update-MgDevice -ErrorAction SilentlyContinue)) {
        throw 'Microsoft.Graph PowerShell SDK not installed; Update-MgDevice is unavailable.'
    }
    # Devices carry the slots under extensionAttributes — NOT
    # onPremisesExtensionAttributes, which exists only on users.
    Update-MgDevice -DeviceId $DeviceId -BodyParameter @{
        extensionAttributes = $attributes
    }
    return @{
        TargetType = 'device'
        TargetId   = $DeviceId
        Property   = 'extensionAttributes'
        Attributes = $attributes
    }
}


Export-ModuleMember -Function `
    'New-OrgPath', `
    'Get-OrgPathPrefix', `
    'Test-OrgPathDrift', `
    'Update-OrgAttributes'
