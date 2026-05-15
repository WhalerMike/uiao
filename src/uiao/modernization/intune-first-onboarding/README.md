---
document_id: IFO_000
title: "Intune-First Asset Onboarding — Doctrine, Process, and Per-Platform Procedures"
version: "1.0"
status: CANONICAL
owner: "Michael Stratton"
created_at: "2026-05-13"
updated_at: "2026-05-14"
boundary: GCC-Moderate
canon_anchor: ADR-071
provenance:
  promoted_from: "inbox/drafts/intune-first-asset-onboarding/"
  promoted_at: "2026-05-14"
---

# Intune-First Asset Onboarding — Doctrine, Process, and Per-Platform Procedures

> **Status:** CANONICAL as of 2026-05-14, anchored by [ADR-071](../../canon/adr/adr-071-intune-first-asset-onboarding.md).
> Companion to the AD→Intune migration path under
> [`src/uiao/modernization/directory-migration/`](../directory-migration/README.md).
> This module covers the *inverse* path: net-new assets that should never
> touch Active Directory or SCCM, landing in Intune from day zero.
>
> **Scope:** All-platforms onboarding doctrine — Windows endpoints,
> macOS, iOS/iPadOS, Android Enterprise, and Azure Arc-managed servers.
> Single coherent process, per-platform enrollment annexes.

---

## Why this module exists

UIAO already has a mature canon for **migrating** Active Directory-joined
endpoints into Entra ID + Intune:

- [`src/uiao/modernization/directory-migration/README.md`](../directory-migration/README.md) — the five-phase Discover → Normalize → Map → Migrate → Validate process
- [`src/uiao/modernization/directory-migration/adapters/device-management/device-adapter-interface.md`](../directory-migration/adapters/device-management/device-adapter-interface.md) — registers the `sccm-intune/` (co-management) and `intune-native/` (greenfield) sub-adapters
- [ADR-001](../../canon/adr/adr-001-haadj-deprecated-entra-join-only.md) — Entra-join is the sole device join target; HAADJ is deprecated
- [ADR-002](../../canon/adr/adr-002-arc-entra-join-no-domain-join.md) — Arc-enabled servers must be non-domain-joined
- [ADR-038](../../canon/adr/adr-038-device-plane-orgpath.md) — device-plane OrgPath binding

What does **not** exist in canon: the operational doctrine and procurement-
to-validation process for net-new assets that should land in Intune
*first* — before they ever join AD, before they ever touch SCCM, before
they ever run a startup script that depends on a domain controller. The
`intune-native/` adapter slot has been registered but never authored.

This module fills that gap.

---

## What "Intune-first" means

A net-new asset (laptop just unboxed, server just racked, phone just
issued) is governed by Intune (or, for servers, Azure Arc into the same
governance plane) from the moment it first powers on. There is no
intermediate state where the device:

- joins on-prem AD and waits for a future migration,
- is provisioned by SCCM and later co-managed,
- runs without OrgPath assignment,
- enters production without a compliance evaluation,
- or skips the procurement-side organizational positioning step.

The asset's organizational position (OrgPath) is determined at
**procurement time**, written to a pre-staged registration record
(Autopilot device profile, Apple ABM device assignment, Android Zero-Touch
configuration, or Arc onboarding token), and stamped on the device
object during zero-touch enrollment. The device enters production already
in the right groups, already evaluated against the right compliance
policy, already inside the right Conditional Access scope.

This is the inverse of the AD migration path. Migration takes a device
that already exists and brings it under governance. Intune-first refuses
the existence of any ungoverned device in the first place.

---

## What this module contains

| File | Role |
|---|---|
| [`README.md`](README.md) | This file — entry point, scope, taxonomy |
| [`doctrine.md`](doctrine.md) | The five Intune-first doctrine pillars; explicit exception paths |
| [`process.md`](process.md) | The canonical five-phase onboarding process (Procure → Pre-stage → Position → Provision → Validate) |
| [`procurement-handoff.md`](procurement-handoff.md) | The procurement-side intake checklist that triggers the rest of the process |
| [`platforms/windows-autopilot.md`](platforms/windows-autopilot.md) | Windows endpoints via Autopilot Device Preparation (v2) |
| [`platforms/macos-abm-ade.md`](platforms/macos-abm-ade.md) | macOS via Apple Business / School Manager and Automated Device Enrollment |
| [`platforms/mobile-ios-android.md`](platforms/mobile-ios-android.md) | iOS/iPadOS via ABM/ASM ADE; Android via Android Enterprise Zero-Touch and Samsung Knox Mobile Enrollment |
| [`platforms/arc-managed-servers.md`](platforms/arc-managed-servers.md) | Servers via Azure Arc onboarding into the same governance plane |
| [`validation-and-evidence.md`](validation-and-evidence.md) | Validation checklist, drift classes raised, evidence emitted per onboarding |

The doctrinal anchor lives separately at [`../../canon/adr/adr-071-intune-first-asset-onboarding.md`](../../canon/adr/adr-071-intune-first-asset-onboarding.md).

---

## What this module is NOT

- **Not a migration guide.** AD-joined devices that already exist follow
  the migration path under [`../directory-migration/`](../directory-migration/README.md).
  This module is exclusively for net-new asset acquisition.
- **Not an OrgPath specification.** OrgPath is canonical via UIAO_007 and
  ADRs 035/038/048. This module consumes OrgPath as a primitive.
