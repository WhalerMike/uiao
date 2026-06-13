---
adr_id: adr-104
title: "E911 Compliance Layer — Dispatchable-Location Completeness over LocPath, with RTLS-fed Dynamic Enhancement"
status: PROPOSED
decided: 2026-06-13
deciders: Michael Stratton
updated: 2026-06-13
next_review: 2026-12-13
review_trigger: The E911 completeness check is wired into a CLI surface or the substrate-drift report; the first agency location registry sets dispatchableLocationRequired in production; a UCaaS/MLTS emergency-address export consumes the dispatchable location of record; an RTLS tag/reader collection mechanism is proposed for the Dynamic Location Context; 47 CFR Part 9 (Kari's Law / RAY BAUM'S Act § 506) is amended; ADR-102 (LocPath) is revised.
impact: 'Names and ships the E911 Compliance Layer over the LocPath substrate (ADR-102 / UIAO_194). Adds one governed node attribute (e911.dispatchableLocationRequired) that turns on a read-only dispatchable-location completeness check (uiao.modernization.locpath.e911_compliance), classifying gaps DRIFT-SEMANTIC::e911-completeness with error codes GOV-LOCPATH-012..014 against 47 CFR § 9.16. Extends the Dynamic Location Context source enum with the RTLS tag-and-reader sources UWB and RFID (BLE already present), defining their role as observational enhancement that never substitutes for the governed dispatchable location of record. Amends ADR-102 §D2/§D4 and UIAO_194; introduces no new boundary enum and no OrgPath facet/slot. Out of scope (unchanged from ADR-102 §D7): emergency-call routing, RTLS collection mechanisms, facilities/network orchestration.'
supersedes: null
superseded_by: null
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-104-e911-compliance-layer.html
---

# ADR-104: E911 Compliance Layer — Dispatchable-Location Completeness over LocPath

## Status

**PROPOSED** — 2026-06-13.

This ADR is doctrine pending Governance Board acceptance. It is an **extension of [ADR-102](adr-102-locpath-location-addressing.md)** (LocPath), not a supersession: ADR-102 §D4 named E911 dispatchable location as one of the three site-classification blocks and UIAO_194 §Governance rule 5 reserved an "E911 completeness" standing finding; this ADR makes that rule executable and gives the Dynamic Location Context's RTLS sources a defined compliance role. It amends ADR-102 §D2 (the source enum) and §D4 (the obligation flag) and lands the executable artifacts ADR-102 §D6 anticipated for the dispatchable-location surface.

## Context

