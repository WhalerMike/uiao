---
adr_id: adr-075
title: "Surface Hub Reconciliation with ADR-001 — Meeting-Room Class as Migration-Only Carve-Out"
status: DRAFT
decided: null
deciders: Michael Stratton
updated: 2026-05-18
next_review: 2026-11-01
review_trigger: Microsoft Ignite 2026; any Surface Hub or Microsoft Teams Rooms announcement
impact: ADR-001; ADR-071; IFO_014 (windows-surface platform annex)
supersedes: null
superseded_by: null
classification: Controlled
boundary: GCC-Moderate
publish_to_site: false
publication_style: include
---

# ADR-075: Surface Hub Reconciliation with ADR-001 — Meeting-Room Class as Migration-Only Carve-Out

## Status

**DRAFT** — pending acceptance. Companion to the inbox draft set at `inbox/drafts/surface-integration-plan.md` and `inbox/drafts/intune-first-asset-onboarding/platforms/windows-surface.md` (IFO_014).

## Context

[ADR-001](adr-001-haadj-deprecated-entra-join-only.md) declares Microsoft Entra Join as the **sole** device join target for all new and migrated endpoints. The decision is categorical and admits no device-class exceptions. The Computer Object Transformation specification (UIAO_136) operationalizes ADR-001 across the endpoint fleet.

Microsoft Surface Hub is a meeting-room class device family (Surface Hub 1 — retired; Surface Hub 2S — current; Surface Hub 3 — in market). Surface Hub-class hardware has historically used join paths that do not align with the categorical ADR-001 doctrine:

| Surface Hub generation | Native identity model | Reachable Entra Join state? |
|---|---|---|
| Surface Hub 1 | "Device Account" model — a designated room mailbox identity with a hybrid-style on-prem AD computer object | No — retired and out of support; migration-only consideration |
| Surface Hub 2S (factory image) | "Device Account" model; Windows 10 Team OS variant; AAD-registered (not AAD-joined) device object | Partially — Microsoft Teams Rooms on Windows (MTR on Windows) image conversion enables Entra Join on Surface Hub 2S; conversion is OEM-supported but image-replacement, not in-place |
| Surface Hub 3 | Ships either as Surface Hub OS or Microsoft Teams Rooms (MTR) on Windows; MTR variant supports Entra Join directly | Yes — when ordered or converted to MTR on Windows |

ADR-071's Intune-First Asset Onboarding doctrine and its Windows Autopilot platform annex (IFO_010) describe enrollment mechanics that presume an Entra-joined Windows endpoint. Surface Hub running its native Surface Hub OS does not satisfy that presumption.

UIAO must decide: does Surface Hub justify a narrow ADR-001 carve-out for the meeting-room class, or does Surface Hub remain bound to ADR-001 with non-conforming devices treated as migration targets and exception grants?

## Options considered

### Option A — Narrow carve-out from ADR-001 for meeting-room class

Amend ADR-001 (or supersede with this ADR) to recognize "meeting-room class" as a distinct device class with its own join doctrine. Permit Surface Hub OS to remain authoritatively governed via a non-Entra-Join management plane (Microsoft Teams Rooms Pro Management portal + Intune-for-Surface-Hub-OS configuration profiles).

- **Pro:** Operationally honest — Surface Hub OS is the shipping default on much of the installed base, and the carve-out reflects the actual deployment reality.
- **Pro:** Avoids forced hardware refresh or image-replacement for organizations with significant Surface Hub 2S installed base.
- **Con:** Weakens ADR-001's categorical clarity. Once "meeting-room class" is admitted as an exception, the doctrinal door is open for other device-class arguments (kiosks, digital signage, MFDs, hoteling-station thin clients), and the categorical statement becomes a graduated one.
- **Con:** Surface Hub OS reaches end-of-mainstream support; investing carve-out doctrine in a sunsetting OS variant is short-lived.

### Option B — Migration-only with exception-grant requirement (recommended)

Keep ADR-001 categorical. Surface Hub (and any meeting-room class device) is treated as either:

1. **Already-conforming** — Surface Hub 3 ordered as MTR on Windows, or Surface Hub 2S converted to MTR on Windows — governed identically to any other Entra-joined Windows endpoint per ADR-001 / ADR-071. No exception required.
2. **Non-conforming** — Surface Hub OS variants, Surface Hub 1, Surface Hub 2S running factory image. Treated as **migration targets**. Continued operation requires a documented exception grant per ADR-071's doctrine. Net-new procurement of non-conforming Surface Hub configurations is forbidden.

- **Pro:** Preserves ADR-001's categorical force.
- **Pro:** Aligns with Microsoft's own direction — Microsoft has been moving Surface Hub toward MTR on Windows as the management plane; betting against Surface Hub OS is consistent with Microsoft strategy.
- **Pro:** Concentrates governance effort on the Entra-joined MTR-on-Windows path, which is the dominant pattern going forward.
- **Con:** Imposes hardware/image refresh on customers with non-conforming Surface Hub 2S installed base. Re-imaging Surface Hub 2S to MTR on Windows is OEM-supported but not zero-cost — re-imaging requires physical access and Microsoft-provided image media.
- **Con:** Exception-grant pathway for non-conforming meeting-room devices needs explicit operational support in the exception-management framework (currently shaped for endpoint-level grants, not device-class grants).

### Option C — Defer the decision

Leave Surface Hub status undeclared. Treat the question as open until a customer engagement forces a concrete answer.

- **Pro:** No commitment until evidence is in hand.
- **Con:** Leaves a known gap in the Computer Object Transformation specification. The IFO_014 platform annex would have to handle Surface Hub by silence, which is worse than handling it by named exclusion.
- **Con:** Memory note ([project_uiao_regulatory_forcing_functions](../../C:\Users\whale\.claude\projects\C--Users-whale-git-uiao\memory\project_uiao_regulatory_forcing_functions.md)) reminds that compliance/transformation work is forced by external regime — open questions on device classes invite vendor pressure to resolve them in the vendor's favor.

## Decision

**Option B — Migration-only with exception-grant requirement.** ADR-001 remains categorical. Surface Hub is recognized as a device class whose hardware can host either a conforming variant (MTR on Windows, Entra-joined) or a non-conforming variant (Surface Hub OS). UIAO governs the conforming variant identically to any other Entra-joined Windows endpoint; the non-conforming variant is migration-only.

Specifically:

1. **Net-new procurement of Surface Hub 3 MUST specify the MTR on Windows configuration.** Procurement of the Surface Hub OS variant is forbidden under ADR-071 net-new doctrine and requires an exception grant.
2. **Net-new procurement of Surface Hub 2S is forbidden** as of this ADR's acceptance — the device generation is end-of-life on the Microsoft roadmap and migration is required regardless of variant.
3. **Existing Surface Hub 2S installed base** is treated as a migration target. The migration objective is conversion to MTR on Windows (in-place image replacement, Microsoft-supported) or replacement with Surface Hub 3 MTR on Windows. Continued operation pending migration requires an exception grant documenting the conversion plan and target date.
4. **Surface Hub 1 is retired** — no exception path. Devices must be decommissioned and replaced.
5. **The IFO_014 platform annex** (windows-surface) treats MTR on Windows on Surface Hub-class hardware as a sub-pattern of windows-endpoint-surface — identical Autopilot / DFCI / Intune doctrine as any other Surface form factor.

## Rationale

1. **ADR-001's categorical clarity is load-bearing for the Computer Object Transformation specification.** Admitting one device-class carve-out invites a series of similar carve-outs (kiosks, digital signage, hoteling stations, MFDs). Each carve-out independently might be defensible; in aggregate they erode the categorical doctrine that gives UIAO its operational simplicity. The conservative move is to refuse the first carve-out.

2. **Microsoft is moving Surface Hub toward MTR on Windows.** Surface Hub OS is on a sunset trajectory. Betting against Surface Hub OS is consistent with Microsoft's own strategic direction. ADR-001 should not invest doctrine in a sunsetting OS variant.

3. **The conforming path is operationally proven.** Surface Hub 3 ordered as MTR on Windows is governed identically to any other Entra-joined Windows endpoint. IFO_014 covers it without modification. There is no operational gap that requires a doctrinal carve-out — only a procurement-discipline gap that the exception process is designed to handle.

