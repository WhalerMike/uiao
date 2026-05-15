---
adr_id: adr-071
title: "Intune-First Asset Onboarding — All-Platform Doctrine for Net-New Assets"
status: ACCEPTED
decided: 2026-05-14
deciders: Michael Stratton
updated: 2026-05-14
next_review: 2026-11-01
review_trigger: Microsoft Ignite 2026; any Autopilot, ABM, Android Zero-Touch, or Arc onboarding announcement; substantive change to ADR-001 or ADR-002
impact: Establishes new doctrine and operational canon at `src/uiao/modernization/intune-first-onboarding/`; complements ADR-001 (HAADJ deprecation), ADR-002 (Arc non-domain-join), ADR-038 (device-plane OrgPath); fills the previously-empty `intune-native/` sub-adapter slot under `directory-migration/adapters/device-management/`
supersedes: null
superseded_by: null
classification: Controlled
boundary: GCC-Moderate
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-071-intune-first-asset-onboarding.html
---

# ADR-071: Intune-First Asset Onboarding — All-Platform Doctrine for Net-New Assets

## Status

**ACCEPTED** — 2026-05-14 (drafted 2026-05-13; promoted from `inbox/drafts/intune-first-asset-onboarding/` on 2026-05-14)

## Context

UIAO's existing device-modernization doctrine has been authored for the
**migration** path:

- ADR-001 (HAADJ Deprecated) — established Entra-join as the sole device
  join target for Windows endpoints, treating HAADJ as a transitional
  state to be eliminated for existing devices.
- ADR-002 (Arc-Enabled Servers Require Non-Domain-Joined State) —
  established that on-prem servers transition from domain-joined to
  Arc + Entra-join as a hard cutover, never a hybrid coexistence.
- ADR-038 (Device-Plane OrgPath) — bound the OrgPath governance
  attribute to device objects.
- The directory-migration canon under
  `src/uiao/modernization/directory-migration/` documents the
  Discover → Normalize → Map → Migrate → Validate process for moving
  AD-joined devices into Entra ID + Intune.

What does **not** exist in canon: the doctrine for net-new assets that
should never enter the migration pipeline at all because they should
never have been AD-joined in the first place. The
`device-adapter-interface.md` registers an `intune-native/` sub-adapter
slot for "Greenfield Intune deployment" but that slot is empty. There
is no canonical answer to the question: when an organization buys a
new laptop, what is the first governance step?

The implicit answer in operational practice has been: enroll the device
into Autopilot, derive its OrgPath from the provisioning user, accept
that procurement-side governance integration is weak, and rely on
post-enrollment ETL to bring the device into the governance model.

This implicit answer has three failure modes:

1. **Procurement-time OrgPath assignment is missed.** The device's
   organizational position is whatever the user-derivation script
   produces during Autopilot Account Setup. If the provisioning user is
   not the eventual primary user (helpdesk-provisioned device, shared
   device, mismatched assignment), the device's OrgPath is wrong from
   the start and remains wrong until manual correction.

2. **Cross-platform inconsistency.** The Autopilot path is well-
   documented in the OrgPath/Intune narrative. The equivalent paths for
   macOS (Apple Business Manager + ADE), iOS/iPadOS (ADE), Android
   (Zero-Touch + Knox), and Arc-managed servers are not standardized.
   Each platform has been treated as a separate problem rather than
   four implementations of one doctrine.

3. **Co-management drift.** Without an explicit doctrine prohibiting it,
   net-new Windows endpoints occasionally enter the SCCM
   co-management bucket because the existing AD/SCCM environment
   provides easier short-term provisioning. Each such device is a
   future migration ticket and a present compliance gap.

The 2026-Q2 expansion of the AD-to-EntraID Modernization track,
combined with the all-platforms scope established by the
OrgPath/Intune narrative and the procurement-system integrations
required by KYC (ADR-055) and HRIT (ADR-051..054), surfaces the gap.

