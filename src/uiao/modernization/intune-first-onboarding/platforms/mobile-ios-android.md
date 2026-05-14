---
document_id: IFO_012
title: "Platform Annex — Mobile (iOS/iPadOS and Android Enterprise)"
version: "1.0"
status: CANONICAL
owner: "Michael Stratton"
created_at: "2026-05-13"
updated_at: "2026-05-14"
boundary: GCC-Moderate
canon_anchor: ADR-067
platform: mobile
publish_to_site: true
publication_style: narrative
published_at: docs/modernization/intune-first.qmd
---

# Platform Annex — Mobile (iOS/iPadOS and Android Enterprise)

> Per-platform implementation of the five-phase Intune-first process
> for corporate-owned mobile devices. Process is the same as in
> [`../process.md`](../process.md); this annex specifies the
> mobile-specific mechanics.
>
> **Two platforms, two enrollment programs, one doctrine.** iOS/iPadOS
> uses Apple ABM/ASM ADE (the same vendor program as macOS — see
> [`macos-abm-ade.md`](macos-abm-ade.md) for shared mechanics).
> Android uses Android Zero-Touch Enrollment (Google) or Samsung Knox
> Mobile Enrollment (Samsung-specific).
>
> **BYOD is exception path A**, not the default. Doctrine pillar 2
> requires procurement-time governance, which is structurally
> impossible for a device the organization did not purchase. BYOD is
> documented in [`../doctrine.md`](../doctrine.md) §4 — Exception
> Path A.

---

## Part A — iOS / iPadOS via ABM/ASM ADE

### A.1 — Procure (iOS-specific)

- `asset_class` = `ios-phone` (iPhone) or `ios-tablet` (iPad)
- `vendor_program` = `apple-abm` (commercial / federal / state /
  local) or `apple-asm` (educational)
- The procurement organization must be enrolled in ABM/ASM (same
  prerequisite as macOS — see [`macos-abm-ade.md`](macos-abm-ade.md)
  §1)

### A.2 — Pre-stage (iOS mechanics)

iOS pre-stage mechanics mirror macOS exactly. The differences:

- iOS enrollment profiles in Intune are configured for iOS/iPadOS
  rather than macOS
- Setup Assistant skip-pane configuration differs (iOS has Wallet,
  Apple Pay, App Analytics, Display Tone, Restore from iCloud
  panes that macOS does not)
- iOS Supervised mode is required (per Apple, only ADE-enrolled iOS
  devices can be Supervised)

The OrgPath carrier is the same — the ABM device record's note
field. The procurement system writes
`device_note = "OrgPath:" + asset_orgpath` at the same time it
assigns the device to the Intune MDM server.

### A.3 — Position (iOS mechanics)

Mapping file:

```
governance/ios/orgpath-mapping.csv
```

Schema and dry-run validation are equivalent to the macOS process,
adjusted for iOS-specific enrollment profile naming.

### A.4 — Provision (iOS Setup Assistant + ADE)

The flow is the iOS analog of the macOS Setup Assistant flow:

1. User powers on the device
2. iOS Setup Assistant connects to Apple activation
3. Activation identifies the device as ADE-enrolled to the
   organization's Intune MDM server
4. Skip panes per the enrollment profile
5. (User-affinity) User signs in with Entra ID, MFA challenge per CA,
   user-affinity established
6. Initial enrollment payload delivered (management profile, baseline
   configuration profiles, certificate trust)

OrgPath stamping for iOS happens at a different layer than macOS or
Windows. iOS does not allow arbitrary scripts to run on the device
post-enrollment — script execution is forbidden on iOS for security
reasons. Instead, OrgPath is stamped by an Intune-side process
triggered by the device's first check-in:

1. Intune detects new ADE-enrolled device check-in
2. The Intune-side OrgPath stamping job (an Azure Function or Logic
   App in the governance subscription) triggers on the
   `iosUpdatedManagedDevices` Microsoft Graph webhook
