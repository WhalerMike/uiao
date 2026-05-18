---
adr_id: adr-075
title: "Surface Hub Reconciliation with ADR-001 — Meeting-Room Class as Migration-Only Carve-Out"
status: ACCEPTED
decided: 2026-05-18
deciders: Michael Stratton
updated: 2026-05-18
next_review: 2026-11-01
review_trigger: Microsoft Ignite 2026; any Surface Hub or Microsoft Teams Rooms announcement
impact: ADR-001; ADR-071; IFO_014 (windows-surface platform annex)
supersedes: null
superseded_by: null
classification: Controlled
boundary: GCC-Moderate
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-075-surface-hub-reconciliation.html
---

# ADR-075: Surface Hub Reconciliation with ADR-001 — Meeting-Room Class as Migration-Only Carve-Out

## Status

**ACCEPTED** — May 18, 2026

## Context

[ADR-001](adr-001-haadj-deprecated-entra-join-only.md) declares Microsoft Entra Join as the **sole** device join target for all new and migrated endpoints. The decision is categorical and admits no device-class exceptions. The Computer Object Transformation specification (UIAO_136) operationalizes ADR-001 across the endpoint fleet.

Microsoft Surface Hub is a meeting-room class device family. Three generations are in scope:

| Surface Hub generation | Native operating system | Microsoft support state (as of 2026-05) | Reachable Entra Join + Autopilot? |
|---|---|---|---|
| Surface Hub v1 | Windows 10 Team edition | Out of support since 2025-10-14; hardware refresh required | No |
| Surface Hub 2S (factory image) | Windows 10 Team edition | Out of support since 2025-10-14 | Only via migration to Microsoft Teams Rooms on Windows (see below) |
| Surface Hub 2S with Surface Hub 3 Compute Cartridge | Microsoft Teams Rooms on Windows (Windows 11 IoT Enterprise base) | Supported | Yes — Autopilot + Auto-login of Teams Rooms supported |
| Surface Hub 2S software-migrated to MTR on Windows | Microsoft Teams Rooms on Windows | Supported | Yes — Autopilot + Auto-login of Teams Rooms supported |
| Surface Hub 3 | Microsoft Teams Rooms on Windows | Supported | Yes — Autopilot + Auto-login of Teams Rooms supported (Microsoft CSP-partner registration recommended) |

Two date facts are load-bearing for this decision:

1. **Windows 10 Team edition reached end of support on 2025-10-14.** Unlike standard Windows 10 editions, Windows 10 Team has no extended-support option. Devices still running it receive no security updates and are not under Microsoft support.
2. **The "Migration Launcher app" software-migration path expired on 2025-12-14.** The Migration Launcher was the lowest-cost path from Surface Hub 2S running Windows 10 Team to MTR on Windows; that path is no longer available. The remaining migration paths are (a) install a Surface Hub 3 Compute Cartridge (hardware upgrade) or (b) USB recovery image install of the Windows 11 IoT Enterprise + MTR experience.

UIAO must decide: does Surface Hub justify a narrow ADR-001 carve-out for the meeting-room class, or does Surface Hub remain bound to ADR-001 with non-conforming devices treated as migration targets and exception grants?

## Options considered

### Option A — Narrow carve-out from ADR-001 for meeting-room class

Amend ADR-001 (or supersede with this ADR) to recognize "meeting-room class" as a distinct device class with its own join doctrine. Permit Windows 10 Team edition Surface Hub to remain authoritatively governed via a non-Entra-Join management plane.

- **Pro:** Operationally honest for organizations with significant installed base running Windows 10 Team edition.
- **Con:** Weakens ADR-001's categorical clarity. Once "meeting-room class" is admitted as an exception, the doctrinal door is open for other device-class arguments (kiosks, digital signage, MFDs, hoteling-station thin clients), and the categorical statement becomes a graduated one.
- **Con:** Windows 10 Team edition is *already* out of support. Investing carve-out doctrine in an out-of-support OS variant is doctrinally indefensible — the carve-out would protect non-supported devices.

### Option B — Migration-only with exception-grant requirement (recommended and accepted)

Keep ADR-001 categorical. Surface Hub (and any meeting-room class device) is treated as either:

1. **Already-conforming** — Surface Hub 3 (factory MTR on Windows), Surface Hub 2S upgraded with Surface Hub 3 Compute Cartridge, or Surface Hub 2S software-migrated to MTR on Windows — governed identically to any other Entra-joined Windows endpoint per ADR-001 / ADR-071. No exception required.
2. **Non-conforming** — Surface Hub v1, Surface Hub 2S still running Windows 10 Team edition. Treated as **migration targets**. Continued operation requires a documented exception grant per ADR-071's doctrine. Net-new procurement of non-conforming Surface Hub configurations is forbidden.