## Decision

**This ADR establishes Intune-First Asset Onboarding as the canonical
doctrine for all net-new assets across all platforms, governed by five
pillars and three documented exception paths.**

The five pillars (full text in the doctrine document accompanying this
ADR):

1. **No ungoverned device, ever.** Every asset must be governance-
   enrolled before transitioning to production use; quarantine is
   the safety valve, not the steady state.

2. **Procurement is the first governance step.** Asset OrgPath is
   determined when the PO is issued, not when the device arrives.
   Procurement systems integrate with the governance pipeline as a
   peer of HR systems for user provisioning.

3. **Zero-touch only.** Manual enrollment is a controlled exception
   path requiring written justification, compensating controls, a
   finite duration, and an audit entry.

4. **One management plane per asset; no co-management for new assets.**
   Intune for endpoints; Arc + Intune Settings Catalog for servers.
   No greenfield SCCM, no greenfield GPO-based device management, no
   greenfield HAADJ.

5. **Quarantine on failure; never silently degrade.** Onboarding
   failures produce a quarantine entry and a governance ticket, never
   a silently-degraded production device.

The three documented exception paths:

- **Path A — User-driven enrollment for BYOD.** Personal devices
  enrolled through Company Portal under App Protection Policy.
- **Path B — Linux endpoint with Arc fallback.** Linux endpoints
  governed via Arc + Azure Policy Guest Configuration where Intune
  Linux MDM is insufficient.
- **Path C — Pre-Server-2025 Windows servers.** Arc-managed-only,
  consistent with ADR-002 §Negative.

The five-phase canonical process (Procure → Pre-stage → Position →
Provision → Validate) governs all platforms, with per-platform
enrollment mechanics documented as platform annexes.

## Rationale

1. **Generalizes ADR-001 from "no HAADJ" to "no AD-join, ever, for new
   assets."** ADR-001 establishes that HAADJ is not an acceptable
   interim state. The same logic generalizes: SCCM co-management is
   not an acceptable interim state for new endpoints; AD-join is not
   an acceptable interim state for any new asset that is not legacy-
   constrained.

2. **Generalizes ADR-002 from servers to all asset classes.** ADR-002
   established that Arc + Entra-join is a hard cutover for servers,
   not a gradual transition. The same hard-cutover principle applies
   to net-new assets across all platforms — they enter the target
   state on day zero, not after a migration.

3. **Procurement-time OrgPath assignment is deterministic; runtime
   user-derivation is heuristic.** The OrgPath/Intune narrative §4
   acknowledges that Autopilot user-derivation has limitations
   (helpdesk-provisioned devices, shared devices, kiosk devices)
   that require fallback to a hardware-hash mapping table. Making
   procurement-time assignment the primary path eliminates the
   heuristic failure mode rather than working around it.

4. **All-platforms doctrine produces a single governance model.**
   Per-platform documentation that codifies separate processes for
   Windows / macOS / mobile / servers produces a fragmented
   governance model that the OrgPath substrate was designed to
   prevent. One doctrine, four enrollment vectors, one validation
   suite is the structural choice consistent with UIAO's keystone
   primitives (per the AD-to-EntraID Modernization umbrella).

5. **Procurement-pipeline integration is a recognized UIAO surface.**
   The KYC canon block (ADR-055) treats authority-of-record
   integration as a first-class adapter family. Procurement is the
   parallel first-class integration for assets that the workforce
   identity surface needs but does not own. Establishing the
   doctrine now creates the surface area to register procurement
   adapters in a future ADR.

6. **The intune-native/ adapter slot is registered but empty.** The
   device-adapter-interface.md already names this slot. ADR-067
   provides the doctrine; the accompanying bundle provides the
   operational content; promotion fills the slot.

## Consequences

### Positive

- Single coherent doctrine across Windows, macOS, iOS/iPadOS, Android,
  and Arc-managed servers. Cross-platform organizations have one
  process to learn and audit, not four.
