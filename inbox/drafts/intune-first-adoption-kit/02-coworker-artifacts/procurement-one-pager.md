# Procurement Guide: Buying Devices That Land Cloud-Native

**Audience:** Procurement officers, asset managers, contracting staff, and IT
leadership who sign or approve hardware purchase orders.

**Purpose:** Every end-user device or managed server acquired by the
organization should arrive at the user (or the rack) already registered to the
Microsoft Entra tenant, already assigned an enrollment profile, and ready to
provision into Microsoft Intune without a technician touching it. This guide
describes the procurement actions that make that happen — what to put in a
Purchase Order, what to require from the reseller, how to verify pre-registration
before the device ships, and what to do when something is missing.

**Scope:** Windows laptops and desktops (any OEM), Microsoft Surface devices,
macOS devices, iOS and iPadOS devices, Android devices (including Samsung), and
Azure Arc-managed Windows or Linux servers.

**Why this matters:** A device that ships without tenant pre-registration is a
future remediation ticket. Capturing a hardware hash after delivery, manually
uploading it, and assigning a deployment profile costs roughly one hour of
engineering time per device. At any meaningful volume, the difference between
"vendor handled it" and "we handle it after arrival" is a significant
operational tax — one that the clauses below are designed to eliminate.

---

## 1. The clause to include in every Purchase Order

Insert the following language into every PO for end-user devices or managed
servers. Adjust the tenant identifier, point of contact, and remediation
language to match the organization's contracting standards.

> Vendor shall pre-register all devices delivered under this order into the
> Buyer's Microsoft Entra tenant prior to shipment, using the appropriate
> registration mechanism for each device type: Windows Autopilot for Windows
> endpoints, Apple Business Manager (or Apple School Manager) for macOS and
> iOS/iPadOS endpoints, Android Enterprise Zero-Touch Enrollment or Samsung
> Knox Mobile Enrollment for Android endpoints, and Azure Arc onboarding for
> managed servers. Vendor shall provide written confirmation of successful
> tenant registration including device serial numbers and, for Windows
> endpoints, hardware hashes, and shall associate each device with the
> deployment profile specified by Buyer at order placement. Devices delivered
> without successful tenant registration are subject to return or remediation
> at Vendor's expense.

The clause is intentionally vendor-agnostic. Resellers operating under the
Microsoft Cloud Solution Provider program for Windows hardware, the Apple
Authorized Reseller program for Apple hardware, and the Android Enterprise
partner ecosystem for Android hardware can all comply. Vendors that cannot
comply should be requalified or replaced before being added to the approved
vendor list for cloud-native procurement.

---

## 2. Questions to ask the reseller before placing the first order

Before establishing or renewing a procurement relationship with a reseller,
confirm capability by asking five qualifying questions. A reseller who answers
yes to all five is qualified for cloud-native procurement. A reseller who
answers no to any of them should be used only for legacy refresh of devices
that will not be onboarded through cloud-native pathways.

1. **Windows tenant registration capability.** Are you authorized to register
   Windows devices into customer Microsoft Entra tenants via the Cloud Solution
   Provider Autopilot API, and can you do so for both direct purchases and
   drop-ship purchases?

2. **Apple Business Manager integration.** For Apple hardware, are you enrolled
   as an Apple Authorized Reseller capable of pushing devices into Apple
   Business Manager or Apple School Manager under the customer's organization
   identifier?

3. **Android Zero-Touch and Knox Mobile Enrollment.** For Android hardware, do
   you have a relationship with the Android Zero-Touch portal or, for Samsung
   devices specifically, with Samsung Knox Mobile Enrollment, sufficient to
   push devices into the customer's enrollment workflow at shipment?

4. **Turnaround and escalation.** What is your standard turnaround time from
   order placement to tenant registration confirmation, and what is your
   escalation path when registration fails for a specific device or batch?

5. **Profile assignment at order placement.** Can you accept the Autopilot
   deployment profile identifier (or the Apple Business Manager device
   assignment, or the Zero-Touch configuration identifier) at order placement,
   so that devices arrive associated with the correct profile rather than
   registered into the tenant as unprofiled hardware requiring a separate
   assignment step?