- **Pro:** Preserves ADR-001's categorical force.
- **Pro:** Aligns with Microsoft's own direction — Microsoft has *already* ended support for Windows 10 Team edition. UIAO is not betting against an OS variant; the bet is already lost.
- **Pro:** Concentrates governance effort on the Entra-joined MTR-on-Windows path, which is the only supported pattern going forward.
- **Con (acknowledged):** Imposes hardware/image refresh on customers with non-conforming Surface Hub 2S installed base. As of 2025-12-14 the software-only Migration Launcher path is no longer available — the remaining paths are Surface Hub 3 Compute Cartridge install (hardware) or USB recovery image install (requires physical access to each device). Migration is materially more disruptive than it was while the Migration Launcher was available.
- **Con:** Exception-grant pathway for non-conforming meeting-room devices needs explicit operational support in the exception-management framework (currently shaped for endpoint-level grants, not device-class grants).

### Option C — Defer the decision

Leave Surface Hub status undeclared. Treat the question as open until a customer engagement forces a concrete answer.

- **Pro:** No commitment until evidence is in hand.
- **Con:** Leaves a known gap in the Computer Object Transformation specification. The IFO_014 platform annex would have to handle Surface Hub by silence, which is worse than handling it by named exclusion.
- **Con:** Windows 10 Team edition is already EOS. Deferring means UIAO has no posture on out-of-support hardware in customer environments.

## Decision

**Option B — Migration-only with exception-grant requirement.** ADR-001 remains categorical. Surface Hub is recognized as a device class whose hardware can host either a conforming variant (MTR on Windows, Entra-joined) or a non-conforming variant (Windows 10 Team edition, out-of-support). UIAO governs the conforming variant identically to any other Entra-joined Windows endpoint; the non-conforming variant is migration-only.

Specifically:

1. **Net-new procurement of Surface Hub 3 MUST specify the MTR on Windows configuration.** Surface Hub 3 ships in this configuration by default; the requirement is to verify the ordered SKU at procurement intake rather than to alter Microsoft commercial-channel defaults.
2. **Net-new procurement of Surface Hub 2S is forbidden** as of this ADR's acceptance — the device generation is no longer commercially available from Microsoft as a net-new offer and any acquisition would be secondary-market and out-of-support.
3. **Existing Surface Hub 2S installed base** is treated as a migration target. The migration objective is conversion to MTR on Windows. Acceptable migration paths as of 2026-05-18:
   - **Surface Hub 3 Compute Cartridge install** (hardware upgrade, Microsoft-supported, requires physical access)
   - **Windows 11 IoT Enterprise + MTR USB recovery image install** (software, requires physical access, supported via Surface Recovery website)
   - The Migration Launcher app path *was* the simplest migration option but expired on 2025-12-14 and is no longer available.

   Continued operation pending migration requires an exception grant documenting the chosen migration path and target date.
4. **Surface Hub v1 is retired** — no migration path exists. Devices must be decommissioned and replaced (hardware refresh to Surface Hub 3).
5. **The IFO_014 platform annex** (windows-surface) treats MTR on Windows on Surface Hub-class hardware as a sub-pattern of windows-endpoint-surface — identical Autopilot doctrine as any other Surface form factor. Surface Hub Autopilot uses the same Autopilot service infrastructure as other Windows endpoints, with the addition of the **Auto-login of Teams Rooms** capability for meeting-room sign-in.

## Rationale

1. **ADR-001's categorical clarity is load-bearing for the Computer Object Transformation specification.** Admitting one device-class carve-out invites a series of similar carve-outs (kiosks, digital signage, hoteling stations, MFDs). Each carve-out independently might be defensible; in aggregate they erode the categorical doctrine that gives UIAO its operational simplicity. The conservative move is to refuse the first carve-out.

2. **Windows 10 Team edition is already out of support.** ADR-001 should not invest doctrine in a sunsetted OS variant. The bet that UIAO would be making with Option A — that Windows 10 Team edition deserves protection from ADR-001's reach — is a bet to protect non-supported software, which is doctrinally indefensible.

3. **The conforming path is operationally proven.** Surface Hub 3 ordered as MTR on Windows is governed identically to any other Entra-joined Windows endpoint. Microsoft Learn documents Surface Hub Autopilot enrollment with DFCI support for both Compute-Cartridge-upgraded and software-migrated Surface Hub 2S devices. IFO_014 covers all conforming variants without modification.

4. **Exception grants make the cost of non-conformance visible.** Forcing existing Surface Hub 2S installed base through the exception process surfaces the migration debt as an explicit governance artifact rather than letting it ride as silent non-conformance. This aligns with the project doctrine that the substrate's data plane must surface compliance state to all downstream consumers.

## Consequences

