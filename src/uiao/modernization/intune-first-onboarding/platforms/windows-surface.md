---
document_id: IFO_014
title: "Platform Annex — Microsoft Surface Endpoints (sub-pattern of Windows Autopilot)"
version: "1.0"
status: CANONICAL
owner: "Michael Stratton"
created_at: "2026-05-18"
updated_at: "2026-05-18"
boundary: GCC-Moderate
canon_anchor: ADR-071
platform: windows-endpoint-surface
publish_to_site: true
publication_style: narrative
published_at: docs/modernization/intune-first.qmd
---

# Platform Annex — Microsoft Surface Endpoints

> **This annex is a sub-pattern of [`windows-autopilot.md`](windows-autopilot.md).**
> Everything in the Windows Autopilot annex applies to Surface
> without modification. This document specifies *only the
> Surface-specific deltas*: DFCI lockdown, Pluton attestation where
> the underlying silicon supports it, Windows Hello for Business
> delivery on Surface IR cameras / fingerprint sensors, the Surface
> Registration / Microsoft CSP vendor pre-registration lane, and
> the Surface Management Portal fleet-telemetry workspace.
>
> **Asset class:** `windows-endpoint` with sub-class
> `windows-endpoint-surface`.
>
> **Canonical join target:** Microsoft Entra Join (per ADR-001 —
> identical to the parent annex; HAADJ and domain-join remain
> forbidden).
>
> **Surface Hub handling per ADR-075.** Surface Hub-class hardware
> running Microsoft Teams Rooms (MTR) on Windows — i.e., Surface
> Hub 3 (factory), Surface Hub 2S upgraded with Surface Hub 3
> Compute Cartridge, or Surface Hub 2S software-migrated to MTR on
> Windows — is governed identically to any other Surface form
> factor under this annex (Entra-joined Windows endpoint, Autopilot
> + Auto-login of Teams Rooms, DFCI). Surface Hub running the
> Windows 10 Team edition variant is NOT covered by this annex —
> Windows 10 Team edition reached end of support on 2025-10-14 and
> is migration-only per ADR-075. Net-new procurement of
> Windows-10-Team-edition Surface Hub configurations is forbidden;
> Surface Hub v1 is retired (no migration path).

---

## Phase 1 — Procure (Surface-specific)

Phase 1 mechanics from [`../process.md`](../process.md) and
[`windows-autopilot.md`](windows-autopilot.md) §1 apply without
modification. Surface-specific intake fields:

- `asset_class` = `windows-endpoint`
- `asset_sub_class` = `windows-endpoint-surface`
- `surface_form_factor` is one of:
  - `surface-pro` — Pro 9, Pro 10, Pro 11, future Pro generations
  - `surface-laptop` — Laptop 5, Laptop 6, Laptop 7, future generations
  - `surface-laptop-studio` — Studio 1, Studio 2, future generations
  - `surface-book` — Book 3 (legacy; out of net-new procurement as of 2026)
  - `surface-go` — Go 3, Go 4, future Go generations
  - `surface-studio` — Studio 2+ desktop
  - `surface-hub-3` — meeting-room class, Surface Hub 3 (factory MTR on Windows); ALL net-new procurement of meeting-room class must specify this configuration
  - `surface-hub-2s` — **forbidden for net-new procurement** (no longer commercially available as net-new from Microsoft; Windows 10 Team edition is out of support); existing units are migration targets per ADR-075
  - `surface-hub-v1` — **retired; no migration path; hardware refresh required**
- `vendor_program` is one of:
  - `surface-csp-partner` — Surface partner enabled for Autopilot
    (per Microsoft Learn's "Surface partners enabled for Autopilot"
    list). Recommended for Surface Hub 3 to capture the 14-digit
    alphanumeric serial number on the Autopilot service before
    shipping; partner registers the hardware hash + Group Tag at
    fulfillment time.
  - `surface-direct-microsoft` — direct purchase through Microsoft
    commercial channel; hardware hashes pre-registered via
    Microsoft Cloud Solution Provider (CSP) APIs into the customer
    tenant
  - `surface-distributor` — distributor pass-through to a Surface
    CSP partner

DFCI eligibility (see §2.2) requires CSP-partner or OEM-direct
registration. Manually-imported hardware hashes (the
`Get-WindowsAutopilotInfo` path) are **not eligible for DFCI** by
Microsoft design — this is a Microsoft Learn-documented constraint,
not a UIAO policy choice. Procurement that depends on DFCI must
use `surface-csp-partner` or `surface-direct-microsoft`.