---

## 3. How to verify pre-registration before the device ships

Resellers will occasionally report a device as registered when it is not.
Independent verification is necessary for every new reseller relationship and
for every order placed with a reseller whose track record has not yet justified
trust. The verification should occur *before* the device ships, while the
reseller still has the device in their possession and can correct an error
without remediation cost.

**For Windows devices via Windows Autopilot.** Sign in to the Microsoft Intune
admin center, navigate to *Devices > Enrollment > Windows enrollment > Windows
Autopilot devices*, and filter by the serial number reported by the reseller.
The device should appear with its hardware hash, manufacturer, model, and the
deployment profile assigned. For bulk verification, use Microsoft Graph:

```
GET https://graph.microsoft.com/beta/deviceManagement/windowsAutopilotDeviceIdentities?$filter=serialNumber eq '<serial>'
```

A non-empty response indicates the device is registered. An empty response
indicates the device is not. A 200-OK response with empty results is still an
empty response — not an error.

**For macOS, iOS, and iPadOS devices via Apple Business Manager or School
Manager.** Sign in to `business.apple.com` (or `school.apple.com`), navigate to
*Devices*, and search by serial number. The device should appear with its
assigned Mobile Device Management server, which should be the organization's
Microsoft Intune integration (named according to the organization's MDM server
configuration in ABM). The Apple Business Manager API can be used for bulk
verification when the volume justifies automation.

**For Android devices via Android Zero-Touch.** Sign in to
`partner.android.com/zerotouch`, navigate to *Devices*, and confirm the IMEI
(or serial number, depending on the OEM) is present and assigned to the correct
configuration.

**For Samsung devices via Knox Mobile Enrollment.** Sign in to the Knox Mobile
Enrollment console and confirm device presence by IMEI. Samsung devices can
appear in both Zero-Touch and Knox Mobile Enrollment depending on the
provisioning path the reseller used; either is acceptable, but the organization
should standardize on one for any given Samsung device class to avoid
configuration drift.

**For Azure Arc-managed servers.** Confirm the onboarding token or service
principal credentials provided to the vendor have been used to register the
device. The device should appear in the Azure portal under *Azure Arc >
Machines* with the correct resource group, subscription, and tags.

---

## 4. Platform-specific procurement reference

| Platform | Registration mechanism | Identifier needed | Pre-registration channel |
|---|---|---|---|
| Windows laptop/desktop (Dell, HP, Lenovo, etc.) | Windows Autopilot | Hardware hash + serial number | CSP API via reseller, or direct Microsoft purchase |
| Microsoft Surface (Pro, Laptop, Studio, Go) | Windows Autopilot | Hardware hash + serial number | Microsoft direct, or Surface Authorized Device Reseller |
| macOS (MacBook, iMac, Mac Mini, Mac Studio) | Apple ABM/ASM Automated Device Enrollment | Serial number | Apple direct, or Apple Authorized Reseller |
| iOS/iPadOS (iPhone, iPad) | Apple ABM/ASM Automated Device Enrollment | Serial number | Apple direct, or Apple Authorized Reseller |
| Android (Pixel, OnePlus, etc.) | Android Enterprise Zero-Touch | IMEI | Android Zero-Touch reseller |
| Samsung Galaxy (premium tier) | Samsung Knox Mobile Enrollment | IMEI | Samsung-authorized reseller |
| Windows or Linux server (physical or VM) | Azure Arc onboarding | Onboarding script or service principal | Vendor pre-runs onboarding script with credentials supplied by Buyer |

A note on Surface specifically: Microsoft can pre-register Surface hardware
directly into the tenant when the order is placed through Microsoft's
commercial channel. Indirect Surface purchases (through CDW, Insight,
Connection, or other Surface Authorized Device Resellers) require the reseller
to handle registration through their CSP integration. The procurement
experience is identical from the Buyer's perspective; the difference is which
party handles the registration step.

---

## 5. Failure modes and fallbacks

Procurement does not always go cleanly. The following are the failure modes
this guide is designed to either prevent or recover from.

