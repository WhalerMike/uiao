---
adr_id: adr-102
title: "LocPath — Canonical Physical-Location Addressing Dimension (the OrgPath Counterpart for Place)"
status: PROPOSED
decided: 2026-06-11
deciders: Michael Stratton
updated: 2026-06-11
next_review: 2026-12-11
review_trigger: The executable LocPath codebook YAML + JSON Schema are promoted from spec to executable canon; the first HR-duty-station LocPath adapter ships; a UCaaS emergency-address (E911) export consumes Primary LocPath; a TIC 3.0 DIA site-approval decision is recorded against LocPath classification; ADR-088 (HR truth source) or ADR-098 (binding profiles) is revised.
impact: 'Introduces LocPath as a first-class canonical addressing dimension for physical place — Country/Region/Site/Building/Floor/Space — symmetric to OrgPath. Establishes the two-layer location model (governed Primary LocPath vs observational Dynamic Location Context), extends the ADR-088 HR-truth-source doctrine from organizational placement to physical placement (duty station), and defines site classification surfaces for E911 dispatchable location (47 CFR Part 9), TIC 3.0 use cases including Direct Internet Access and Cloud, SD-WAN/EIS transition, Microsoft 365 informed network routing, and location-scoped telemetry governance. Specifies UIAO_194 as the LocPath Codebook. LocPath is not an OrgPath facet and claims no extension-attribute slot; executable schema, adapters, Mover/drift extensions, and Entra ID exposure are deferred to the implementation phase this ADR authorizes. Explicitly out of scope: facilities operations (IWMS/CMMS/EAM), network orchestration, and emergency-call routing.'
supersedes: null
superseded_by: null
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-102-locpath-location-addressing.html
---

# ADR-102: LocPath — Canonical Physical-Location Addressing

## Status

**PROPOSED** — 2026-06-11.

This ADR is doctrine pending Governance Board acceptance. It establishes the canonical model for *where things are* — the physical-place counterpart to OrgPath's *where things sit organizationally*. It changes no runtime behavior, schema, or registry entry on acceptance; the executable artifacts land in the implementation phase the ADR authorizes, mirroring the specification-first pattern of [ADR-098](adr-098-orgpath-vendor-neutral-binding-profiles.md).

## Context

The OrgPath substrate answers organizational placement with a governed registry-and-attribute loop: OrgTree is the versioned registry, OrgPath is the derived, validated attribute, the codebook is executable canon ([ADR-035](adr-035-orgpath-codebook-binding.md), [UIAO_151](../UIAO_151_OrgPath_Codebook.md)), the 15-facet schema is fixed ([ADR-078](adr-078-orgpath-attribute-schema-15-facet.md)), and the HR system of record is the authoritative upstream source for the assignment of persons to organizational nodes ([ADR-088](adr-088-hr-as-orgtree-truth-source.md)).

Physical location has no equivalent. Place data is fragmented across HR duty-station strings, facilities and real-property lists, network site inventories, and UCaaS emergency-address tables — none canonical, none hierarchical, none drift-detected. Every consumer re-derives "site" its own way, and nothing reconciles them. Several forcing functions make this gap load-bearing now:

1. **E911 dispatchable location.** [47 CFR Part 9](https://www.ecfr.gov/current/title-47/chapter-I/subchapter-A/part-9) implements Kari's Law (direct 911 dialing and on-site notification for MLTS, § 9.8) and RAY BAUM'S Act § 506 (dispatchable location — civic address plus floor/room-level detail — conveyed with 911 calls, § 9.16). Teams and other MLTS/UCaaS emergency-address configuration needs a governed, auditable source for "what is the dispatchable location of record for this identity/site"; today that source is hand-maintained per platform.
2. **TIC 3.0 and Direct Internet Access.** [CISA's Trusted Internet Connections 3.0 program](https://www.cisa.gov/resources-tools/programs/trusted-internet-connections-tic) replaces mandatory centralized backhaul with risk-based use cases (Traditional, Branch Office, Remote User, Cloud) in which sites may break out directly to the internet and to cloud services when the required security capabilities are applied at or near the edge. The decision "which sites are approved for DIA, at what capability level" is a *per-site governance record* — exactly the kind of classified, drift-detected assertion UIAO exists to hold. The acquisition path for the modern architecture is [GSA Enterprise Infrastructure Solutions (EIS)](https://www.gsa.gov/technology/it-contract-vehicles-and-purchasing-programs/telecommunications-and-network-services/enterprise-infrastructure-solutions), which agencies are using to transition off legacy MPLS vehicles toward SD-WAN with local breakout.
3. **Network path optimization.** [Microsoft 365 informed network routing](https://learn.microsoft.com/en-us/microsoft-365/enterprise/office-365-network-mac-perf-cpe) and SD-WAN policy engines consume per-site context; without a canonical site hierarchy, the network team's site model and the identity/HR model drift apart with no detector.
4. **Location-scoped telemetry governance.** In constrained boundaries (GCC-Moderate today), *which telemetry classes may originate from which locations and egress to which destinations* is a governance assertion that currently lives nowhere. A governed site classification gives telemetry pipelines a policy subject.
5. **Zero Trust context.** Physical location is a core contextual signal in Zero Trust policy. OrgPath already projects organizational facets onto enforcement surfaces ([ADR-098](adr-098-orgpath-vendor-neutral-binding-profiles.md), [UIAO_193](../UIAO_193_OrgPath_MultiCloud_Binding.md)); the place dimension has no equivalent subject.

The matrix question — *Finance-org identities whose assigned place is not under the HQ site* — is unanswerable today because only one axis of the matrix is governed.

### Boundary scope

This decision and everything it authorizes is scoped to the **Moderate and Commercial** boundaries only, per the AGENTS.md boundary-enum rule. No GovCloud, sovereign, or high-side surfaces are in scope, and this ADR adds no boundary enum values.

## Decision

### D1. LocPath is a first-class canonical addressing dimension

UIAO adopts **LocPath**: a canonical, hierarchical, path-based representation of physical place, symmetric to OrgPath. The canonical hierarchy is

```
/<Country>/<Region>/<Site>/<Building>/<Floor>/<Space>
```

with **Site as the minimum governance unit** — every governed LocPath assertion resolves at least to a Site. Deeper segments (Building/Floor/Space) exist where E911 dispatchable-location precision or space-level governance requires them. Path syntax, segment rules, node attributes, and worked examples are specified in [UIAO_194](../UIAO_194_LocPath_Codebook.md), which this ADR establishes as the LocPath Codebook — the place counterpart to UIAO_151.

### D2. Two-layer location model: governed Primary LocPath vs observational Dynamic Location Context

Every in-scope identity carries at most one **Primary LocPath** — the governed location of record, derived from the authoritative source per D3. It is the dispatchable-location source for E911 configuration and the subject of all governance rules.

Real-time positioning signals (GPS, Wi-Fi, BLE, network-derived) are modeled as **Dynamic Location Context**: observational enrichment with source, accuracy, confidence, and timestamp. Dynamic context may *enhance* downstream consumers (e.g., higher-precision emergency location when a platform supports it) and *feeds drift detection*, but it never overrides the Primary LocPath for governance, access review, or compliance reporting. Persistent divergence between assigned and observed location is a drift signal, not a silent update.

### D3. The HR system of record is the authoritative source for assigned place

[ADR-088](adr-088-hr-as-orgtree-truth-source.md) names the workforce HR system of record as the authoritative upstream source for *organizational* placement. This ADR extends the same doctrine to *physical* placement: the HR duty-station/work-location assignment is the authoritative source for a person's Primary LocPath. Facilities and real-property systems are secondary enrichment sources for node-level detail (civic address, building/floor/space geometry, dispatchable-location attributes) — they describe the *nodes*, HR assigns the *people*. UIAO remains the governance overlay throughout, consistent with the [ADR-092](adr-092-active-governance.md) control-plane/data-plane boundary: it governs and reconciles location data; it is never the facilities system of record.

### D4. Site classification is the governed policy surface

LocPath nodes carry three classification attribute blocks, specified normatively in UIAO_194:

- **E911 dispatchable location** — civic address, floor, room/space, geodetic coordinates, location description (the § 9.16 payload).
- **Network / TIC 3.0** — `diaApproved`, `sdwanBreakoutType`, `ticCapabilityTier`, `networkZone`, `legacyMplsStatus`. `ticCapabilityTier` is an **agency-defined internal maturity tier** over the TIC 3.0 Security Capabilities Catalog; TIC 3.0 itself defines no official tiers, and the codebook says so explicitly. These attributes are the policy subject for DIA approval, the TIC 3.0 Branch Office and Cloud use cases, and SD-WAN/EIS transition tracking.
- **Telemetry / service boundaries** — `telemetryBoundary`, `dataResidencyZone`, `serviceAccessBoundary`, `boundaryEnforcementLevel`, `allowedTelemetryDestinations`. These classify what telemetry may originate from a location and what service access posture applies there.

### D5. LocPath is a dimension, not a facet — matrix governance with OrgPath

LocPath is **not** a sixteenth OrgPath facet and claims **no `extensionAttribute` slot**; the ADR-078 slot table is untouched, and the OrgPath `Region` facet retains its codebook semantics unchanged (organizational region is not physical place). Identities carry both an OrgPath and a Primary LocPath, and governance rules may predicate on the **OrgPath × LocPath matrix** (prefix matching on both axes). When LocPath storage-on-target ships, it rides the [ADR-098](adr-098-orgpath-vendor-neutral-binding-profiles.md) binding-profile mechanism — a locator declared per target profile — not a new hardcoded slot contract.

### D6. Specification first; executable artifacts deferred

On acceptance, the canonical artifacts are this ADR and UIAO_194 (narrative codebook with the normative JSON Schema embedded). Deferred to the implementation phase this ADR authorizes, each landing in its own PR:

1. Executable codebook data + JSON Schema under `src/uiao/canon/data/locpath/` and `src/uiao/schemas/locpath/` (the ADR-035 pattern).
2. The HR duty-station → LocPath conformance adapter (read-only, provenance-anchored).
3. Mover-workflow extension: duty-station change triggers Primary LocPath recalculation and impact analysis.
4. Drift-taxonomy extension ([UIAO_163](../UIAO_163_Drift_Detection_Engine_Specification.md)): location-assignment, location-policy, and location-boundary drift classes.
5. Entra ID exposure: LocPath-derived attributes for dynamic groups ([UIAO_152](../UIAO_152_Dynamic_Group_Library.md)) and Administrative Unit scoping ([UIAO_154](../UIAO_154_Delegation_Matrix_AUs_Roles.md)).

### D7. Scope guardrails

LocPath governs **identity-governance-relevant location data only**. Explicitly out of scope, permanently, inside UIAO: facilities operations (work orders, preventive maintenance, space booking, move management, lease administration — IWMS/CMMS/EAM territory), network device orchestration (SD-WAN controllers consume LocPath classification; UIAO never programs them), and emergency-call routing (UCaaS platforms consume the dispatchable location of record; UIAO never sits in the 911 call path). Any proposal to cross these lines requires its own ADR.

## Consequences

**Positive.** A single governed site hierarchy serves E911 configuration, TIC 3.0 DIA decisions, SD-WAN/EIS transition tracking, telemetry-boundary policy, and Zero Trust location context — replacing four or more uncoordinated site lists. The OrgPath × LocPath matrix makes cross-axis rules and reviews expressible for the first time. Assigned-vs-observed divergence becomes a detectable drift class instead of an invisible condition. The HR-truth-source doctrine stays coherent: one upstream authority for both placements.

**Trade-offs.** New canon surface area: a second addressing codebook to maintain, a mapping table from HR duty-station codes to LocPath nodes, and eventually new adapters and drift classes. `ticCapabilityTier` is agency-defined, so cross-agency comparability is limited by construction. Dynamic Location Context introduces privacy-sensitive observational data; the codebook constrains it to enrichment and drift roles, and any future collection mechanism needs its own review.

**Neutral.** No runtime behavior, schema, or registry entry changes on acceptance. Facilities and network systems of record are unaffected; UIAO consumes and classifies, it does not replace.

## Alignment

- **ADR-085 (universal-enterprise positioning):** place is vertical-agnostic; the federal drivers (47 CFR Part 9, TIC 3.0, EIS) are the most mature vertical instantiation, not a property of the core model.
- **ADR-088 (HR truth source):** same upstream authority, extended from organizational to physical placement.
- **ADR-092 (active governance):** LocPath is control-plane classification over provider data planes; provider systems keep their jobs.
- **ADR-098 / UIAO_193 (binding profiles):** future LocPath storage-on-target is a profile locator, not a new slot contract.
- **AGENTS.md boundary rule:** Moderate/Commercial only; no new boundary enums.

## Next actions

1. Publish UIAO_194 (LocPath Codebook) alongside this ADR — same PR.
2. Implementation phase per D6, sequenced: executable schema → HR duty-station adapter → Mover/drift extensions → Entra ID exposure.

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