The `vendor_program_records[]` schema from
[`windows-autopilot.md`](windows-autopilot.md) §1 is unchanged;
Surface-specific records add `surface_registration_portal_url`
(the CSP-partner portal record link) for traceability and
`autopilot_serial_format` (one of `14-digit-alphanumeric` for
Surface Hub 3 factory, `12-digit-numeric` for Surface Hub 3
customer-driven, or `oem-standard` for other Surface form factors)
because Surface Hub 3 has distinct serial-number formats that
gate the available Autopilot enrollment methods.

---

## Phase 2 — Pre-stage (Surface-specific mechanics)

### 2.1 — Hardware-hash registration

Identical to [`windows-autopilot.md`](windows-autopilot.md) §2.1
*except* the recommended path:

| Path | Used for Surface |
|---|---|
| **Surface partner pre-registration** (`surface-csp-partner`) — Microsoft / authorized partner writes the hash and Group Tag to the customer tenant before shipping | Recommended for all Surface form factors. Required for DFCI eligibility. |
| **Direct Microsoft commercial channel** (`surface-direct-microsoft`) with Microsoft CSP pre-registration | Recommended. Required for DFCI eligibility. |
| Manual registration via `Get-WindowsAutopilotInfo` | Exception-only for Surface hardware that arrived without pre-registration. **Forfeits DFCI eligibility** by Microsoft design. |

The Group Tag convention `groupTag = "OrgPath:" + asset_orgpath`
from [`windows-autopilot.md`](windows-autopilot.md) §2.2 is
identical and required.

### 2.2 — DFCI profile assignment (Surface-distinctive)

Surface is the reference device for DFCI (Device Firmware
Configuration Interface). DFCI authoring is an Intune
configuration-profile class (`Windows 10 and later → Templates →
Device Firmware Configuration Interface`) that writes UEFI-level
settings the signed-in user cannot reverse, even with local admin.
DFCI's trust chain uses public-key cryptography and does not
depend on local UEFI password security.

**DFCI prerequisites (per Microsoft documentation):**
1. Device manufacturer must have DFCI added to UEFI firmware (Surface generations from Surface Pro 7+, Surface Laptop 3+, Surface Book 3, Surface Go 2+, and **Surface Hub 3** all support DFCI as of 2026).
2. Device must be registered for Windows Autopilot by a **Microsoft Cloud Solution Provider partner** or **registered directly by the OEM** — manually-imported hashes are not eligible.
3. Both a Windows Autopilot deployment profile and an Enrollment Status Page profile must be assigned to the device's Entra security group before the DFCI profile is applied.

For every Surface deployed under this annex with DFCI-eligible
registration, a DFCI profile MUST be assigned through the same
OrgPath-prefixed Group-Tag dynamic group used for the Autopilot
deployment profile. The DFCI profile locks at minimum:

- **Cameras** — disabled by default for service / kiosk / lab
  assignment types; enabled with documented exception for personal
  and shared assignment types
- **Microphones** — same posture as cameras
- **Wireless radios** (Bluetooth, Wi-Fi) — Bluetooth disabled by
  default for service / kiosk / lab; Wi-Fi enabled for all (note:
  DFCI's category setting `Radios (Bluetooth, Wi-Fi, NFC, etc.)`
  conflicts with the granular per-radio settings if both are
  configured — use the granular Wi-Fi / Bluetooth / NFC settings
  and leave the category set to Not configured to avoid the
  documented configuration loop)
- **USB ports** — locked to "no boot from USB" for all asset types
  (prevents offline-image reboot bypass); per-port data-mode
  lockdown follows the asset's OrgPath compliance branch
- **Boot order** — internal storage first; PXE/network boot
  disabled
- **Hibernate / sleep firmware behavior** — set to enterprise
  defaults documented per OrgPath branch
- **Built-in audio / built-in keyboard / built-in trackpad** —
  enabled (these flags exist for kiosk hardening scenarios;
  default posture is enabled)
- **Allow local user to change UEFI (BIOS) settings** — set to
  "Only not configured settings" for all assignment types except
  retire / decommission state

The DFCI profile is **distinct from** the generic device
configuration profile. Both are assigned to the same OrgPath
dynamic group.

**DFCI reboot sequence (per Microsoft Learn):** During Autopilot
provisioning, the Enrollment Status Page may force a reboot — this
first reboot enrolls UEFI to Intune. After the Intune service has
delivered the DFCI settings to Windows, a second reboot is
required for UEFI to receive the DFCI settings from Windows. Plan
ESP timeouts accordingly.