- Procurement-time OrgPath assignment eliminates the user-derivation
  heuristic failure mode for the dominant case. The runtime
  user-derivation script remains as a fallback for Phase 4 only when
  procurement record is missing, and with that fallback now flagged
  as an exception rather than the primary path.
- Net-new SCCM co-management deployments are prohibited. Existing
  co-management workloads continue under the migration path; new
  workloads must enter Intune-first.
- The intune-native/ adapter slot becomes load-bearing rather than
  reserved.
- Foundation for future procurement-system adapter registrations
  (CDW, SHI, Apple ABM-enrolled resellers, etc.) without
  re-deciding the doctrine each time.

### Negative

- **Procurement system integration is non-trivial.** Many
  organizations' procurement systems do not natively read OrgPath
  from Entra ID or write to Autopilot service principals. Initial
  rollout requires either custom integration code or a manual hand-
  off step that is itself a governance gate.
- **Vendor program enrollment cycles bound the latency.** A vendor
  that takes 5 business days to register hardware hashes is the
  bottleneck for the entire onboarding process for that vendor's
  hardware. Vendor selection becomes a governance-relevant decision.
- **Initial dry-run validation pipeline does not exist.** Phase 3
  requires a dry-run of the OrgPath assignment; that validation
  surface is not yet implemented in the modernization adapters and
  is a follow-up engineering item.
- **Some current operational practices become exception paths.**
  Helpdesk-provisioned devices that previously relied on user-
  derivation now require procurement-side OrgPath assignment or an
  exception-path grant. Operational processes need updating.
- **BYOD doctrine becomes more explicit.** Exception path A makes
  BYOD a documented carve-out rather than an unstated practice. Some
  organizations may need to update their BYOD policies in response.

### Risks

- **Vendor program limitations.** If a vendor program (e.g., Knox
  Mobile Enrollment for a specific Samsung tier, Apple ABM for a
  specific reseller relationship) does not support arbitrary tag
  values, the OrgPath cannot be carried in the vendor program record
  and the assignment must occur at Phase 3 rather than Phase 2. This
  is operationally tolerable but reduces the strength of the
  procurement-time guarantee for that vendor.

- **Procurement integration as a new attack surface.** A compromised
  procurement service principal could write incorrect OrgPath values
  to vendor program records, producing devices that enroll into the
  wrong organizational segment. The compensating control is the
  two-person review of governance repository commits at Phase 3 —
  the dry-run validation step exists specifically to surface
  procurement-side errors before they propagate to Phase 4.

- **Latency targets may be unmet for certain vendors.** If the
  organization sources from vendors with slow hardware-hash
  registration cycles, the 14-day standard target may be unmet.
  The fallback is to allow the device to enroll under user-
  derivation as an exception, with the exception logged and the
  vendor's latency surfaced as a governance metric.

- **Existing operational practices push back.** Operations teams
  accustomed to the current implicit process may resist the explicit
  procurement-side gate. Mitigation: the doctrine is rolled out per
  asset class, not all at once. Windows endpoints first (where
  Autopilot is mature); mobile and macOS second; servers and
  exceptions last.

## Verification Sources

