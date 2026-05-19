# Phase II — Early Transition: Step-by-Step Laptop Onboarding (Without UIAO)

## Audience and purpose

This guide is for new IT staff learning the early transition laptop onboarding process — the phase in which user identity has been extended into Microsoft Entra ID (formerly Azure Active Directory) for cloud-application access, while device identity, device configuration, and device governance remain entirely anchored in on-premises Active Directory. The device-side provisioning workflow is essentially identical to the legacy phase; what changes is the user's interaction with cloud applications and the additional identity preparation that happens before the user first signs in.

The phase architecture is described in [`01-customer-narrative/without-uiao-early-transition.md`](../01-customer-narrative/without-uiao-early-transition.md).

## Quick reference

| Question | Answer |
|---|---|
| Is PXE boot used? | **Yes** — same as Phase I Legacy. Device-side provisioning is unchanged. |
| Is imaging used? | **Yes** — same reference image, same task sequence. |
| Is a barcode scanner used? | **Yes** — same as Phase I Legacy. |
| Is the laptop joined to a domain? | **Yes** — on-premises Active Directory. The device does NOT join Microsoft Entra ID. |
| Does the device have a cloud identity? | **No** — only the user has a cloud identity. The device is unknown to Microsoft Entra ID. |
| Does the user touch the device before final handoff? | **No** — provisioning is performed by IT staff. The user first interacts with cloud services on first sign-in. |
| How long does provisioning take? | Same as Phase I Legacy: 2-3 hours elapsed, 30-45 minutes hands-on. |
| What's different in Phase II? | The user's cloud identity is pre-provisioned (mailbox, MFA enrollment campaign, license assignment) before the device is handed off. The user signs in to cloud apps via modern authentication on first use. |
| Network used | Wired Ethernet for imaging. After imaging, the device uses corporate Wi-Fi or wired Ethernet. |

## Software inventory at provisioning completion

Identical to Phase I Legacy with one notable addition: Microsoft 365 Apps for Enterprise installed in the corporate baseline now reaches Microsoft 365 cloud services on first user sign-in. The installed software set is unchanged; what changes is what those clients connect to.

## Pre-arrival activities

Identical to Phase I for the device side. New activities specific to Phase II happen on the cloud identity side, in parallel:

**Cloud identity provisioning**: When the user is hired (or moved to a new role), the human-resources information technology system feeds the joiner event to identity provisioning. The on-premises Active Directory user object is created (via the existing legacy provisioning process); Microsoft Entra Connect synchronizes the user object to Microsoft Entra ID within thirty minutes of the on-premises creation; a Microsoft 365 license is assigned in the Microsoft 365 admin center; Exchange Online provisions a mailbox; OneDrive for Business provisions the user's cloud storage; the user is added to the security groups that drive Conditional Access scoping.

**Multi-factor authentication enrollment**: Before the user's first sign-in, the user must enroll an authentication factor (Microsoft Authenticator app, FIDO2 security key, hardware token, or phone-based factor). The enrollment can happen either through a self-service portal in advance of the device handoff or during the first sign-in attempt itself. Most organizations prefer pre-enrollment to avoid blocking the user on first device use.

**License assignment**: The user must have a Microsoft 365 license (E3, E5, Business Premium, or equivalent) assigned before they can access cloud services. This is performed in the Microsoft 365 admin center or, in mature organizations, through a license assignment automation tied to security group membership.

## Step 1: Device receipt and inspection

Identical to Phase I Legacy. Receive the device, inspect, scan serial number, affix and scan asset tag, stage in imaging area.

## Step 2: BIOS / UEFI verification

Identical to Phase I Legacy. UEFI boot mode, Secure Boot enabled, TPM active, boot order with network adapter first.

## Step 3: Network connectivity (for imaging)

Identical to Phase I Legacy. Wired Ethernet to the imaging subnet.

## Step 4: PXE boot to Windows Preinstallation Environment

Identical to Phase I Legacy. PXE boot, boot image delivery, WinPE loads, task sequence wizard appears.

## Step 5: Task sequence execution

Identical to Phase I Legacy. Disk format, image apply, driver injection, reboot, mini-setup bypass, domain join, ConfigMgr client install, application installation, Group Policy application, BitLocker enablement, final reboot.

The task sequence is unchanged from Phase I. The same reference image is used, the same applications are installed, the same Group Policy applies. The device emerges from imaging as a legacy-pattern AD-joined Windows endpoint.

## Step 6: Post-imaging verification

Identical to Phase I Legacy. Verify domain join, ConfigMgr client registration, application set present, BitLocker enabled, Group Policy applied, event log clean.

## Step 7: Asset record update and user assignment

Identical to Phase I Legacy. Update the asset database with the assigned user, device name, and deployment date.

## Step 8: Pre-handoff cloud identity verification

This step is new in Phase II — it does not exist in Phase I because Phase I has no cloud identity surface.

The technician performing handoff (typically the helpdesk receiving the device from the imaging team) verifies the cloud identity is ready for the user:

1. **Mailbox provisioning verified**: In the Exchange admin center or Microsoft 365 admin center, confirm the user's mailbox is provisioned and reachable. The user's email address (the user's UPN, typically the same as their on-premises UPN) should resolve to the Exchange Online mailbox.

2. **License verified**: Confirm the assigned Microsoft 365 license matches the user's expected role. License gaps will manifest as application activation failures on first sign-in.

3. **MFA enrollment verified**: Confirm the user has at least one MFA factor enrolled. The Microsoft Entra admin center *Authentication methods* user blade shows enrolled factors. If no factor is enrolled, the user will be prompted to enroll on first sign-in to a cloud application, which can be confusing during initial device use.

4. **Group memberships verified**: Confirm the user is in the security groups expected for their role (Conditional Access scoping groups, license assignment groups if not directly licensed, application access groups for federated SaaS applications).

If any of these is incomplete, the gap is resolved before handoff. Handing off a device to a user whose cloud identity is not ready produces helpdesk volume immediately.

## Step 9: User handoff

The device is repacked with accessories and a welcome packet, and either handed off in person or shipped to the user.

The welcome packet for Phase II includes additional instructions beyond Phase I:

- The user's UPN (login name for both on-premises and cloud sign-ins)
- A reminder that Microsoft 365 services (Outlook, Teams, OneDrive, SharePoint) are cloud-resident
- Instructions for MFA: which factor the user has enrolled, how to use it, how to add additional factors via the My Sign-Ins portal
- A note that the first sign-in to Office applications may prompt for the user's cloud credentials and MFA factor — this is expected behavior on first use of a new device

## Step 10: User first sign-in (the user does this, not the technician)

The user signs in to the device for the first time with their domain credentials. On-premises Active Directory authentication succeeds; the user reaches the Windows desktop.

The user then opens Outlook, Word, Excel, or another Microsoft 365 client application. The application detects it has no cached cloud credentials and presents the sign-in prompt:

1. The application opens to a Microsoft sign-in page (a hosted page at `login.microsoftonline.com`).
2. The user enters their UPN.
3. Microsoft Entra ID redirects through a series of authentication checks: the password is validated (either against the cloud-stored hash via Password Hash Sync, or by forwarding to a pass-through authentication agent that consults an on-premises domain controller).
4. **Conditional Access evaluates**: based on the policies in place, the sign-in may be challenged for MFA, evaluated for sign-in risk, evaluated for location compliance, and checked against any other configured conditions.
5. The user is prompted for their MFA factor (the Microsoft Authenticator push notification, the FIDO2 security key tap, the phone-based factor).
6. On successful authentication and MFA, the application receives an OAuth 2.0 token and the user is signed in to the cloud application.
7. **Seamless single sign-on**: Once the user has signed in to one Microsoft 365 client, subsequent clients on the same device typically sign in silently using the cached refresh token, avoiding repeated prompts.

The first-time cloud sign-in is the most visible difference between Phase I and Phase II from the user's perspective. In Phase I, the user signs in to Windows and immediately has access to all internal resources via Kerberos. In Phase II, the same Windows sign-in works identically for on-premises resources, but cloud applications require an additional one-time sign-in with MFA.

## Tools and equipment required

Same as Phase I Legacy for the imaging operation. Additional cloud-side preparation requires:

- Access to the Microsoft Entra admin center (for verifying user identity, group memberships, MFA enrollment)
- Access to the Microsoft 365 admin center (for verifying license assignment, mailbox provisioning)
- Self-service MFA enrollment portal (the My Sign-Ins portal at `aka.ms/mysignins`)

## Common failures during provisioning and first sign-in

The Phase I imaging failure modes (PXE failure, driver mismatch, domain join failure, application failure, BitLocker failure) apply identically.

**Additional Phase II-specific failure modes**:

**User cannot sign in to cloud apps on first try (no MFA prompt at all)**: The user is not in any Conditional Access policy scope that requires MFA. This can be a misconfiguration (intended population not actually targeted) or correct behavior (the user is in an exempted role).

**User signs in but is denied access by Conditional Access**: The sign-in matched a policy with a Block grant. The Microsoft Entra sign-in log shows which policy and condition matched. Typical causes include sign-in from a disallowed location, sign-in using legacy authentication (the user's email client is too old or misconfigured), or sign-in matching a sign-in-risk-based block.

**MFA enrollment was never completed**: The user is prompted to enroll an MFA factor on first sign-in. If the user is unfamiliar with the process and the enrollment is awkward to complete during their first device experience, the user may abandon the attempt and contact the helpdesk. Pre-enrollment campaigns in advance of device handoff mitigate this.

**License missing**: The user's account is not licensed for the requested service. Outlook reports "Your Office 365 subscription has expired" or a similar message. Assign the license in the admin center; activation typically takes 5 to 15 minutes to propagate.

**Modern authentication disabled in a specific client**: An older Outlook client (Outlook 2013 or earlier without the Modern Auth registry keys) attempts to authenticate using legacy basic authentication. Conditional Access blocks legacy auth, the client cannot connect, and the user reports inability to access email. Resolution: update the client to a version that supports Modern Auth, or update the registry keys to enable Modern Auth in the legacy client.

**Microsoft Entra Connect synchronization lag**: The user was created in on-premises Active Directory but has not yet synchronized to Microsoft Entra ID. The user cannot sign in to cloud applications because the cloud identity does not exist yet. Resolution: force a synchronization from the Entra Connect server, or wait for the next scheduled cycle (default 30 minutes).

## Total time and resource cost per device

Imaging time per device: same as Phase I, 2 to 3 hours elapsed and 30 to 45 minutes hands-on.

Cloud identity preparation per user (before device handoff): typically 10 to 20 minutes of identity-team time, mostly performed in advance of any specific device and amortized across many devices.

Total marginal cost over Phase I: small at the per-device level; substantial at the program level due to the ongoing operation of two identity surfaces and the new licensing costs for Microsoft 365 services.
