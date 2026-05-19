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
> Surface-specific deltas*: DFCI lockdown, Pluton attestation,
> Windows Hello for Business delivery, the Surface vendor pre-
> registration lane, and the Surface Management Portal fleet-
> telemetry surface.
>
> **Asset class:** `windows-endpoint` with sub-class
> `windows-endpoint-surface`.
>
> **Canonical join target:** Microsoft Entra Join (per ADR-001 —
> identical to the parent annex; HAADJ and domain-join remain
> forbidden).
>
> **Surface Hub handling.** Surface Hub-class hardware running
> Microsoft Teams Rooms (MTR) on Windows is governed identically to
> any other Surface form factor under this annex — it is an Entra-
> joined Windows endpoint per ADR-001. Surface Hub running the
> Surface Hub OS variant is NOT covered by this annex; it is
> migration-only per the draft reconciliation ADR at
> `inbox/drafts/adr-075-surface-hub-reconciliation.md`. Net-new
> procurement of Surface Hub 3 MUST specify the MTR on Windows
> configuration; net-new procurement of Surface Hub 2S is
> forbidden; existing Surface Hub OS installed base requires an
> exception grant pending migration.

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
  - `surface-hub` — **forbidden for net-new procurement; requires exception grant**
- `vendor_program` is one of:
  - `surface-direct-microsoft` — direct purchase through Microsoft
    commercial channel; hardware hashes pre-registered via Microsoft
    Cloud Solution Provider (CSP) APIs into the customer tenant
  - `surface-reseller` — reseller (CDW, Insight, Connection) with
    Surface Authorized Device Reseller status; hash registration
    flows through the reseller's CSP integration
  - `surface-distributor` — distributor (Synnex, Ingram Micro) with
    pass-through to a reseller

The `vendor_program_records[]` schema from
[`windows-autopilot.md`](windows-autopilot.md) §1 is unchanged;
Surface-specific records add `surface_registration_portal_url`
(the CSP-portal record link) for traceability.

---

## Phase 2 — Pre-stage (Surface-specific mechanics)

### 2.1 — Hardware-hash registration

Identical to [`windows-autopilot.md`](windows-autopilot.md) §2.1
*except* the recommended path:

| Path | Used for Surface |
|---|---|
| **Vendor pre-provisioned via Microsoft CSP** (`surface-direct-microsoft` / `surface-reseller`) | Recommended. Microsoft / authorized reseller writes the hash to the customer tenant before shipping. |
| Reseller-supplied via Autopilot CSP API | Equivalent path for `surface-reseller` orders. |
| Organization-collected (`Get-WindowsAutopilotInfo`) | Exception-only for Surface hardware that arrived without pre-registration. |

The Group Tag convention `groupTag = "OrgPath:" + asset_orgpath`
from [`windows-autopilot.md`](windows-autopilot.md) §2.2 is
identical and required.

### 2.2 — DFCI profile assignment (Surface-distinctive)

Surface is the reference device for DFCI (Device Firmware
Configuration Interface). DFCI authoring is an Intune
configuration-profile class (`Windows 10 and later → Templates →
Device Firmware Configuration Interface`) that writes UEFI-level
settings the signed-in user cannot reverse, even with local admin.

For every Surface deployed under this annex, a DFCI profile MUST
be assigned through the same OrgPath-prefixed Group-Tag dynamic
group used for the Autopilot deployment profile. The DFCI profile
locks at minimum:

- **Cameras** — disabled by default for service / kiosk / lab
  assignment types; enabled with documented exception for personal
  and shared assignment types
- **Microphones** — same posture as cameras
- **Wireless radios** (Bluetooth, Wi-Fi)  — Bluetooth disabled by
  default for service / kiosk / lab; Wi-Fi enabled for all
- **USB ports** — locked to "no boot from USB" for all asset types
  (prevents offline-image reboot bypass); per-port data-mode
  lockdown follows the asset's OrgPath compliance branch
- **Boot order** — internal storage first; PXE/network boot
  disabled
- **Hibernate / sleep firmware behavior** — set to enterprise
  defaults documented per OrgPath branch
- **Built-in audio / built-in keyboard / built-in trackpad** —
  enabled (these flags exist for kiosk hardening scenarios; default
  posture is enabled)
- **WLAN auto-connect** — controlled at OS level via separate
  Wi-Fi profile, not at firmware level

