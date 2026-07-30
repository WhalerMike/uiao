# New-Day2AdLab.ps1 — provisions a throwaway lab Active Directory domain on
# Hyper-V so the AD leg (AdHybridClient.js + mid/Invoke-Day2AdAction.ps1) can be
# exercised against a REAL domain controller instead of a mock ServiceNow
# harness. See ../CURRENT-STATE-AD-LAB-VALIDATION.md for the test plan this
# lab exists to run.
#
# =============================================================================
# READ BEFORE RUNNING
#
#   * This is disposable, isolated lab infrastructure. It is NOT reviewed for
#     production use and must never point at a real corporate domain, a real
#     MID Server, or any network segment that matters.
#   * The virtual switch this script creates is Hyper-V "Internal" (host <->
#     guest only, no bridge to your physical LAN) specifically so a lab DNS
#     server / domain controller cannot collide with DHCP, DNS, or Kerberos
#     realms on your real network. Do not change it to "External" without
#     understanding that consequence.
#   * This script is meant to be READ and RUN DELIBERATELY BY A HUMAN, one
#     phase at a time. It is not meant to be piped into an unattended CI job.
#   * No password is ever hardcoded. Every secret is a SecureString parameter,
#     prompted interactively if you do not supply one on the command line.
#   * Three things here CANNOT be unattended and are called out explicitly
#     where they occur:
#       1. Downloading the Windows Server evaluation ISO (Microsoft Evaluation
#          Center, requires a browser and — depending on the download — a
#          free Microsoft account). This script takes the ISO path as a
#          required parameter and never fetches it.
#       2. The Windows Setup (OOBE) wizard the FIRST time the VM boots off
#          the ISO: language/edition selection, EULA, and setting the local
#          Administrator password. Hyper-V has no supported way to script
#          keystrokes into that wizard without an injected unattend answer
#          file, and this script deliberately does not attempt one — an
#          unattend.xml with a plaintext-or-obfuscated local admin password
#          baked into a mounted/attached disk is a worse secret-handling
#          story than "a human types a password once at a console," not a
#          better one. You WILL do this step yourself in the VM Connect
#          console. Budget 10-15 minutes.
#       3. Install-ADDSForest reboots the machine automatically as part of
#          promotion. PowerShell Direct sessions cannot survive that reboot;
#          this script disconnects cleanly, polls for the VM to come back,
#          and then requires you to invoke Phase 3 as a separate step once
#          you've confirmed the reboot completed. This is a deliberate
#          checkpoint, not a missing feature.
#
#   Everything else — virtual switch, VHDX, VM creation, guest network
#   configuration, AD DS role install + forest promotion (kicking off the
#   reboot), OU structure, delegated service account, and dsacls delegation —
#   is scripted below via PowerShell Direct (Invoke-Command -VMName), which
#   needs no guest network path at all, only a running VM and a credential.
#
# =============================================================================
# WORKFLOW
#
#   1. Download a Windows Server 2022 (or 2025) evaluation ISO yourself from
#      https://www.microsoft.com/evalcenter — this script does not do it.
#   2. .\New-Day2AdLab.ps1 -IsoPath 'C:\isos\WinServer2022Eval.iso' -Phase 1
#        -> creates the switch, VHDX, and VM; attaches the ISO; starts the VM.
#   3. MANUAL: vmconnect.exe . Day2AdLab-DC1  (or Hyper-V Manager -> Connect)
#      Walk the Windows Setup wizard: language/edition (Desktop Experience
#      recommended so you have a console to troubleshoot from), accept the
#      EULA, and set the local Administrator password. Wait for the desktop.
#   4. .\New-Day2AdLab.ps1 -Phase 2 -LocalAdminCredential (Get-Credential)
#        -> configures the guest NIC with a static IP, installs the AD DS
#           role, and promotes the box to a new forest root domain
#           controller. The guest reboots automatically; the script polls
#           for it to come back and then STOPS — it does not chain into
#           Phase 3 automatically, on purpose (see workflow rule 3 above).
#   5. .\New-Day2AdLab.ps1 -Phase 3 -LocalAdminCredential (Get-Credential)
#        -> creates the OU structure, the delegated MID service account, the
#           two test AD-sourced groups, and the dsacls delegation ACEs. Local
#           Administrator is Domain Admin on a fresh forest root, so the same
#           credential from Phase 2 authenticates here.
#   6. Prints the exact x_fed_day2_ops.* property values
#      (CURRENT-STATE-BUILD-DELTA.md §2 / CURRENT-STATE-SCRIPTS.md §5) that
#      now correspond to this lab, for you to copy into your validation run.
#
# =============================================================================

