---
document_id: IFO_011
title: "Platform Annex — macOS Endpoints via ABM/ASM and Automated Device Enrollment"
version: "1.0"
status: CANONICAL
owner: "Michael Stratton"
created_at: "2026-05-13"
updated_at: "2026-05-14"
boundary: GCC-Moderate
canon_anchor: ADR-071
platform: macos-endpoint
publish_to_site: true
publication_style: narrative
published_at: docs/modernization/intune-first.qmd
---

# Platform Annex — macOS Endpoints via ABM/ASM and Automated Device Enrollment

> Per-platform implementation of the five-phase Intune-first process
> for macOS endpoints. Process is the same as in
> [`../process.md`](../process.md); this annex specifies the
> macOS-specific mechanics for each phase.
>
> **Default enrollment vector:** Apple Business Manager (ABM) or
> Apple School Manager (ASM) Automated Device Enrollment (ADE),
> formerly known as the Device Enrollment Program (DEP), with
> Microsoft Intune as the assigned MDM server.
>
> **Canonical management plane:** Microsoft Intune. macOS does not
> "Entra-join" in the Windows sense; the equivalent governance state
> is **Supervised + ADE-enrolled into Intune as MDM**.

---

## Phase 1 — Procure (macOS-specific)

The Phase 1 mechanics in [`../process.md`](../process.md) apply
without modification. macOS-specific intake fields:

- `asset_class` = `macos-endpoint` (MacBook Air, MacBook Pro, iMac,
  Mac mini, Mac Studio)
- `vendor_program` is one of:
  - `apple-abm` — Apple Business Manager (commercial / federal /
    state / local government)
  - `apple-asm` — Apple School Manager (educational institutions)

The procurement organization must be enrolled in ABM or ASM as a
prerequisite. Apple verifies organizational eligibility through
D-UNS number for commercial, agency identifiers for federal/state.

---

## Phase 2 — Pre-stage (ABM/ASM mechanics)

### 2.1 — Hardware enrollment to ABM

Apple hardware enters ABM/ASM through one of three paths:

| Source | Method |
|---|---|
| Apple direct purchase | Apple's order pipeline registers the hardware to the customer's ABM organization at fulfillment |
| Apple Authorized Reseller | Reseller registers the device using their reseller ID against the organization's ABM token; appears in ABM within 24–72 hours |
| Manual upload (existing devices) | Apple Configurator on a Mac enrolls a connected iOS/iPadOS device or supervises a connected macOS device, exporting an ABM-compatible record |

For Intune-first net-new procurement, the recommended path is
**Apple direct purchase or Apple Authorized Reseller**. Manual
Apple Configurator-based enrollment is an exception path used only
for hardware that pre-dates the organization's ABM enrollment.

### 2.2 — MDM server assignment

Within ABM, each device record can be assigned to an MDM server. The
MDM server is the connection ABM has to the organization's MDM
solution (in this case, Microsoft Intune). The MDM server connection
is established once at organizational onboarding via:

1. ABM portal → Settings → MDM Servers → Add MDM Server
2. Upload an MDM server token from Intune (Endpoint Manager admin
   center → Devices → Enroll devices → Apple Enrollment → Enrollment
   Program Tokens)

Each managed device must be assigned to this MDM server. Devices
not assigned to any MDM server are owned by the organization but not
under management — a governance gap this doctrine forbids.

### 2.3 — OrgPath carrier on the ABM device record

ABM device records support a free-text **device note** field. This
bundle's convention:

```
device_note = "OrgPath:" + asset_orgpath
```

The procurement system writes this device note via the ABM API at the
same time it assigns the device to the Intune MDM server. The device
note is the carrier signal that the runtime macOS enrollment
pre-stage script reads in Phase 4.

ABM does not have a Windows-Autopilot-equivalent Group Tag
mechanism — the device note is the closest available carrier. The
device note is mutable, which is a weaker guarantee than Autopilot's
Group Tag (which is also mutable but more directly integrated with
deployment profile selection). The compensating control: the
governance pipeline polls ABM device records and validates that
notes have not drifted from procurement record values, raising a
drift event on any divergence.

### 2.4 — Enrollment profile assignment

Within Intune, an Apple Enrollment Profile is configured per
deployment scenario:

| Profile | Use |
|---|---|
| `macos-personal` | User-affinity enrollment for personally-assigned Mac |
| `macos-shared` | Device-affinity enrollment for shared Macs |
| `macos-kiosk` | Device-affinity, no user enrollment, single-app or kiosk-mode profile |
| `macos-lab` | Device-affinity, lab equipment profile |