3. The job reads the device's ABM record (via the Intune Graph API
   for device enrollment programs) and extracts the OrgPath from
   the device note
4. The job writes OrgPath to the iOS device object in Entra ID

This Intune-side stamping flow is the iOS-specific implementation;
the result (OrgPath stamped on the device object) matches the
Windows and macOS outcomes.

### A.5 — iOS-specific compliance items

- Passcode: 6-digit minimum, alphanumeric for `/Root/Finance` and
  similar high-sensitivity branches
- Jailbreak detection: required, non-compliant if jailbroken
- Minimum iOS version per organizational policy
- Required apps: organizational signing certificate trust app, the
  governance pipeline's compliance check apps
- Personal hotspot: disabled or restricted per branch policy
- iCloud backup: organizational policy decision (typically restricted
  for high-sensitivity branches; permitted for general-purpose
  devices)

---

## Part B — Android via Zero-Touch and Knox Mobile Enrollment

Android Enterprise has two enrollment programs depending on device
manufacturer:

| Program | Manufacturer scope | Operator |
|---|---|---|
| Android Zero-Touch Enrollment | Most Android Enterprise Recommended devices (Google Pixel, Sony Xperia, OnePlus, Nokia, etc.) | Google |
| Samsung Knox Mobile Enrollment (KME) | Samsung Galaxy enterprise SKUs | Samsung |

Both programs achieve the same governance outcome — corporate-owned
fully-managed device or dedicated device profile, enrolled into
Intune. The difference is the vendor program and procurement
integration path. This bundle treats them as parallel
implementations of the same process.

### B.1 — Procure (Android-specific)

- `asset_class` = `android-phone` or `android-tablet`
- `vendor_program` = `android-zerotouch` or `samsung-knox-me`
- For Samsung devices, both programs may apply; the convention is
  to use Knox Mobile Enrollment for Samsung Galaxy (Knox
  capabilities) and Android Zero-Touch as a fallback
- Android Enterprise enrollment mode is one of:
  - `fully-managed` — corporate-owned, work-only profile
  - `corporate-owned-work-profile` — corporate-owned with personal
    work-life separation
  - `dedicated-device` — kiosk or single-purpose device

The enrollment mode is recorded on the procurement record; it
governs which Intune Android Enterprise enrollment profile
the device receives.

### B.2 — Pre-stage (Android mechanics)

#### B.2.1 — Android Zero-Touch (Google)

Hardware enters the Android Zero-Touch portal via:

| Source | Method |
|---|---|
| Reseller (Synnex, TD Synnex, CDW, etc.) | Reseller registers IMEI / serial against the customer's Zero-Touch account at fulfillment |
| Direct from manufacturer | Manufacturer registers via OEM portal for Pixel, Nokia, Sony, etc. |
| Manual upload | Zero-Touch admin uploads CSV of IMEI / serials for existing devices (exception path) |

Within the Zero-Touch portal, each device is assigned to a
**configuration**. The configuration defines:

- Default MDM (Microsoft Intune)
- Custom JSON config payload — this is the Android equivalent of the
  Autopilot Group Tag and the ABM device note
- Optional metadata fields (asset tag, etc.)

This bundle's convention for the custom JSON config:

```json
{
  "android.app.extra.PROVISIONING_ADMIN_EXTRAS_BUNDLE": {
    "OrgPath": "/Root/Finance/Accounting/AccountsReceivable",
    "OrgNodeId": "AR-NODE-042",
    "AssignmentType": "personal",
    "RecipientUPN": "j.smith@agency.gov"
  }
}
```

The procurement system writes this configuration via the Zero-Touch
Customer API at the same time it assigns the device to the
configuration.

#### B.2.2 — Samsung Knox Mobile Enrollment

Samsung's Knox Mobile Enrollment (KME) is the Samsung-specific
parallel to Zero-Touch. Hardware enters KME via:

| Source | Method |
|---|---|
| Samsung Reseller | Reseller registers IMEI / serial against the customer's KME account |
| Knox Deployment App | Manual enrollment via app for existing devices (exception path) |
| Direct purchase from Samsung B2B | Samsung registers at fulfillment |

