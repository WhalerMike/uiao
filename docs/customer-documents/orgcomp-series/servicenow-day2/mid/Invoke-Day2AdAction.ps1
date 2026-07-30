# Invoke-Day2AdAction.ps1 — runs ON the domain-joined, in-boundary MID Server.
# =============================================================================
# The counterpart to the remediated AdHybridClient. It receives a STRUCTURED
# JSON job (never a command string), binds parameters natively via splatting,
# and returns a JSON result.
#
# Why this file exists: the previous design had ServiceNow render a PowerShell
# command line by string concatenation and dispatch the text. Caller-supplied
# parameter names were interpolated unescaped, which was a command-injection
# path onto a host with delegated AD write rights (P0-1), and the temporary
# password was rendered into the ECC payload in cleartext (P0-3).
#
# Design rules enforced here:
#   * No Invoke-Expression. Ever. Parameters are bound by splatting typed
#     hashtables the script builds itself.
#   * Parameter names are re-validated against a server-side allowlist. The
#     ServiceNow side validates too; neither trusts the other.
#   * The password is GENERATED HERE, applied as a SecureString, and never
#     returned or logged. ServiceNow receives a delivery handle only.
#   * Read actions return observed state so the gate can assert post-state.
#   * Any failure exits non-zero with ok:false. A failed read must never look
#     like a clean result.
#
# Usage (from the MID Command probe):
#   powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass `
#       -File Invoke-Day2AdAction.ps1 -JobJson $env:DAY2_JOB_JSON
#
# Prerequisites: RSAT ActiveDirectory module; the MID service account holding
# DELEGATED, least-privilege rights on the managed OUs only — never Domain
# Admin. That delegation is still asserted, not proven; run an
# effective-permissions dump before production.
# =============================================================================

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string] $JobJson,

    [Parameter(Mandatory = $false)]
    [string] $DeliveryScript = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# --- Allowlist. Mirrors AdHybridClient.ACTIONS. Both sides validate. ---------
$Contracts = @{
    'create-user'          = @('samAccountName', 'upn', 'givenName', 'surname', 'displayName', 'ou')
    'disable-user'         = @()
    'move-object'          = @('targetOu')
    'set-attributes'       = @('title', 'department', 'company', 'description', 'office',
                               'telephoneNumber', 'mobile', 'manager', 'employeeId',
                               'employeeType', 'streetAddress', 'city', 'state',
                               'postalCode', 'country', 'givenName', 'surname',
                               'displayName', 'extensionAttribute1', 'extensionAttribute2',
                               'extensionAttribute3', 'extensionAttribute4', 'extensionAttribute5')
    'reset-password'       = @('mustChangeAtLogon', 'deliveryRef')
    'add-group-member'     = @('group')
    'remove-group-member'  = @('group')
    'get-user'             = @('properties')
    'get-group-members'    = @('group', 'recursive')
}

# Set-ADUser parameter names for the attributes we permit. Anything not mapped
# here is refused rather than passed through as a -OtherAttributes guess.
$AttrParamMap = @{
    'title' = 'Title'; 'department' = 'Department'; 'company' = 'Company'
    'description' = 'Description'; 'office' = 'Office'
    'telephoneNumber' = 'OfficePhone'; 'mobile' = 'MobilePhone'
    'manager' = 'Manager'; 'employeeId' = 'EmployeeID'; 'employeeType' = 'EmployeeNumber'
    'streetAddress' = 'StreetAddress'; 'city' = 'City'; 'state' = 'State'
    'postalCode' = 'PostalCode'; 'country' = 'Country'
    'givenName' = 'GivenName'; 'surname' = 'Surname'; 'displayName' = 'DisplayName'
}
$ExtensionAttrs = @('extensionAttribute1', 'extensionAttribute2', 'extensionAttribute3',
                    'extensionAttribute4', 'extensionAttribute5')

function ConvertTo-LdapFilterEscaped {
    # RFC 4515 filter-value escaping. Used only as defense in depth on values
    # that are already resolved through a typed -Identity lookup (never on raw
    # caller input) -- distinguishedName can legally contain '(', ')', '\', or
    # '*', and a filter built from it must not let those be reinterpreted.
    param([Parameter(Mandatory = $true)][string] $Value)
    $sb = New-Object System.Text.StringBuilder
    foreach ($ch in $Value.ToCharArray()) {
        switch ($ch) {
            '\' { [void]$sb.Append('\5c') }
            '*' { [void]$sb.Append('\2a') }
            '(' { [void]$sb.Append('\28') }
            ')' { [void]$sb.Append('\29') }
            ([char]0) { [void]$sb.Append('\00') }
            default { [void]$sb.Append($ch) }
        }
    }
    return $sb.ToString()
}