The procurement system's Phase 2 step assigns the device to the
appropriate enrollment profile based on `asset_assignment_type`.

Within Intune, the enrollment profile governs the macOS Setup
Assistant experience: which screens are skipped (privacy, location,
analytics, Apple Pay, Siri), whether the device requires
Supervision (yes, always — Supervision is the macOS analog of
Entra-Join's elevated trust), and whether the user account on the
Mac is set up as a managed account or local account.

---

## Phase 3 — Position (macOS mechanics)

Phase 3 produces an entry in:

```
governance/macos/orgpath-mapping.csv
```

with columns: `SerialNumber`, `OrgPath`, `OrgNodeId`, `Source`,
`AssignmentType`, `RecipientUPN`, `EnrollmentProfile`. The
macOS-specific dry-run validation:

1. The pipeline retrieves the ABM device record by serial
2. Validates that the device is assigned to the Intune MDM server
3. Validates that the device note matches `OrgPath:{asset_orgpath}`
4. Validates that the Intune enrollment profile matches the
   procurement-recorded `asset_assignment_type`
5. Validates that the enrollment profile is configured to require
   Supervision

A mismatch at any step is a Phase 3 blocking error.

---

## Phase 4 — Provision (macOS Setup Assistant + ADE enrollment)

### 4.1 — Setup Assistant

The user powers on the Mac. macOS Setup Assistant connects to
Apple's activation servers, which check the device's serial against
ABM. The device is identified as ADE-enrolled and assigned to the
organization's Intune MDM server. The Setup Assistant skips the
screens configured-skip in the enrollment profile and proceeds to
the management-handshake step.

For User-affinity (personal) enrollment, the user signs in with
their Entra ID credentials. The user is challenged for MFA per
Conditional Access. After successful authentication, the Mac
proceeds to enrollment.

For Device-affinity (shared/kiosk/lab), no user sign-in occurs. The
Mac authenticates itself to Intune via the ADE token.

### 4.2 — Initial enrollment payload

Intune delivers the initial enrollment payload to the Mac:

- Management profile (the MDM enrollment payload)
- Initial configuration profiles (filevault, password policy, Wi-Fi,
  certificate trust, root CA bundle)
- The OrgPath stamping launch agent (see §4.3 below)
- Required first-run scripts

The enrollment payload includes a PKCS-distributed certificate from
the governance App Registration's certificate authority, used for
the OrgPath stamping script's authentication to Microsoft Graph.

### 4.3 — OrgPath stamping (macOS-specific)

The OrgPath/Intune narrative was authored for Windows; the macOS
equivalent of the OrgPath stamping script is a launch agent
deployed via Intune's macOS shell script feature. The script runs
as root after enrollment completes and:

1. Reads the device's serial number via `system_profiler
   SPHardwareDataType`
2. Authenticates to Microsoft Graph using the certificate-based
   service principal from the PKCS-distributed certificate (using
   `msgraph-cli` or a small Swift binary distributed via Intune)
3. Looks up the corresponding Autopilot-equivalent record by serial
   (via the ABM device record's note field, fetched through the
   Intune Graph API endpoint for device enrollment programs)
4. Determines `$deviceOrgPath` using the same source priority as the
   Windows script (procurement record → mapping CSV → user
   derivation → quarantine)
5. Writes `$deviceOrgPath` to the device's OrgPath extension
   attribute via Graph (`Update-MgDevice` equivalent — the device
   object exists in Entra ID with the macOS device ID)

The macOS device object in Entra ID is created automatically when
the Mac enrolls in Intune; Intune writes the device to Entra ID via
the Apple device management plane.

### 4.4 — Dynamic group convergence

After OrgPath is stamped, the Entra ID dynamic group membership
engine re-evaluates the macOS device against rules. The device
appears in its ORG-NODE-* and ORG-BRANCH-* groups. macOS-specific
configuration profiles assigned to those groups deliver to the
device on its next MDM check-in.

### 4.5 — First compliance evaluation

Compliance policies for macOS are evaluated on a different cadence
from Windows — Intune for macOS evaluates compliance on each MDM
check-in. The first evaluation typically completes within 15
minutes of enrollment. The compliance policy includes:

- FileVault encryption enabled
- System Integrity Protection enabled
- Gatekeeper enabled
- Firewall enabled with stealth mode (per organizational policy)
- Minimum macOS version
- Password policy (length, complexity, lockout)

A compliant Mac satisfies the Conditional Access compliance grant
control.

---

## Phase 5 — Validate (macOS-specific checks)

The full validation checklist is in
[`../validation-and-evidence.md`](../validation-and-evidence.md).
macOS-specific items:

- [ ] Device is **Supervised** (verify in Intune device details, or
      via `profiles status -type enrollment` on the device)
- [ ] Device is enrolled via ADE (not user-driven enrollment) — the
      `Device.deviceManagementType` is `appleDevice` with
      `enrollmentType` of `appleBulkWithUser` or
      `appleBulkWithoutUser`
- [ ] ABM device record's note field matches
      `OrgPath:{asset_orgpath}` from the procurement record
- [ ] OrgPath extension attribute on the Entra device object matches
      the procurement-record `asset_orgpath`
- [ ] Intune device category matches the OrgTree node type
- [ ] FileVault is enabled and recovery key escrowed to Intune
- [ ] First Conditional Access grant log entry exists

---

## Anti-patterns explicitly forbidden

The following macOS-specific patterns are forbidden by this doctrine
for net-new assets:

- **Manual MDM enrollment** via the Profiles preference pane.
  Bypasses ADE and produces a non-Supervised state — exception path A
  only.
- **Apple Configurator manual supervision** for net-new hardware.
  Apple Configurator is an exception path for pre-ABM hardware only.
- **Jamf Pro / Kandji / Mosyle as primary MDM** in lieu of Intune.
  Pillar 4 — Intune is the canonical management plane. Third-party
  MDMs may be acceptable as compensating tools where Intune lacks
  capability, but they cannot be primary for net-new assets without
  an ADR explicitly carving them out.
- **Local administrator-mode operation** without Supervision.
  Supervised mode is required for the governance pipeline to enforce
  configuration profiles.
- **macOS join to Active Directory** via the legacy AD bind feature.
  Generalization of ADR-001 to macOS — no AD bind for new Macs.

If any of these patterns is operationally required for a specific
asset class, an exception grant is required per
[`../doctrine.md`](../doctrine.md) §4.

---

## Vendor-specific notes

### Apple direct purchase

Apple's enterprise sales channel registers hardware to ABM
automatically at fulfillment. The procurement system supplies the
ABM organization ID at order time; Apple writes the device record
upon shipment.

### Apple Authorized Resellers

CDW-G, SHI, Insight, and other federal Apple resellers register
hardware to the customer's ABM via the reseller integration.
Registration latency is 24–72 hours after shipment.

### Existing-fleet integration via Apple Configurator

For existing Macs not in ABM, Apple Configurator on a connected Mac
can supervise the device and produce an ABM-compatible record. This
is the exception path for hardware that pre-dates the ABM
enrollment of the organization. Use only with documented exception
grant.

---

## Differences from Windows

The Windows and macOS processes are structurally identical (same
five phases, same OrgPath carrier, same compliance integration) but
mechanically different:

| Aspect | Windows | macOS |
|---|---|---|
| Device enrollment program | Autopilot | ABM/ASM ADE |
| OrgPath carrier in vendor program | Group Tag | Device note |
| Trust elevation state | Entra Join | Supervision |
| Initial OS experience | OOBE + ESP | Setup Assistant + initial enrollment payload |
| OrgPath stamping mechanism | PowerShell script during ESP Account Setup | Shell script run as root post-enrollment |
| Compliance evaluation cadence | Periodic + sync-triggered | Per MDM check-in |
| User-affinity model | Primary user assignment | User-affinity at enrollment time |

---

## References

- OrgPath/Intune narrative §4 (Autopilot enrollment — referenced for
  the OrgPath stamping pattern adapted to macOS) — `inbox/drafts/complete-narrative/source-docx/OrgPath and Microsoft Intune — Structural Device Governance at Enterprise Scale.md`
- [Microsoft Learn — Set up Microsoft Intune enrollment for Apple devices](https://learn.microsoft.com/en-us/mem/intune/enrollment/device-enrollment-program-enroll-macos)
- [Apple Support — About ABM/ASM Automated Device Enrollment](https://support.apple.com/guide/apple-business-manager/intro-to-automated-device-enrollment-axm402c5a5b/web)
- [Microsoft Learn — Configure Intune as MDM in ABM](https://learn.microsoft.com/en-us/mem/intune/enrollment/device-enrollment-program-enroll-ios)