KME devices are assigned to a **profile** that defines the MDM
agent installer URL (Microsoft Intune Company Portal),
configuration payload, and Knox-specific platform settings.

This bundle's convention for the KME custom JSON:

```json
{
  "OrgPath": "/Root/Finance/Accounting/AccountsReceivable",
  "OrgNodeId": "AR-NODE-042",
  "AssignmentType": "personal",
  "RecipientUPN": "j.smith@agency.gov"
}
```

Passed via the KME profile's `customJSON` field.

### B.3 — Position (Android mechanics)

Mapping file:

```
governance/android/orgpath-mapping.csv
```

with columns: `IMEI`, `SerialNumber`, `OrgPath`, `OrgNodeId`,
`Source`, `AssignmentType`, `RecipientUPN`, `EnrollmentProgram`
(zero-touch / knox-me), `EnrollmentMode` (fully-managed /
corporate-owned-work-profile / dedicated-device).

Dry-run validation:

1. Pipeline retrieves the Zero-Touch or KME device record
2. Validates the device is assigned to the appropriate configuration/
   profile
3. Validates the OrgPath value in the custom JSON matches procurement
4. Validates the enrollment mode matches procurement

### B.4 — Provision (Android Enterprise enrollment)

#### B.4.1 — Android Zero-Touch flow

1. User powers on the device
2. Setup wizard detects Zero-Touch registration via
   `factory_reset_protection` payload
3. Device downloads the configured MDM agent (Intune Company Portal)
4. Company Portal installs and runs first-launch
5. (Fully-managed / corporate-owned-work-profile) device is
   provisioned as Android Enterprise device owner
6. (Personal-affinity modes) user signs in with Entra ID
7. Intune delivers the initial enrollment payload, including
   configuration profiles for the device's branch group

#### B.4.2 — Samsung KME flow

Mechanically similar to Zero-Touch:

1. User powers on the Samsung device
2. Setup wizard detects KME registration
3. Knox Manage agent (or Intune Company Portal, per profile config)
   installs
4. Device is provisioned per the Knox Mobile Enrollment profile
5. (User-affinity) user signs in with Entra ID
6. Initial enrollment payload delivered

#### B.4.3 — OrgPath stamping (Android-specific)

Android Enterprise managed configuration values (the custom JSON
from Phase 2) are accessible to managed apps via the
`RestrictionsManager` API. The OrgPath value is stamped on the
Entra ID device object via:

1. Intune detects new Android device enrollment
2. Intune-side OrgPath stamping job (Azure Function — same pattern
   as iOS) triggers on Android device check-in webhook
3. The job reads the managed configuration payload (with OrgPath)
   that was delivered to the device via the Zero-Touch / KME
   configuration
4. The job writes OrgPath to the Android device object in Entra ID

The device-side path: a managed configuration value is delivered to
the Intune Company Portal app; the Company Portal app reads OrgPath
on first launch and reports it back to Intune via its standard
device-property reporting mechanism. The Intune-side job is the
canonical write path; the Company Portal-side report is verification.

### B.5 — Android-specific compliance items

- Device encryption: required
- SafetyNet attestation (or its successor, Google Play Integrity API):
  required, non-compliant if attestation fails (root detection)
- Minimum Android version per organizational policy
- Required apps: Intune Company Portal, certificate trust apps, branch-
  specific apps
- Work profile separation enforced for `corporate-owned-work-profile`
  mode
- Knox Mobile Enrollment-only items: Knox Configure profile (Samsung
  hardware enforcement), Knox Mobile Threat Defense (if licensed)

---

## Part C — Cross-mobile validation (Phase 5)

The full validation checklist is in
[`../validation-and-evidence.md`](../validation-and-evidence.md).
Mobile-specific items (cover both iOS and Android):

- [ ] Device is enrolled in Intune via the corporate enrollment
      program (ADE for iOS; Zero-Touch or KME for Android), not via
      user-driven enrollment
