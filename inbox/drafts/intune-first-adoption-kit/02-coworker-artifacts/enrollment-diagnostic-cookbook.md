# Windows Enrollment Diagnostic Cookbook

**Audience:** Helpdesk staff, field technicians, desktop engineers, and identity
engineers diagnosing individual Windows devices that have failed to enroll
cleanly into Microsoft Entra ID, Microsoft Intune, or both.

**Purpose:** This is a symptom-first reference for the most common Intune-first
device enrollment failure modes. Each failure mode starts with the symptom
visible to the user or administrator, lists the diagnostic commands and portal
queries that confirm the diagnosis, identifies the most common root causes,
and provides remediation steps. It is intended to be scanned, bookmarked, and
pasted into tickets — not read end-to-end.

**Scope:** Windows 10 and Windows 11 endpoints (Autopilot, hybrid join, native
Entra join). Apple, Android, and Azure Arc-managed server enrollment failures
have different surfaces and are out of scope; they warrant separate cookbooks.

---

## 0. Triage — capture this on every ticket before diagnosing

Most failure modes diverge on a small number of state variables. Gathering
these once at the top of a ticket saves time and prevents misdiagnosis later.

**On the device, in an elevated PowerShell prompt:**

```powershell
dsregcmd /status
```

Capture the entire output. The key fields are `AzureAdJoined`, `DomainJoined`,
`WorkplaceJoined`, `EnterpriseJoined`, `MdmUrl`, `MdmTouUrl`,
`MdmComplianceUrl`, `AzureAdPrt`, `AzureAdPrtAuthority`, and `TpmProtected`.
The combination of these fields uniquely identifies most failure modes below.

**Capture MDM enrollment registry state:**

```powershell
Get-ChildItem 'HKLM:\SOFTWARE\Microsoft\Enrollments' |
    Where-Object { $_.Property -contains 'EnrollmentState' } |
    ForEach-Object { Get-ItemProperty $_.PSPath }
```

A fully enrolled device has at least one entry with `EnrollmentState = 1`,
`EnrollmentType = 6` (Mobile Device Management), and `ProviderID = MS DM Server`.
Partial or missing entries indicate enrollment did not complete.

**Bundle full MDM diagnostic logs (use for escalations):**

```powershell
MdmDiagnosticsTool.exe -area Autopilot;DeviceEnrollment;DeviceProvisioning;TPM -cab C:\Temp\MDMDiagReport.cab
```

This produces a CAB file with all relevant event logs, registry exports, and
Autopilot state files. Attach to escalations.

**In the Intune admin center** (`intune.microsoft.com`), find the device under
*Devices > All devices*. Capture: enrollment date, last check-in date, primary
user, compliance state, and any error codes on the overview blade.

**In the Microsoft Entra admin center** (`entra.microsoft.com`), find the
device under *Devices > All devices*. Capture: join type (Microsoft Entra
joined, hybrid joined, or registered), the associated user, and whether a
duplicate device object exists for the same serial or name.

With this state in hand, jump to the matching failure mode below.

---

## 1. Hybrid join did not complete

**Symptom.** `dsregcmd /status` shows `DomainJoined: YES` but
`AzureAdJoined: NO`. The device is on-premises domain-joined and should be
hybrid-joined, but the cloud half of the join never completed. Conditional
Access policies that require a hybrid-joined or compliant device will deny the
user access to cloud resources, even though the user can sign in to Windows
itself.

**Confirm.** Check the User Device Registration event log:

```powershell
Get-WinEvent -LogName 'Microsoft-Windows-User Device Registration/Admin' -MaxEvents 50 |
    Format-List TimeCreated, Id, LevelDisplayName, Message
```

Look for messages containing "Automatic registration failed" or "device join
failed." Absence of events entirely means the registration task never ran.

In the Entra admin center, search Devices for the computer name. No device
object means hybrid registration never reached the cloud directory. A device
object marked "Pending" means registration started but did not complete.

**Common root causes.**

*The on-premises computer object is not synchronized to Entra ID.* Hybrid join
requires the computer object to be present in the cloud directory before the
device-side handshake can complete. If Microsoft Entra Connect filters exclude
the computer's OU, or if synchronization is delayed, hybrid join fails with a
"device not found" condition. Verify the computer object appears under
*Devices > All devices* in Entra before troubleshooting further.