The compliance policy assigned to the same group includes a
DFCI-applied check (settings catalog `firmware/dfci-status =
applied`); a Surface where DFCI did not apply (e.g., DFCI-
ineligible registration path, or older firmware that lacks DFCI
support) is non-compliant and fails Conditional Access.

DFCI authoring is covered by the existing modernization-side
`intune` reserved slot (ADR-049 / [`intune.qmd:37`](../../docs/customer-documents/adapter-specs/intune/intune.qmd))
— no new adapter slot is required for the authoring surface.

### 2.3 — Pluton firmware update path (where supported by chipset)

Microsoft Pluton is a **chipset feature**, not a Surface-vendor
feature. Surface devices receive Pluton when the underlying
silicon supports it: AMD Ryzen 6000 / 7000 / 8000 / 9000 / Ryzen
AI series, Intel Core Ultra 200V / Ultra Series 3 / Series 3
processors, and Qualcomm Snapdragon 8cx Gen 3 / Snapdragon X
series. Surface generations that ship with these chipsets
(Surface Pro 11 SQ series, Surface Laptop 6 / 7 with current Intel
Core Ultra silicon, etc.) get Pluton; older Surface generations
use the discrete TPM 2.0 module instead.

When Pluton is present and configured as the system TPM, Pluton
firmware updates flow through Windows Update for Business — the
firmware lifecycle is Microsoft-managed via OS update, distinct
from third-party TPM firmware that ships through OEM-specific
update channels. The Phase 2 pre-stage MUST verify the Windows
Update for Business ring assignment for the OrgPath branch
includes the Pluton-relevant update channel.

For Surface devices without Pluton (older generations or chipsets
that do not include Pluton), the discrete TPM 2.0 module is the
attestation source; OEM firmware updates flow through Surface
firmware update packages distributed via the Surface Management
Portal and Intune.

The branch update-ring policy assigned through
`entra-policy-targeting` is the authoring surface for this
binding — no new adapter slot.

---

## Phase 3 — Position (no Surface-specific delta)

Phase 3 mechanics from [`../process.md`](../process.md) §3 and
[`windows-autopilot.md`](windows-autopilot.md) §3 apply without
modification. The dry-run validation entries for a Surface in
`governance/autopilot/orgpath-mapping.csv` include the DFCI-
profile assignment check (added column: `DfciProfileId`) and the
DFCI-eligibility check (added column: `DfciEligible`, derived from
`vendor_program`).

---

## Phase 4 — Provision (Surface-specific runtime)

The runtime enrollment flow is identical to
[`windows-autopilot.md`](windows-autopilot.md) §4 (OOBE → ESP →
OrgPath stamping → dynamic-group convergence → first compliance
evaluation) with two Surface-specific additions:

### 4.1 — DFCI application during ESP Device Setup

For DFCI-eligible Surface registrations, during the Enrollment
Status Page's **Device Setup** phase, the DFCI profile is applied
alongside other device-targeted configuration profiles. As
documented in §2.2, application of DFCI involves a UEFI-enrollment
reboot and a settings-application reboot — plan ESP duration
accordingly.

A Surface where DFCI was not applied (DFCI-ineligible registration,
or DFCI-eligible registration but UEFI firmware does not support
DFCI) reports `dfciStatus = not-applied`; the compliance policy
fails; Conditional Access blocks access until remediation. There
is no user-driven workaround — this is by design.

### 4.2 — Windows Hello for Business enrollment prompt

On Surface devices with IR camera (Surface Pro / Surface Laptop
Studio / Surface Book) and/or fingerprint reader (Surface Laptop
power-button fingerprint, Surface Type Cover fingerprint), the
post-OOBE Windows Hello provisioning prompt offers face and/or
fingerprint enrollment in addition to PIN.

Per IA-2(1) and IA-5 in the control library, WHfB with TPM-backed
(or Pluton-backed) key storage is an approved authenticator. The
Surface IR-camera and fingerprint paths are the canonical delivery
vehicle for WHfB on Microsoft hardware. The Surface annex requires:

- WHfB enrollment is **not blocked** by the Account Setup ESP
  phase — the user completes WHfB enrollment *after* OOBE/ESP,
  not during, to keep ESP duration bounded
- The Authentication Methods Policy assigned at the tenant level
  enables `windowsHelloForBusiness` with `securityKeyForSignIn:
  enabled` for the OrgPath branches that include Surface assets
- The compliance policy validates `bitlocker = on` AND `tpm-
  present = true` AND `secure-boot = on` — all three are
  preconditions for WHfB key storage in the Pluton / TPM 2.0
  hardware
