---
adr_id: adr-003
title: "API-Driven Inbound Provisioning as HR-Agnostic Canonical Path"
status: ACCEPTED
decided: 2026-04-28
deciders: Michael Stratton
updated: 2026-04-28
next_review: 2026-07-01
review_trigger: OPM GAO protest decisions (expected June 2026); any Entra ID provisioning announcement
impact: UIAO_IDT_002 Spec 2 (HR-Agnostic Provisioning Architecture)
supersedes: null
superseded_by: null
classification: Controlled
boundary: GCC-Moderate
---

# ADR-003: API-Driven Inbound Provisioning as HR-Agnostic Canonical Path

## Status

**ACCEPTED** — April 28, 2026

## Context

The federal government is consolidating to a single governmentwide HCM system under OPM's HR IT modernization procurement. As of April 2026, two finalists remain — **Workday** (with Accenture) and **Oracle** (with Deloitte) — with GAO protest decisions expected by early June 2026. IBM and SAP have been eliminated.

UIAO must define the canonical HR-driven identity provisioning architecture for the Joiner-Mover-Leaver (JML) lifecycle. This architecture must:

- Populate OrgPath from HR organizational hierarchy data
- Support both Entra ID (cloud-only) and on-prem AD (coexistence) targets
- Not create a dependency on a specific HR vendor that may or may not be selected
- Produce auditable provenance records for UIAO Governance OS

Microsoft Entra ID supports three distinct inbound provisioning paths:

1. **Native HR connectors** — Purpose-built connectors for Workday and SAP SuccessFactors (not Oracle HCM)
2. **API-driven inbound provisioning** — Microsoft Graph bulkUpload API accepting SCIM-formatted payloads from any source
3. **Legacy bridge** — On-prem HR → MIM/FIM → AD → Entra Connect Sync

## Decision

**API-driven inbound provisioning via Microsoft Graph is the UIAO canonical path for HR-to-identity provisioning. Native HR connectors are permitted as accelerators when available but must not be architecturally required. The provisioning architecture must function with only the Graph API as the integration interface.**

## Rationale

1. **HR-system-agnostic by design.** The API-driven approach accepts SCIM-formatted bulk payloads from any source. From Microsoft Learn: *"With API-driven inbound provisioning, the Microsoft Entra provisioning service now supports integration with any system of record. Customers and partners can use any automation tool of their choice to retrieve workforce data from the system of record and ingest it into Microsoft Entra ID."*

2. **OPM vendor selection is unresolved.** With GAO protests pending and the award delayed from January 2026, the UIAO architecture cannot depend on knowing which HR system will be selected. API-driven provisioning works identically regardless of whether the source is Workday, Oracle, SAP, a custom system, or a CSV export.

3. **Native Workday connector exists; native Oracle HCM connector does not.** If OPM selects Workday, a Microsoft-built native connector is available as an optimization. If OPM selects Oracle, the API-driven path is the only Microsoft-supported option. Architecting for the API-driven path ensures UIAO works in both scenarios.

4. **Middleware normalization layer is required regardless.** Even with native connectors, UIAO's OrgPath calculation and governance provenance requirements demand a middleware layer that transforms HR data before it reaches Entra ID. This middleware naturally maps to the API-driven architecture.

5. **Future-proof against HR system changes.** Federal HR consolidation has a long history of false starts. If the selected vendor changes or agencies adopt different systems, the API-driven architecture requires only a new middleware adapter — not an architectural redesign.

## Architecture Pattern

```
┌─────────────────┐     ┌──────────────────────┐     ┌─────────────────────┐
│   HR System      │     │  Middleware Layer      │     │  Entra ID            │
│  (Workday OR     │────▶│  (Azure Functions /    │────▶│  Provisioning        │
│   Oracle OR      │     │   Logic Apps)          │     │  Service             │
│   any source)    │     │                        │     │                      │
│                  │     │  • Schema normalization │     │  • Attribute mapping │
│                  │     │  • OrgPath calculation  │     │  • JML workflows     │
│                  │     │  • Validation           │     │  • Group assignment  │
│                  │     │  • Provenance logging   │     │  • License assignment│
└─────────────────┘     └──────────────────────┘     └────────┬────────────┘
                                                              │
                                                    ┌────────▼────────────┐
                                                    │  Provisioning Agent  │
                                                    │  (On-prem, HA)      │
                                                    │  • AD writeback      │
                                                    │  (coexistence only)  │
                                                    └─────────────────────┘
```

## Consequences

### Positive
- Architecture works regardless of OPM HR vendor selection
- Single canonical pattern for all agencies, regardless of their current HR system
- OrgPath calculation happens in middleware, ensuring every identity gets OrgPath before reaching Entra ID
- Governance provenance records generated at middleware layer, independent of Entra ID audit logs
- Native connectors can be layered on as accelerators without architectural change
- Supports hybrid provisioning (Entra ID + on-prem AD via provisioning agent) during coexistence

### Negative
- **Requires building a middleware layer** — native connectors handle the integration automatically; API-driven requires custom middleware (Azure Functions or Logic Apps)
- **Additional infrastructure to maintain** — middleware layer adds operational surface area (monitoring, patching, scaling)
- **Slightly higher latency than native connectors** — native connectors process changes in near-real-time; API-driven depends on middleware polling/push frequency
- **Microsoft Graph API rate limits apply** — bulk provisioning of large workforces must respect Graph API throttling (currently ~40 requests/second for provisioning endpoints)

### Risks
- If Microsoft builds a native Oracle HCM connector (moderate probability), the middleware layer for Oracle becomes optional but the architecture remains valid
- If OPM procurement collapses entirely and agencies retain individual HR systems, the API-driven pattern is even more valuable (works with any source)
- If Microsoft deprecates the bulkUpload API (very low probability — GA and actively invested), alternative Graph provisioning endpoints exist

## Verification Sources

| Source | URL | Last Verified |
|---|---|---|
| Microsoft Learn — API-driven inbound provisioning concepts | https://learn.microsoft.com/en-us/entra/identity/app-provisioning/inbound-provisioning-api-concepts | 2026-04-28 |
| GitHub — AzureAD/entra-id-inbound-provisioning samples | https://github.com/AzureAD/entra-id-inbound-provisioning | 2026-04-28 |
| Step-by-step guide — API-driven provisioning to on-prem AD | https://thetechtrails.com (Sreejith R. Pillai, Aug 2025) | 2026-04-28 |

## Review Triggers

This ADR must be re-evaluated when any of the following occur:

- [ ] OPM announces HR vendor selection (Workday or Oracle)
- [ ] GAO protest decisions issued (expected June 2026)
- [ ] Microsoft builds a native Oracle HCM provisioning connector
- [ ] Microsoft announces changes to the bulkUpload API or SCIM provisioning endpoints
- [ ] Entra ID Lifecycle Workflows adds new JML automation capabilities
- [ ] July 2026 — scheduled review (post-GAO decision window)
- [ ] Microsoft Ignite 2026 (November) — scheduled review

## Related Documents

- UIAO_IDT_001 — Identity & Directory Transformation Inventory (Transformation #10: HR-Driven Provisioning)
- UIAO_IDT_002 — Spec 2: HR-Agnostic Provisioning Architecture (all phases)
- ADR-003 supplements the HR system discussion in UIAO_IDT_001 Section 2
