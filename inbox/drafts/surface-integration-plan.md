# Implementation Plan — Microsoft Surface as a First-Class Asset Class

> **Branch:** `claude/modest-lamarr-9cd649`
> **Date:** 2026-05-18
> **Status:** LANDED — canon promotion completed 2026-05-18 (this plan retained as historical record)
> **Anchor ADRs:** ADR-071 (Intune-First Asset Onboarding); ADR-075 (Surface Hub Reconciliation — ACCEPTED 2026-05-18)
> **Pattern model:** the existing platform-annex pattern under `src/uiao/modernization/intune-first-onboarding/platforms/`
>
> **Promotion record (2026-05-18):**
> - IFO_014 windows-surface annex → [`src/uiao/modernization/intune-first-onboarding/platforms/windows-surface.md`](../../src/uiao/modernization/intune-first-onboarding/platforms/windows-surface.md) (CANONICAL)
> - `surface-management-portal` adapter entry → merged into [`src/uiao/canon/adapter-registry.yaml`](../../src/uiao/canon/adapter-registry.yaml) (reserved, phase-planning)
> - ADR-075 → [`src/uiao/canon/adr/adr-075-surface-hub-reconciliation.md`](../../src/uiao/canon/adr/adr-075-surface-hub-reconciliation.md) (ACCEPTED) + [`docs/adr/adr-075-surface-hub-reconciliation.qmd`](../../docs/adr/adr-075-surface-hub-reconciliation.qmd) wrapper
> - ADR index updated: [`src/uiao/canon/adr/index.md`](../../src/uiao/canon/adr/index.md)
>
> **Pre-promotion verification corrections applied:**
> - Three of four Microsoft Learn URLs in ADR-075 were placeholders that returned 404; replaced with verified URLs (`surface-hub-3-get-started`, `surface-hub-2s-migrate-to-mtr-w`, `managed-meeting-rooms-portal`).
> - DFCI URL in the annex was redirecting; updated to canonical (`intune/device-configuration/templates/configure-dfci-windows`).
> - SMP described as "first-party fleet telemetry surface" was structurally wrong; it is "a workspace within the Microsoft Intune admin center" per Microsoft Learn. Adapter notes corrected.
> - DFCI prerequisites: organization-collected (manually-imported) hardware hashes are not eligible for DFCI by Microsoft design. Annex now states this explicitly.
> - Pluton was described as Surface-specific; corrected to chipset-feature framing (AMD Ryzen 6000+, Intel Core Ultra 200V+, Qualcomm Snapdragon 8cx Gen 3+) — Surface gets Pluton when the underlying silicon supports it.
> - ADR-075 Consequences: the Migration Launcher app path expired 2025-12-14, removing the cheapest software-only migration path for Surface Hub 2S. Surface Hub 2S customers now have only Compute Cartridge install or USB recovery image install. Recorded explicitly in the canonical ADR.
> - Windows 10 Team edition end-of-support already occurred (2025-10-14). ADR-075 reframed from "sunsetting OS" to "out-of-support OS", strengthening Option B's argument.

## 1. Goal

Promote Microsoft Surface from an incidental example (`asset_class = windows-endpoint (... Surface ...)` in [`windows-autopilot.md:38`](../../src/uiao/modernization/intune-first-onboarding/platforms/windows-autopilot.md)) to a first-class governance target, with one new platform annex and one new conformance adapter slot. Defer Surface Hub and any ADR-001 carve-out to a separate decision.

## 2. Context recap

### Why Surface needs special treatment vs. generic Windows endpoint

The generic Windows Autopilot annex covers join target (Entra Join only per ADR-001), enrollment vector (Autopilot v2 Device Preparation), OrgPath stamping, and dynamic-group convergence. Those mechanics are identical on a Surface, a Dell Latitude, and a generic OEM. What is **not** identical:

| Surface-specific surface | Generic Windows endpoint | Governance consequence |
|---|---|---|
| **DFCI** (Device Firmware Configuration Interface) | DFCI requires UEFI cooperation; Surface is Microsoft's reference DFCI device. Most non-Surface OEMs ship partial / no DFCI support. | Camera, microphone, USB, Bluetooth, radios, and boot order can be locked at the UEFI level via an Intune-authored DFCI profile — irreversible by the signed-in user, even with local admin. |
| **Microsoft Pluton** | On newer Surface (and partner) hardware; co-signed firmware update path through Windows Update for Business | Hardware root-of-trust with Microsoft-managed firmware lifecycle — distinct attestation surface from a discrete TPM 2.0. |
| **Surface Management Portal (SMP)** | First-party Microsoft fleet telemetry portal for Surface hardware (firmware versions across fleet, warranty drift, device health) — separate Graph endpoints from `deviceManagement/managedDevices` | Telemetry surface that the existing `intune` conformance adapter does NOT cover. |
| **Surface Registration Portal / OEM pre-registration** | Vendor lane distinct from CDW / HP / Dell / Lenovo flows documented in [`windows-autopilot.md`](../../src/uiao/modernization/intune-first-onboarding/platforms/windows-autopilot.md) §"Vendor-specific notes" | Procurement integration mechanics differ — Microsoft Cloud Solution Provider APIs, not OEM portal APIs. |
| **Windows Hello for Business delivery** | IR camera + fingerprint sensor combination on Surface Pro / Surface Laptop / Surface Book / Surface Studio | WHfB enrollment posture is observable per device; Surface IR is the canonical delivery vehicle and worth calling out in the validation checklist. |
| **Surface Hub / Microsoft Teams Rooms Pro** | Separate management plane (Teams Rooms Pro Management portal); historical hybrid-join semantics | **Conflicts with ADR-001** (Entra-Join-only). Out of scope for this PR set — see §5. |

### Existing canon Surface would touch

- **ADR-071** ([`adr-071-intune-first-asset-onboarding.md`](../../src/uiao/canon/adr/adr-071-intune-first-asset-onboarding.md)) — controlling doctrine for net-new endpoint onboarding
- **ADR-001** ([`adr-001-haadj-deprecated-entra-join-only.qmd`](../../docs/adr/adr-001-haadj-deprecated-entra-join-only.qmd)) — controlling precedent for Windows endpoint join target
- **`intune` adapter** ([`adapter-registry.yaml` L260](../../src/uiao/canon/adapter-registry.yaml), status: reserved) — covers `deviceManagement/managedDevices`; does NOT cover the Surface Management Portal
- **`entra-device-orgpath` adapter** — OrgPath stamping on device objects, same for Surface as any Entra-joined endpoint
- **`defender-for-endpoint` adapter** — EDR signal, same for Surface
- **NIST IA-2(1) / IA-5 control library entries** ([`IA-2(1).yml:28`](../../src/uiao/canon/data/control-library/ia/IA-2(1).yml), [`IA-5.yml:30`](../../src/uiao/canon/data/control-library/ia/IA-5.yml)) — Windows Hello for Business already accepted as a TPM-backed authenticator; no observable adapter exists for WHfB posture

## 3. Scope decisions

### In scope for this PR set

1. **Platform annex** — `src/uiao/modernization/intune-first-onboarding/platforms/windows-surface.md` (IFO_014). Sub-pattern of the Windows Autopilot annex. Surface-specific Phase-1 intake, DFCI Phase-2 mechanics, Pluton / SMP / WHfB Phase-5 validation checks, and an explicit forbidden-patterns subsection.
2. **Conformance adapter slot** — `surface-management-portal` reserved in [`adapter-registry.yaml`](../../src/uiao/canon/adapter-registry.yaml). Mission-class `telemetry`. Read-only fleet telemetry from SMP: firmware versions, DFCI compliance, warranty/lifecycle drift, device-health signals. Status: `reserved`, phase: `phase-planning`. Implementation deferred — slot allocation only.

### Explicitly out of scope (deferred, separate decision)

1. **Surface Hub / Teams Rooms Pro ADR.** Surface Hub historically has join paths that don't align with ADR-001's Entra-Join-only doctrine. A reconciliation ADR has been drafted at [`inbox/drafts/adr-075-surface-hub-reconciliation.md`](adr-075-surface-hub-reconciliation.md) — status: DRAFT, recommending **Option B (migration-only with exception-grant requirement)** rather than narrow carve-out. The draft is internally consistent with this PR set but requires explicit user acceptance before promotion to canon. See §5.
2. **Windows Hello for Business as its own adapter family.** WHfB is currently a referenced authenticator type in the IA-2/IA-5 control library, not a first-class observable. A future ADR could split out two slots — `windows-hello-for-business` (conformance / telemetry: per-device per-user enrollment state) and `entra-authentication-methods` (modernization / integration: tenant-wide authentication-methods-policy authoring). Deferred so this PR set stays anchored to Surface; flagged here so it doesn't get lost.
3. **DFCI as a separate adapter slot.** DFCI is authored *through Intune* — the existing `intune` modernization-side reserved slot (ADR-049) covers the configuration-profile authoring surface, of which DFCI is one class. DFCI does not justify a third Intune-shaped slot today.
4. **Pluton attestation as a separate adapter slot.** Pluton signals reach UIAO via existing Entra ID device-object attestation properties + Intune compliance evaluation. No new collector surface today. Re-evaluate if Microsoft exposes a distinct Pluton attestation API.