**The reseller does not support tenant registration at all.** Either qualify a
different reseller for cloud-native procurement, or accept that this purchase
will require post-arrival registration. Post-arrival registration is
operationally expensive (someone must capture the hardware hash from each
device, upload it to the tenant, and assign a profile) and partially defeats
the purpose of cloud-native procurement, but it is recoverable for small
volumes. For Windows, the standard hash-capture script is
`Get-WindowsAutopilotInfo.ps1` from the PowerShell Gallery.

**The reseller supports registration but missed it on a specific order.**
Capture the hardware hash on arrival, upload to the tenant, assign the correct
deployment profile, and bill the remediation effort back to the reseller under
the PO clause. The PO clause is enforceable only if it was included in the
original PO; insert it in every order, every time, without exception.

**The reseller registered the device into the wrong tenant.** This occurs with
resellers serving multiple customers through a shared procurement pipeline.
Recovery requires the reseller (or in some cases, the incorrect tenant's
administrator) to remove the device from the incorrect tenant before it can be
added to the correct one. For Windows Autopilot, the removal can take up to 24
hours to propagate through Microsoft's systems before the device can be
re-registered. For Apple ABM, removal is typically faster but requires the
original tenant administrator to release the device, which can be difficult to
arrange across organizational boundaries.

**The reseller registered the device but did not assign a deployment profile.**
The verification step in section 3 catches this before shipment. If discovered
after shipment, the device will provision to default settings on first boot,
which typically results in either an enrollment failure or a device joined to
the tenant with the wrong configuration. Recovery requires either a fresh
out-of-box experience reset (acceptable on a still-in-box device, time-consuming
on a delivered device) or remediation through Intune after enrollment.

**The reseller registered the device, assigned a profile, but the wrong
profile.** Verification in section 3 catches this. The fix is for the reseller
(or the Buyer) to reassign the profile in the appropriate portal; reassignment
takes effect on the next device check-in or out-of-box experience attempt.

**Never accept "we'll register it after delivery" from a vendor on a
cloud-native procurement.** Post-delivery registration is the failure case the
PO clause exists to prevent. A vendor unwilling to register before shipment is
signaling that their cloud-native procurement pipeline is not mature, and the
organization should treat that signal as disqualifying for cloud-native orders.

---

## 6. Authoritative sources

The procurement mechanisms described above are documented by their respective
vendors. The landing pages below are the most stable entry points; specific
deep links within the vendor documentation are restructured frequently and
should be relied on only after current verification.

- Windows Autopilot device registration, Microsoft Learn. https://learn.microsoft.com/en-us/autopilot/
- Apple Business Manager User Guide, Apple Support. https://support.apple.com/guide/apple-business-manager/welcome/web
- Apple School Manager User Guide, Apple Support. https://support.apple.com/guide/apple-school-manager/welcome/web
- Android Enterprise Zero-Touch Enrollment, Google. https://www.android.com/enterprise/management/zero-touch/
- Samsung Knox Mobile Enrollment, Samsung Knox. https://docs.samsungknox.com/admin/knox-mobile-enrollment/
- Azure Arc-enabled servers onboarding, Microsoft Learn. https://learn.microsoft.com/en-us/azure/azure-arc/servers/

*All vendor URLs above should be verified before this document is distributed.
Vendor documentation is reorganized regularly, and stable-looking URLs
occasionally redirect or return errors after a reorganization.*

---

## 7. Quick checklist for a new procurement

For a procurement officer placing a single order, this is the workflow in
condensed form:

1. Confirm the reseller is qualified for cloud-native procurement (section 2).
2. Insert the PO clause from section 1 into the Purchase Order.
3. Provide the reseller with the tenant identifier and the deployment profile
   to be assigned (Autopilot profile ID, ABM device assignment, or Zero-Touch
   configuration ID).
4. Receive the reseller's confirmation of registration before the device ships.
5. Independently verify registration using the appropriate portal or API
   (section 3) before authorizing shipment.
6. Document any failures and recover using the relevant fallback in section 5.
7. Track the device through delivery and first user sign-in to confirm the
   end-to-end pipeline worked. A device that registers correctly, ships
   correctly, and provisions correctly closes the procurement loop; a device
   that fails at any stage indicates a gap in the vendor's process that should
   be fed back into reseller qualification.