4. **Exception grants make the cost of non-conformance visible.** Forcing existing Surface Hub 2S installed base through the exception process surfaces the migration debt as an explicit governance artifact rather than letting it ride as silent non-conformance. This aligns with the project memory's "agencies are both vendors and customers of each other" doctrine — the exception-grant record is what allows downstream consumers of the substrate to see the device class accurately.

## Consequences

### Positive
- ADR-001 retains categorical force; the Computer Object Transformation specification continues to admit no device-class exceptions
- Surface Hub 3 MTR on Windows fits the existing Windows Autopilot / IFO_014 doctrine without special-casing
- Exception-grant records surface the migration debt for non-conforming Surface Hub 2S installed base
- Aligns UIAO's posture with Microsoft's own move away from Surface Hub OS

### Negative
- Customers with significant Surface Hub 2S installed base face a migration cost — either image replacement to MTR on Windows or hardware replacement to Surface Hub 3
- Procurement discipline must be tightened to ensure Surface Hub 3 orders specify MTR on Windows; default Microsoft commercial channel configuration may default to Surface Hub OS depending on SKU
- Exception-management framework must extend to accept Surface Hub 2S migration plans (target date, conversion path, interim compensating controls)

### Risks
- If Microsoft reverses direction and re-invests in Surface Hub OS as a separately-managed plane, this ADR becomes a forcing function for an inconvenient re-conversion. Low probability based on current Microsoft signals; review trigger included below.
- Some Surface Hub 2S firmware revisions may not support clean conversion to MTR on Windows. Customers in that situation may have no path other than hardware replacement; this is a hardware-vendor problem, not a UIAO governance problem, but UIAO documentation should call it out.

## Verification Sources

| Source | URL | Last Verified |
|---|---|---|
| Microsoft Learn — Surface Hub 3 overview | https://learn.microsoft.com/en-us/surface-hub/surface-hub-3-overview | 2026-05-18 (pending verification) |
| Microsoft Learn — Migrate Surface Hub 2S to Windows 10 Pro/Enterprise (image replacement to Windows 11 IoT Enterprise / MTR) | https://learn.microsoft.com/en-us/surface-hub/surface-hub-2s-migrate-to-windows-10-pro-enterprise | 2026-05-18 (pending verification) |
| Microsoft Learn — Microsoft Teams Rooms Pro Management | https://learn.microsoft.com/en-us/microsoftteams/rooms/microsoft-teams-rooms-pro-management | 2026-05-18 (pending verification) |
| ADR-001 — HAADJ Deprecated | [adr-001-haadj-deprecated-entra-join-only.md](adr-001-haadj-deprecated-entra-join-only.md) | 2026-05-18 |
| ADR-071 — Intune-First Asset Onboarding | [adr-071-intune-first-asset-onboarding.md](adr-071-intune-first-asset-onboarding.md) | 2026-05-18 |

> Sources marked "pending verification" need an authoritative pass before this ADR moves from DRAFT to ACCEPTED — the URLs are the canonical Microsoft Learn locations as of authoring but the page content / titles must be confirmed at the time of acceptance.

## Review Triggers

This ADR must be re-evaluated when any of the following occur:

- [ ] Microsoft announces a new Surface Hub generation or substantive Surface Hub roadmap change
- [ ] Microsoft re-positions Surface Hub OS as a forward-supported variant
- [ ] In-place Surface Hub 2S → MTR on Windows conversion becomes unsupported (forcing hardware replacement as the only path)
- [ ] Microsoft Ignite 2026 (November) — scheduled review
- [ ] Customer engagement surfaces a Surface Hub installed base where Option B's migration cost is operationally infeasible (forces reconsideration of Option A's narrow carve-out)

## Related Documents

- ADR-001 — HAADJ Deprecated, Entra-Join-Only ([adr-001-haadj-deprecated-entra-join-only.md](adr-001-haadj-deprecated-entra-join-only.md))
- ADR-071 — Intune-First Asset Onboarding ([adr-071-intune-first-asset-onboarding.md](adr-071-intune-first-asset-onboarding.md))
- IFO_014 — Platform Annex for Microsoft Surface Endpoints ([../intune-first-asset-onboarding/platforms/windows-surface.md](intune-first-asset-onboarding/platforms/windows-surface.md))
- Surface integration plan (umbrella draft) ([../surface-integration-plan.md](surface-integration-plan.md))
- UIAO_136 — Computer Object Transformation specification