*The Service Connection Point is misconfigured or missing.* Hybrid join uses
an SCP in the on-premises directory to advertise the tenant identifier and
target join type. Confirm:

```powershell
$ctx = "CN=Configuration,$((Get-ADDomain).DistinguishedName)"
Get-ADObject -SearchBase $ctx -Filter "objectClass -eq 'serviceConnectionPoint'" -Properties keywords |
    Where-Object { $_.Name -eq '62a0ff2e-97b9-4513-bf6a-008b8dfc9b8c' } |
    Select-Object -ExpandProperty keywords
```

The `keywords` attribute should contain two strings: `azureADId:<tenant-guid>`
and `azureADName:<tenant-name>`. Wrong tenant GUID or missing keywords blocks
hybrid join globally.

*Network path to Entra registration endpoints is blocked.* Hybrid join
requires reachability to `enterpriseregistration.windows.net` and
`login.microsoftonline.com`. Corporate proxies, network segmentation, or
split-tunnel VPN configurations occasionally block one or both. Test:

```powershell
Test-NetConnection enterpriseregistration.windows.net -Port 443
Test-NetConnection login.microsoftonline.com -Port 443
```

*Time skew.* The device clock must be within five minutes of Entra ID for
certificate validation to succeed. Devices that have drifted (common after a
CMOS battery failure) will fail hybrid join even when everything else is
correct.

**Remediation.** After resolving the root cause, force a registration retry:

```powershell
dsregcmd /join
```

On Windows 10 builds before 1809, run the scheduled task directly:

```powershell
Start-ScheduledTask -TaskPath '\Microsoft\Windows\Workplace Join\' -TaskName 'Automatic-Device-Join'
```

Re-run `dsregcmd /status` and confirm `AzureAdJoined: YES`. If registration
still fails, attach the User Device Registration event log to escalation.

**Escalation criteria.** Escalate to identity engineering if the SCP is
missing or pointed at the wrong tenant, if Entra Connect sync is the blocker,
or if network reachability requires a firewall or proxy change.

---

## 2. Autopilot did not pick up the device at OOBE

**Symptom.** A newly-shipped Windows device boots into the consumer
out-of-box experience: no corporate branding, no organization name on the
sign-in page, no work-account sign-in prompt. The device was supposed to be
Autopilot-registered but is not behaving that way.

**Confirm.** At OOBE, press Shift+F10 to open a command prompt. Capture the
serial number:

```cmd
wmic bios get serialnumber
```

From another workstation, check whether that serial is registered to the
tenant. In the Intune admin center: *Devices > Enrollment > Windows enrollment
> Windows Autopilot devices*, filter by serial. Or via Microsoft Graph:

```
GET https://graph.microsoft.com/beta/deviceManagement/windowsAutopilotDeviceIdentities?$filter=serialNumber eq 'XXXXXXXX'
```

An empty result means the device is not registered. A registered result with
no `deploymentProfileAssignmentStatus` of `assignedInSync` means a profile is
not assigned.

**Common root causes.**

*The device is not registered to the tenant at all.* The vendor missed the
pre-registration step. This is a procurement contract failure — see the
procurement one-pager for prevention. Recovery requires capturing the
hardware hash manually and uploading it.

*The device is registered but no deployment profile is assigned.* Profile
assignment is a separate step from device registration, and resellers
sometimes do one but not the other. Assign the appropriate profile in the
admin center; reset the device (`systemreset.exe -factoryreset` from the
Shift+F10 prompt, or boot into recovery) to force Autopilot to re-attempt.

*The device boots on a network that cannot reach Autopilot endpoints.* OOBE
requires reachability to `ztd.dds.microsoft.com`, `cs.dds.microsoft.com`,
and `login.microsoftonline.com`. Guest Wi-Fi with captive portals, networks
behind restrictive firewalls, and some hotel/conference networks will fail.
Try a different network (mobile hotspot is fastest for diagnosis).

*Time skew.* If the device clock is wrong, certificate validation against
Autopilot endpoints will fail. Set the time manually in the OOBE command
prompt: `w32tm /resync` or set via the Settings clock.