| Source | Reference | Last Verified |
|---|---|---|
| Microsoft Learn — Windows Autopilot Device Preparation overview | https://learn.microsoft.com/en-us/autopilot/device-preparation/overview | 2026-05-13 |
| Microsoft Learn — Apple Business Manager and Intune | https://learn.microsoft.com/en-us/mem/intune/enrollment/device-enrollment-program-enroll-ios | 2026-05-13 |
| Microsoft Learn — Android Enterprise enrollment | https://learn.microsoft.com/en-us/mem/intune/enrollment/android-enrollment-overview | 2026-05-13 |
| Microsoft Learn — Azure Arc onboarding | https://learn.microsoft.com/en-us/azure/azure-arc/servers/onboard-portal | 2026-05-13 |
| ADR-001 — HAADJ Deprecated | [adr-001-haadj-deprecated-entra-join-only.md](adr-001-haadj-deprecated-entra-join-only.md) | 2026-04-28 |
| ADR-002 — Arc-Enabled Servers Require Non-Domain-Joined | [adr-002-arc-entra-join-no-domain-join.md](adr-002-arc-entra-join-no-domain-join.md) | 2026-04-28 |
| ADR-038 — Device-Plane OrgPath | [adr-038-device-plane-orgpath.md](adr-038-device-plane-orgpath.md) | (in canon) |
| OrgPath/Intune narrative — Chapters 4, 6, 8 | `inbox/drafts/complete-narrative/source-docx/OrgPath and Microsoft Intune — Structural Device Governance at Enterprise Scale.md` | 2026-05-13 |

## Review Triggers

This ADR must be re-evaluated when any of the following occur:

- [ ] Microsoft announces in-place HAADJ → Entra-join conversion (would
      relax some of the migration-vs-greenfield distinction)
- [ ] Microsoft retires Autopilot Device Preparation v1 (would reduce
      one of the platform annex's footnoted compatibility paths)
- [ ] Apple announces material changes to ABM/ASM enrollment APIs
- [ ] Android Zero-Touch or Knox Mobile Enrollment program changes
- [ ] Azure Arc adds Conditional Access support for server logins
      (would close the gap noted in ADR-002 §Negative and reduce one
      of the documented exceptions)
- [ ] Microsoft Intune adds first-class Linux MDM coverage that closes
      Exception Path B
- [ ] Microsoft Ignite 2026 (November) — scheduled review
- [ ] Microsoft Build 2027 (May) — scheduled review

## Related Documents

- ADR-001 — HAADJ Deprecated (precedent; this ADR generalizes it)
- ADR-002 — Arc-Enabled Servers (precedent; this ADR generalizes it)
- ADR-038 — Device-Plane OrgPath (consumed primitive)
- ADR-049 — Microsoft Adapter Coverage Expansion (registry of Microsoft
  surfaces this doctrine touches)
- ADR-055 — Customer Identity Canon Block (parallel doctrine for the
  customer-identity surface; this ADR is the device-onboarding peer)
- UIAO_007 — OrgTree Modernization (consumed primitive)
- UIAO_136 Spec 1 — Computer Object Transformation (sibling spec for
  the migration path)
- `src/uiao/modernization/directory-migration/` — sibling canon for
  the migration path
- `src/uiao/modernization/directory-migration/adapters/device-management/device-adapter-interface.md` — registers the `intune-native/` slot this doctrine fills
- OrgPath/Intune narrative (in `inbox/drafts/complete-narrative/`) —
  per-script implementation detail this ADR's process layer references
- This ADR's accompanying operational canon at `src/uiao/modernization/intune-first-onboarding/`:
  [`README.md`](../../modernization/intune-first-onboarding/README.md),
  [`doctrine.md`](../../modernization/intune-first-onboarding/doctrine.md),
  [`process.md`](../../modernization/intune-first-onboarding/process.md),
  [`procurement-handoff.md`](../../modernization/intune-first-onboarding/procurement-handoff.md),
  [`platforms/windows-autopilot.md`](../../modernization/intune-first-onboarding/platforms/windows-autopilot.md),
  [`platforms/macos-abm-ade.md`](../../modernization/intune-first-onboarding/platforms/macos-abm-ade.md),
  [`platforms/mobile-ios-android.md`](../../modernization/intune-first-onboarding/platforms/mobile-ios-android.md),
  [`platforms/arc-managed-servers.md`](../../modernization/intune-first-onboarding/platforms/arc-managed-servers.md),
  [`validation-and-evidence.md`](../../modernization/intune-first-onboarding/validation-and-evidence.md)