- For Surface Hub running MTR on Windows, the equivalent
  authentication path is **Auto-login of Teams Rooms** with a
  Resource Account configured via the Teams Rooms Pro Management
  Portal; per-user WHfB does not apply on shared meeting-room
  hardware

WHfB *posture* observation (per-user, per-device enrollment state)
is **not currently a first-class adapter surface**. It is
referenced in IA-2(1) / IA-5 but no conformance adapter observes
the `signInActivity` + `authenticationMethod` Graph endpoints for
WHfB enrollment evidence. This gap is acknowledged in the
companion working-plan draft and deferred for future ADR.

---

## Phase 5 — Validate (Surface-specific checks)

The full validation checklist is in
[`../validation-and-evidence.md`](../validation-and-evidence.md)
and [`windows-autopilot.md`](windows-autopilot.md) §5. Surface-
specific items, in addition:

- [ ] **Surface Management Portal** (a workspace within the
      Microsoft Intune admin center) reports the device with
      current firmware version matching the OrgPath branch's
      target firmware (once the `surface-management-portal`
      conformance adapter is active — until then, manual check
      via the SMP workspace in Intune admin center)
- [ ] DFCI profile is in `applied` state on the device
      (`Get-MgDeviceManagementManagedDeviceComplianceState`
      `dfciStatus`) — only applicable for DFCI-eligible
      registrations
- [ ] DFCI lockdowns visible in UEFI: cameras / microphones /
      Bluetooth / USB boot disabled per the branch DFCI policy
- [ ] BitLocker recovery key escrowed to Entra ID device object
      (this is generic Windows behavior but verify on Surface
      explicitly because of the Pluton key-storage path on
      Pluton-equipped silicon)
- [ ] If device chipset supports Pluton and Pluton is configured
      as the TPM: device reports `tpm-manufacturer = MSFT` and
      `tpm-firmware-version` matches the Windows Update for
      Business ring's target
- [ ] WHfB enrollment is *available* (not necessarily completed)
      for the signed-in user on personally-assigned Surface
      devices: device reports `passwordless-credential-eligible =
      true`. For Surface Hub MTR on Windows, the equivalent check
      is that the Resource Account is configured and the device
      auto-logs into Teams Rooms.
- [ ] Conditional Access compliance grant control allows the
      device through with `dfciStatus = applied` (where
      applicable) AND `complianceState = compliant`
- [ ] Microsoft Cloud Solution Provider or OEM-direct record for
      the device hash matches the customer tenant ID (verifies the
      Surface vendor pre-registration lane completed correctly)
- [ ] For Surface Hub MTR on Windows: device record syncs to the
      Teams Rooms Pro Management Portal **Planning > Autopilot
      Devices** tab; Resource Account assignment for Auto-login
      of Teams Rooms is in place

---

## Anti-patterns explicitly forbidden (Surface-specific)

In addition to the patterns forbidden in
[`windows-autopilot.md`](windows-autopilot.md) §"Anti-patterns":

- **USB recovery image re-imaging that bypasses Autopilot reset.**
  Surface ships a USB recovery image download flow at
  `support.microsoft.com/surface-recovery`. Using this flow on a
  managed Surface bypasses Autopilot enrollment-time governance —
  the device returns to factory state without an Autopilot record
  refresh, and OrgPath stamping does not occur on re-enrollment
  until the hash is re-registered. **Exception:** USB recovery
  image install IS the documented Microsoft path for Surface Hub
  2S migration to MTR on Windows; that exception is governed by
  ADR-075's documented migration paths and is the only authorized
  bypass.

  **Standard remediation path for non-migration recovery:**
  Intune-driven `Autopilot Reset` (preserves enrollment) or
  `Wipe with device retention removed` (re-enrolls via Autopilot
  on next boot).

- **Net-new procurement of Windows-10-Team-edition Surface Hub.**
  Forbidden per ADR-075. Windows 10 Team edition reached end of
  support on 2025-10-14. Net-new Surface Hub procurement MUST
  specify Surface Hub 3 with MTR on Windows.

- **DFCI bypass via UEFI password.** UEFI password on a managed
  Surface is owned by the tenant DFCI policy, not the user. Any
  workflow that involves setting a local UEFI password to bypass
  DFCI is a governance exception requiring documented grant.

- **Disabling Pluton in UEFI on Pluton-equipped Surface.** Where
  the UEFI offers a Pluton on/off toggle, the DFCI profile MUST
  lock Pluton to `on` for any Surface where Pluton is configured
  as the system TPM. Disabling Pluton invalidates BitLocker, WHfB,
  and device attestation simultaneously.