[ADR-102](adr-102-locpath-location-addressing.md) established LocPath as the canonical physical-location addressing dimension and named E911 dispatchable location ([47 CFR § 9.16](https://www.ecfr.gov/current/title-47/chapter-I/subchapter-A/part-9), RAY BAUM'S Act § 506 — civic address plus floor/room-level detail conveyed with a 911 call) as the first forcing function. [UIAO_194](../UIAO_194_LocPath_Codebook.md) carried that into the node attribute catalog (the `e911` block) and a standing governance rule:

> *A Site with MLTS/UCaaS presence and no resolvable dispatchable-location attributes at the required depth is a standing compliance gap, surfaced like any other governance finding.*

Two gaps remained after the ADR-102 §D6 phases shipped:

1. **The rule was prose, not code.** Nothing distinguished a node that *should* carry a dispatchable location (because 911 can be dialed from it) from one that has no telephony presence, and nothing checked the `e911` payload for § 9.16 completeness. The HR-assignment, Mover, policy/boundary, and Entra-exposure passes (§D6 phases 2–4) all shipped executable; the dispatchable-location surface did not.
2. **The RTLS sources had no defined role.** The Dynamic Location Context source enum (UIAO_194 §Two-layer model) listed `GPS | WiFi | BLE | Network | Hybrid | Manual`. An enterprise Real-Time Location System (RTLS) — UWB and Active RFID anchors/tags for cm-to-room precision, BLE 5.1+ AoA/AoD for room/zone, passive RFID readers at choke points for "last seen" — is exactly the kind of high-precision signal that can enhance an emergency-location answer at call time, but `UWB` and `RFID` were not expressible, and nothing stated the governance posture (observational enhancement, never the system of record).

The architecture question that motivated this layer — *where do tags go, what reads them, and how does that feed LocPath* — resolves cleanly onto the existing two-layer model: tags and readers feed the **observational** layer (Dynamic Location Context); the **governed** layer (the `e911` block on the Primary LocPath node) remains the dispatchable location of record. The missing piece was the completeness check that audits the governed layer and the enum values that let the observational layer name RTLS sources.

### Boundary scope

This decision is scoped to the **Moderate and Commercial** boundaries only, per the AGENTS.md boundary-enum rule and consistent with ADR-102 §"Boundary scope". It adds no boundary enum values.

## Decision

### D1. The E911 Compliance Layer is named, and is a layer over LocPath — not a new dimension

The **E911 Compliance Layer** is the regulatory-completeness surface over the LocPath substrate. It introduces no new addressing dimension, no OrgPath facet, and no `extensionAttribute` slot; it is a governed attribute plus a read-only check plus a defined role for the existing observational sources. It governs the *completeness of the dispatchable location of record* and nothing else — consistent with ADR-102 §D7, UIAO never sits in the 911 call path and never programs RTLS readers.

### D2. One governed obligation flag turns the check on

A LocPath node declares `e911.dispatchableLocationRequired: true` when it has Multi-Line Telephone System / UCaaS presence — somewhere a 911 call can originate. This is a governed node attribute (a canon change, provenance-anchored, subject to impact analysis), not an observation, and it is the place counterpart of "this site has phones." The obligation attaches at **Site or deeper**. The attribute is added to the `e911` block in UIAO_194 §Node attribute catalog and the node JSON Schema; it is optional and defaults to absent, so existing registries are unaffected.

### D3. The completeness check is executable, read-only, and inheritance-aware

`uiao.modernization.locpath.e911_compliance.detect_e911_completeness_gaps()` is the Compare/Classify pass. For every obligated node it resolves the **effective dispatchable location** — the node's own `e911` attributes plus any inherited from registered ancestors (a Floor inherits the Site's `civicAddress`; the Site need not repeat the floor) — and classifies the result against § 9.16:

| Code | Severity | Condition |
|---|---|---|
| `GOV-LOCPATH-012` | P1 | No civic address resolvable on the node or any ancestor — no dispatchable location of record exists |
| `GOV-LOCPATH-013` | P2 | A civic address resolves but no sub-address precision (`floor`/`room`/`locationDescription`) does, at Building/Floor/Space depth |
| `GOV-LOCPATH-014` | P3 | The obligation is declared at a non-locatable level (Country/Region) — a modeling fault |

The codes continue the `GOV-LOCPATH-NNN` series (006–011 are the phase-3 location-drift codes). A single-structure Site may carry a complete dispatchable location with civic address alone, so no precision finding is raised at Site level. The pass never writes and never consults Dynamic Location Context.

### D4. E911-completeness drift is a sub-class of the canonical taxonomy

Findings carry the class `DRIFT-SEMANTIC::e911-completeness` — a content-completeness gap (the governed model is missing data a regulatory obligation requires), sub-classed off the canonical ADR-012 `DRIFT-SEMANTIC` top level. This is the same extension mechanism as `DRIFT-SCHEMA::slot-occupied` ([ADR-063](adr-063-orgpath-storage-slot-binding.md)) and the phase-3 `DRIFT-*::location-*` classes ([ADR-102](adr-102-locpath-location-addressing.md) §D6 phase 3). The five ADR-012 top-level classes and the ADR-033 `DRIFT-BOUNDARY` class are unchanged.

### D5. RTLS sources enhance the observational layer; they never become the record

The Dynamic Location Context source enum (UIAO_194 §Two-layer model) is extended with the RTLS tag-and-reader sources **`UWB`** and **`RFID`** (`BLE` is already present). These are observational enhancement: on platforms that support real-time location they may sharpen an emergency-location answer at call time, and persistent divergence between observed and governed location is a drift signal (UIAO_194 §Two-layer model rule 4). They **never** substitute for the governed `e911` payload the UCaaS/MLTS platform consumes. Three constraints bind any use:

1. **Enterprise-managed only.** Tags, anchors, and readers must be enterprise-managed; consumer location services (e.g., Find My) are out of scope.
2. **Collection requires its own review.** Defining the enum value is not authorization to collect. Any tag/reader collection mechanism — especially continuous people-tracking in the federal/GCC-Moderate privacy context — requires its own review before it ships (UIAO_194 §Two-layer model rule 5), and respects the node's telemetry `boundaries` block.
3. **No call-path or reader orchestration.** UIAO consumes RTLS observations; it does not program readers and is not in the 911 path (ADR-102 §D7).

### D6. Amendment to ADR-102, not supersession

ADR-102 remains CURRENT. This ADR amends its §D2 (source enum extended with `UWB`/`RFID`) and §D4 (the `dispatchableLocationRequired` flag) and discharges the dispatchable-location portion of the §D6 implementation intent. No other ADR-102 decision changes.

## Consequences

**Positive.** The standing E911 completeness rule becomes a deterministic, testable check instead of prose — a P1 finding now fires when an MLTS/UCaaS-present location has no resolvable street address, exactly the § 9.16 floor of compliance. Inheritance-aware resolution means deep hierarchies (Floor/Space) need not redundantly restate the Site's civic address. The RTLS sources gain a defined, privacy-bounded role, so the "tags feeding LocPath" architecture has a canonical home without expanding UIAO's scope into call routing or reader orchestration.

**Trade-offs.** `dispatchableLocationRequired` is a governed input an operator must set; an unflagged MLTS-present node is invisible to the check (the layer audits declared obligations, it does not discover telephony presence — that discovery is a collector concern, like the phase-3 observational contracts). The check audits completeness, not correctness: it cannot tell whether a civic address is *accurate*, only that one resolves.

**Neutral.** The new schema field is optional and defaults absent, so existing registries validate unchanged. No new boundary enum, no OrgPath facet, no CLI surface (library-only, matching the other LocPath passes). The reference registry's worked example flags one Space node already carrying a complete payload, so it stays clean.

## Alignment

- **ADR-102 (LocPath):** amends §D2/§D4; discharges the dispatchable-location slice of §D6. Same two-layer model, same boundary scope.
- **ADR-085 (universal-enterprise positioning):** dispatchable-location completeness is vertical-agnostic; 47 CFR Part 9 is the most mature vertical instantiation, not a property of the core.
- **ADR-012 / ADR-033 / ADR-063 (drift taxonomy):** `DRIFT-SEMANTIC::e911-completeness` is a sub-class under the unchanged canonical top levels, per the established sub-classing convention.
- **ADR-092 (active governance):** the layer classifies governed data and consumes observations; it programs no data plane and routes no call.
- **AGENTS.md boundary rule:** Moderate/Commercial only; no new boundary enums.

## Next actions

1. Publish this ADR alongside the UIAO_194 amendment and the executable check — same PR.
2. Future (own PRs): surface the check in the substrate-drift report and/or a `uiao locpath e911-check` CLI command; define the RTLS collection mechanism (with its own review) if and when a deployment needs observed enhancement.

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
