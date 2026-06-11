---
document_id: UIAO_194
title: "LocPath Codebook — Canonical Physical-Location Addressing & Site Classification"
version: "1.0"
status: Draft
owner: Michael Stratton
created_at: "2026-06-11"
updated_at: "2026-06-11"
publish_to_site: true
publication_style: include
lifecycle: aspirational
lifecycle_review: "2026-12-11"
---

# UIAO_194: LocPath Codebook

> **LocPath is the OrgPath counterpart for place.** Per [ADR-102](adr/adr-102-locpath-location-addressing.md), LocPath is the canonical, hierarchical, path-based representation of physical location — the governed answer to *where is this site, building, space, or person assigned* — symmetric to OrgPath's governed answer for organizational placement. This codebook is the single source of truth for LocPath syntax, hierarchy, node attributes, classification surfaces, and governance rules. The facet semantics of OrgPath ([UIAO_151](UIAO_151_OrgPath_Codebook.md)) are untouched: LocPath is a second addressing **dimension**, not a sixteenth facet.

## Purpose

This codebook specifies:

1. The **path syntax** and construction rules for LocPath values.
2. The **hierarchy levels** (Country → Region → Site → Building → Floor → Space) and what each level is for.
3. The **node attribute catalog** — core identity/provenance attributes plus the three classification blocks established by ADR-102 §D4: E911 dispatchable location, network/TIC 3.0, and telemetry/service boundaries.
4. The **two-layer location model** — governed Primary LocPath vs observational Dynamic Location Context (ADR-102 §D2).
5. The **matrix relationship** with OrgPath and the governance rules that operate on it.
6. The **normative JSON Schema** that the executable artifacts (deferred per ADR-102 §D6) must satisfy.

Scope is identity-governance-relevant location data only, at the Moderate and Commercial boundaries. Facilities operations, network orchestration, and emergency-call routing are out of scope per ADR-102 §D7.

## Path syntax

The canonical string form is:

```
/<Country>/<Region>/<Site>/<Building>/<Floor>/<Space>
```

Construction rules:

- A leading `/` is required; segments are separated by `/`.
- Each segment is a stable canonical identifier drawn from the location registry, not free text. Allowed characters per segment: `A–Z a–z 0–9 _ . -`.
- Comparison is case-insensitive; storage is in the registered canonical casing.
- Trailing segments may be omitted to address a containing node (`/USA/MD/ANNAPOLIS-HQ` addresses the whole Site).
- Governance rules match on **path prefixes** (`/USA/MD/ANNAPOLIS-HQ/*` covers every node under the Site), exactly as OrgPath rules match facet predicates.
- Every governed assertion resolves at least to the **Site** level.

## Hierarchy levels

| Level | Governance role | E911 relevance | Network/TIC relevance |
|---|---|---|---|
| **Country** | Jurisdiction grouping | — | Low |
| **Region** | Geographic/administrative grouping (state, region) | — | Medium |
| **Site** | **Minimum governance unit.** DIA approval, telemetry boundary, SD-WAN classification, and assignment all resolve here | Recommended (default civic address) | **High** — the TIC 3.0 / DIA / SD-WAN policy subject |
| **Building** | Physical structure within a site | Required for dispatchable location | Medium |
| **Floor** | Floor within a building | Required for dispatchable location | Low |
| **Space** | Room, suite, or defined area | Highest dispatchable precision | Low |

Not every LocPath needs all six levels. Sites with a single building may stop at Site for governance and carry the dispatchable attributes there; campuses with E911 obligations extend to Building/Floor/Space.

The `Region` **level of LocPath** and the `Region` **facet of OrgPath** are distinct concepts: the OrgPath facet describes organizational region (a reporting structure); the LocPath level describes geography. Neither derives from the other.

## Node attribute catalog

### Core attributes (all levels)

