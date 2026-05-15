---
document_id: IFO_001
title: "Intune-First Asset Onboarding — Doctrine"
version: "1.0"
status: CANONICAL
owner: "Michael Stratton"
created_at: "2026-05-13"
updated_at: "2026-05-14"
boundary: GCC-Moderate
canon_anchor: ADR-071
publish_to_site: true
publication_style: narrative
published_at: docs/modernization/intune-first.qmd
---

# Intune-First Asset Onboarding — Doctrine

> **Five pillars.** Every net-new asset acquired by the organization
> must satisfy all five before it enters production. Exceptions are
> documented carve-outs, never improvisations.

---

## Pillar 1 — No ungoverned device, ever

A device is **governed** when, at minimum: (a) its directory object
exists in Entra ID, (b) it carries an OrgPath value matching an Active
node in the OrgTree registry, (c) it is enrolled in Intune (or, for
servers, in Azure Arc and bound to the Intune Settings Catalog where
that surface is supported), and (d) it has been evaluated by at least
one compliance policy whose result is recorded in the Intune compliance
state.

A device is **production** when an organizational user signs in to it
and uses it to access organizational data.

**The pillar.** No device may transition from "powered on for the first
time" to "production" without first becoming governed. The transition
is gated by zero-touch enrollment and OrgPath stamping; absent those,
Conditional Access denies access to all organizational resources.

The quarantine OrgPath value `/UNPOSITIONED` and the corresponding
restricted-compliance policy described in the OrgPath/Intune narrative
are the safety valve, not the steady state. A device parked in
`/UNPOSITIONED` is governance-visible but resource-blocked, which
satisfies the pillar while signaling that human review is required.

**Why:** the alternative — a window of ungoverned operation between
power-on and first ETL pipeline run — is the failure mode the AD-era
governance model exhibited. It produces devices that authenticate
against on-prem directory services without ever being inventoried, and
those devices are the population from which lateral-movement and
ransomware blast radius is drawn.

---

## Pillar 2 — Procurement is the first governance step

Asset organizational position is determined when the purchase order is
issued, not when the device arrives. The purchase order carries (at
minimum): the recipient's Entra ID UPN or the receiving location's
OrgPath, the device class (laptop / mobile / server / etc.), the SKU
and serial-number range if known at PO time, and the OrgPath value the
asset should carry in production.

The procurement system writes these values to the appropriate vendor
pre-registration surface during PO fulfillment: Autopilot device
profile assignment for Windows, ABM/ASM device assignment for Apple
hardware, Android Zero-Touch or Knox Mobile Enrollment device record
for Android, Arc onboarding token issuance for servers. By the time
the asset's serial number is registered with the vendor's enrollment
program, the OrgPath assignment is already in place.

**The pillar.** No device may complete vendor pre-registration without
its OrgPath assignment. Procurement systems integrate with the
governance pipeline as a peer of HR systems for user provisioning.

**Why:** the OrgPath/Intune narrative documents the runtime fallback —
deriving OrgPath from the provisioning user's OrgPath during Autopilot
Account Setup. That fallback exists because procurement integration
has historically been weak. It works, but it produces devices whose
position depends on whoever happens to provision them, which is not
deterministic and is not auditable. Procurement-time assignment is
deterministic, auditable, and precedes any user interaction with the
device.

---

## Pillar 3 — Zero-touch only, manual enrollment is exception

Production-enrolling a device by manually walking through an enrollment
wizard, manually entering user credentials, or manually registering the
device with Intune from the device itself is forbidden by default.
Zero-touch enrollment via the platform's vendor program — Windows
Autopilot, Apple Automated Device Enrollment, Android Zero-Touch /
Knox — is the only sanctioned path.

Manual enrollment is permissible only as a documented exception path
with: (a) written justification from the requesting governance owner,
(b) a compensating control specifying how the OrgPath assignment will
be verified after enrollment, (c) a finite duration after which the
device will either be re-enrolled via zero-touch or decommissioned, and
(d) an audit-log entry recording the exception grant.

**The pillar.** Manual enrollment is a controlled exception, never the
norm. The exception path exists because some asset classes (lab
prototype hardware, vendor-loaner devices, hardware that pre-dated
zero-touch program enrollment) cannot use zero-touch, and refusing to
govern them at all would be worse than governing them through a weaker
path.

**Why:** zero-touch enrollment is the only enrollment vector that
guarantees OrgPath stamping happens before first user logon. Manual
enrollment opens a window between user logon and post-enrollment ETL
during which the device may be used to access organizational resources
without a compliance policy applied. Zero-touch closes the window.

---

## Pillar 4 — One management plane per asset; no co-management for new assets

Net-new endpoints are managed by Intune. Net-new servers are managed by
Azure Arc, with policy delivered via the Intune Settings Catalog where
applicable. There is no greenfield deployment of SCCM, no greenfield
deployment of GPO-based device management, no greenfield deployment of
HAADJ. Existing co-managed devices are governed by the AD migration
path under [`src/uiao/modernization/directory-migration/`](../directory-migration/README.md);
they are not propagated forward.

For multi-platform organizations, "one management plane" means
Intune-or-Arc as the *governance* plane. Per-platform vendor consoles
(Apple Configurator, Samsung Knox Manage, etc.) may be used for
hardware-specific configuration that Intune does not yet expose, but
they are subordinate to Intune for compliance evaluation and policy
targeting. A device's governance state is determined by Intune, not by
the per-platform vendor console.

**The pillar.** No new asset enters a co-management arrangement.
Intune (or Arc + Intune Settings Catalog for servers) is the sole
governance authority for the asset's lifetime under organizational
ownership. Vendor-specific consoles operate within Intune's
boundaries, not parallel to them.