The DFCI profile is **distinct from** the generic device
configuration profile. Both are assigned to the same OrgPath
dynamic group. The compliance policy assigned to the same group
includes a DFCI-applied check (settings catalog `firmware/dfci-
status = applied`); a Surface where DFCI did not apply (e.g.,
older firmware that lacks DFCI support) is non-compliant and
fails Conditional Access.

DFCI authoring is covered by the existing modernization-side
`intune` reserved slot (ADR-049 / [`intune.qmd:37`](../../docs/
customer-documents/adapter-specs/intune/intune.qmd)) — no new
adapter slot is required for the authoring surface.

### 2.3 — Pluton firmware update path

Newer Surface generations (Pro 11, Laptop 6 and later) ship the
Microsoft Pluton security processor as the discrete TPM
replacement. Pluton firmware updates flow through Windows Update
for Business — distinct from third-party TPM firmware, which
typically ships through OEM-specific update channels.

The Phase 2 pre-stage MUST verify the Windows Update for Business
ring assignment for the OrgPath branch includes the Pluton-
relevant update channel. The branch update-ring policy assigned
through `entra-policy-targeting` is the authoring surface for this
binding — no new adapter slot.

---

## Phase 3 — Position (no Surface-specific delta)

Phase 3 mechanics from [`../process.md`](../process.md) §3 and
[`windows-autopilot.md`](windows-autopilot.md) §3 apply without
modification. The dry-run validation entries for a Surface in
`governance/autopilot/orgpath-mapping.csv` include the DFCI-
profile assignment check (added column: `DfciProfileId`).

---

## Phase 4 — Provision (Surface-specific runtime)

The runtime enrollment flow is identical to
[`windows-autopilot.md`](windows-autopilot.md) §4 (OOBE → ESP →
OrgPath stamping → dynamic-group convergence → first compliance
evaluation) with two Surface-specific additions:

### 4.1 — DFCI application during ESP Device Setup

During the Enrollment Status Page's **Device Setup** phase, the
DFCI profile is applied alongside other device-targeted
configuration profiles. Application is gated on:

1. Surface UEFI firmware version supports DFCI (true for Surface
   Pro 7+, Surface Laptop 3+, Surface Book 3, Surface Go 2+, and
   all later generations as of 2026)
2. Device is enrolled in Autopilot under the customer tenant
   (DFCI authority is bound to tenant)
3. Network connectivity is available during ESP (DFCI profile
   download)

A Surface where any precondition fails reports DFCI status
`not-applied`; the compliance policy fails; Conditional Access
blocks access until remediation. There is no user-driven
workaround — this is by design.

### 4.2 — Windows Hello for Business enrollment prompt

On Surface devices with IR camera (Surface Pro / Surface Laptop
Studio / Surface Book) and/or fingerprint reader (Surface Laptop
power-button fingerprint, Surface Type Cover fingerprint), the
post-OOBE Windows Hello provisioning prompt offers face and/or
fingerprint enrollment in addition to PIN.

Per IA-2(1) and IA-5 in the control library, WHfB with TPM-backed
key storage is an approved authenticator. The Surface IR-camera
and fingerprint paths are the canonical delivery vehicle for WHfB
on Microsoft hardware. The Surface annex requires:

- WHfB enrollment is **not blocked** by the Account Setup ESP
  phase — the user completes WHfB enrollment *after* OOBE/ESP, not
  during, to keep ESP duration bounded
- The Authentication Methods Policy assigned at the tenant level
  enables `windowsHelloForBusiness` with `securityKeyForSignIn:
  enabled` for the OrgPath branches that include Surface assets
- The compliance policy validates `bitlocker = on` AND `tpm-
  present = true` AND `secure-boot = on` — all three are
  preconditions for WHfB key storage in the Pluton / TPM 2.0
  hardware

WHfB *posture* observation (per-user, per-device enrollment state)
is **not currently a first-class adapter surface**. It is
referenced in IA-2(1) / IA-5 but no conformance adapter observes
the `signInActivity` + `authenticationMethod` graph endpoints
for WHfB enrollment evidence. This gap is acknowledged and
deferred — a future ADR could split out two slots
(`windows-hello-for-business` for per-device per-user enrollment
state, `entra-authentication-methods` for tenant-wide policy
authoring); neither is in scope under this annex.

---

## Phase 5 — Validate (Surface-specific checks)

The full validation checklist is in
[`../validation-and-evidence.md`](../validation-and-evidence.md)
and [`windows-autopilot.md`](windows-autopilot.md) §5. Surface-
specific items, in addition:

- [ ] Surface Management Portal reports the device with current
      firmware version matching the OrgPath branch's target firmware
      (once the `surface-management-portal` adapter is active — until
      then, manual check via SMP web UI)