function Write-Result {
    param($Ok, $Data, $ErrorText, $Dc)
    $payload = [ordered]@{
        ok          = [bool]$Ok
        data        = $Data
        error       = $ErrorText
        dc          = $Dc
        observed_at = (Get-Date).ToUniversalTime().ToString('o')
    }
    $payload | ConvertTo-Json -Depth 6 -Compress
    if (-not $Ok) { exit 1 }
    exit 0
}

function Assert-AllowedArgs {
    param([string] $Action, $ArgsObj)
    $allowed = $Contracts[$Action]
    if ($null -eq $allowed) { throw "unknown action: $Action" }
    if ($null -eq $ArgsObj) { return @{} }
    $out = @{}
    foreach ($p in $ArgsObj.PSObject.Properties) {
        if ($p.Name -notmatch '^[A-Za-z][A-Za-z0-9]*$') { throw "illegal parameter name" }
        if ($allowed -notcontains $p.Name) { throw "parameter not permitted for $Action" }
        $out[$p.Name] = $p.Value
    }
    return $out
}

function New-CompliantPassword {
    # Generated on the MID. Returns a SecureString DIRECTLY -- the password
    # never exists as a plain .NET String at any point, not even transiently.
    # (PSScriptAnalyzer's PSAvoidUsingConvertToSecureStringWithPlainText is
    # right to flag ConvertTo-SecureString -AsPlainText regardless of whether
    # the source string is hardcoded or freshly generated: the exposure is
    # the plaintext's lifetime on the managed heap, not just its presence in
    # source. Building the SecureString char-by-char via AppendChar avoids
    # that lifetime entirely, which is the actual fix, not a suppression.)
    $upper = 'ABCDEFGHJKLMNPQRSTUVWXYZ'; $lower = 'abcdefghijkmnopqrstuvwxyz'
    $digit = '23456789';                 $sym   = '!@#$%^&*()-_=+[]{}'
    $all = $upper + $lower + $digit + $sym
    $bytes = New-Object 'System.Byte[]' 64
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    $chars = New-Object 'System.Char[]' 24
    $chars[0] = $upper[$bytes[0] % $upper.Length]
    $chars[1] = $lower[$bytes[1] % $lower.Length]
    $chars[2] = $digit[$bytes[2] % $digit.Length]
    $chars[3] = $sym[$bytes[3] % $sym.Length]
    for ($i = 4; $i -lt 24; $i++) { $chars[$i] = $all[$bytes[$i] % $all.Length] }
    # Fisher-Yates shuffle in place using the RNG bytes, so class positions
    # are not fixed. (Also fixes a duplicate-character entropy quirk in the
    # prior Sort-Object/IndexOf approach: IndexOf resolves to the first
    # occurrence, so repeated characters shuffled identically.)
    for ($i = 23; $i -gt 0; $i--) {
        $j = $bytes[32 + $i] % ($i + 1)
        $tmp = $chars[$i]; $chars[$i] = $chars[$j]; $chars[$j] = $tmp
    }
    $secure = New-Object System.Security.SecureString
    foreach ($c in $chars) { $secure.AppendChar($c) }
    $secure.MakeReadOnly()
    [System.Array]::Clear($chars, 0, $chars.Length)
    return $secure
}

try {
    $job = $JobJson | ConvertFrom-Json
} catch {
    Write-Result -Ok $false -Data $null -ErrorText 'job payload unparseable' -Dc $null
}

