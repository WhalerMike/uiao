# Phase I — Legacy: Step-by-Step Laptop Onboarding (Without UIAO)

## Audience and purpose

This guide is for new information technology staff, deployment technicians, and helpdesk personnel learning the legacy on-premises laptop onboarding process. It documents exactly what happens from the moment a laptop is delivered to the IT receiving area through the moment the laptop reaches the end user as a fully managed corporate device. A new technician should be able to follow this guide end-to-end after one shadow session with an experienced colleague.

The phase architecture is described in [`01-customer-narrative/without-uiao-legacy.md`](../01-customer-narrative/without-uiao-legacy.md). This document is the operational procedure that implements the architecture.

## Quick reference

| Question | Answer |
|---|---|
| Is PXE boot used? | **Yes** — the laptop boots from the network into Windows Preinstallation Environment, which runs the deployment task sequence. |
| Is imaging used? | **Yes** — a corporate Windows reference image (a `.wim` file) is applied to the laptop's disk. |
| Is a barcode scanner used? | **Yes** — at receiving (to capture serial number and link the corporate asset tag) and again during asset record creation. |
| Is the laptop joined to a domain? | **Yes** — to the on-premises Active Directory domain. |
| Does the user touch the device before final handoff? | **No** — provisioning is performed entirely by IT staff; the user receives a ready-to-use device. |
| How long does provisioning take? | 2 to 3 hours total elapsed; 30 to 45 minutes of hands-on technician time. |
| Roles involved | Procurement, receiving, imaging technician, asset management, helpdesk |
| Network used | Wired Ethernet (Wi-Fi cannot be used because there are no credentials yet) |
| Software delivery mechanism | Microsoft Configuration Manager task sequence + Group Policy |

## Software inventory at provisioning completion

A fully provisioned legacy-phase laptop has the following installed when the user receives it:

- Windows 10 or Windows 11 Enterprise (from the corporate reference image)
- Microsoft Configuration Manager client agent
- Microsoft Defender Antivirus
- Microsoft 365 Apps for Enterprise (Outlook, Word, Excel, PowerPoint, Teams)
- Microsoft Edge browser
- Corporate VPN client (Cisco AnyConnect, Palo Alto GlobalProtect, or equivalent)
- Adobe Acrobat Reader
- Standard business applications (PDF tools, browser plugins, internal LOB apps)
- BitLocker enabled, recovery key escrowed to the AD computer object
- Machine certificate for 802.1X Wi-Fi authentication (from Active Directory Certificate Services)
- Group Policy applied (computer-side at imaging, user-side at first user logon)

## Pre-arrival activities (happen before the laptop is unboxed)

**Procurement** issues a purchase order to the approved hardware vendor for the agreed model, configuration, and quantity. The PO specifies shipping to the IT receiving area, not to the end user. Standard configurations are pre-negotiated with the vendor to keep the driver-package matrix manageable.

**The reference image** is maintained by the imaging team on the Microsoft Configuration Manager deployment server. The image is updated quarterly (or after each Windows feature update) with current OS build, current Microsoft 365 Apps version, and current third-party application versions. The image is built once in a controlled environment, captured with `DISM /Capture-Image`, and stored as a `.wim` file on the distribution points.

**Task sequences** are pre-built in the Configuration Manager admin console for each device class (standard knowledge worker, executive, kiosk, lab equipment, etc.). Each task sequence references the reference image, the device-class-specific driver packages, the application list, and the post-deployment configuration steps.

**Asset tags** with sequential barcodes are pre-printed in batches by the asset management team and held in the receiving area for immediate application to incoming devices.

## Step 1: Device receipt and inspection

The carrier delivers the boxed laptop to the IT receiving area. The receiving technician:

1. Verifies the shipment against the purchase order — model, quantity, and configuration must match. Discrepancies are reported to procurement before proceeding.
2. Opens the outer shipping carton and inspects for shipping damage. Damaged outer cartons trigger careful inspection of the device; obviously damaged devices are returned to the vendor.
3. Removes the laptop from its retail box. Sets aside the accessories (power supply, USB-C cables, USB-C-to-Ethernet adapter, documentation) — these will be repacked with the provisioned laptop for the end user.
4. **Scans the serial number** on the bottom of the laptop with the handheld barcode scanner. The scan enters the serial number into the receiving system, creating a record that this specific device has arrived.
5. **Affixes the corporate asset tag** in the standard location (typically the bottom of the chassis near the front edge). Scans the asset tag's barcode to link it to the serial number in the asset database. The asset record is now created with status "Received, awaiting provisioning."
6. Stages the device in the imaging area, racked or shelved with other waiting devices.