[CmdletBinding()]
param(
    # --- Phase 1 (host-side, fully scriptable) ----------------------------
    [Parameter(Mandatory = $true, HelpMessage = 'Path to a Windows Server evaluation ISO you already downloaded from the Microsoft Evaluation Center. This script never downloads one.')]
    [ValidateScript({
        if (-not (Test-Path -LiteralPath $_ -PathType Leaf)) { throw "ISO not found: $_" }
        if (([System.IO.Path]::GetExtension($_)) -ne '.iso') { throw "Expected a .iso file: $_" }
        $true
    })]
    [string] $IsoPath,

    [ValidateSet(1, 2, 3)]
    [int] $Phase = 1,

    [string] $VmName = 'Day2AdLab-DC1',
    [string] $SwitchName = 'Day2AdLab-Internal',
    [int] $MemoryGB = 4,
    [int] $CpuCount = 2,
    [int] $Generation = 2,
    [string] $VhdxPath,                     # default computed below (script dir\vhd\<VmName>.vhdx)
    [int] $VhdxSizeGB = 80,                 # dynamically-expanding max size, not allocated up front

    # Isolated lab subnet. The HOST gets HostInternalIp on the vEthernet
    # adapter for this switch; the DC gets StaticIp. Kept in the same /24 so
    # the host machine can act as a stand-in "MID Server" for the validation
    # runbook without a second VM.
    [string] $HostInternalIp = '10.88.0.1',
    [string] $StaticIp = '10.88.0.10',
    [int] $PrefixLength = 24,

    # --- Domain / OU / delegation shape ------------------------------------
    # .test is an IANA-reserved TLD (RFC 2606) specifically for non-production
    # use — it will never resolve on the real internet or collide with a real
    # registered domain, which matters more here than it would for a
    # throwaway ".local" (mDNS ambiguity) or a borrowed real-looking name.
    [string] $DomainDnsName = 'day2lab.test',
    [string] $DomainNetbiosName = 'DAY2LAB',

    # Maps onto x_fed_day2_ops.ad_managed_ous (CURRENT-STATE-BUILD-DELTA §2).
    [string] $ManagedUsersOuName = 'Day2ManagedUsers',
    # Maps onto x_fed_day2_ops.ad_disabled_ou.
    [string] $DisabledOuName = 'Day2DisabledAccounts',
    # Not itself a BUILD-DELTA property, but where the AD-sourced test groups
    # live so addGroupMemberAd/removeGroupMemberAd have something delegated
    # and something NOT delegated to exercise both directions.
    [string] $ManagedGroupsOuName = 'Day2ManagedGroups',
    [string] $ServiceAccountsOuName = 'Day2ServiceAccounts',

    [string] $MidServiceAccountName = 'svc-day2-mid',
    [string[]] $TestGroupNames = @('Day2Test-Group1', 'Day2Test-Group2'),

    # --- Phase 2/3 guest credentials (never hardcoded) ---------------------
    [PSCredential] $LocalAdminCredential,
    [SecureString] $SafeModeAdministratorPassword,
    [SecureString] $MidServiceAccountPassword
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if (-not $VhdxPath) {
    $VhdxPath = Join-Path -Path (Join-Path $PSScriptRoot 'vhd') -ChildPath ($VmName + '.vhdx')
}

function ConvertTo-Day2DomainDn {
    # 'day2lab.test' -> 'DC=day2lab,DC=test'
    param([Parameter(Mandatory = $true)][string] $DnsName)
    ($DnsName.Split('.') | ForEach-Object { "DC=$_" }) -join ','
}

function Assert-Day2HyperVAvailable {
    if (-not (Get-Command -Name 'Get-VM' -ErrorAction SilentlyContinue)) {
        throw @'
The Hyper-V PowerShell module is not available. This script cannot enable the
Hyper-V role for you unattended -- it requires a reboot and is a host-level
change you should make deliberately, not as a side effect of a lab script.

Run, then reboot, then re-run this script:
    Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -All
'@
    }
}

# =============================================================================
# PHASE 1 -- host-side. Fully scriptable: no guest OS exists yet.
# =============================================================================
function New-Day2LabSwitch {
    param([string] $Name, [string] $HostIp, [int] $Prefix)

    $existing = Get-VMSwitch -Name $Name -ErrorAction SilentlyContinue
    if (-not $existing) {
        Write-Host "Creating Internal (host<->guest only) virtual switch '$Name'..."
        New-VMSwitch -SwitchName $Name -SwitchType Internal | Out-Null
    } else {
        if ($existing.SwitchType -ne 'Internal') {
            throw "Virtual switch '$Name' already exists with SwitchType '$($existing.SwitchType)', not Internal. Refusing to reuse a switch that might bridge to a real network -- pick a different -SwitchName or remove the existing one deliberately."
        }
        Write-Host "Reusing existing Internal virtual switch '$Name'."
    }

    $ifAlias = "vEthernet ($Name)"
    $adapter = Get-NetAdapter -Name $ifAlias -ErrorAction SilentlyContinue
    if ($adapter) {
        $haveIp = Get-NetIPAddress -InterfaceAlias $ifAlias -IPAddress $HostIp -ErrorAction SilentlyContinue
        if (-not $haveIp) {
            Write-Host "Assigning host-side static IP $HostIp/$Prefix on '$ifAlias'..."
            New-NetIPAddress -InterfaceAlias $ifAlias -IPAddress $HostIp -PrefixLength $Prefix -ErrorAction SilentlyContinue | Out-Null
        } else {
            Write-Host "Host-side adapter '$ifAlias' already has $HostIp assigned."
        }
    } else {
        Write-Warning "Could not find host adapter '$ifAlias' yet (Hyper-V sometimes takes a few seconds to surface it after New-VMSwitch). Re-run this phase if the static IP assignment did not take."
    }
}

function New-Day2LabVirtualMachine {
    param(
        [string] $Name, [string] $Switch, [string] $VhdPath, [int] $SizeGB,
        [int] $MemGB, [int] $Cpus, [int] $Gen, [string] $Iso
    )

    if (Get-VM -Name $Name -ErrorAction SilentlyContinue) {
        throw "A VM named '$Name' already exists. Remove it deliberately (Remove-VM) or pick a different -VmName before re-running Phase 1."
    }

    $vhdDir = Split-Path -Parent $VhdPath
    if (-not (Test-Path -LiteralPath $vhdDir)) { New-Item -ItemType Directory -Path $vhdDir -Force | Out-Null }

    Write-Host "Creating dynamically-expanding VHDX (max $SizeGB GB) at $VhdPath..."
    New-VHD -Path $VhdPath -SizeBytes ([int64]$SizeGB * 1GB) -Dynamic | Out-Null

    Write-Host "Creating VM '$Name' (Generation $Gen, $MemGB GB, $Cpus vCPU)..."
    New-VM -Name $Name -Generation $Gen -MemoryStartupBytes ([int64]$MemGB * 1GB) `
        -VHDPath $VhdPath -SwitchName $Switch | Out-Null

    # Static memory: a lone-DC lab is small enough that dynamic memory ballooning
    # buys nothing, and static allocation avoids a whole class of "why is AD
    # slow / why did NTDS complain about memory pressure" red herrings while
    # you're trying to isolate AD-leg behavior, not diagnose Hyper-V memory
    # management.
    Set-VMMemory -VMName $Name -DynamicMemoryEnabled $false -StartupBytes ([int64]$MemGB * 1GB)
    Set-VMProcessor -VMName $Name -Count $Cpus

    Add-VMDvdDrive -VMName $Name -Path $Iso
    if ($Gen -eq 2) {
        Set-VMFirmware -VMName $Name -EnableSecureBoot On -SecureBootTemplate 'MicrosoftWindows'
        $dvd = Get-VMDvdDrive -VMName $Name
        Set-VMFirmware -VMName $Name -FirstBootDevice $dvd
    }

    Write-Host "Starting VM '$Name'..."
    Start-VM -Name $Name
}

function Invoke-Day2LabPhase1 {
    Assert-Day2HyperVAvailable
    New-Day2LabSwitch -Name $SwitchName -HostIp $HostInternalIp -Prefix $PrefixLength
    New-Day2LabVirtualMachine -Name $VmName -Switch $SwitchName -VhdPath $VhdxPath `
        -SizeGB $VhdxSizeGB -MemGB $MemoryGB -Cpus $CpuCount -Gen $Generation -Iso $IsoPath

    Write-Host "`n=== Phase 1 complete. This part cannot go further unattended. ===" -ForegroundColor Yellow
    Write-Host @"
Next (MANUAL — no clean unattended path for the initial Setup wizard):

  1. vmconnect.exe . $VmName        (or Hyper-V Manager -> Connect)
  2. Walk Windows Setup: pick an edition (Desktop Experience recommended for
     this lab), accept the EULA, set the local Administrator password.
  3. Wait until you reach the desktop / a login prompt.
  4. Then run:
       .\New-Day2AdLab.ps1 -Phase 2 -LocalAdminCredential (Get-Credential -UserName '.\Administrator' -Message 'Local admin you just set in the VM')
"@
}

# =============================================================================
# PHASE 2 -- guest-side via PowerShell Direct. Requires the OOBE above done.
# Configures the guest NIC, installs the AD DS role, and promotes to a new
# forest. Install-ADDSForest triggers an automatic reboot; PowerShell Direct
# cannot survive that, so this function disconnects cleanly and polls for the
# VM to come back rather than pretending the session continued.
# =============================================================================
function Wait-Day2LabVmBack {
    param([string] $Name, [int] $TimeoutSeconds = 900, [PSCredential] $Credential)
    Write-Host "Waiting for '$Name' to reboot and become reachable via PowerShell Direct (up to $([int]($TimeoutSeconds/60)) minutes)..."
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Seconds 15
        try {
            $vm = Get-VM -Name $Name
            if ($vm.State -ne 'Running') { continue }
            $ok = Invoke-Command -VMName $Name -Credential $Credential -ScriptBlock { $true } -ErrorAction Stop
            if ($ok) { Write-Host "'$Name' is back up."; return $true }
        } catch {
            # Expected repeatedly while the guest is mid-reboot / services not
            # up yet. Only the timeout below is a real failure.
        }
    }
    throw "Timed out waiting for '$Name' to come back after the reboot. Check the VM console directly -- Install-ADDSForest may have failed, or the credential no longer matches (a DC promotion does not change the local Administrator's password, so this would indicate something else went wrong)."
}