- [ ] Device's enrollment program record carries the procurement-
      assigned OrgPath value
- [ ] OrgPath extension attribute on the Entra device object matches
      the procurement-record `asset_orgpath`
- [ ] (iOS) Device is Supervised
- [ ] (Android Zero-Touch / KME) Device is in `fully-managed`,
      `corporate-owned-work-profile`, or `dedicated-device` mode —
      not in BYOD work-profile mode
- [ ] Compliance policy result is recorded and is Compliant
- [ ] (iOS) Jailbreak detection passed
- [ ] (Android) SafetyNet / Play Integrity attestation passed

---

## Anti-patterns explicitly forbidden

- **User-driven enrollment via Company Portal** as the primary
  enrollment vector. Exception path A only (BYOD).
- **iOS user-enrolled (formerly "BYOD enrollment")** for corporate-
  owned hardware. Use ADE for corporate ownership.
- **Android personal device enrollment with work profile** for
  corporate-owned hardware. Use Zero-Touch or KME for corporate
  ownership.
- **Device Owner mode without enrollment program registration**
  (e.g., QR-code enrollment of an existing device for Android
  Enterprise). This is exception path A only.
- **MDM other than Intune** as primary for new mobile fleet. Pillar
  4 — Intune is the canonical management plane. Knox Manage may
  operate in conjunction with Intune for Samsung-specific features
  but cannot be primary.

---

## Vendor-specific notes

### Apple resellers for iOS/iPadOS

Same as macOS — Apple direct, Apple Authorized Resellers (CDW-G,
SHI, Insight) supporting ABM device assignment at fulfillment.

### Android Zero-Touch reseller integration

Reseller integration with Zero-Touch is per-reseller. CDW, SHI,
Insight, and TD Synnex have established Zero-Touch integration for
Pixel, Sony, Nokia, OnePlus, and Android Enterprise Recommended
devices. The procurement system supplies the Zero-Touch
configuration ID at order time.

### Samsung Knox Mobile Enrollment

Samsung's KME requires the customer to be enrolled in the Samsung
Knox Customer Portal. Authorized Samsung resellers can register
Galaxy devices to the customer's KME account at fulfillment.

---

## Differences between iOS and Android within mobile

| Aspect | iOS / iPadOS | Android Enterprise |
|---|---|---|
| Vendor enrollment program | ABM / ASM | Zero-Touch (Google) or KME (Samsung) |
| OrgPath carrier in vendor program | ABM device note | Custom JSON managed config |
| Trust elevation state | Supervised (via ADE) | Device Owner / Profile Owner mode |
| Initial OS experience | Setup Assistant | Setup Wizard |
| OrgPath stamping mechanism | Intune-side Azure Function (iOS does not allow scripts) | Intune-side Azure Function with managed config delivery to Company Portal |
| Compliance evaluation | Per MDM check-in | Per MDM check-in with platform attestation |
| Work-personal separation | App management policies (no work-profile concept on iOS) | Work profile (corporate-owned-work-profile mode) or fully-managed (no personal partition) |

---

## References

- [Microsoft Learn — Set up iOS/iPadOS device enrollment in Intune](https://learn.microsoft.com/en-us/mem/intune/enrollment/ios-enrollment-methods)
- [Microsoft Learn — Set up Android Enterprise enrollment](https://learn.microsoft.com/en-us/mem/intune/enrollment/android-enrollment-overview)
- [Google — Android Zero-Touch Enrollment](https://www.android.com/enterprise/management/zero-touch/)
- [Samsung — Knox Mobile Enrollment](https://www.samsungknox.com/en/solutions/it-solutions/knox-mobile-enrollment)
- [`macos-abm-ade.md`](macos-abm-ade.md) for shared ABM mechanics with iOS
- OrgPath/Intune narrative — `inbox/drafts/complete-narrative/source-docx/OrgPath and Microsoft Intune — Structural Device Governance at Enterprise Scale.md`