Time: 5 to 10 minutes per device when processing a batch.

## Step 2: BIOS / UEFI verification

The imaging technician verifies firmware configuration before starting deployment.

1. Powers on the device while holding the firmware setup key (F2 for Dell and most Lenovo; F10 for HP; Esc-then-F12 for some Lenovo; varies by model).
2. Verifies **Boot Mode is UEFI** (not Legacy / CSM). All modern Windows deployments require UEFI.
3. Verifies **Secure Boot is Enabled**. Required for the corporate security baseline and for Windows 11.
4. Verifies **TPM is Enabled and Active**. BitLocker requires a functional TPM 2.0 (TPM 1.2 on older devices, with documented exceptions).
5. Verifies **Boot Order** has the network adapter as the first boot device (for PXE), with internal storage second.
6. Saves and exits. The device reboots.

Most modern devices ship from the vendor with the corporate-standard firmware settings, particularly when the vendor honors a pre-configured BIOS specification negotiated at procurement. Devices shipped with non-conforming settings are corrected here.

Time: 2 to 5 minutes per device.

## Step 3: Network connectivity

The imaging technician connects the laptop to the imaging network using **wired Ethernet** — Wi-Fi is not usable for imaging because the device has no Wi-Fi credentials yet.

1. Plugs the USB-C-to-Ethernet adapter into a USB-C port (most modern laptops do not have a built-in RJ-45 port).
2. Plugs a CAT-6 Ethernet cable from the imaging network switch into the adapter.
3. Confirms link by inspecting the LED indicator on the Ethernet adapter.

The imaging network is a dedicated subnet configured with DHCP options 66 (boot server IP) and 67 (boot file path) so PXE boot succeeds when the device powers on.

## Step 4: PXE boot to Windows Preinstallation Environment

1. The technician powers on the laptop. With the network adapter as the first boot device, the laptop broadcasts a DHCP request.
2. The DHCP server replies with an IP address plus the PXE options, directing the laptop to the boot server.
3. The boot server delivers the Configuration Manager boot image — a WinPE-based image containing the task sequence engine. The image downloads over TFTP or HTTP and boots.
4. **Windows Preinstallation Environment (WinPE) loads**: a stripped-down Windows running from a RAM disk, with the Configuration Manager task sequence wizard ready.
5. The wizard prompts the technician to select the task sequence appropriate for this device (Standard Knowledge Worker, Executive Laptop, Kiosk, Lab, etc.).
6. The wizard may prompt for additional metadata: device name (typically generated from a corporate naming convention using the asset tag), assigned user UPN, department code, location code.

Time to PXE boot through wizard: 3 to 5 minutes.

## Step 5: Task sequence execution

The task sequence runs unattended for the bulk of the provisioning time. The technician monitors progress but does not interact during normal operation.

1. **Disk format and partition**: The local storage is formatted (typically a single C: partition plus a recovery partition).
2. **Reference image application**: The Windows reference image (`.wim` file) is downloaded from the distribution point and applied to C:. This is typically the longest step — 10 to 20 minutes depending on image size (8 to 15 GB) and network speed.
3. **Driver injection**: Device-class-specific drivers are applied from the driver package store, matched by hardware identifiers.
4. **Reboot to Windows**: The device reboots from the local disk into the freshly-installed Windows.
5. **Mini-setup and OOBE bypass**: Windows runs initial setup; the task sequence's unattended answer file (`Unattend.xml`) pre-populates the responses, bypassing the consumer out-of-box experience.
6. **Domain join**: The task sequence runs `Add-Computer` or `djoin`, joining the device to the on-premises Active Directory domain in a "New Devices" OU.
7. **Configuration Manager client installation**: The ConfigMgr client agent installs and registers with the site server.
8. **Application installation**: The task sequence iterates the application list, installing each required application. Typically the longest variable phase — 15 to 60 minutes depending on the application set.
9. **Group Policy application**: With the device domain-joined, Group Policy applies on the next refresh, delivering security baseline settings, audit policies, certificate autoenrollment policies, and the Wi-Fi machine certificate.
10. **BitLocker enablement**: With Group Policy applied, BitLocker is enabled on the system drive. The recovery key is escrowed to the device's Active Directory computer object (specifically, to the `msFVE-RecoveryInformation` child object).
11. **Final reboot**: The task sequence completes and triggers a final reboot.

Total task sequence time: 45 to 90 minutes unattended.