**Remediation.** If the device is not registered, exit OOBE temporarily by
completing a local account setup (Shift+F10 at the OOBE sign-in,
`taskkill /im wwahost.exe /f`, then the OOBE will offer local setup). Once
on the desktop, register the device:

```powershell
Install-Script Get-WindowsAutopilotInfo -Force
Get-WindowsAutopilotInfo.ps1 -Online
```

Authenticate with credentials that have at least Intune Service Administrator
rights. The script captures the hash and registers the device. Then reset the
device (Settings > System > Recovery > Reset this PC, keep nothing) — the
next boot will go through Autopilot.

**Escalation criteria.** Escalate to procurement if a pattern of unregistered
devices appears from a specific vendor (this is a contract issue, not a
technical one).

---

## 3. Device stuck on the Enrollment Status Page

**Symptom.** The Enrollment Status Page (ESP) appears during Autopilot
provisioning, shows progress for some items, then either stalls indefinitely
on "Identifying" / "Setting up your device" / "Setting up your account," or
displays an error code such as `0x80180014`, `0x80070774`, `0x800705B4`, or
`0x8018002A`.

**Confirm.** On the device, after exiting ESP (either through a successful
completion, a "Continue anyway" if the ESP allows it, or by pressing
Shift+F10 and rebooting), inspect the Intune Management Extension log:

```powershell
Get-Content "$env:ProgramData\Microsoft\IntuneManagementExtension\Logs\IntuneManagementExtension.log" -Tail 200
```

And the AgentExecutor log:

```powershell
Get-Content "$env:ProgramData\Microsoft\IntuneManagementExtension\Logs\AgentExecutor.log" -Tail 200
```

And the device management diagnostics provider event log:

```powershell
Get-WinEvent -LogName 'Microsoft-Windows-DeviceManagement-Enterprise-Diagnostics-Provider/Admin' -MaxEvents 100
```

**Common root causes by error code.**

`0x80180014` — MDM enrollment failed because the user is not licensed for
Intune, or the user is outside the MDM user scope. Verify license assignment
and MDM scope under *Microsoft Entra admin center > Devices > Device settings*.

`0x80070774` — DNS resolution failed for an MDM endpoint. Network/DNS issue;
test `nslookup manage.microsoft.com` from the device.

`0x800705B4` — A required tracked application timed out. ESP waits for
"required" apps to install; if any required app takes longer than the ESP
timeout, ESP fails. Either reduce the required app set, increase the ESP
timeout, or fix the slow app.

`0x8018002A` — Autopilot device record was deleted from the tenant after
the device received its profile but before it could enroll. Re-register the
device or remove and recreate the Autopilot record.

`Identifying` stuck indefinitely — Autopilot service is contacting the
device but cannot confirm tenant assignment. Usually a network issue; check
reachability to `cs.dds.microsoft.com` and `ztd.dds.microsoft.com`.

*A required app deployment is hung.* The most common cause of "indefinite
hang" symptoms. ESP waits for required apps; an app that downloads slowly,
fails to install silently, or requires user interaction will block ESP.
Inspect the IntuneManagementExtension log for the app GUID that is stuck.

**Remediation.** For licensing or scope issues, fix in the admin portal and
reset the device. For required-app issues, remove the offending app from the
ESP "block until installed" list and reset. For timeout issues, increase the
ESP timeout under *Devices > Enrollment > Windows > Enrollment Status Page*.
For network issues, resolve connectivity and reset the device.

**Escalation criteria.** Escalate when the same ESP failure recurs across
multiple devices on the same Autopilot profile — that indicates a profile
configuration problem rather than a device-specific one.

---

## 4. Device joined to Entra ID but never enrolled in Intune

**Symptom.** `dsregcmd /status` shows `AzureAdJoined: YES` but `MdmUrl` is
blank and there is no entry under `HKLM:\SOFTWARE\Microsoft\Enrollments`. The
device appears in Entra under *Devices > All devices* but does not appear in
Intune under *Devices > All devices*.

**Confirm.** Verify MDM user and device scope in the Entra admin center:
*Microsoft Entra > Mobility (MDM and MAM) > Microsoft Intune*. Confirm the
user is in the MDM user scope (either "All" or a group the user is a member
of). Confirm automatic enrollment is enabled.

Check the device management event log:

```powershell
Get-WinEvent -LogName 'Microsoft-Windows-DeviceManagement-Enterprise-Diagnostics-Provider/Admin' -MaxEvents 50
```

**Common root causes.**

*User is outside the MDM scope.* Most common cause. The user signed in to a
device that joined Entra ID, but the user is not assigned to the MDM user
scope, so automatic enrollment never triggered. Fix by adding the user to the
MDM scope group.

*User does not have an Intune license.* MDM enrollment requires a license
that includes Intune (Microsoft 365 Business Premium, EMS, etc.). Assign the
license and reset enrollment.

*Automatic enrollment is disabled.* The MDM user scope is set to "None" or
the MDM application is disabled in the tenant.

*The device's TPM is unhealthy.* Intune enrollment requires a functional
TPM for device certificate issuance. Check:

```powershell
Get-Tpm
```

If `TpmReady: False` or `TpmPresent: False`, the device's TPM is the
blocker. May require BIOS/UEFI configuration change to enable.

**Remediation.** After fixing scope or licensing, trigger enrollment from
the device:

```powershell
Start-Process -FilePath "$env:WinDir\System32\DeviceEnroller.exe" -ArgumentList '/c /AutoEnrollMDM'
```

Or have the user sign out and sign back in — the next sign-in will trigger
automatic enrollment if scope is now correct. Confirm with `dsregcmd /status`
showing a populated `MdmUrl`.

**Escalation criteria.** Escalate to identity engineering if MDM scope or
licensing decisions exceed the helpdesk's authority.

---

## 5. Conditional Access blocking sign-in

**Symptom.** User receives a sign-in error such as "You can't get there from
here," "Your device does not meet your organization's requirements," or
"AADSTS50005" / "AADSTS530003" / "AADSTS530002" / "AADSTS53003." The device
appears healthy from a join perspective but cannot reach corporate resources.

**Confirm.** In the Entra admin center, navigate to *Monitoring > Sign-in
logs*, filter by the affected user, and find the failed sign-in. The sign-in
detail shows which Conditional Access policy applied and which condition
failed. Capture: policy name, failure reason, device ID, device platform,
and the user's IP address.

**Common root causes.**

*Device is not compliant but the CA policy requires compliance.* The device
exists in Intune but has a compliance state of "Not compliant" or "Not
evaluated." Move to failure mode 8.

*Device is not Entra-joined or hybrid-joined but the CA policy requires it.*
Verify with `dsregcmd /status`. The device may be Workplace-joined (BYOD
registration) rather than Entra-joined.

*User is outside a required group.* CA policies often require membership in
a specific security group; verify the user's group memberships.

*Sign-in is from a blocked location or platform.* Some CA policies block
sign-ins from outside named locations or from non-managed mobile platforms.
Check the sign-in log's IP and platform fields.

*Legacy authentication protocol.* CA policies routinely block legacy auth
(POP, IMAP, basic SMTP, EWS basic auth). The user's client may be falling
back to legacy auth without their knowledge. The sign-in log shows the
client app and protocol used.

**Remediation.** Depends on the root cause:

- For compliance failures, fix the underlying compliance issue (run a sync,
  remediate the failed setting).
- For join-type mismatches, complete the correct join type.
- For group memberships, add the user to the required group (and wait for
  token refresh — up to one hour, or force with `dsregcmd /refreshprt`).
- For location/platform blocks, the user must comply or request a
  documented exception.
- For legacy auth, fix the user's client configuration.

**Never disable a Conditional Access policy as a workaround.** Disabling CA
policies for individual troubleshooting tickets degrades the organization's
security posture. Use the named exception process if a genuine exception is
required.

**Escalation criteria.** Escalate to identity engineering if the CA policy
itself is the issue (over-broad scope, misconfigured condition), or if a
documented exception is being requested.

---

## 6. PRT is invalid or the user cannot acquire tokens

**Symptom.** User signs in to the device successfully but cloud applications
(Outlook, Teams, OneDrive) repeatedly prompt for credentials, fail to sync,
or fail with `AADSTS50196`, `AADSTS50173`, or "PrtFailed" errors. The user
can sometimes work around it by signing out and back in, but the issue
returns.

**Confirm.** On the device:

```powershell
dsregcmd /status
```