### Positive
- ADR-001 retains categorical force; the Computer Object Transformation specification continues to admit no device-class exceptions
- Surface Hub 3 (and Compute-Cartridge-upgraded or software-migrated Surface Hub 2S) fits the existing Windows Autopilot / IFO_014 doctrine without special-casing
- Exception-grant records surface the migration debt for non-conforming Surface Hub installed base
- Aligns UIAO's posture with Microsoft's own ended-support state for Windows 10 Team edition

### Negative
- Customers with significant Surface Hub 2S installed base running Windows 10 Team edition face a material migration cost. The simplest software-only migration path (Migration Launcher app) expired 2025-12-14; remaining paths require physical access to each device, either for Compute Cartridge install or USB recovery image install.
- Surface Hub v1 customers face a hardware refresh — no migration path exists.
- Procurement discipline must verify Surface Hub 3 SKU configuration is MTR on Windows (it is by default; this is verification, not configuration).
- Exception-management framework must extend to accept Surface Hub 2S migration plans (target date, conversion path, interim compensating controls).

### Risks
- If Microsoft reverses direction and re-invests in Windows 10 Team edition or a successor Surface Hub OS variant, this ADR becomes a forcing function for an inconvenient re-conversion. Low probability based on the executed end-of-support on 2025-10-14; review trigger included below.
- Some Surface Hub 2S firmware revisions may not accept the Windows 11 IoT Enterprise + MTR recovery image cleanly. Customers in that situation may have no path other than Compute Cartridge upgrade or hardware replacement; this is a hardware-vendor problem, not a UIAO governance problem, but UIAO documentation should call it out.

## Verification Sources

| Source | URL | Verified |
|---|---|---|
| Microsoft Learn — Surface Hub admin guide (root) | https://learn.microsoft.com/en-us/surface-hub/ | 2026-05-18 |
| Microsoft Learn — Get started with Surface Hub 3 running Teams Rooms on Windows | https://learn.microsoft.com/en-us/surface-hub/surface-hub-3-get-started | 2026-05-18 |
| Microsoft Learn — End of support options and migration paths for Surface Hub v1 and 2S running Windows 10 Team edition | https://learn.microsoft.com/en-us/surface-hub/surface-hub-windows10-eos-migration | 2026-05-18 |
| Microsoft Learn — Migrate Surface Hub 2S to MTR on Windows (Migration Launcher; expired 2025-12-14) | https://learn.microsoft.com/en-us/surface-hub/surface-hub-2s-migrate-to-mtr-w | 2026-05-18 |
| Microsoft Learn — Deploy Surface Hub with Windows Autopilot & Teams Rooms Auto-login | https://learn.microsoft.com/en-us/surface-hub/surface-hub-autopilot | 2026-05-18 |
| Microsoft Learn — Microsoft Teams Rooms documentation root | https://learn.microsoft.com/en-us/microsoftteams/rooms/ | 2026-05-18 |
| Microsoft Learn — Teams Rooms Pro Management Portal | https://learn.microsoft.com/en-us/microsoftteams/rooms/managed-meeting-rooms-portal | 2026-05-18 |
| ADR-001 — HAADJ Deprecated | [adr-001-haadj-deprecated-entra-join-only.md](adr-001-haadj-deprecated-entra-join-only.md) | 2026-05-18 |
| ADR-071 — Intune-First Asset Onboarding | [adr-071-intune-first-asset-onboarding.md](adr-071-intune-first-asset-onboarding.md) | 2026-05-18 |

## Review Triggers

This ADR must be re-evaluated when any of the following occur:

- [ ] Microsoft announces a new Surface Hub generation or substantive Surface Hub roadmap change
- [ ] Microsoft re-positions Windows 10 Team edition as a forward-supported variant or announces a successor OS that is not MTR on Windows
- [ ] In-place Surface Hub 2S → MTR on Windows conversion becomes unsupported (forcing hardware replacement as the only path)
- [ ] Microsoft Ignite 2026 (November) — scheduled review
- [ ] Customer engagement surfaces a Surface Hub installed base where Option B's migration cost is operationally infeasible (forces reconsideration of Option A's narrow carve-out)

## Related Documents

- ADR-001 — HAADJ Deprecated, Entra-Join-Only ([adr-001-haadj-deprecated-entra-join-only.md](adr-001-haadj-deprecated-entra-join-only.md))
- ADR-071 — Intune-First Asset Onboarding ([adr-071-intune-first-asset-onboarding.md](adr-071-intune-first-asset-onboarding.md))
- IFO_014 — Platform Annex for Microsoft Surface Endpoints (`src/uiao/modernization/intune-first-onboarding/platforms/windows-surface.md`)
- Surface integration plan (working draft) — `inbox/drafts/surface-integration-plan.md`
- UIAO_136 — Computer Object Transformation specification