## Step 6: Post-imaging verification

The imaging technician verifies the provisioned device before handoff.

1. Signs in as a domain administrator (or as the local administrator with the password set by the task sequence).
2. Runs `dsregcmd /status` — confirms `DomainJoined: YES` and the domain name matches.
3. Runs `nltest /sc_query:<domain>` — confirms the secure channel to the domain controller is operational.
4. Opens *Control Panel > Configuration Manager* — confirms the ConfigMgr client is registered with the site, has retrieved policy, and is reporting inventory.
5. Opens the Start menu — confirms the corporate application set is present.
6. Runs `manage-bde -status` — confirms BitLocker is enabled and a recovery password is escrowed.
7. Runs `gpresult /h C:\gpresult.html` — opens the HTML and confirms the expected Group Policy Objects applied.
8. Inspects the Application and System event logs for errors during deployment.
9. Shuts down the device.

Time: 5 to 10 minutes per device.

## Step 7: Asset record update and user assignment

Before handoff, the asset management database is updated.

1. The asset management technician opens the asset record (created at receiving in Step 1).
2. The assigned user is set, linking the device to the user's Active Directory account.
3. The device name (generated during the task sequence) is recorded.
4. The deployment date is timestamped.
5. If the organization uses ConfigMgr's primary-device feature, the primary device assignment is made here.

## Step 8: User handoff

1. The provisioned device is repacked with its accessories (power supply, USB-C-to-Ethernet adapter, docking station if included, carrying case if included).
2. A welcome packet is added containing the device serial number, asset tag, device name, first-sign-in instructions, and helpdesk contact information.
3. For local users, the device is handed off at the IT helpdesk. For remote users, the device is shipped to the user's office or home address.
4. **First sign-in by the user**: The user signs in with their domain credentials. User-side Group Policy applies (folder redirection, drive mappings, default browser, Office configuration). The user is now operating a fully provisioned corporate device.

## Tools and equipment required at the imaging station

- PXE-enabled imaging network with DHCP options 66/67 configured
- Microsoft Configuration Manager site server (or MDT server) hosting boot images, reference images, driver packages, applications, and task sequences
- Distribution point(s) hosting content delivered during task sequences
- Imaging workspace with multiple Ethernet drops
- Handheld barcode scanner
- Corporate asset tag printer (label printer with appropriate label stock)
- CAT-6 Ethernet cables
- USB-C-to-Ethernet adapters (for laptops without built-in RJ-45)
- Spare laptop power supplies
- Corporate domain administrator credentials (or appropriate delegated credentials for OU permissions)

## Common failures during provisioning

**PXE boot fails to start**: Boot order is wrong, network port is not configured for PXE, or DHCP options are missing. Investigate the firmware, the network switch port, and the DHCP scope.

**PXE boot starts but cannot reach the boot server**: Network connectivity issue. Verify the imaging subnet is correctly configured and the boot server is reachable.

**WinPE loads but the task sequence wizard does not appear**: The task sequence is not advertised to the device, or the boot media is misconfigured. Re-advertise the task sequence to the unknown-computer collection.

**Driver mismatch**: Task sequence applies a driver package that does not match the actual hardware. Update the driver category mapping or add the missing driver package.

**Domain join failure**: Time skew (the device clock is more than 5 minutes off from the domain controller), the join account lacks computer-object creation permissions in the target OU, or the device name conflicts with an existing computer object. Resolve per the specific error code.

**Application installation failure**: Investigate the `SMSTS.log` file (typically at `X:\Windows\Temp\SMSTSLog\smsts.log` during the task sequence, then at `C:\Windows\CCM\Logs\smsts.log` afterward) for the specific application's installation output.

**BitLocker fails to enable**: Typically because Group Policy has not yet applied or the TPM is not fully provisioned. Investigate the BitLocker event log (`Microsoft-Windows-BitLocker-API/Management`) and the TPM management console (`tpm.msc`).

## Total time and resource cost per device

- Receiving and tagging: 5-10 minutes hands-on
- BIOS verification and PXE initiation: 5-10 minutes hands-on
- Unattended task sequence: 45-90 minutes elapsed
- Verification: 5-10 minutes hands-on
- Asset record update: 2-5 minutes
- Repack and handoff (or ship): 5-10 minutes

Total elapsed: 2 to 3 hours per device. Total hands-on IT staff time: 30 to 45 minutes per device. An imaging technician working through a batch of 8 to 12 identical devices can complete the batch in a single day, processing devices in parallel.