- **Manual `Get-WindowsAutopilotInfo` registration when DFCI is
  required.** By Microsoft design, manually-registered Surface
  devices are not eligible for DFCI. If DFCI is a requirement of
  the OrgPath branch, procurement must use
  `surface-csp-partner` or `surface-direct-microsoft`.

---

## Vendor-specific notes

### Microsoft Surface partners enabled for Autopilot

`vendor_program = surface-csp-partner`. Microsoft maintains a list
of "Surface partners enabled for Autopilot" — partners that have
the integration to write hardware hashes and Group Tags into the
customer tenant before shipping. Use this list at procurement
time to validate that the chosen partner supports Group-Tag-at-
order. Partners on the list typically also support DFCI
prerequisites.

### Microsoft direct (commercial channel)

`vendor_program = surface-direct-microsoft`. Hardware hashes are
pre-registered through the Microsoft commercial channel's CSP
integration. The customer tenant receives the device in the
`Microsoft Intune admin center → Devices → Windows → Windows
enrollment → Devices` list within minutes of order confirmation.

Group Tag assignment at order time is supported through the
commercial portal's order configuration screen — supply the
OrgPath-tagged value (`OrgPath:/Root/...`) at the time of order.

### Surface Hub 3 — Autopilot enrollment methods

Surface Hub 3 has two distinct Autopilot enrollment paths based
on serial-number format:

| Serial format | Enrollment method | Notes |
|---|---|---|
| 14-digit alphanumeric (factory-fresh) | Partner-driven on customer's behalf, OR submit request to Microsoft support | Both methods support DFCI |
| 12-digit numeric | Customer-driven directly in Intune (manual hardware-hash extraction) | DFCI-eligible per Microsoft documentation |

For Surface Hub 2S devices upgraded with a Surface Hub 3 Compute
Cartridge, a new hardware hash is generated for the unique
chassis+cartridge combination — manual hash extraction is
required, customer-driven Intune registration.

For Surface Hub 2S being software-migrated to MTR on Windows, the
hash should be extracted *before* migration (while the device is
still on Windows 10 Team edition) so Autopilot is primed to take
over after the migration completes.

### Surface Hub Pro Management Portal (Auto-login)

The Microsoft Teams Rooms Pro Management Portal at
`Planning > Autopilot Devices` is the configuration plane for the
**Auto-login of Teams Rooms** capability. After a Surface Hub
device is Autopilot-enrolled, it syncs to this tab; admins assign
the Resource Account credentials that drive the Teams Rooms
experience's automatic sign-in. This portal is the only
authorized configuration surface for Surface Hub Auto-login.

### Distributor pass-through

`vendor_program = surface-distributor`. Equivalent to
`surface-csp-partner` provided the distributor is on the Microsoft
"Surface partners enabled for Autopilot" list. Validate Group Tag
support per distributor account before standardizing.

---

## References

- [ADR-001 — HAADJ Deprecated, Entra-Join-only](../../../../docs/adr/adr-001-haadj-deprecated-entra-join-only.qmd)
- [ADR-071 — Intune-First Asset Onboarding](../../../canon/adr/adr-071-intune-first-asset-onboarding.md)
- [ADR-075 — Surface Hub Reconciliation](../../../canon/adr/adr-075-surface-hub-reconciliation.md)
- [Parent annex — Windows Autopilot Device Preparation](windows-autopilot.md)
- [Microsoft Learn — Surface Management Portal](https://learn.microsoft.com/en-us/surface/surface-management-portal)
- [Microsoft Learn — DFCI profiles for Windows devices in Intune](https://learn.microsoft.com/en-us/intune/device-configuration/templates/configure-dfci-windows)
- [Microsoft Learn — Pluton security processor](https://learn.microsoft.com/en-us/windows/security/hardware-security/pluton/microsoft-pluton-security-processor)
- [Microsoft Learn — Windows Hello for Business overview](https://learn.microsoft.com/en-us/windows/security/identity-protection/hello-for-business/)
- [Microsoft Learn — Autopilot Device Preparation overview](https://learn.microsoft.com/en-us/autopilot/device-preparation/overview)
- [Microsoft Learn — Deploy Surface Hub with Windows Autopilot & Teams Rooms Auto-login](https://learn.microsoft.com/en-us/surface-hub/surface-hub-autopilot)
- [Microsoft Learn — Surface Hub Windows 10 Team end-of-support migration](https://learn.microsoft.com/en-us/surface-hub/surface-hub-windows10-eos-migration)
- [Microsoft Learn — Teams Rooms Pro Management Portal](https://learn.microsoft.com/en-us/microsoftteams/rooms/managed-meeting-rooms-portal)
