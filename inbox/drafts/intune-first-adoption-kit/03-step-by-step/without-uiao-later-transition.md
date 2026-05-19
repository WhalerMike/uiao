# Phase III — Later Transition: Step-by-Step Laptop Onboarding (Without UIAO)

## Audience and purpose

This guide is for new IT staff learning the hybrid laptop onboarding process — the phase characterized by Hybrid Microsoft Entra Join and Microsoft Intune co-management with Microsoft Configuration Manager. Devices in this phase carry two identities (on-premises Active Directory computer object and Microsoft Entra ID device object) and are governed by two management planes (Configuration Manager for legacy workloads, Microsoft Intune for cloud-aware workloads), with the partition controlled by configurable workload sliders. The provisioning workflow extends the Phase II workflow with additional steps for hybrid join verification, Microsoft Intune enrollment, and dual-plane configuration verification.

The phase architecture is described in [`01-customer-narrative/without-uiao-later-transition.md`](../01-customer-narrative/without-uiao-later-transition.md).

## Quick reference

| Question | Answer |
|---|---|
| Is PXE boot used? | **Yes** — for the traditional hybrid path. Devices are imaged the same way as Phase I and II. |
| Is imaging used? | **Yes** — same reference image with updated baseline to include hybrid-join GPO and MDM enrollment GPO. |
| Is Windows Autopilot used? | **Sometimes** — for pilot greenfield cohorts that hybrid-join via Autopilot rather than via PXE imaging. The traditional path remains the predominant one for the existing-device population. |
| Is a barcode scanner used? | **Yes** — same as Phase I and II. Additionally, for Autopilot pilots, the hardware hash is captured (typically via the vendor pre-registration rather than at the imaging station). |
| Is the laptop joined to a domain? | **Yes** — on-premises Active Directory, with additional hybrid registration to Microsoft Entra ID. |
| Does the device have a cloud identity? | **Yes** — a Microsoft Entra ID device object is created via hybrid registration. |
| Does the device enroll in Microsoft Intune? | **Yes** — automatic MDM enrollment is triggered after hybrid join completes. |
| How long does provisioning take? | 3 to 4 hours elapsed (longer than Phase I/II because of additional hybrid join verification, Intune enrollment, and Intune policy application). |
| Network used | Wired Ethernet for imaging; Wi-Fi after. |

## Software inventory at provisioning completion

The Phase III provisioned device has the Phase I/II software set plus:

- Microsoft Intune Management Extension (the IME service that handles Win32 apps and PowerShell scripts delivered from Intune)
- Hybrid-join machinery (registered through the "Automatic-Device-Join" scheduled task)
- Microsoft Entra ID device certificate (the device's identity proof against the cloud directory)
- Intune compliance policy evaluation engine (built into the Windows MDM stack)
- Microsoft Defender for Endpoint client (typically deployed during this phase as part of the modern security stack)
- Additional applications delivered through Intune Win32 apps (alongside the legacy ConfigMgr-delivered set)

## Pre-arrival activities

The Phase I and II pre-arrival activities apply (procurement, vendor preparation, asset tags, reference image, task sequences). Additional Phase III preparation includes:

**Hybrid join configuration verification**: The identity team confirms that Microsoft Entra Connect is synchronizing the organizational unit where new computers will be placed, that the Service Connection Point in the on-premises directory is configured for the correct Microsoft Entra tenant, and that the "Automatic-Device-Join" scheduled task is in place via Group Policy.

**Microsoft Intune tenant readiness**: The endpoint management team confirms that MDM scope is set to "All users" (or the appropriate scope group), that automatic enrollment is enabled, that the Intune licensing is in place for the user population, and that the relevant Microsoft Intune configuration profiles, security baselines, compliance policies, and applications are published.

**Co-management workload sliders**: The endpoint management team configures the workload sliders in Configuration Manager according to the current canonical assignment. Compliance Policies is typically the first slider moved to Intune (so that Conditional Access can evaluate device compliance); other workloads (Resource Access Policies, Device Configuration, Windows Update, Endpoint Protection, Client Apps) may remain on Configuration Manager or pilot to Intune depending on migration plan.

**Cloud identity preparation**: As in Phase II, the user's cloud identity is prepared (license assignment, mailbox, MFA enrollment, group memberships) before the device is handed off.

## Step 1 through Step 5: Device receipt through PXE task sequence start

Identical to Phase I Legacy. Receive, BIOS verify, network connect, PXE boot, task sequence wizard.

## Step 6: Task sequence execution (with Phase III additions)

The task sequence runs the Phase I steps (format, image apply, drivers, mini-setup, domain join, ConfigMgr client, applications, Group Policy, BitLocker) plus the additional Phase III steps:

1. **Hybrid join scheduled task trigger**: After domain join completes, Group Policy delivers the "Automatic-Device-Join" scheduled task configuration. The task runs at user logon or at the next scheduled trigger.

2. **Microsoft Entra ID device registration**: The scheduled task contacts Microsoft Entra ID at `enterpriseregistration.windows.net`, presents the device's machine credential, and registers the device. A Microsoft Entra ID device object is created, linked to the on-premises computer object.

3. **Microsoft Entra Connect synchronization** (server-side, not on the device): Within 30 minutes of the on-premises computer object's existence, Entra Connect synchronizes it to the cloud directory. The hybrid registration handshake completes only when the cloud directory has the synchronized computer object record to match against.

4. **Automatic MDM enrollment**: Group Policy delivers the "Enable automatic MDM enrollment" policy. The device's MDM enrollment subsystem contacts Microsoft Intune, presents proof of the hybrid join, and enrolls. An entry appears in `HKLM\SOFTWARE\Microsoft\Enrollments\` with a GUID key, the Microsoft Intune service URL, and the `EnrollmentState = 1` flag.

5. **Intune configuration profile delivery**: With enrollment complete, the device polls Intune for assigned configuration profiles. Profiles assigned to the user (and to device groups containing the device) deliver and apply.

6. **Intune compliance policy evaluation**: The compliance policy evaluates the device's posture (BitLocker enabled, OS version current, security signatures current, etc.) and reports the compliance state to Intune. The result flows to Conditional Access on the next sign-in evaluation.

7. **Microsoft Defender for Endpoint enrollment**: If the device receives a Defender for Endpoint configuration profile, the agent activates and the device joins the Defender for Endpoint tenant. Threat and vulnerability management data begins flowing.

8. **Intune Win32 app delivery**: Required Win32 apps assigned through Intune begin downloading and installing through the Intune Management Extension. This is a parallel application delivery channel to ConfigMgr's application delivery.

Time for the additional Phase III steps: 30 to 60 minutes beyond the Phase I task sequence completion.

## Step 7: Post-imaging verification (with Phase III additions)

The Phase I verification (domain join, ConfigMgr client, applications, BitLocker, Group Policy) applies. Additional verification:

1. **Hybrid join state**: Run `dsregcmd /status`. Confirm `AzureAdJoined: YES` and `DomainJoined: YES`. Both must be YES for the device to be considered hybrid-joined.

2. **MDM URL populated**: Confirm `MdmUrl` shows the Microsoft Intune service URL (`https://manage.microsoft.com/EnrollmentServer/Discovery.svc`).

3. **MDM enrollment registry**: Confirm `HKLM\SOFTWARE\Microsoft\Enrollments\` contains a GUID subkey with `EnrollmentState = 1` and `ProviderID = MS DM Server`.

4. **Microsoft Entra ID device object**: In the Microsoft Entra admin center, search for the device by name and confirm the device object exists with join type "Microsoft Entra hybrid joined."

5. **Microsoft Intune managed device record**: In the Microsoft Intune admin center, search for the device by name and confirm the managed device record exists with the expected primary user, OS version, and compliance state.

6. **Configuration profile application state**: In the Intune admin center, click into the device, then *Device configuration*, and verify each assigned profile is in "Succeeded" state.

7. **Compliance state**: In the Intune admin center, confirm the device's compliance state is "Compliant" (after the first evaluation cycle, which can take up to 30 minutes after enrollment).

8. **Microsoft Defender for Endpoint onboarding**: If Defender for Endpoint is in scope, confirm the device appears in the Microsoft Defender XDR portal under Devices.

A device that has completed the Phase I verifications but failed any of the Phase III additions is not ready for handoff. Common gaps include silent hybrid join failure (Step 1 — `AzureAdJoined: NO`), missing MDM enrollment (Step 3 — no registry entry), and stuck compliance evaluation (Step 7 — compliance shows "Not evaluated" indefinitely).

## Step 8: Asset record update and user assignment

Same as Phase II. The asset database is updated with the assigned user, device name, and deployment date.

## Step 9: Pre-handoff cloud identity verification

Same as Phase II. The technician verifies the user's cloud identity (mailbox, license, MFA, group memberships, Conditional Access scope).

Additional verification specific to Phase III:

- **Device-compliance Conditional Access policy applies**: Verify that the user, when signing in from this device, would pass any Conditional Access policy requiring device compliance. The Conditional Access "What If" tool in the Microsoft Entra admin center supports this verification.

- **Group memberships for the device**: Confirm the device is in any required Microsoft Entra security groups (typically derived from device naming convention or from dynamic membership rules over device attributes).

## Step 10: User handoff

Repack with accessories and welcome packet. Hand off in person or ship.

The welcome packet for Phase III references the additional cloud capabilities now available (device-aware Conditional Access, Microsoft Defender for Endpoint protection, Intune-delivered applications via the Company Portal app).

## Step 11: User first sign-in

The user signs in to Windows with their domain credentials, then opens Microsoft 365 clients. The cloud sign-in flow is the same as Phase II — modern authentication, MFA challenge, OAuth token issuance — with one significant addition: Conditional Access evaluates the device-aware conditions. The user's sign-in is granted because the device is hybrid-joined and Intune-compliant; users on a non-compliant or non-hybrid-joined device would be denied.

If the user encounters a Conditional Access denial on first sign-in, the diagnosis path begins with the Microsoft Entra sign-in log, which shows which policy and condition matched. Common Phase III-specific causes include device compliance still in "Not evaluated" state (the first evaluation has not completed; the user can typically wait 30 minutes and retry) and silent hybrid join failure that was not caught during verification (Step 7 was missed or misread).

## Tools and equipment required

The Phase I tools (imaging server, distribution points, PXE network, barcode scanner) apply. Additional Phase III tools:

- Access to the Microsoft Intune admin center for post-imaging device verification
- Access to the Microsoft Entra admin center for device object verification
- Access to Microsoft Defender XDR portal for Defender onboarding verification (if Defender for Endpoint is in scope)
- The MDM Diagnostic Tool (`MdmDiagnosticsTool.exe`) for collecting MDM diagnostic logs when enrollment issues arise

## Common failures during provisioning

The Phase I failures (PXE failure, driver mismatch, domain join failure, application failure, BitLocker failure) and Phase II failures (cloud sign-in issues, MFA enrollment issues, license missing) all apply.

**Phase III-specific failure modes**:

**Silent hybrid join failure**: After the task sequence completes, `dsregcmd /status` shows `DomainJoined: YES` but `AzureAdJoined: NO`. The Microsoft Entra ID device object never appears. The user, on first sign-in, is denied access to compliance-protected resources by Conditional Access. The cause is one of: Entra Connect synchronization has not yet propagated the new computer object to the cloud directory (resolution: wait 30 minutes and retry); the Service Connection Point is misconfigured (resolution: verify keywords attribute on the SCP); time skew exceeds 5 minutes (resolution: correct device clock); network path to `enterpriseregistration.windows.net` is blocked (resolution: investigate proxy or firewall).

**Failed MDM enrollment**: `dsregcmd /status` shows `AzureAdJoined: YES` but `MdmUrl` is blank. The device is hybrid-joined but not Intune-enrolled. Cause is typically a missing MDM enrollment GPO, a user outside the MDM scope, or a missing Microsoft Intune license for the user. Resolution: verify GPO, MDM scope, and licensing.

**Compliance state stuck at "Not evaluated"**: The device is hybrid-joined and Intune-enrolled, but the compliance evaluation has not completed. Resolution: force an Intune sync from the device (Settings > Accounts > Access work or school > Sync), then wait 15 minutes for evaluation.

**Conflicting GPO and Intune policy**: A setting expressed by both Group Policy and Intune produces unexpected behavior. Diagnosis requires inspecting both `gpresult` output and the Intune device configuration application state. Resolution depends on which provider should be authoritative for that setting per the current co-management workload assignment.

**Duplicate device objects**: A previously-decommissioned device's Microsoft Entra ID object persists, and the new device's hybrid join creates a second object with the same display name or serial. Resolution: identify and retire the stale object before or shortly after the new device's hybrid registration.

## Total time and resource cost per device

Imaging time per device: 3 to 4 hours elapsed (longer than Phase I/II by 30 to 60 minutes for the additional hybrid join, Intune enrollment, and Intune policy application steps).

Hands-on technician time: 45 to 60 minutes per device (longer than Phase I/II by 15 minutes for the additional verifications).

For an organization deploying 100 devices per week, the additional Phase III steps add roughly 15 to 25 staff-hours per week compared to Phase I/II, plus the ongoing operational cost of maintaining both Configuration Manager and Microsoft Intune as parallel management planes.