- **Not a replacement for the OrgPath/Intune narrative.** The deep
  enrollment-script detail (Autopilot OrgPath stamping PowerShell, KQL
  compliance dashboards, scope tag delegation) lives in
  [`inbox/drafts/complete-narrative/source-docx/OrgPath and Microsoft Intune — Structural Device Governance at Enterprise Scale.md`](../../../inbox/drafts/complete-narrative/source-docx/OrgPath%20and%20Microsoft%20Intune%20%E2%80%94%20Structural%20Device%20Governance%20at%20Enterprise%20Scale.md).
  This module references that document; it does not duplicate it.
- **Not Apple/Google/Samsung product documentation.** Per-platform docs
  here describe the *governance integration*, not vendor-program
  enrollment mechanics that the vendor's own documentation covers.
- **Does not modify** `adapter-registry.yaml` or `modernization-registry.yaml`.
  Per ADR-071 and repo invariant **I5**, registry slot allocation for the
  paired procurement-integration adapters is a follow-up activity.

---

## Asset taxonomy covered

| Class | Day-zero management plane | Enrollment vector | Doctrine pillar |
|---|---|---|---|
| Windows endpoint (laptop / desktop / Surface) | Intune | Windows Autopilot Device Preparation (v2) | Pillars 1, 2, 3 |
| Windows tablet / 2-in-1 / kiosk | Intune | Autopilot self-deploying or pre-provisioned | Pillars 1, 2, 3 |
| macOS endpoint | Intune | Apple ABM/ASM + Automated Device Enrollment | Pillars 1, 2, 3 |
| iOS / iPadOS phone or tablet (corporate-owned) | Intune | Apple ABM/ASM + ADE | Pillars 1, 2, 3 |
| iOS / iPadOS personal device (BYOD) | Intune | User-driven enrollment via Company Portal — exception path, see [`doctrine.md`](doctrine.md) §4 | Exception path A |
| Android Enterprise dedicated / fully managed (corporate) | Intune | Android Zero-Touch or Knox Mobile Enrollment | Pillars 1, 2, 3 |
| Android personal device (BYOD work profile) | Intune | User-driven enrollment via Company Portal — exception path | Exception path A |
| Linux endpoint (corporate-issued) | Intune (Linux MDM) or Arc | Manual enrollment with day-zero compliance check — exception path B | Exception path B |
| Windows Server 2025+ (on-prem or hosted) | Intune via Azure Arc + Entra-join | Arc onboarding script → Entra-join → AADLoginForWindows | Pillars 1, 2, 3 (per ADR-002) |
| Windows Server 2019/2022 | Arc-managed only (no Entra-join until OS upgrade) — exception path C | Arc onboarding script | Exception path C |
| Linux server | Arc-managed | Arc onboarding script | Pillars 1, 2, 3 |
| IoT / OT / specialty device | Out of scope for this module | — | — |
| Unmanaged guest device | Out of scope; governed by Conditional Access guest-access policy, not this process | — | — |

The exception paths are documented in [`doctrine.md`](doctrine.md) §4 with
required justifications and compensating controls.

---

## Tie-back to existing canon

| Existing canon | This module's tie-in |
|---|---|
| ADR-001 — HAADJ deprecated, Entra-join only | This module generalizes the principle from "no HAADJ for new devices" to "no AD-join, no SCCM, no manual enrollment for any new asset" |
| ADR-002 — Arc-enabled servers require non-domain-joined | Arc-managed-servers platform doc operates within this constraint and treats it as the day-zero target state, not a future migration target |
| ADR-038 — Device-plane OrgPath | Day-zero OrgPath assignment (Phase 3 of the process) is the procurement-time equivalent of the post-enrollment ETL stamping that ADR-038 specifies |
| UIAO_007 — OrgTree Modernization | Procurement-handoff.md treats UIAO_007's OrgTree as the authoritative source for the OrgPath value assigned to each asset |
| [`../directory-migration/`](../directory-migration/README.md) | Sibling — that path covers existing AD assets; this module covers net-new assets. The two paths converge at the Intune steady state |
| `device-adapter-interface.md` registered `intune-native/` slot | This module is the operational content for that registered-but-empty slot, hoisted to a top-level location because the doctrine spans procurement, endpoints, and servers (broader than the single device-management adapter slot) |
| OrgPath/Intune narrative (in `inbox/drafts/complete-narrative/`) | This module's per-platform docs reference the narrative's enrollment scripts; this module establishes the doctrine, the narrative provides the implementation detail |

---

## Open follow-ups

These items are deferred from the initial promotion (2026-05-14) and
tracked for subsequent ADRs and PRs:

1. **Adapter-registry slot allocation.** Today the registry has one
   `intune-native/` slot under device-management. The four platform
   surfaces in this module could each receive their own conformance-
   adapter slot, or share a single modernization-adapter slot. Decision
   pending; current recommendation is one modernization slot referencing
   this module, with the four platform annexes as scope notes.

2. **Procurement-integration adapter family.** Procurement-handoff.md
   depends on procurement-system integration (PO triggers, vendor
   portals). UIAO has not yet codified a procurement adapter surface.
   Tracked as a follow-up ADR opportunity.

3. **Linux endpoint posture.** Microsoft's Intune Linux MDM is GA but
   limited; Arc is the alternative. The doctrine treats Linux endpoints
   as exception-by-default (Path B). Re-evaluate when Intune Linux MDM
   coverage expands.

4. **BYOD treatment.** Currently Exception Path A. Some agencies cannot
   offer BYOD at all (federal civilian); others treat it as primary
   (commercial). Acceptable as exception path A; reconsider per-tenant
   if a customer engagement requires elevated BYOD treatment.

5. **Implementation pipeline.** The validation pipeline contract is
   specified in [`validation-and-evidence.md`](validation-and-evidence.md);
   the implementing adapter under `src/uiao/adapters/modernization/intune_first/`
   is a follow-up engineering item.