Look at the SSO State section. `AzureAdPrt: NO` or `AzureAdPrtUpdateTime`
significantly in the past indicates a stale or absent Primary Refresh Token.

Inspect the AAD operational log:

```powershell
Get-WinEvent -LogName 'Microsoft-Windows-AAD/Operational' -MaxEvents 50 |
    Format-List TimeCreated, Id, Message
```

Look for entries describing PRT acquisition failures.

**Common root causes.**

*Password recently changed and the device has not received the new
credential.* The PRT is bound to the user's credential at sign-in time. A
password change invalidates the PRT until the user signs in with the new
password on the device.

*Multi-factor authentication state has changed.* Adding or removing an MFA
method can invalidate the PRT.

*TPM issue.* The PRT is sealed to the device's TPM. TPM clearing, TPM
firmware update, or a broken TPM invalidates the PRT.

*User signed in with a different account.* If a different user signed in
on a single-user device and then signed out, the original user's PRT may be
stale until they sign in again.

**Remediation.** First, attempt a PRT refresh from the user's session:

```powershell
dsregcmd /refreshprt
```

If that fails, have the user lock the screen (Win+L) and sign back in with
their password. This forces a fresh credential exchange and a new PRT.

For TPM issues, run `Get-Tpm` and check the TPM is ready. If the TPM was
recently cleared, the device may need to be re-enrolled.

**Escalation criteria.** Escalate if PRT failures recur across multiple
users on the same device (suggests TPM or hardware issue) or across the
same user on multiple devices (suggests an account-level issue).

---

## 7. Duplicate device object in Entra ID

**Symptom.** A single physical device appears as two (or more) device
objects in the Entra admin center, sometimes one marked as "stale" and one
as "current," or both showing the same serial number. Compliance state and
Conditional Access decisions become inconsistent because policies may
evaluate against the stale object.

**Confirm.** In Entra admin center, search Devices by serial number or
device name. Two records with the same serial and different `Object IDs`
are duplicates. Check the "Registered" date on each — the older one is
typically stale.

Verify on the device which object is "current":

```powershell
dsregcmd /status
```

The `DeviceId` field shows the GUID the device believes is its own. That
GUID should match exactly one of the Entra device objects.

**Common root causes.**

*Device was reset and re-enrolled without removing the old object.* Reset
creates a new device record; if the old one is not deleted, both exist.

*Device was migrated between tenants or domains.* The device may have a
record from a previous tenant that was not properly removed.

*Hybrid-to-cloud migration left a stale hybrid object.* When a hybrid-joined
device is converted to Entra-joined, the hybrid device object can linger.

*Two users signed in to the same device with different work accounts.* In
some configurations, this creates two device objects with the same hardware
serial.

**Remediation.** Identify the active object (the one matching the device's
`DeviceId` from `dsregcmd /status`). Delete the stale object(s) from the
Entra admin center. If the device also appears duplicated in Intune, delete
the stale Intune record as well.

Be careful: deleting the *active* object will cause the device to fall out
of compliance and lose its PRT. Always confirm the active `DeviceId` first.

**Escalation criteria.** Escalate if duplicates are accumulating at scale —
that indicates a process problem (resets without retirement, migration
without cleanup) rather than individual device issues.

---

## 8. Compliance state stuck at "Not evaluated" or persistently "Not compliant"

**Symptom.** Device appears in Intune but its compliance state is "Not
evaluated" indefinitely, or it is "Not compliant" but the user/admin
believes it should be compliant. Conditional Access policies that require
compliance will deny access.

**Confirm.** In the Intune admin center, locate the device and click into
the compliance blade. Identify which specific compliance policy is failing
and which setting within that policy is the failing one.

Force a sync from the device:

```powershell
$session = New-CimSession
$omaUri = "./Vendor/MSFT/DMClient/Provider/MS DM Server/SyncML/ServerWins"
# Or trigger from Settings > Accounts > Access work or school > [account] > Info > Sync
```

Or simpler — open *Settings > Accounts > Access work or school*, select the
work account, click *Info*, scroll down, and click *Sync*. This triggers an
immediate Intune check-in.

**Common root causes.**

*The device hasn't checked in recently.* Compliance evaluation requires a
check-in. Devices that have been offline, asleep, or on flaky networks may
have a stale state. Force a sync.

