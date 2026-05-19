# Phase IV — Full Transition: Step-by-Step Laptop Onboarding (Without UIAO)

## Audience and purpose

This guide is for new IT staff learning the cloud-native laptop onboarding process — the phase in which net-new devices are provisioned directly to Microsoft Entra ID and Microsoft Intune via Windows Autopilot, with no on-premises Active Directory relationship. The workflow is fundamentally different from Phases I, II, and III: there is no PXE boot, no imaging, no Configuration Manager task sequence, and no IT staging area in the traditional sense. Devices are pre-registered to the tenant at the vendor (or, in some cases, at IT receiving as a fallback), then shipped directly to the end user. The user unboxes the device, powers it on, signs in with their cloud credentials, and the device provisions itself through Windows Autopilot in a process that typically takes 15 to 60 minutes from first boot to ready-to-work.

The phase architecture is described in [`01-customer-narrative/without-uiao-full-transition.md`](../01-customer-narrative/without-uiao-full-transition.md).

## Quick reference

| Question | Answer |
|---|---|
| Is PXE boot used? | **No** — Autopilot replaces PXE entirely. Devices boot from their factory-installed Windows and contact the Autopilot service over the internet. |
| Is imaging used? | **No** — the OEM-installed Windows is the baseline; corporate customization layers on top via Microsoft Intune policy after provisioning. |
| Is Windows Autopilot used? | **Yes** — Autopilot is the cloud-native provisioning service that orchestrates the experience. |
| Is a barcode scanner used? | **Not typically by the user; possibly by IT at vendor receiving for asset tagging when devices flow through IT receiving as a fallback.** Asset tags may be pre-applied by the vendor as part of an asset-tagging-at-source service. The hardware hash (the key identifier for Autopilot) is captured by the vendor at order fulfillment and registered to the tenant; the scanner is not needed at user unboxing. |
| Does the device join Active Directory? | **No** — pure Microsoft Entra Join only. |
| Does the device have a cloud identity? | **Yes** — a Microsoft Entra ID device object is created at first sign-in; there is no on-premises computer object. |
| Does the device enroll in Microsoft Intune? | **Yes** — automatic MDM enrollment is part of the Autopilot user-driven experience. |
| Where does the device ship? | **Directly to the end user** (home address or office) in most configurations. The traditional IT receiving area is bypassed. |
| Who touches the device before the user? | **No one** — the vendor ships sealed, the carrier delivers to the user, the user unboxes. |
| How long does provisioning take? | 15 to 60 minutes elapsed from first power-on to ready-to-work desktop, depending on the assigned configuration profile and application set. |

## Software inventory at provisioning completion

A Phase IV provisioned device has:

- Windows 11 Enterprise or Pro (whatever the OEM ships, typically pre-licensed and pre-activated)
- Microsoft Entra ID device certificate (created at the cloud join)
- Primary Refresh Token bound to the device's TPM
- Microsoft Intune Management Extension (the IME service for Win32 apps and PowerShell scripts)
- Configuration profiles applied (security baseline, BitLocker, Windows Hello for Business, Wi-Fi profile, VPN profile if applicable, certificate profile if SCEP/PKCS profiles are in use)
- Compliance policy evaluation engine active (continuous evaluation of the device's posture)
- Microsoft 365 Apps for Enterprise (delivered through Intune)
- Microsoft Edge (typically already present from the OEM image)
- Microsoft Defender Antivirus (active; signatures current from Windows Update)
- Microsoft Defender for Endpoint (onboarded via Intune)
- Required Win32 apps from the Intune Win32 app catalog
- Microsoft Teams (delivered as part of Microsoft 365 Apps or as a standalone Win32 app)
- Corporate VPN client if applicable (delivered as a Win32 app)
- Any role-specific applications assigned via Intune

Notably absent from a Phase IV device: Configuration Manager client, on-premises Active Directory machine certificate, Group Policy applied (because there is no Active Directory), corporate imaging artifacts.

## Pre-arrival activities

Pre-arrival in Phase IV is fundamentally different from earlier phases because the device is pre-registered at the vendor rather than imaged at IT receiving.

**Procurement with Autopilot registration clause**: The purchase order includes the clause requiring the vendor to register the device hardware hash into the organization's Microsoft Entra tenant before shipment (see [`02-coworker-artifacts/procurement-one-pager.md`](../02-coworker-artifacts/procurement-one-pager.md) for the contract language). The PO specifies the deployment profile to be assigned to the device.

**Vendor pre-registration**: The vendor (or the reseller acting on the vendor's behalf) captures the device's hardware hash during order fulfillment. The hash is uploaded to the organization's Microsoft Entra tenant via the Cloud Solution Provider API. The Autopilot deployment profile is assigned to the device record. The vendor confirms registration to the buyer (via the procurement contact) before shipment.

**Verification of pre-registration**: Before the device ships, an IT staff member (typically in procurement or asset management) verifies the registration in the Microsoft Intune admin center under *Devices > Enrollment > Windows enrollment > Windows Autopilot devices*. The device should appear with its serial number, hardware hash, and assigned deployment profile. If verification fails (the device is not present, or has the wrong profile assigned), the gap is resolved with the vendor before the device ships.

**Cloud identity preparation**: As in Phases II and III, the user's cloud identity is prepared in advance (license assignment, mailbox, MFA enrollment, group memberships). The cloud identity work is identical across Phases II, III, and IV; the difference in Phase IV is that the device identity work is also cloud-resident.

**Configuration profile authoring**: The endpoint management team has authored the deployment profile that will be assigned (user-driven Microsoft Entra Join, with appropriate Enrollment Status Page configuration), the configuration profiles for security baseline, BitLocker, Wi-Fi, etc., the compliance policy, the required Win32 apps, and the optional Win32 apps available through the Company Portal.

## Step 1: Device receives at user

The carrier delivers the sealed retail box directly to the end user. The user's role in Phase IV provisioning begins here — there is no IT receiving step in the traditional sense for the predominant Phase IV configuration.

Some organizations elect to route devices through IT receiving for asset tagging (the corporate asset tag is applied at IT receiving before forwarding to the user) or for compliance reasons (verification of the device's physical state before shipment to the user). The choice is operational rather than architectural — Phase IV supports both paths, with vendor-direct shipment being the most cost-effective.

When devices are routed through IT receiving:

1. The receiving technician verifies the shipment against the PO.
2. The technician opens the outer box and inspects for damage.
3. The technician scans the serial number to confirm the device matches the expected user assignment in the asset database.
4. The technician applies the corporate asset tag and scans it to link to the serial number.
5. The technician repacks the device with its accessories and the welcome packet, and ships it to the user.

The technician does NOT power on the device, does NOT image it, does NOT touch the firmware, does NOT install software. The device's first power-on is by the user.

## Step 2: User unboxes the device

The user receives the sealed retail box at their home or office address. The welcome packet (either shipped separately or included in the IT-receiving repack) instructs the user on the first-power-on process.

Typical contents of the welcome packet for Phase IV:

- A welcome letter explaining the cloud-native provisioning process
- The user's sign-in identity (UPN) — for reference; the user already knows it
- A reminder that the device will need internet connectivity for first boot (Wi-Fi or Ethernet)
- Instructions for the first sign-in: power on, select language and keyboard, connect to a network, sign in with the corporate UPN
- The expected time for first-boot provisioning (15 to 60 minutes; the user is asked to plug in the power supply and not interrupt the process)
- Helpdesk contact information for any issues

The user opens the box, removes the laptop and accessories (power supply, cables), and proceeds to first boot.

## Step 3: First power-on and initial setup screens

The user plugs in the power supply (recommended to avoid battery drain during provisioning) and powers on the laptop.

1. The Windows out-of-box experience starts. The user selects their region and keyboard layout.
2. The setup screen asks the user to connect to a network. The user connects to a network using Wi-Fi (selecting the network and entering the password) or by plugging in an Ethernet cable (typically via a USB-C-to-Ethernet adapter if the laptop has no built-in RJ-45 port).
3. Once the network is connected, Windows reaches out to Microsoft's services. The device contacts the Autopilot service at `ztd.dds.microsoft.com` to check for an assigned deployment profile.

## Step 4: Autopilot detects pre-registration

1. The Autopilot service receives the device's hardware hash, looks it up in the cloud-resident Autopilot database, and finds the registration created during pre-arrival.
2. The deployment profile assigned to the device is retrieved. The profile specifies the join type (Microsoft Entra Join), the user-experience mode (user-driven), the user name handling (typically hidden during sign-in for a cleaner experience), the Enrollment Status Page configuration, and the device naming template.
3. The out-of-box experience switches from the consumer-oriented setup to the corporate-branded experience. The corporate logo appears, the corporate sign-in page replaces the personal-account sign-in, and the user is prompted to sign in with their work credentials.

This transition is the user's visible signal that Autopilot has detected the pre-registration. If the transition does not occur — the user continues to see the personal-Microsoft-Account setup — the device is not registered, or the network connection has not allowed Autopilot to reach its endpoints.

## Step 5: User signs in to Microsoft Entra ID

1. The user enters their UPN. The sign-in page redirects to the organization's sign-in branding (the corporate logo, sign-in image, and welcome text appear).
2. The user enters their password. Microsoft Entra ID validates the password (through password hash synchronization or pass-through authentication, depending on the tenant configuration).
3. Conditional Access evaluates the sign-in. Multi-factor authentication is challenged if the policy requires it. The user provides the MFA factor (Microsoft Authenticator push, FIDO2 security key, etc.).
4. Microsoft Entra ID issues an identity token. The device, which until this moment is a generic Windows machine, joins Microsoft Entra ID natively. A device object is created in the cloud directory, with the user identified as the primary user.
5. The device receives a device registration certificate from Microsoft Entra ID. A Primary Refresh Token is issued, sealed to the device's TPM, and stored for future cloud authentication.

This step takes 1 to 3 minutes depending on network speed, MFA factor selection, and the user's familiarity with the process. The user is then prompted to wait while the device provisions.

## Step 6: Enrollment Status Page

The Enrollment Status Page (ESP) is a Windows-resident status display that runs during Autopilot to track the application of configuration policies, security baselines, and required applications. ESP has three phases: device preparation, device setup, and account setup. Each phase runs sequentially, with the user blocked at the ESP until the configured policies and applications complete.

**Device preparation phase**: Microsoft Entra Join, MDM enrollment, and the initial Intune configuration profile delivery. The device polls Intune for its assigned profiles and applies them. Typical duration: 2 to 5 minutes.

**Device setup phase**: Required Win32 applications, Microsoft 365 Apps for Enterprise, security baselines, compliance policy evaluation, certificate profile delivery (if SCEP/PKCS is in use), Wi-Fi profile delivery (for future network changes), VPN profile delivery (if applicable). Typical duration: 10 to 40 minutes depending on the application set.

**Account setup phase**: User-specific configuration profiles and applications. Typical duration: 2 to 10 minutes.

If the ESP "Block device use until all apps and profiles are installed" option is enabled (and it usually is), the user cannot use the device until ESP completes. The user is asked to wait, with progress visible on screen.

## Step 7: ESP completes and the user reaches the desktop

When ESP completes successfully, the user transitions from the status page to the Windows desktop. The desktop appears with the corporate wallpaper, the Start menu shows the installed application set, Outlook is preconfigured to the user's mailbox, OneDrive begins syncing to the user's cloud storage, and the device is ready for production use.

The user typically signs in to Microsoft 365 applications once during the first session (the silent single sign-on from the Primary Refresh Token usually handles this transparently), then begins working.

## Step 8: IT verification (server-side, no device interaction)

IT staff verify the device's state through the cloud admin consoles. There is no in-person verification because there is no IT-staged device.

1. **Microsoft Intune admin center**: Navigate to *Devices > All devices*, search by serial number. Confirm the managed device record exists, the primary user matches the expected assignment, the OS version matches the expected baseline, the configuration profile state is "Succeeded" for all assigned profiles, and the compliance state is "Compliant."

2. **Microsoft Entra admin center**: Navigate to *Devices > All devices*, search by name. Confirm the device object exists with join type "Microsoft Entra joined" and the primary user matches.

3. **Microsoft Defender XDR portal**: Navigate to *Devices*. Confirm the device is onboarded to Microsoft Defender for Endpoint and is reporting health and threat data.

4. **Compliance status check**: Confirm the device passes any Conditional Access policy that requires device compliance.

If any verification fails, IT staff investigate through the relevant admin console. Common Phase IV verification issues are addressed in the enrollment-diagnostic-cookbook artifact.

## Step 9: Continuous operation

After provisioning completes, the device operates under continuous Microsoft Intune management. Configuration profile updates are delivered via the MDM channel on the device's regular check-in cadence (typically every 8 hours, with on-demand syncs available). Compliance evaluation runs continuously. Application updates flow through the Win32 app delivery channel. Windows updates flow through Windows Update for Business per the assigned update ring. Microsoft Defender for Endpoint monitors the device continuously.

The user typically does not interact with IT for routine operation; helpdesk involvement occurs only for issues that require human intervention.

## Tools and equipment required

Phase IV requires substantially less hands-on equipment than Phases I, II, and III. The principal tooling is cloud-resident:

- Access to the Microsoft Intune admin center (the principal management console)
- Access to the Microsoft Entra admin center (for device object verification)
- Access to the Microsoft Defender XDR portal (for endpoint security verification)
- Access to the Microsoft Endpoint Manager / Intune service via Microsoft Graph for automation
- The vendor's pre-registration confirmation channel (typically email or a portal report)

For the optional IT-receiving path (when devices route through IT for asset tagging before shipping to users):

- Barcode scanner for asset tag application
- Asset tag printer
- Repacking materials
- Shipping infrastructure to the user's address

No PXE network, no Configuration Manager site server, no imaging workstation, no driver package store, no reference image, no WIM repository, no on-premises distribution points are required for Phase IV provisioning. (These remain in service for legacy and hybrid devices in the existing population, but new Phase IV devices do not consume them.)

## Common failures during Phase IV provisioning

**Autopilot does not switch to corporate branding (Step 4)**: The device is not pre-registered, or the network does not allow Autopilot to reach its endpoints. Resolution: verify pre-registration through the Intune admin center; verify network connectivity; if pre-registration is missing, capture the hardware hash on the device and register it manually (the procurement issue is a separate vendor-relationship matter).

**Conditional Access denies sign-in (Step 5)**: The sign-in matches a Conditional Access policy with a Block grant. The sign-in is denied; the user cannot proceed. Resolution: inspect the Microsoft Entra sign-in log to identify the policy and condition that matched. Common causes: sign-in from a disallowed location, sign-in from an unmanaged device that requires hybrid join (a misconfiguration if Phase IV is expected), or a policy that requires the user to be a member of a specific group that the user has not been added to.

**ESP hangs on a specific application (Step 6)**: A required Win32 application is stuck installing. ESP waits up to its configured timeout (default 60 minutes), then either fails ESP or marks the app as failed and continues, depending on the ESP configuration. Resolution: investigate the IntuneManagementExtension.log on the device to identify which app is stuck; resolve the underlying app installation issue (typically network, prerequisite, or installer bug).

**ESP error 0x80180014**: MDM enrollment failed because the user is not licensed for Intune or is outside the MDM scope. Resolution: verify license and scope.

**ESP error 0x800705B4**: A required tracked application exceeded the ESP timeout. Resolution: review the app's installation, reduce the required-app set, or increase the ESP timeout.

**User signs in with a personal Microsoft Account by accident (Step 5)**: The user enters their personal email instead of their work UPN. The device joins as a personal device, not a corporate Entra-joined device. Resolution: reset the device (Settings > Recovery > Reset this PC, choose "Remove everything") and walk the user through the correct sign-in path.

**TPM not provisioned (various steps)**: The device's TPM is not in the expected state for cloud join and BitLocker. Resolution: enter firmware, verify TPM is enabled, possibly clear the TPM (which invalidates any prior BitLocker keys — coordinate with the user if they have prior data).

## Total time and resource cost per device

Provisioning time per device: 15 to 60 minutes elapsed (entirely on the user's first boot, with no IT staff involvement during the elapsed time).

Hands-on IT staff time per device: typically 5 to 10 minutes (the pre-shipment verification of vendor pre-registration plus the post-provisioning admin-console verification). For organizations using the IT-receiving fallback path, additional 5 to 10 minutes for asset tagging.

The substantial cost reduction in Phase IV is at the imaging-workflow level. The Phase I, II, and III imaging operation — PXE network, Configuration Manager, distribution points, imaging technicians, reference image maintenance, driver package store — is entirely absent in Phase IV. For organizations deploying 100 devices per week, the imaging staff reduction is typically 1 to 2 full-time equivalents, with the saved capacity redirecting to higher-value cloud-side work or to retirement of legacy infrastructure.