**Why:** ADR-001 established that HAADJ is a transitional state to be
eliminated, not a permanent operating mode. The same logic generalizes:
co-management with SCCM is a transitional state for existing fleets.
Net-new assets should not be born into a transitional state. They
should be born into the target state.

---

## Pillar 5 — Quarantine on failure; never silently degrade

If any phase of the onboarding process fails — procurement does not
write OrgPath, vendor pre-registration is missed, zero-touch enrollment
encounters an error, OrgPath stamping cannot complete — the device
must enter the `/UNPOSITIONED` quarantine state. The
ORG-BRANCH-UNPOSITIONED group's compliance policy marks the device
non-compliant immediately on evaluation. Conditional Access blocks
all resource access from non-compliant devices.

The quarantine is governance-visible — the device appears in Intune,
in the OrgPath drift dashboard, and in the daily Sentinel analytics
rule from the OrgPath/Intune narrative §8.3. The governance team has
an SLA for resolving quarantine entries (defined in the governance
charter referenced from the narrative §5.3). The quarantine is not a
backlog; it is a queue with a target latency.

**The pillar.** No onboarding failure is silent. Every failure
produces a quarantine entry and a governance ticket. Devices in
quarantine cannot access organizational resources, but they exist in
the governance model and are visible to the governance team.

**Why:** silent failures during onboarding produce devices that are
enrolled in Intune but not in any branch group, that have a default
compliance policy assigned only because some catch-all rule covered
them, and that operate for weeks before anyone notices. The
quarantine model trades visibility for productivity — a quarantined
device cannot do work, but its inability to do work is the signal that
governance attention is needed.

---

## §4. Documented exception paths

Three exception paths are recognized by this doctrine. Each requires
written justification, a compensating control, and an audit entry.

### Exception path A — User-driven enrollment for BYOD

**Applies to:** personally-owned devices being enrolled to a corporate
work profile or partition. iOS/iPadOS user-enrolled, Android
Enterprise work-profile, Windows registered (not joined) devices.

**Compensating controls required:**
- App Protection Policy enforced on the work profile / corporate apps
- Conditional Access policy requires App Protection Policy compliance
  as a grant control before access to corporate data
- OrgPath assignment derived from the user's OrgPath at enrollment time
  (no procurement pre-registration, since procurement did not occur)
- Compliance policy a strict subset of corporate-device policy
  (acknowledging the device is not under full corporate control)

**Why permissible:** some agencies and organizations require BYOD
support for cost or workforce-flexibility reasons. Refusing to govern
BYOD at all would push users to entirely-unmanaged access via personal
browsers, which is worse than the user-driven enrollment path. The
exception path is governed, just at a lower assurance level.

**Why not the default:** procurement pre-registration is the strongest
governance signal; user-driven enrollment cannot satisfy it. Pillar 2
requires procurement to be the first step, which is structurally
impossible for a device the organization did not purchase.

### Exception path B — Linux endpoint with Arc fallback

**Applies to:** Linux endpoints that cannot use Microsoft Intune's
Linux MDM surface (developer workstations requiring root, embedded
Linux devices, Linux endpoints in air-gapped networks where Arc
connectivity is unavailable).

**Compensating controls required:**
- Arc onboarding within the GCC/commercial boundary appropriate to the
  asset
- Manual OrgPath assignment via tag on the Arc-enabled machine
  resource, recorded in the governance audit log
- Compliance evaluation via Azure Policy Guest Configuration
  (DSC-based), substituting for Intune compliance policy
- Documented decommissioning timeline if Linux MDM coverage extends to
  the asset's use case in a future Intune release

**Why permissible:** Microsoft's Intune Linux MDM is GA but limited.
Many Linux use cases cannot be accommodated. Arc + Guest Configuration
is the substitute governance plane.

**Why not the default:** Intune is the canonical management plane for
endpoints (Pillar 4). Arc is the canonical plane for servers, not
endpoints. Using Arc for an endpoint is acknowledging that the
endpoint cannot be governed by the canonical plane; that
acknowledgment is the carve-out.

### Exception path C — Pre-Server-2025 Windows servers

**Applies to:** Windows Server 2019 and 2022 hosts that the
organization owns and operates, and whose OS upgrade to Windows Server
2025 is not yet feasible or scheduled.

**Compensating controls required:**
- Arc-enabled for management and telemetry (per ADR-002)
- Cannot use AADLoginForWindows extension (per ADR-002 §Negative)
- Local administrator access remains AD-bound until OS upgrade
- OS upgrade to Windows Server 2025 scheduled with a target date, or
  decommissioning scheduled if upgrade not feasible
- Server-specific compliance policy (Azure Policy Guest Configuration)
  acknowledging the dual identity state

**Why permissible:** ADR-002 explicitly notes that Windows Server
2019/2022 cannot use Entra-ID login through Arc. The decision was
made at ADR-002 time that Arc-managed-only is acceptable as an interim
state for these OS versions.

**Why not the default:** Pillar 4 requires Intune (or Arc into Intune
Settings Catalog) as the sole governance authority. AADLoginForWindows
unavailability means part of the server's identity surface remains in
AD, which is sub-optimal but tolerated for a finite duration.

---

## §5. What the pillars are not

The pillars do not require:

- That every asset already in production be re-enrolled under
  Intune-first. Existing assets follow the migration path.
- That the organization have zero AD presence. AD continues to exist
  for legacy applications; Intune-first applies to new assets only.
- That every governance decision be made at procurement time. Some
  decisions (compliance policy version, scope tag membership) are
  derived from OrgPath at runtime. Procurement determines OrgPath, not
  every downstream consequence.
- That manual enrollment never happen. It is the exception path, not
  the prohibited path.

The pillars *do* require that any departure from the doctrine be
documented, justified, and time-bounded — never silently accepted.