function Invoke-Day2LabPhase2 {
    if (-not $LocalAdminCredential) {
        $LocalAdminCredential = Get-Credential -UserName '.\Administrator' `
            -Message "Local Administrator credential for $VmName (the password you set during Windows Setup OOBE)"
    }
    if (-not $SafeModeAdministratorPassword) {
        $SafeModeAdministratorPassword = Read-Host -AsSecureString -Prompt 'DSRM (Directory Services Restore Mode) password for the new forest'
    }

    Write-Host 'Configuring guest network (static IP, DNS pointed at self) and installing the AD DS role...'
    Invoke-Command -VMName $VmName -Credential $LocalAdminCredential -ScriptBlock {
        param($Ip, $Prefix)
        $adapter = Get-NetAdapter | Where-Object { $_.Status -eq 'Up' } | Select-Object -First 1
        if (-not $adapter) { throw 'No up network adapter found in the guest -- is it attached to the Internal switch?' }
        if (-not (Get-NetIPAddress -InterfaceIndex $adapter.ifIndex -IPAddress $Ip -ErrorAction SilentlyContinue)) {
            New-NetIPAddress -InterfaceIndex $adapter.ifIndex -IPAddress $Ip -PrefixLength $Prefix -ErrorAction SilentlyContinue | Out-Null
        }
        Set-DnsClientServerAddress -InterfaceIndex $adapter.ifIndex -ServerAddresses $Ip
        Install-WindowsFeature -Name AD-Domain-Services, RSAT-AD-PowerShell -IncludeManagementTools | Out-Null
    } -ArgumentList $StaticIp, $PrefixLength

    Write-Host "Promoting '$VmName' to a new forest root domain controller for $DomainDnsName. This WILL reboot the VM automatically."
    try {
        Invoke-Command -VMName $VmName -Credential $LocalAdminCredential -ScriptBlock {
            param($DnsName, $NetbiosName, $SafePwd)
            Import-Module ADDSDeployment
            Install-ADDSForest -DomainName $DnsName -DomainNetbiosName $NetbiosName `
                -SafeModeAdministratorPassword $SafePwd -InstallDns `
                -DatabasePath 'C:\Windows\NTDS' -LogPath 'C:\Windows\NTDS' -SysvolPath 'C:\Windows\SYSVOL' `
                -Force -NoRebootOnCompletion:$false -WarningAction SilentlyContinue -Confirm:$false
        } -ArgumentList $DomainDnsName, $DomainNetbiosName, $SafeModeAdministratorPassword
    } catch {
        # Expected: the reboot tears down the PowerShell Direct session before
        # it returns cleanly. Anything else surfaced here is a real failure.
        Write-Host "(session ended, most likely due to the expected reboot: $($_.Exception.Message))"
    }

    Wait-Day2LabVmBack -Name $VmName -Credential $LocalAdminCredential

    Write-Host "`n=== Phase 2 complete. Do not chain straight into Phase 3. ===" -ForegroundColor Yellow
    Write-Host @'