### Why "tight" not "wide"

The wider option in the prior exploration message would have stood up four adapter slots (`surface-management-portal`, `windows-hello-for-business`, `surface-hub`, `dfci-firmware`) and a new device-substrate adapter class. That is the right destination over time, but for a first PR set it inflates surface area before any one slot has even validated its Graph scope and evidence shape. The tight option matches the SailPoint precedent ([`sailpoint-adapter-plan.md`](sailpoint-adapter-plan.md)) — Option A landed one NERM slot before contemplating the wider ISC family.

## 4. Deliverables (this PR set)

| File | Status | Notes |
|---|---|---|
| `inbox/drafts/intune-first-asset-onboarding/platforms/windows-surface.md` | NEW | IFO_014. Surface platform annex. Mirrors the structure of [`windows-autopilot.md`](../../src/uiao/modernization/intune-first-onboarding/platforms/windows-autopilot.md). |
| `inbox/drafts/surface-management-portal-adapter-entry.yaml` | NEW | Proposed reserved entry for `src/uiao/canon/adapter-registry.yaml`. Mirrors the [`intune` adapter shape](../../src/uiao/canon/adapter-registry.yaml). |
| `inbox/drafts/surface-integration-plan.md` | NEW (this file) | Umbrella plan. |

After review, promotion to canon follows the existing pattern:

- Annex moves from `inbox/drafts/intune-first-asset-onboarding/platforms/windows-surface.md` → `src/uiao/modernization/intune-first-onboarding/platforms/windows-surface.md` (per IFO_010-013 precedent).
- Adapter entry merges into `src/uiao/canon/adapter-registry.yaml` after the YAML fragment is validated against [`adapter-registry.schema.json`](../../src/uiao/schemas/adapter-registry/adapter-registry.schema.json).
- Canon sync (`uiao/tools/sync_canon.py`) regenerates the published `docs/customer-documents/adapter-specs/surface-management-portal/` ATS wrapper.

## 5. Open question (resolved in draft form by ADR-075)

The Surface Hub ↔ ADR-001 reconciliation question was raised by this plan and is now addressed in draft form by [`adr-075-surface-hub-reconciliation.md`](adr-075-surface-hub-reconciliation.md).

The draft ADR recommends **Option B — Migration-only with exception-grant requirement.** Key points:

- ADR-001 remains categorical; no device-class carve-out.
- Surface Hub 3 ordered as MTR on Windows is conforming and governed identically to any other Entra-joined Windows endpoint per ADR-071 / IFO_014.
- Surface Hub OS variants, Surface Hub 1, and unconverted Surface Hub 2S are migration-only and require exception grants for continued operation pending migration.
- Net-new procurement of Surface Hub 2S is forbidden; net-new procurement of Surface Hub 3 MUST specify MTR on Windows.

The draft ADR includes Options A (narrow carve-out) and C (defer) with their respective pro/con analysis. The recommendation Option B is the conservative path that preserves ADR-001's categorical force and aligns with Microsoft's own Surface Hub OS sunset direction.

Until ADR-075 is accepted, the IFO_014 platform annex flags Surface Hub net-new procurement as a forbidden pattern requiring exception grant — that posture is the same outcome either Option B or "defer" produces, so the annex is internally consistent regardless of the ADR-075 decision timing.

## 6. References

- ADR-071 — Intune-First Asset Onboarding ([`adr-071-intune-first-asset-onboarding.md`](../../src/uiao/canon/adr/adr-071-intune-first-asset-onboarding.md))
- ADR-001 — HAADJ deprecated, Entra-Join-only ([`adr-001-haadj-deprecated-entra-join-only.qmd`](../../docs/adr/adr-001-haadj-deprecated-entra-join-only.qmd))
- Windows Autopilot platform annex (parent doctrine) — [`windows-autopilot.md`](../../src/uiao/modernization/intune-first-onboarding/platforms/windows-autopilot.md)
- `intune` adapter registry entry — [`adapter-registry.yaml` L260+](../../src/uiao/canon/adapter-registry.yaml)
- SailPoint adapter plan (pattern reference for staged adapter slot allocation) — [`sailpoint-adapter-plan.md`](sailpoint-adapter-plan.md)
- Microsoft Learn — [Surface Management Portal](https://learn.microsoft.com/en-us/surface/surface-management-portal)
- Microsoft Learn — [Device Firmware Configuration Interface (DFCI) profiles](https://learn.microsoft.com/en-us/mem/intune/configuration/device-firmware-configuration-interface-windows)
- Microsoft Learn — [Microsoft Pluton security processor](https://learn.microsoft.com/en-us/windows/security/hardware-security/pluton/microsoft-pluton-security-processor)