*A compliance policy targets a setting the device does not report.* Some
compliance settings rely on signals the device may not be sending
(Defender for Endpoint risk score, Microsoft Defender Antivirus signature
age). Verify the underlying signal is flowing.

*The compliance policy itself has a misconfigured threshold.* For example,
a policy requiring minimum OS build that is higher than any released build.
Verify the policy by reviewing recent changes.

*Grace period expired but should not have.* If a compliance policy applies
a grace period and the device was non-compliant at the end of the period,
the device is marked non-compliant until it actively becomes compliant
again.

**Remediation.** Trigger a sync from the device (as above), wait 10-15
minutes, and re-check. If the state does not update, restart the Intune
Management Extension service:

```powershell
Restart-Service -Name 'IntuneManagementExtension' -Force
```

For specific failing settings, address the underlying issue (enable
BitLocker, update Windows, install missing app, etc.) and re-sync.

**Escalation criteria.** Escalate if a compliance policy is misconfigured
or if a setting the policy depends on is not being reported by devices
broadly.

---

## 9. Device joined to a personal Microsoft Account instead of work tenant

**Symptom.** During OOBE, the user signed in with a personal Microsoft
Account (`@outlook.com`, `@hotmail.com`, `@live.com`, etc.) rather than
their work account. The device is `WorkplaceJoined: YES` but `AzureAdJoined:
NO`, and it shows up nowhere in the corporate Entra tenant.

**Confirm.**

```powershell
dsregcmd /status
```

`DeviceState` section shows `AzureAdJoined: NO`. `User State` section shows
the signed-in account as a personal account rather than a corporate UPN.

In the Entra admin center, the device does not appear in the corporate
tenant's *Devices > All devices*.

**Common root causes.**

*Autopilot did not run.* See failure mode 2.

*User clicked "I don't have an account" or "Set up for personal use" at
OOBE.* This is a user-driven path that bypasses the corporate join.

*Device was set up before Autopilot registration completed in the tenant.*
The device shipped before its hardware hash propagated to Autopilot, so OOBE
defaulted to consumer behavior.

**Remediation.** There is no in-place migration from personal-account
Windows to corporate Entra-joined Windows. Reset the device:

```powershell
systemreset.exe -factoryreset
```