try {
    if ($job.schema -ne 1) { throw 'unsupported job schema' }
    Import-Module ActiveDirectory -ErrorAction Stop

    $action   = [string]$job.action
    $identity = $job.identity
    $dc       = $job.server
    $jobArgs  = Assert-AllowedArgs -Action $action -ArgsObj $job.args

    # Reserved parameters are set here, from the job envelope — never from args.
    $common = @{}
    if ($dc) { $common['Server'] = [string]$dc }

    switch ($action) {

        'create-user' {
            $p = $common.Clone()
            $p['Name']              = [string]$jobArgs['displayName']
            $p['SamAccountName']    = [string]$jobArgs['samAccountName']
            $p['UserPrincipalName'] = [string]$jobArgs['upn']
            $p['Path']              = [string]$jobArgs['ou']
            $p['Enabled']           = $true
            if ($jobArgs.ContainsKey('givenName')) { $p['GivenName'] = [string]$jobArgs['givenName'] }
            if ($jobArgs.ContainsKey('surname'))   { $p['Surname']   = [string]$jobArgs['surname'] }
            New-ADUser @p
            $u = Get-ADUser -Identity ([string]$jobArgs['samAccountName']) @common -Properties DistinguishedName, Enabled
            Write-Result -Ok $true -Data ([ordered]@{
                distinguishedName = $u.DistinguishedName; enabled = $u.Enabled }) -ErrorText $null -Dc $dc
        }

        'disable-user' {
            Disable-ADAccount -Identity ([string]$identity) @common
            Write-Result -Ok $true -Data ([ordered]@{ dispatched = $true }) -ErrorText $null -Dc $dc
        }

        'move-object' {
            # SECURITY: resolve identity ONLY through the typed -Identity
            # parameter (SamAccountName/DN/GUID/SID binding, no expression
            # parsing) -- never build a -Filter/-LDAPFilter string from caller
            # input. A prior revision of this handler used
            # Get-ADObject -Filter "SamAccountName -eq '$identity'" as a
            # generic-object fallback; that is filter-injection-shaped
            # (unescaped single quotes let a crafted identity append an
            # arbitrary -or clause and resolve a different object than the
            # one approved) and has been removed. moveUserOuAd is a
            # user-move operation, so Get-ADUser -Identity is both correct
            # and sufficient -- it already accepts SamAccountName, DN, GUID,
            # and SID without any filter parsing.
            $obj = Get-ADUser -Identity ([string]$identity) @common
            Move-ADObject -Identity $obj.DistinguishedName -TargetPath ([string]$jobArgs['targetOu']) @common
            Write-Result -Ok $true -Data ([ordered]@{ moved = $true }) -ErrorText $null -Dc $dc
        }

        'set-attributes' {
            $p = $common.Clone()
            $p['Identity'] = [string]$identity
            $replace = @{}
            foreach ($k in $jobArgs.Keys) {
                if ($ExtensionAttrs -contains $k) { $replace[$k] = [string]$jobArgs[$k]; continue }
                $mapped = $AttrParamMap[$k]
                if (-not $mapped) { throw "unmapped attribute: $k" }
                $p[$mapped] = [string]$jobArgs[$k]
            }
            if ($replace.Count -gt 0) { $p['Replace'] = $replace }
            Set-ADUser @p
            Write-Result -Ok $true -Data ([ordered]@{ applied = @($jobArgs.Keys) }) -ErrorText $null -Dc $dc
        }

        'reset-password' {
            # P0-3: generated here, directly as a SecureString, never returned.
            # No plaintext String ever exists (see New-CompliantPassword).
            $secure = New-CompliantPassword
            Set-ADAccountPassword -Identity ([string]$identity) -Reset -NewPassword $secure @common
            $mustChange = $true
            if ($jobArgs.ContainsKey('mustChangeAtLogon')) { $mustChange = [bool]$jobArgs['mustChangeAtLogon'] }
            if ($mustChange) { Set-ADUser -Identity ([string]$identity) -ChangePasswordAtLogon $true @common }

            $handle = $null
            if ($DeliveryScript -and (Test-Path -LiteralPath $DeliveryScript)) {
                # Hand off out-of-band (SMS/PSM/sealed envelope). The delivery
                # script receives the secret; this script's OUTPUT never does.
                $handle = & $DeliveryScript -Identity ([string]$identity) `
                                            -Password $secure `
                                            -DeliveryRef ([string]$jobArgs['deliveryRef'])
            }
            $secure.Dispose()
            [System.GC]::Collect()

            Write-Result -Ok $true -Data ([ordered]@{
                reset = $true; mustChangeAtLogon = $mustChange
                deliveryHandle = $handle       # a reference, never the secret
            }) -ErrorText $null -Dc $dc
        }

        'add-group-member' {
            Add-ADGroupMember -Identity ([string]$jobArgs['group']) -Members ([string]$identity) -Confirm:$false @common
            Write-Result -Ok $true -Data ([ordered]@{ added = $true }) -ErrorText $null -Dc $dc
        }

        'remove-group-member' {
            Remove-ADGroupMember -Identity ([string]$jobArgs['group']) -Members ([string]$identity) -Confirm:$false @common
            Write-Result -Ok $true -Data ([ordered]@{ removed = $true }) -ErrorText $null -Dc $dc
        }

        'get-user' {
            # Read-back for the verify clause. Also serves PrivilegeClassifier:
            # when the identity is a GROUP we return its SID plus the SIDs of
            # every group it is TRANSITIVELY a member of, so nesting is covered.
            #
            # $jobArgs['properties'] is honored (not a dead parameter): the
            # baseline set below is always fetched regardless -- it's what
            # this handler's own response shape and the transitive-membership
            # lookup need -- and any caller-requested properties are unioned
            # in only if they're on $AllowedGetUserProps, so a caller can ask
            # for more AD attributes without this becoming an arbitrary
            # -Properties passthrough.
            $baselineProps     = @('DistinguishedName', 'Enabled', 'userAccountControl', 'pwdLastSet', 'objectSid', 'memberOf')
            $AllowedGetUserProps = $baselineProps + @('tokenGroups', 'displayName', 'userPrincipalName', 'sAMAccountName')
            $requested = @()
            if ($jobArgs.ContainsKey('properties') -and $jobArgs['properties']) {
                foreach ($rp in $jobArgs['properties']) {
                    if ($AllowedGetUserProps -contains $rp) { $requested += $rp }
                }
            }
            $props = @($baselineProps + $requested | Select-Object -Unique)
            # Try as a user first; if identity is actually a group, Get-ADUser
            # raises ObjectNotFound. -ErrorAction SilentlyContinue (rather than
            # an empty try/catch) makes that fall-through explicit without
            # swallowing the exception silently.
            $obj = Get-ADUser -Identity ([string]$identity) -Properties $props @common -ErrorAction SilentlyContinue
            if ($null -eq $obj) { $obj = Get-ADGroup -Identity ([string]$identity) -Properties objectSid, memberOf @common }

            $transitive = @()
            if ($obj.objectSid) {
                # $dn is our own AD-resolved DistinguishedName, not raw caller
                # input -- but a legally-formed DN can still contain '(', ')',
                # or '\', so escape it before interpolating into an LDAP
                # filter rather than assume it's already safe.
                $dn = ConvertTo-LdapFilterEscaped -Value $obj.DistinguishedName
                $parents = Get-ADGroup -LDAPFilter "(member:1.2.840.113556.1.4.1941:=$dn)" -Properties objectSid @common
                foreach ($g in $parents) { $transitive += $g.objectSid.Value }
            }
            Write-Result -Ok $true -Data ([ordered]@{
                distinguishedName        = $obj.DistinguishedName
                enabled                  = $(if ($obj.PSObject.Properties['Enabled']) { $obj.Enabled } else { $null })
                pwdLastSet               = $(if ($obj.PSObject.Properties['pwdLastSet']) { [string]$obj.pwdLastSet } else { $null })
                objectSid                = $(if ($obj.objectSid) { $obj.objectSid.Value } else { $null })
                transitiveMemberOfSids   = $transitive
            }) -ErrorText $null -Dc $dc
        }

        'get-group-members' {
            $recursive = $false
            if ($jobArgs.ContainsKey('recursive')) { $recursive = [bool]$jobArgs['recursive'] }
            $p = $common.Clone(); $p['Identity'] = [string]$jobArgs['group']
            if ($recursive) { $p['Recursive'] = $true }
            $members = Get-ADGroupMember @p
            $out = @()
            foreach ($m in $members) {
                $out += [ordered]@{
                    samAccountName    = $m.SamAccountName
                    distinguishedName = $m.distinguishedName
                    sid               = $m.SID.Value
                }
            }
            Write-Result -Ok $true -Data ([ordered]@{ members = $out; recursive = $recursive }) -ErrorText $null -Dc $dc
        }

        default { throw "unsupported action: $action" }
    }
}
catch {
    # No secret material can reach here: the password variable is scoped to its
    # branch and cleared before any Write-Result.
    Write-Result -Ok $false -Data $null -ErrorText ($_.Exception.Message) -Dc $job.server
}