Confirm the promotion actually finished (log into the console once and check
`Get-ADDomain` succeeds, or just trust the heartbeat check above), then run:
    .\New-Day2AdLab.ps1 -Phase 3 -LocalAdminCredential (Get-Credential -UserName '.\Administrator')
'@
}

# =============================================================================
# PHASE 3 -- guest-side via PowerShell Direct, post-promotion. OU structure,
# delegated (NEVER Domain Admin) MID service account, test groups, and dsacls
# delegation scoped to exactly the OUs/groups the kit is allowed to touch.
# =============================================================================
function Invoke-Day2LabPhase3 {
    if (-not $LocalAdminCredential) {
        $LocalAdminCredential = Get-Credential -UserName '.\Administrator' `
            -Message "Domain Administrator credential for $VmName (same local Administrator password from Phase 2 -- it became Domain Admin on forest creation)"
    }
    if (-not $MidServiceAccountPassword) {
        $MidServiceAccountPassword = Read-Host -AsSecureString -Prompt "Password for the delegated MID service account ($MidServiceAccountName)"
    }

    $domainDn = ConvertTo-Day2DomainDn -DnsName $DomainDnsName

    Write-Host 'Creating OU structure, delegated service account, test groups, and dsacls delegation...'
    Invoke-Command -VMName $VmName -Credential $LocalAdminCredential -ScriptBlock {
        param($DomainDn, $ManagedOu, $DisabledOu, $GroupsOu, $SvcOu, $SvcName, $SvcPwd, $Groups, $NetbiosName)

        Import-Module ActiveDirectory

        foreach ($ouName in @($ManagedOu, $DisabledOu, $GroupsOu, $SvcOu)) {
            if (-not (Get-ADOrganizationalUnit -Filter "Name -eq '$ouName'" -SearchBase $DomainDn -SearchScope OneLevel -ErrorAction SilentlyContinue)) {
                New-ADOrganizationalUnit -Name $ouName -Path $DomainDn -ProtectedFromAccidentalDeletion $true
            }
        }

        $svcOuDn = "OU=$SvcOu,$DomainDn"
        if (-not (Get-ADUser -Filter "SamAccountName -eq '$SvcName'" -ErrorAction SilentlyContinue)) {
            New-ADUser -Name $SvcName -SamAccountName $SvcName -Path $svcOuDn `
                -AccountPassword $SvcPwd -Enabled $true -PasswordNeverExpires $true `
                -Description 'Day-2 kit AD-lab MID service account -- delegated rights ONLY on the managed OUs below. NEVER add to Domain Admins / Account Operators / any built-in privileged group.'
        }

        $groupsOuDn = "OU=$GroupsOu,$DomainDn"
        foreach ($g in $Groups) {
            if (-not (Get-ADGroup -Filter "Name -eq '$g'" -ErrorAction SilentlyContinue)) {
                New-ADGroup -Name $g -GroupScope Global -GroupCategory Security -Path $groupsOuDn `
                    -Description 'Day-2 kit AD-lab test group -- delegated to the MID service account for add/removeGroupMemberAd testing.'
            }
        }

        # --- Delegation. Everything here is scoped to the specific OUs/groups
        # the kit manages -- this is the "delegation of control", never
        # Domain Admin / Account Operators, that CURRENT-STATE-BUILD-DELTA.md
        # §1.2 requires. /I:S = inherit down to objects in the OU (not to
        # child OUs' own permission model beyond what AD already propagates).
        #
        # This delegation set is ILLUSTRATIVE, matched to the actions
        # AdHybridClient/Invoke-Day2AdAction.ps1 actually perform (create,
        # disable, reset-password, move, set a curated attribute set, manage
        # membership of named groups) -- it is not guaranteed to be the exact
        # minimum needed for every property in AttrParamMap. Verify with the
        # effective-permissions dump in CURRENT-STATE-AD-LAB-VALIDATION.md §4
        # before treating this as a production delegation template.
        $managedOuDn  = "OU=$ManagedOu,$DomainDn"
        $disabledOuDn = "OU=$DisabledOu,$DomainDn"
        $principal    = "$NetbiosName\$SvcName"

        foreach ($ouDn in @($managedOuDn, $disabledOuDn)) {
            # Create/delete USER child objects -- covers createUserAd, and is
            # also what Move-ADObject needs on BOTH the source and target OU
            # (a move is a delete-from-source + create-in-target under the
            # hood), so both managed OUs need this, not just the "active" one.
            dsacls.exe $ouDn /I:S /G "${principal}:CCDC;user" | Out-Null

            # Extended right: reset password.
            dsacls.exe $ouDn /I:S /G "${principal}:CA;Reset Password;user" | Out-Null

            # Property set: userAccountControl and friends -- Disable-ADAccount
            # / Enable-ADAccount write through this set.
            dsacls.exe $ouDn /I:S /G "${principal}:WP;Account Restrictions;user" | Out-Null

            # Property sets covering the set-attributes allowlist (title,
            # department, phone, address, display name, etc.). Names must
            # match the schema's property-set display names exactly -- these
            # are the stock English ones; verify on a non-English DC.
            dsacls.exe $ouDn /I:S /G "${principal}:WP;Personal Information;user" | Out-Null
            dsacls.exe $ouDn /I:S /G "${principal}:WP;Web Information;user" | Out-Null
            dsacls.exe $ouDn /I:S /G "${principal}:WP;General Information;user" | Out-Null
        }

        # Group membership: delegated to the two NAMED test groups only, not
        # to "any group in this OU" and not to the OU itself -- so a caller
        # cannot walk the delegation up to a group that was never intended to
        # be managed by this kit.
        foreach ($g in $Groups) {
            dsacls.exe "CN=$g,$groupsOuDn" /G "${principal}:WP;member" | Out-Null
        }

    } -ArgumentList $domainDn, $ManagedUsersOuName, $DisabledOuName, $ManagedGroupsOuName, $ServiceAccountsOuName, `
                    $MidServiceAccountName, $MidServiceAccountPassword, $TestGroupNames, $DomainNetbiosName

    $managedOuDn  = "OU=$ManagedUsersOuName,$domainDn"
    $disabledOuDn = "OU=$DisabledOuName,$domainDn"

    Write-Host "`n=== Phase 3 complete. Lab domain is up. ===" -ForegroundColor Green
    Write-Host @"