- [ ] DFCI profile is in `applied` state on the device
      (`Get-MgDeviceManagementManagedDeviceComplianceState`
      `dfciStatus`)
- [ ] DFCI lockdowns visible in UEFI: cameras / microphones /
      Bluetooth / USB boot disabled per the branch DFCI policy
- [ ] BitLocker recovery key escrowed to Entra ID device object
      (this is generic Windows behavior but verify on Surface
      explicitly because of the Pluton key-storage path)
- [ ] If device generation supports Pluton: device reports `tpm-
      manufacturer = MSFT` and `tpm-firmware-version` matches the
      Windows Update for Business ring's target
- [ ] WHfB enrollment is *available* (not necessarily completed)
      for the signed-in user: device reports `passwordless-credential-
      eligible = true`
- [ ] Conditional Access compliance grant control allows the
      device through with `dfciStatus = applied` AND
      `complianceState = compliant`
- [ ] Microsoft Cloud Solution Provider record for the device
      hash matches the customer tenant ID (verifies the Surface
      vendor pre-registration lane completed correctly)

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
  until the hash is re-registered. **Required remediation path:**
  Intune-driven `Autopilot Reset` (preserves enrollment) or
  `Wipe with device retention removed` (re-enrolls via Autopilot
  on next boot).
- **Surface Hub net-new procurement.** Forbidden pending the
  Surface Hub ↔ ADR-001 reconciliation ADR. Exception grant
  required for any Surface Hub order.
- **DFCI bypass via UEFI password.** UEFI password on a managed
  Surface is owned by the tenant DFCI policy, not the user. Any
  workflow that involves setting a local UEFI password to bypass
  DFCI is a governance exception requiring documented grant.
- **Disabling Pluton in UEFI on Pluton-equipped Surface.** Where
  the UEFI offers a Pluton on/off toggle, the DFCI profile MUST
  lock Pluton to `on` for any Surface where Pluton is the system
  TPM. Disabling Pluton invalidates BitLocker, WHfB, and device
  attestation simultaneously.

---

## Vendor-specific notes

### Microsoft (direct purchase)

`vendor_program = surface-direct-microsoft`. Hardware hashes are
pre-registered through the Microsoft commercial channel's CSP
integration. The customer tenant receives the device in the
`Microsoft Intune admin center → Devices → Windows → Windows
enrollment → Devices` list within minutes of order confirmation.

Group Tag assignment at order time is supported through the
commercial portal's order configuration screen — supply the
OrgPath-tagged value (`OrgPath:/Root/...`) at the time of order.

### Authorized resellers (CDW, Insight, Connection)

`vendor_program = surface-reseller`. Each reseller has its own
CSP integration; mechanics are equivalent to the
`autopilot-reseller` flow described in
[`windows-autopilot.md`](windows-autopilot.md) §"Vendor-specific
notes — CDW" but the SKUs eligible for Group-Tag-at-order vary by
reseller and Surface generation. Validate Group Tag support per
reseller account before standardizing on a reseller.

### Surface Hub / Microsoft Teams Rooms on Surface Hub-class hardware

**Forbidden for net-new procurement under this annex.** See §"Anti-
patterns" above and the Surface Hub reconciliation ADR at
`inbox/drafts/adr-075-surface-hub-reconciliation.md` (DRAFT —
recommends migration-only with exception-grant requirement).

---

## References

- [ADR-071 — Intune-First Asset Onboarding](../../../canon/adr/adr-071-intune-first-asset-onboarding.md)
- [ADR-001 — HAADJ deprecated, Entra-Join-only](../../../../docs/adr/adr-001-haadj-deprecated-entra-join-only.qmd)
- [Parent annex — Windows Autopilot Device Preparation](windows-autopilot.md)
- [Microsoft Learn — Surface Management Portal](https://learn.microsoft.com/en-us/surface/surface-management-portal)
- [Microsoft Learn — DFCI profiles for Windows devices in Intune](https://learn.microsoft.com/en-us/mem/intune/configuration/device-firmware-configuration-interface-windows)
- [Microsoft Learn — Pluton security processor](https://learn.microsoft.com/en-us/windows/security/hardware-security/pluton/microsoft-pluton-security-processor)
- [Microsoft Learn — Windows Hello for Business overview](https://learn.microsoft.com/en-us/windows/security/identity-protection/hello-for-business/)
- [Microsoft Learn — Autopilot Device Preparation overview](https://learn.microsoft.com/en-us/autopilot/device-preparation/overview)