| Attribute | Type | Required | Description |
|---|---|---|---|
| `locPathId` | string (UUID) | yes | Canonical unique identifier for the node (UIAO-generated SSOT key) |
| `locPath` | string | yes | Full canonical path string |
| `displayName` | string | yes | Human-readable name |
| `level` | enum | yes | `Country` \| `Region` \| `Site` \| `Building` \| `Floor` \| `Space` |
| `status` | enum | yes | `Active` \| `Inactive` \| `Planned` \| `Deprecated` |
| `owner` | string | recommended | Organizational steward (an OrgPath reference or principal) |
| `lastUpdated` | timestamp | yes | Last change, with provenance |
| `sourceSystem` | string | yes | Authoritative source for this node (e.g., facilities/real-property system) |
| `sourceRecordId` | string | recommended | Identifier in the source system |

### E911 dispatchable location (Building / Floor / Space; Site default)

The dispatchable-location payload per [47 CFR § 9.16](https://www.ecfr.gov/current/title-47/chapter-I/subchapter-A/part-9) — civic address plus information sufficient to locate the caller (floor, room, or equivalent).

| Attribute | Type | Description |
|---|---|---|
| `civicAddress` | string | Validated street address |
| `floor` | string | Floor identifier |
| `room` | string | Room/space identifier |
| `geoLatitude` / `geoLongitude` | number | WGS84 coordinates |
| `locationDescription` | string | Free-text aid for responders ("West Wing, 2nd Floor, Room 210") |

### Network / TIC 3.0 classification (primarily Site)

| Attribute | Type | Description |
|---|---|---|
| `diaApproved` | boolean | Site approved for Direct Internet Access under the agency's TIC 3.0 risk determination |
| `sdwanBreakoutType` | enum | `Local` \| `Centralized` \| `Hybrid` |
| `ticCapabilityTier` | enum | `Tier-1` \| `Tier-2` \| `Tier-3` — **agency-defined** internal maturity tier over the TIC 3.0 Security Capabilities Catalog. TIC 3.0 defines no official tiers; this attribute records the agency's own determination and must not be presented as a CISA designation |
| `networkZone` | string | Trust-zone classification |
| `legacyMplsStatus` | enum | `Active` \| `Decommissioning` \| `Decommissioned` — EIS/SD-WAN transition tracking |

These attributes are the policy subject for the TIC 3.0 Branch Office and Cloud use cases: a site's eligibility for direct internet or direct-to-cloud breakout is read from `diaApproved` + `ticCapabilityTier`, and the decision history is provenance-anchored like every other canon assertion.

### Telemetry / service boundaries (primarily Site)

| Attribute | Type | Description |
|---|---|---|
| `telemetryBoundary` | enum | `InternalOnly` \| `GCCAllowed` \| `FedRAMPModerate` \| `Restricted` — what telemetry may originate from this location |
| `dataResidencyZone` | string | Residency zone label |
| `serviceAccessBoundary` | enum | `Full` \| `Limited` \| `BoundaryEnforced` \| `Isolated` |
| `boundaryEnforcementLevel` | enum | `Strict` \| `Monitored` \| `Advisory` |
| `telemetryClassification` | string | Telemetry-category allowance label |
| `allowedTelemetryDestinations` | string[] | Explicit destination allow-list |

### HR linkage (identity-side)

| Attribute | Type | Description |
|---|---|---|
| `primaryDutyStation` | boolean | True for at most one LocPath assignment per identity |
| `hrSourceSystem` | string | HR system of record (per [ADR-088](adr/adr-088-hr-as-orgtree-truth-source.md), extended to place by ADR-102 §D3) |
| `hrRecordId` | string | Identifier in the HR system |

## The two-layer location model

**Primary LocPath** is the governed location of record for an identity: derived from the HR duty-station assignment, mapped through the duty-station → LocPath mapping table, validated against this codebook, and provenance-anchored. It is the source for E911 emergency-address configuration, access reviews, matrix governance, and compliance reporting.

**Dynamic Location Context** is observational: the most recent positioning signal for an identity/device, with its origin and quality:

| Attribute | Type | Description |
|---|---|---|
| `source` | enum | `GPS` \| `WiFi` \| `BLE` \| `Network` \| `Hybrid` \| `Manual` |
| `latitude` / `longitude` | number | WGS84 |
| `accuracyMeters` | number | Estimated horizontal accuracy radius |
| `floorHint` | string | Indoor-positioning floor estimate |
| `timestamp` | timestamp | Capture time |
| `confidence` | enum | `High` \| `Medium` \| `Low` |
| `isCurrent` | boolean | Most recent known reading |

Relationship rules (normative):

1. An identity has **at most one** Primary LocPath and **at most one** current Dynamic Location Context.
2. Dynamic context **never overrides** the Primary LocPath for governance, access review, or compliance reporting.
3. Downstream consumers that support real-time location (e.g., UCaaS emergency calling) may prefer high-confidence dynamic data at call time; the Primary LocPath remains the governed dispatchable-location fallback and the configured location of record.
4. **Persistent divergence** between Primary LocPath and Dynamic Location Context is a drift signal (location-assignment drift, below), not a silent update.
5. Dynamic Location Context is privacy-sensitive observational data. This codebook defines its shape and governance role only; any collection mechanism requires its own review before it ships.

## Matrix governance with OrgPath

Identities carry both an OrgPath and a Primary LocPath. Governance rules may predicate on both axes by prefix:

- *Identities with OrgPath Department=Finance whose Primary LocPath is not under `/USA/MD/ANNAPOLIS-HQ/*` require step-up review.*
- *Dynamic group: all identities at Sites where `diaApproved = false`, for conditional-access backhaul policy.*
- *Access certification: does this person still need Building-3 resources given their current duty station?*

The matrix is evaluated against governed values only (Primary LocPath, registered node attributes) — never against Dynamic Location Context.

## Governance and provenance rules

1. **Registry-outward authority.** Like OrgTree over OrgPath, the location registry is authoritative over stamped/derived LocPath values; per-object edits are not authoritative.
2. **Source priority.** HR duty station assigns people (Primary LocPath); facilities/real-property systems describe nodes (addresses, dispatchable attributes). Conflicts are reconciled toward the declared source for that attribute class and logged.
3. **Change control.** Node creation, status changes, and classification changes (`diaApproved`, `telemetryBoundary`, `serviceAccessBoundary`, …) are canon changes: provenance-anchored, with impact analysis on assigned identities and dependent rules. Deactivating a Site with assigned identities is blocked until assignments are remapped.
4. **Drift classes** (taxonomy extension deferred per ADR-102 §D6, names reserved here):
   - **Location-assignment drift** — Primary LocPath disagrees with the HR duty station, or observed context persistently diverges from assignment.
   - **Location-policy drift** — enforced network/access behavior disagrees with site classification (e.g., a `diaApproved: false` site exhibiting local breakout).
   - **Location-boundary drift** — telemetry observed originating from, or egressing to, destinations outside the site's `telemetryBoundary` / `allowedTelemetryDestinations`.
5. **E911 completeness.** A Site with MLTS/UCaaS presence and no resolvable dispatchable-location attributes at the required depth is a standing compliance gap, surfaced like any other governance finding.

## Normative JSON Schema

The executable node schema ships at `src/uiao/schemas/locpath/location.schema.json` and must remain equivalent to the following normative definition. The registry envelope (a versioned, provenance-anchored collection of nodes) ships at `src/uiao/schemas/locpath/location-registry.schema.json`, and the **reference registry** — the executable form of §Worked example — ships at `src/uiao/canon/data/locpath/location-registry.yaml`. Both are loaded and integrity-validated (level/depth consistency, case-insensitive path uniqueness, parent existence) by `uiao.modernization.locpath`. The **duty-station → LocPath mapping table** is likewise executable: schema at `src/uiao/schemas/locpath/duty-station-map.schema.json`, reference map at `src/uiao/canon/data/locpath/duty-station-map.yaml`, consumed by the read-only HR assignment pass `uiao.modernization.locpath.hr_assign` (adapter `hr-duty-station-locpath`, ADR-102 §D6 phase 2) — every map target must resolve in the paired registry at Site level or deeper.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://uiao.io/schemas/locpath/location.schema.json",
  "title": "UIAO Location Node",
  "description": "Canonical LocPath location node: core identity, E911 dispatchable location, network/TIC 3.0 classification, and telemetry/service boundaries. Normative per UIAO_194 / ADR-102.",
  "type": "object",
  "required": ["locPathId", "locPath", "displayName", "level", "status", "lastUpdated", "sourceSystem"],
  "properties": {
    "locPathId": { "type": "string", "format": "uuid" },
    "locPath": { "type": "string", "pattern": "^/([A-Za-z0-9_.-]+)(/[A-Za-z0-9_.-]+)*$" },
    "displayName": { "type": "string" },
    "level": { "enum": ["Country", "Region", "Site", "Building", "Floor", "Space"] },
    "status": { "enum": ["Active", "Inactive", "Planned", "Deprecated"] },
    "owner": { "type": "string" },
    "lastUpdated": { "type": "string", "format": "date-time" },
    "sourceSystem": { "type": "string" },
    "sourceRecordId": { "type": "string" },
    "e911": {
      "type": "object",
      "properties": {
        "civicAddress": { "type": "string" },
        "floor": { "type": "string" },
        "room": { "type": "string" },
        "geoLatitude": { "type": "number", "minimum": -90, "maximum": 90 },
        "geoLongitude": { "type": "number", "minimum": -180, "maximum": 180 },
        "locationDescription": { "type": "string" }
      },
      "additionalProperties": false
    },
    "network": {
      "type": "object",
      "properties": {
        "diaApproved": { "type": "boolean" },
        "sdwanBreakoutType": { "enum": ["Local", "Centralized", "Hybrid"] },
        "ticCapabilityTier": { "enum": ["Tier-1", "Tier-2", "Tier-3"] },
        "networkZone": { "type": "string" },
        "legacyMplsStatus": { "enum": ["Active", "Decommissioning", "Decommissioned"] }
      },
      "additionalProperties": false
    },
    "boundaries": {
      "type": "object",
      "properties": {
        "telemetryBoundary": { "enum": ["InternalOnly", "GCCAllowed", "FedRAMPModerate", "Restricted"] },
        "dataResidencyZone": { "type": "string" },
        "serviceAccessBoundary": { "enum": ["Full", "Limited", "BoundaryEnforced", "Isolated"] },
        "boundaryEnforcementLevel": { "enum": ["Strict", "Monitored", "Advisory"] },
        "telemetryClassification": { "type": "string" },
        "allowedTelemetryDestinations": { "type": "array", "items": { "type": "string" } }
      },
      "additionalProperties": false
    }
  },
  "additionalProperties": false
}
```

The identity-side assignment object (Primary LocPath reference + HR linkage + Dynamic Location Context) is specified with the adapter in the implementation phase; its dynamic-context shape must match the attribute table above.

## Worked example

A fictional agency headquarters (all values illustrative):

```yaml
locPath: /USA/MD/ANNAPOLIS-HQ/BLDG-3/FL-2/RM-210
level: Space
displayName: "Headquarters Building 3, Room 210"
status: Active
sourceSystem: facilities-real-property
e911:
  civicAddress: "100 Main Street, Annapolis, MD 21401"
  floor: "2"
  room: "RM-210"
  locationDescription: "Building 3, West Wing, 2nd Floor, Room 210"
```

Site-level classification for the same campus:

```yaml
locPath: /USA/MD/ANNAPOLIS-HQ
level: Site
displayName: "Headquarters Campus, Annapolis"
status: Active
network:
  diaApproved: true
  sdwanBreakoutType: Local
  ticCapabilityTier: Tier-1
  legacyMplsStatus: Decommissioning
boundaries:
  telemetryBoundary: GCCAllowed
  serviceAccessBoundary: Full
  boundaryEnforcementLevel: Monitored
```

An identity assignment reads: *Primary LocPath `/USA/MD/ANNAPOLIS-HQ/BLDG-3` (from HR duty station HQ-B3), OrgPath Department=Finance* — and both axes are now available to every rule, review, and drift check.

## Open questions (future ADRs)

1. Multi-source reconciliation when HR duty station and a badging/physical-access system disagree about a person's assigned place.
2. Representation of telework/alternative-worksite arrangements within Tier-1 scope (the governed record may be a Region-level LocPath plus an E911 registered address held by the UCaaS platform).
3. Whether device objects (not just identities) carry Primary LocPath, and how that interacts with Intune-first asset onboarding (ADR-071).
4. LocPath storage-on-target locators in ADR-098 binding profiles once a write-back use case exists.

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
