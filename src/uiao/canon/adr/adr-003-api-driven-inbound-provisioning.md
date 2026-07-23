---
adr_id: adr-003
title: "API-Driven Inbound Provisioning as HR-Agnostic Canonical Path"
status: ACCEPTED
decided: 2026-04-28
deciders: Michael Stratton
updated: 2026-07-23
next_review: 2026-11-30
review_trigger: Microsoft Ignite 2026 (native Oracle HCM connector watch); post-award PWS Appendix A changes; OPM HR-services consolidation memo; GCC provisioning-feature confirmation
impact: UIAO_136 Spec 2 (HR-Agnostic Provisioning Architecture)
supersedes: null
superseded_by: null
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-003-api-driven-inbound-provisioning.html
---

# ADR-003: API-Driven Inbound Provisioning as HR-Agnostic Canonical Path

## Status

**ACCEPTED** — April 28, 2026 · **Reaffirmed at scheduled review** — July 23, 2026

## Review 2026-07-23 — the review triggers fired; the decision is vindicated

Two of this ADR's review triggers fired, and both resolved in the direction that
strengthens the decision:

1. **OPM selected Oracle.** The Federal HRIT Modernization Core HCM contract
   (24322625C0006, ~$395.8M, 10-year) was awarded to **Oracle** and announced
   June 11, 2026; the platform is **Oracle Fusion Cloud HCM**. (The May 2025
   sole-source Workday award had been withdrawn and re-competed.) Because Entra ID
   still ships native HR connectors only for Workday and SAP SuccessFactors —
   **not Oracle HCM** — the API-driven path this ADR chose is no longer merely the
   vendor-agnostic hedge; it is **the only Microsoft-supported integration path**
   for the selected government-wide HCM. Rationale #3 resolved to its harder branch.

2. **The program acquired its governing directive.** The joint OMB/OPM memorandum
   *"Creating 'Federal HR 2.0' by Consolidating Core Human Capital Management
   Across the Federal Government"* (December 10, 2025 — Vought/Kupor) directs the
   consolidation this ADR anticipated: two transition waves (Wave 1 begins FY26;
   Wave 2 — **including SSA** — completes in FY 2027), government-wide adoption by
   FY 2028, agencies pausing their own Core HCM modernization, and the eventual
   decommissioning of eOPF and EHRI. The memo's sample onboarding timeline puts
   **interconnection go-live at roughly month 5 of an 8-month transition** — the
   slot a provisioning feed must be ready for.

Microsoft's own integration guidance for Oracle HCM (*Configure Oracle HCM for
automatic user provisioning*, updated June 2026) implements exactly this ADR's
pattern: HCM Extracts / ATOM feeds → middleware transform → SCIM `bulkUpload` →
Entra ID (cloud-only) or on-prem AD via the provisioning agent (hybrid), with
Lifecycle Workflows keyed on `employeeHireDate` / `employeeLeaveDateTime`.

**Decision unchanged.** The middleware obligations (schema normalization, OrgPath
calculation, provenance logging) stand. Execution against the now-known program is
specified in *OrgComp — HRIT to HR-Driven IAM Execution Plan* (orgcomp-series),
which concretizes UIAO_136 Spec 2.

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
| OMB/OPM memo — *Creating "Federal HR 2.0" by Consolidating Core HCM Across the Federal Government* (Dec 10, 2025; waves, FY 2028 goal, eOPF/EHRI decommissioning) | https://content.govdelivery.com/attachments/USOPM/2025/12/10/file_attachments/3489280/HR%202.0%20memo%2012-10-2025.pdf | 2026-07-23 |
| OPM news release — Core HCM contract award to Oracle (Oracle Fusion Cloud HCM; contract 24322625C0006) | https://www.opm.gov/news/news-releases/opm-awards-contract-for-first-ever-governmentwide-hr-platform/ | 2026-07-23 |
| Microsoft Learn — Configure Oracle HCM for automatic user provisioning (ATOM feeds → SCIM → bulkUpload; Entra + on-prem AD targets) | https://learn.microsoft.com/en-us/entra/identity/saas-apps/oracle-hcm-provisioning-tutorial | 2026-07-23 |
| OPM Federal HRIT Modernization — Solicitation 24322626R0007 (Amendments 2, 3, 4); Appendix A Requirements Checklist Req #5 (SCIM 2.0 near-real-time provisioning) | sam.gov solicitation 24322626R0007 | 2026-04-30 |
| Microsoft Learn — API-driven inbound provisioning concepts | https://learn.microsoft.com/en-us/entra/identity/app-provisioning/inbound-provisioning-api-concepts | 2026-04-28 |
| GitHub — AzureAD/entra-id-inbound-provisioning samples | https://github.com/AzureAD/entra-id-inbound-provisioning | 2026-04-28 |
| Step-by-step guide — API-driven provisioning to on-prem AD | https://thetechtrails.com (Sreejith R. Pillai, Aug 2025) | 2026-04-28 |

## Review Triggers

This ADR must be re-evaluated when any of the following occur:

- [x] OPM announces HR vendor selection (Workday or Oracle) — **fired: Oracle, June 11, 2026; reviewed 2026-07-23, decision reaffirmed**
- [x] GAO protest decisions issued (expected June 2026) — **fired: award announced June 11, 2026; reviewed 2026-07-23**
- [x] July 2026 — scheduled review (post-GAO decision window) — **completed 2026-07-23**
- [ ] Microsoft builds a native Oracle HCM provisioning connector (would make middleware optional; architecture unchanged)
- [ ] Microsoft announces changes to the bulkUpload API or SCIM provisioning endpoints
- [ ] Entra ID Lifecycle Workflows adds new JML automation capabilities
- [ ] Post-award PWS Appendix A interface changes surface (agency-visible requirements)
- [ ] OPM issues the promised HR-services consolidation memorandum (Federal HR 2.0 memo, footnote 4)
- [ ] GCC (Moderate) availability of API-driven inbound provisioning + Lifecycle Workflows confirmed for the target tenant
- [ ] Microsoft Ignite 2026 (November) — scheduled review

## Related Documents

- UIAO_135 — Identity & Directory Transformation Inventory (Transformation #10: HR-Driven Provisioning)
- UIAO_136 — Spec 2: HR-Agnostic Provisioning Architecture (all phases)
- OrgComp — HRIT to HR-Driven IAM Execution Plan (orgcomp-series) — the execution of this decision against the awarded program (Federal HR 2.0 / Oracle Core HCM)
- Vol I Book 04 — OPM HRIT and the Identity & Organizational SSOT (orgcomp-series)
- ADR-003 supplements the HR system discussion in UIAO_135 Section 2