x_fed_day2_ops.* property values for this lab (CURRENT-STATE-BUILD-DELTA.md §2,
CURRENT-STATE-SCRIPTS.md §5) -- set these on whatever you use to run the
validation plan (see ../CURRENT-STATE-AD-LAB-VALIDATION.md):

    x_fed_day2_ops.ad_mid_server    = <hostname/IP of whatever runs Invoke-Day2AdAction.ps1 -- see the validation doc's note on the lab using the Hyper-V host itself as a stand-in MID>
    x_fed_day2_ops.ad_dc            = $StaticIp   (or $VmName if your resolver can reach it by name)
    x_fed_day2_ops.ad_disabled_ou   = $disabledOuDn
    x_fed_day2_ops.ad_managed_ous   = $managedOuDn
    x_fed_day2_ops.ad_protected_groups = <leave at the kit default -- none of the AD built-in Tier-0 groups were touched by this lab>

Delegated service account: $DomainNetbiosName\$MidServiceAccountName
    (rights scoped to $managedOuDn and $disabledOuDn only, plus WP;member on
    $($TestGroupNames -join ', ') -- NOT Domain Admin, NOT Account Operators)

Next: ../CURRENT-STATE-AD-LAB-VALIDATION.md for the adversarial test plan.
"@
}

# =============================================================================
switch ($Phase) {
    1 { Invoke-Day2LabPhase1 }
    2 { Invoke-Day2LabPhase2 }
    3 { Invoke-Day2LabPhase3 }
}