Or *Settings > System > Recovery > Reset this PC*. Choose "Remove
everything." Before the reset, confirm the device is now registered in
Autopilot (use failure mode 2's verification steps). After the reset, the
device will run OOBE again and should pick up Autopilot correctly.

**Escalation criteria.** Escalate if a pattern of personal-account
provisioning is emerging — that suggests an Autopilot registration gap or
user-education issue at scale.

---

## 10. ESP succeeded but policies/apps are not applying

**Symptom.** ESP completed and the user reached the desktop, but expected
Intune policies are not visible (no BitLocker, missing required apps, no
configured Wi-Fi profile, etc.). The device shows as enrolled in Intune but
nothing seems to actually be configured.

**Confirm.** In Intune admin center, locate the device. Under *Device
configuration*, check the per-policy status — is each policy listed as
"Succeeded," "Pending," "Error," or "Conflict"?

On the device, check the IME log for app and policy delivery:

```powershell
Get-Content "$env:ProgramData\Microsoft\IntuneManagementExtension\Logs\IntuneManagementExtension.log" -Tail 500 |
    Select-String -Pattern 'error|fail|exception'
```

**Common root causes.**

*The device is in the wrong group.* Policies are assigned to groups. If
the device is not a member of the targeted group (or has not yet been
synced into Entra after group assignment), policies will not apply.

*Policies conflict.* When two policies target the same setting with
different values, the conflict resolution may result in neither applying.
Intune flags this as "Conflict."

*App requirements not met.* A Win32 app with detection rules pointing at a
specific file path or registry key may report "Not applicable" if the
detection rule is wrong, even though the app should install.

*Sync has not happened yet.* Newly-assigned policies require a sync to
deliver. Initial sync after enrollment can take up to 8 hours; force it
from *Settings > Accounts > Access work or school > [account] > Info > Sync*.

**Remediation.** Trigger a sync. Wait 15 minutes. Re-check status. If a
specific policy reports an error, click into the per-setting status in
Intune to see which setting is failing. For Win32 apps, inspect the
detection rule and the AgentExecutor log.

For conflicts, identify the conflicting policies in Intune (the
per-setting status shows both) and resolve by removing one or changing
the targeted scope.

**Escalation criteria.** Escalate if conflicts are appearing systemically
across many devices, or if a specific policy has an Intune-side error that
the admin cannot resolve.

---

## Reference: Where to look on the device

| What you want | Where to look |
|---|---|
| Overall join + MDM state | `dsregcmd /status` |
| MDM enrollment registry | `HKLM:\SOFTWARE\Microsoft\Enrollments\` (GUID-named subkeys) |
| Entra registration events | Event log `Microsoft-Windows-AAD/Operational` |
| User device registration events | Event log `Microsoft-Windows-User Device Registration/Admin` |
| MDM enrollment events | Event log `Microsoft-Windows-DeviceManagement-Enterprise-Diagnostics-Provider/Admin` |
| Modern deployment / Autopilot events | Event log `Microsoft-Windows-ModernDeployment-Diagnostics-Provider/Autopilot` |
| Intune Management Extension app delivery | `$env:ProgramData\Microsoft\IntuneManagementExtension\Logs\IntuneManagementExtension.log` |
| Win32 app installation detail | `$env:ProgramData\Microsoft\IntuneManagementExtension\Logs\AgentExecutor.log` |
| Autopilot policy and ESP state | `$env:Windir\Provisioning\Autopilot\` |
| TPM health | `Get-Tpm` |
| Diagnostic bundle for escalation | `MdmDiagnosticsTool.exe -area Autopilot;DeviceEnrollment;DeviceProvisioning;TPM -cab <path>` |

## Reference: Where to look in the cloud

| What you want | Where to look |
|---|---|
| Device join type and ownership | Entra admin center > Devices > All devices |
| Device compliance state | Intune admin center > Devices > [device] > Compliance |
| Per-policy / per-setting result | Intune admin center > Devices > [device] > Device configuration |
| Per-app installation status | Intune admin center > Devices > [device] > Managed apps |
| Conditional Access evaluation | Entra admin center > Monitoring > Sign-in logs > [sign-in] > Conditional Access |
| Autopilot device registration | Intune admin center > Devices > Enrollment > Windows enrollment > Windows Autopilot devices |
| MDM user/device scope | Entra admin center > Mobility (MDM and MAM) > Microsoft Intune |
| Device sign-in activity | Entra admin center > Monitoring > Sign-in logs (filter by Device) |

## Reference: Microsoft Graph quick queries

```
# Autopilot device record by serial
GET https://graph.microsoft.com/beta/deviceManagement/windowsAutopilotDeviceIdentities?$filter=serialNumber eq 'XXXXXXXX'

# Managed device record by device name
GET https://graph.microsoft.com/v1.0/deviceManagement/managedDevices?$filter=deviceName eq 'XXXXX'

# Entra device record by display name
GET https://graph.microsoft.com/v1.0/devices?$filter=displayName eq 'XXXXX'

# Recent sign-ins for a user
GET https://graph.microsoft.com/v1.0/auditLogs/signIns?$filter=userPrincipalName eq 'user@domain.com'&$top=20&$orderby=createdDateTime desc
```

## Authoritative sources

The behaviors and commands above are documented by Microsoft at the
following landing pages. Specific deep links are reorganized regularly;
landing pages are more stable.

- Troubleshoot Microsoft Entra joined devices, Microsoft Learn. https://learn.microsoft.com/en-us/entra/identity/devices/troubleshoot-device-dsregcmd
- Troubleshoot Windows Autopilot, Microsoft Learn. https://learn.microsoft.com/en-us/autopilot/troubleshooting
- Troubleshoot MDM enrollment errors, Microsoft Learn. https://learn.microsoft.com/en-us/mem/intune/enrollment/troubleshoot-windows-enrollment-errors
- Collect diagnostics from Windows devices in Intune, Microsoft Learn. https://learn.microsoft.com/en-us/mem/intune/remote-actions/collect-diagnostics
- Conditional Access sign-in failure reasons (AADSTS codes), Microsoft Learn. https://learn.microsoft.com/en-us/entra/identity-platform/reference-error-codes

*Verify URLs before distribution. Microsoft documentation is reorganized
regularly, and stable-looking links occasionally redirect.*
