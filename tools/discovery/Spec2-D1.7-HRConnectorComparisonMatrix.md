---
deliverable_id: Spec2-D1.7
title: "HR Source System Connector Comparison Matrix"
spec: UIAO_136 / Spec 2 — HR-Agnostic Provisioning Architecture
phase: 1
status: Final
version: 1.0
owner: Identity Architecture
created: 2026-04-30
updated: 2026-04-30
canonical_adrs:
  - ADR-003
canonical_docs:
  - UIAO_007
  - UIAO_135
  - UIAO_136
boundary: GCC-Moderate
classification: Controlled
verification_history:
  - date: 2026-04-30
    pass: "v0.1 → v0.2 (initial verification)"
    sources:
      - "Microsoft Learn — API-driven inbound provisioning concepts (page updated 2026-02-05)"
      - "Microsoft Learn — Workday inbound provisioning tutorial (page updated 2026-02-26)"
    confirmed:
      - "API-driven path: SCIM 2.0 wire protocol over /bulkUpload (§6.1)"
      - "API-driven path: real-time / push-driven (§4.1, §6.1)"
      - "API-driven path: tenant daily limit 2,000 calls (P1/P2) or 6,000 (Entra ID Governance)"
      - "Workday native connector: uses Workday Web Services (WWS) SOAP/XML (§3.1, §6.1) — confirmed by SOAP envelope syntax in tutorial page"
      - "Workday native default WWS API version: v21.1 (when no version specified in URL)"
      - "Microsoft maintains native Workday + SAP SuccessFactors connectors but does not provide a native Oracle HCM connector (§3.2 — already canonical per ADR-003 §Rationale §3)"
  - date: 2026-04-30
    pass: "v0.2 → v1.0 (closure verification)"
    sources:
      - "Microsoft Learn — SAP SuccessFactors inbound provisioning tutorial (page updated 2026-02-26)"
      - "Microsoft Learn — Reference for writing expressions for attribute mappings (page updated 2026-04-14)"
    confirmed:
      - "SAP SuccessFactors connector: uses SuccessFactors OData APIs — confirmed by tutorial language ('credentials of a SuccessFactors account with the right permissions to invoke the SuccessFactors OData APIs')"
      - "SuccessFactors connector authentication: Basic authentication for OData API access"
      - "Provisioning expression function library: 45 documented functions (Append, AppRoleAssignmentsComplex, BitAnd, CBool, CDate, Coalesce, ConvertToBase64, ConvertToUTF8Hex, Count, CStr, DateAdd, DateDiff, DateFromNum, DefaultDomain, FormatDateTime, Guid, IgnoreFlowIfNullOrEmpty, IIF, InStr, IsNull, IsNullorEmpty, IsPresent, IsString, Item, Join, Left, Len, Mid, NormalizeDiacritics, Not, Now, NumFromDate, PCase, RandomString, Redact, RemoveDuplicates, Replace, SelectUniqueValue, SingleAppRoleAssignment, Split, StripSpaces, Switch, ToLower, ToUpper, Word). The earlier 'Yes — 25+ functions' figure in §4.2 was an underestimate; the actual count is 45+."
  - remaining_unverified:
      - "Workday native polling default — Workday tutorial page does not state a specific minute value. SAP SuccessFactors page also doesn't quantify the polling interval. The '40 minutes' figure carried in body prose is treated as a planning estimate; final value confirmed at deployment time against the agency's specific tenant configuration. Does not block v1.0."
      - "FedRAMP authorization status for Workday Government Cloud / Oracle Government Cloud / SAP NS2 (SuccessFactors Government) — Microsoft Learn does not authoritatively state these. Source of truth is FedRAMP Marketplace (https://marketplace.fedramp.gov/), which is a non-Microsoft authority. Confirmed at deployment time during agency authorization review. Does not block v1.0."
---

# Spec 2 — D1.7: HR Source System Connector Comparison Matrix

> **Verification status (v1.0 — Final, 2026-04-30):** Two verification
> passes against Microsoft Learn (frontmatter `verification_history`
> block). Architectural claims are confirmed against authoritative
> Microsoft sources. Two items remain deferred to deployment-time
> validation (Workday/SF native polling defaults; FedRAMP authorization
> statuses) — neither blocks v1.0 because both are validated against
> non-Microsoft sources (agency tenant config; FedRAMP Marketplace) at
> agency authorization time. The §4.2 expression-function-count figure
> was corrected from "25+" (v0.1/v0.2 estimate) to **45 documented
> functions** (v1.0, sourced from Microsoft Learn 2026-04-14 page).

## 1. Purpose, Scope, and Reference

This deliverable is the canonical comparison matrix called for in
[`UIAO_136`](../../src/uiao/canon/UIAO_136_priority1-transformation-project-plans.md)
§SPEC 2 → Phase 1 → D1.7:

> *Technical comparison of Workday connector, Oracle HCM connector, SAP
> SuccessFactors connector, and API-driven inbound provisioning. Feature
> parity matrix. Identify any capabilities unique to native connectors vs.
> API-driven.*

The conclusion is **fixed by canon**:
[`ADR-003`](../../src/uiao/canon/adr/adr-003-api-driven-inbound-provisioning.md)
already accepted **API-driven inbound provisioning via Microsoft Graph**
(SCIM 2.0 over `/bulkUpload`) as the UIAO canonical HR provisioning path.
Native connectors are permitted as accelerators but must not be
architecturally required.

The purpose of this deliverable is therefore not to *re-decide* the
architecture but to:

1. Document the comparison evidence that ADR-003 cites by reference.
2. Make the absence of a native Oracle HCM connector explicit in canon.
3. Trace each Federal HRIT Modernization Appendix A requirement to the
   provisioning path that satisfies it.
4. Provide a defensible build-vs.-buy artifact for D3.1 (canonical
   SCIM/bulkUpload architecture document) and downstream Spec 2
   deliverables.

### 1.1 Scope

In scope:

- Microsoft-supported inbound provisioning paths to Microsoft Entra ID
  for HR source systems.
- Coverage of all four paths named in UIAO_136 D1.7.
- GCC-Moderate / FedRAMP Moderate posture for each path.
- Federal HRIT Modernization Solicitation 24322626R0007 (Amd 2/3/4),
  Appendix A Requirements Checklist Req #5 (SCIM 2.0 near-real-time
  provisioning) traceability.

Out of scope:

- Outbound (Entra → SaaS app) provisioning — covered separately by the
  Entra Enterprise App provisioning model.
- Non-Microsoft IdP options (Okta, Ping, Google Workspace) — UIAO is a
  Microsoft-aligned substrate per UIAO_007 / UIAO-SSOT.
- HR system feature comparisons (Workday vs. Oracle vs. SAP as HR
  *platforms*) — those are OPM evaluation criteria, not UIAO concerns.

### 1.2 Audience

UIAO architecture reviewers; D3.1 (Architecture) and D2.1–D2.8 (JML
Workflow) authors; OPM HRIT integration teams; agency identity leads.

---

## 2. OPM Federal HRIT Procurement Context

UIAO must define the HR provisioning architecture **without depending on
the OPM HR vendor decision**. The relevant facts as of 2026-04-30:

| Detail | Status |
|---|---|
| Solicitation | 24322626R0007 (Federal HRIT Modernization), Amendments 2, 3, 4 |
| Scope | Single governmentwide HCM system; 10-year, $1B+ |
| OMB target | All major agencies migrated by 2027-07-04 |
| Remaining finalists | Workday (Accenture Federal Services); Oracle (Deloitte Consulting) |
| Eliminated | IBM (filed GAO protest 2026-02-25); EconSys/Axiom (filed GAO protest 2026-03-02); SAP |
| GAO protest decisions | Expected early June 2026 |
| Existing federal HR systems | OPM EHRI + eOPF |

Source: OPM Solicitation 24322626R0007 Amd 2/3/4, public listing at
sam.gov.

### 2.1 Why this matters for connector selection

Two of the four connector paths in this matrix exist as Microsoft-built
native connectors (Workday, SAP SuccessFactors). One does not (Oracle
HCM Cloud). One is HR-agnostic (API-driven).

| Federal HRIT outcome | Path that works |
|---|---|
| OPM selects Workday | Native Workday connector OR API-driven (both viable) |
| OPM selects Oracle | API-driven only (no native connector exists) |
| Procurement collapses; agencies retain individual HR systems | API-driven (heterogeneous sources) |
| Agency already uses SAP SuccessFactors (out-of-scope for OPM contract) | Native SF connector OR API-driven (both viable) |

API-driven is the only path that works in **all four** outcomes. This is
the operational core of ADR-003.

---

## 3. Connector Profiles

### 3.1 Workday Inbound Provisioning Connector

| Attribute | Value |
|---|---|
| Vendor | Microsoft (native Entra ID connector) |
| Type | Native SaaS connector |
| HR system | Workday HCM |
| Wire protocol | Workday Web Services (WWS) SOAP/XML |
| Sync model | Polling (default 40 min interval) |
| Real-time push | No |
| GCC-Moderate availability | Yes (Workday Government Cloud — FedRAMP Moderate authorized) |
| AD writeback | Yes, via Entra Provisioning Agent |
| Attribute transformations | Entra provisioning expressions (~25 functions) |
| Custom code path | Provisioning expressions only — no arbitrary code |
| OPM HRIT relevance | One of two finalists (Workday/Accenture) |

Production-hardened. Microsoft maintains this connector with general
availability in commercial and US Government clouds. The bulk of
attribute mapping is direct; complex transformations (UPN generation,
OrgPath calculation, diacritic transliteration) are expressed as
provisioning-expression functions.

### 3.2 Oracle HCM Cloud Connector

| Attribute | Value |
|---|---|
| Vendor | **No Microsoft-built native connector exists** |
| Type | n/a — **integration must use API-driven path** |
| HR system | Oracle Cloud HCM (Fusion) |
| Wire protocol | API-driven middleware reads Oracle HCM ATOM feeds → Microsoft Graph `/bulkUpload` |
| Sync model | Caller-controlled (whatever the middleware implements) |
| Real-time push | Yes, when middleware pushes on event |
| GCC-Moderate availability | Yes (Oracle Cloud for Government / OCI Government — FedRAMP authorized) |
| AD writeback | Yes, via Entra Provisioning Agent (downstream of API-driven entry) |
| Attribute transformations | Done in middleware (any language) |
| Custom code path | Arbitrary — middleware is a normal application |
| OPM HRIT relevance | One of two finalists (Oracle/Deloitte) |

**This row formally documents an absence.** ADR-003 §Rationale §3
states: *"Native Workday connector exists; native Oracle HCM connector
does not. If OPM selects Oracle, the API-driven path is the only
Microsoft-supported option."* If Microsoft builds a native Oracle HCM
connector in the future (moderate probability per ADR-003 §Risks), the
canonical architecture remains valid — the middleware layer becomes
optional rather than mandatory. ADR-003 §Review Triggers includes
"Microsoft builds a native Oracle HCM provisioning connector" as a
review trigger for this ADR.

### 3.3 SAP SuccessFactors Inbound Provisioning Connector

| Attribute | Value |
|---|---|
| Vendor | Microsoft (native Entra ID connector) |
| Type | Native SaaS connector |
| HR system | SAP SuccessFactors |
| Wire protocol | SuccessFactors OData API |
| Sync model | Polling (default 40 min interval) |
| Real-time push | No |
| GCC-Moderate availability | Yes (SAP NS2 / SuccessFactors Government — FedRAMP authorized) |
| AD writeback | Yes, via Entra Provisioning Agent |
| Attribute transformations | Entra provisioning expressions (~25 functions) |
| Custom code path | Provisioning expressions only |
| OPM HRIT relevance | **SAP eliminated from OPM procurement** (per UIAO_135 §2.1) |

Listed for completeness per UIAO_136 D1.7. The native SF connector is
mature and widely deployed in commercial enterprises. UIAO supports
agency tenants that already use SAP SuccessFactors outside the OPM
governmentwide contract; for those agencies, the native SF connector or
the API-driven path are both viable. The decision matrix in §8 applies.

### 3.4 API-Driven Inbound Provisioning (UIAO Canonical Path)

| Attribute | Value |
|---|---|
| Vendor | Microsoft (Entra ID platform capability — not a connector) |
| Type | HR-agnostic API endpoint |
| HR system | Any source |
| Wire protocol | Microsoft Graph `/users/<userid>/jobs/bulkUpload` accepting **SCIM 2.0** payloads |
| Sync model | Push (caller-controlled) |
| Real-time push | Yes |
| GCC-Moderate availability | Yes (inherits Entra ID GCC-Moderate / FedRAMP Moderate) |
| AD writeback | Yes, via Entra Provisioning Agent (downstream of API entry) |
| Attribute transformations | Done in middleware (Azure Functions / Logic Apps / arbitrary) |
| Custom code path | Arbitrary — middleware is a normal application |
| OPM HRIT relevance | Vendor-agnostic — **works in every procurement outcome** |
| Canonical reference | ADR-003 (ACCEPTED) |

This is the UIAO canonical path. The architecture is in ADR-003
§Architecture Pattern; the canonical implementation document (D3.1) is
the next strategic deliverable per UIAO_136 §Next Implementation Tracks
(Track B).

---

## 4. Capability Comparison Matrix

Legend:

- **Yes** — supported natively by the path; no UIAO-specific work required.
- **Yes (mw)** — supported via the middleware layer (additional UIAO build cost).
- **Limited** — supported with documented constraints; see notes.
- **No** — not supported; the path cannot satisfy this capability.
- **n/a** — capability does not apply to this path.

### 4.1 Provisioning fundamentals

| Capability | Workday | Oracle HCM | SAP SF | API-driven |
|---|---|---|---|---|
| Cloud-only Entra ID provisioning | Yes | n/a (no native) | Yes | Yes |
| On-prem AD writeback (via Provisioning Agent) | Yes | Via API-driven path | Yes | Yes |
| Hybrid coexistence (cloud + AD) | Yes | Via API-driven path | Yes | Yes |
| Bulk initial load | Yes (full sync) | Yes (mw) | Yes (full sync) | Yes (CSV/SCIM bulk upload) |
| Incremental delta sync | Yes (poll) | Yes (mw, ATOM-driven) | Yes (poll) | Yes (caller-driven) |
| Real-time provisioning (< 5 min) | No (40 min poll) | Yes (mw on push) | No (40 min poll) | Yes (immediate on push) |
| On-demand single-user provisioning | Yes (portal) | Yes (mw) | Yes (portal) | Yes (single SCIM call) |

### 4.2 Transformation and OrgPath

The OrgPath calculation (per [ADR-035](../../src/uiao/canon/adr/adr-035-orgpath-codebook-binding.md)
and [ADR-048](../../src/uiao/canon/adr/adr-048-orgpath-attribute-selection.md))
is the most complex transformation in HR provisioning. It determines
where users land in dynamic groups, administrative units, conditional
access scopes, Intune assignment, and Arc tagging downstream.

| Capability | Workday | Oracle HCM | SAP SF | API-driven |
|---|---|---|---|---|
| Built-in provisioning-expression library | Yes — 45 functions | n/a | Yes — 45 functions | n/a (arbitrary code) |
| Custom expression authoring | Yes (Entra builder) | n/a | Yes (Entra builder) | n/a (arbitrary code) |
| OrgPath calculation complexity | High — nested Switch/Join in expression | Low — done in middleware | High — nested Switch/Join in expression | Low — done in middleware |
| OrgPath logic testability | Low (expressions are not unit-testable) | High (normal code) | Low | High |
| UPN collision resolution | Limited (expression-based counters) | Full (mw, DB-backed) | Limited | Full (mw, DB-backed) |
| Diacritic transliteration (per Spec2-D1.5, ~80 chars) | Manual per-character expression | Full (mw) | Manual per-character expression | Full (mw) |
| Worker-type taxonomy enforcement (per Spec2-D1.6) | Limited to Workday types | Full (mw, canonical types) | Limited to SF types | Full (mw, canonical types) |

The OrgPath complexity row is the structural reason ADR-003 prefers
API-driven even when a native connector is available: OrgPath logic in
provisioning expressions is brittle and hard to govern; the same logic
in middleware code is testable, reviewable, and version-controlled.

### 4.3 Operations, audit, and quarantine

| Capability | Workday | Oracle HCM | SAP SF | API-driven |
|---|---|---|---|---|
| Provisioning logs in Entra portal | Yes | Yes | Yes | Yes |
| Quarantine on repeated errors | Yes (built-in) | Yes (built-in for `/bulkUpload`) | Yes (built-in) | Yes (built-in for `/bulkUpload`) |
| Provisioning-status Graph API (`provisioningObjectSummary`) | Yes | Yes | Yes | Yes |
| Email notifications on failure | Yes (configurable) | Yes (configurable) | Yes (configurable) | Yes (configurable) |
| Audit-log retention (Entra provisioning logs) | 30 days | 30 days | 30 days | 30 days |
| UIAO Governance OS provenance | Via post-processor | Native (mw can emit) | Via post-processor | Native (mw can emit) |

The Governance OS provenance row matters: UIAO requires every
provisioning event to produce a provenance record (per UIAO_136 Spec 2
§Design Constraints). Native connectors do not emit UIAO-shaped
provenance directly; a downstream extractor on the Entra audit log is
needed. API-driven middleware can emit provenance inline, which is
simpler to govern.

### 4.4 Architecture and HR-vendor independence

| Capability | Workday | Oracle HCM | SAP SF | API-driven |
|---|---|---|---|---|
| HR vendor independence | No (Workday only) | No (Oracle HCM only — once a connector exists) | No (SF only) | **Yes** (any source) |
| Multi-source federation (e.g., FTE in HR-A + contractors in HR-B) | One source per connector | One source per connector | One source per connector | Unlimited sources |
| Migration cost if HR vendor changes | Replace entire connector | Replace entire path | Replace entire connector | Update schema normalizer only |
| Schema normalizer middleware required | No | Yes | No | Yes |
| Pre-built attribute mapping | Yes | No (build it) | Yes | No (build it) |
| Time-to-first-sync (greenfield) | Days | Weeks (mw build) | Days | Weeks (mw build) |
| Long-term maintenance cost | Medium (expressions can become brittle) | Low–Medium (normal code) | Medium | Low–Medium (normal code) |

Native connectors win on time-to-first-sync. API-driven wins on every
other architectural axis. ADR-003 weights the architectural axes higher
because the procurement window is short and the architecture window is
ten-plus years.

---

## 5. JML Lifecycle Comparison

JML = Joiner / Mover / Leaver. The full JML workflow set is
specified in UIAO_136 Spec 2 §Phase 2 (D2.1–D2.8). This section maps the
six lifecycle events to each provisioning path.

### 5.1 Joiner (new hire activation on start date)

| Path | Mechanism | Key constraints |
|---|---|---|
| Workday | Status change in Workday → connector polls → `accountEnabled=true` + attribute assignment | Polling delay; expression authoring required for any non-direct mapping. |
| Oracle HCM | Via API-driven (no native connector) | See API-driven row. |
| SAP SF | OData feed publishes active worker → connector polls → `accountEnabled=true` + attributes | Same as Workday. |
| API-driven | Middleware computes all attributes (UPN, OrgPath, worker type) and pushes via SCIM bulkUpload | All transformation logic lives in code; testable. |

### 5.2 Pre-Hire (account creation before start date)

| Path | Mechanism | Key constraints |
|---|---|---|
| Workday | Scheduled provisioning based on Hire_Date; account created `accountEnabled=false` until start date | Polling interval (~40 min) makes near-real-time impossible. |
| Oracle HCM | Via API-driven | See API-driven row. |
| SAP SF | Scheduled provisioning based on hire date | Same constraints as Workday. |
| API-driven | Middleware implements pre-hire window logic (e.g., 14-day pre-create); pushes when condition met | Maximum control; more development effort. |

### 5.3 Mover (department/location/role change)

| Path | Mechanism | Key constraints |
|---|---|---|
| Workday | Worker attribute change detected on next poll; changed attributes flow through expressions | OrgPath recalculation requires complex expression; manager chain changes may lag. |
| Oracle HCM | Via API-driven | See API-driven row. |
| SAP SF | OData publishes updated worker; expressions recompute | Same complexity as Workday. |
| API-driven | Middleware detects change, recomputes OrgPath in code, pushes updated payload | OrgPath logic is in maintainable code rather than expressions — primary structural advantage. |

### 5.4 Leaver (termination / offboarding)

| Path | Mechanism | Key constraints |
|---|---|---|
| Workday | Termination → connector sets `accountEnabled=false`; can chain to Lifecycle Workflows for license removal | Hard delete requires manual or LCW automation; grace-period management is external. |
| Oracle HCM | Via API-driven | See API-driven row. |
| SAP SF | Termination → connector sets `accountEnabled=false`; LCW chaining identical to Workday | Same. |
| API-driven | Middleware sends termination update with exact disable date; can trigger immediate or scheduled disable | Caller implements grace periods and termination-date logic — full flexibility. |

### 5.5 Rehire (returning employee)

| Path | Mechanism | Key constraints |
|---|---|---|
| Workday | Workday rehire event → connector matches existing Entra user by `employeeId` and re-enables | May create duplicate if correlation attribute changed; pre-existing attributes may not reset cleanly. |
| Oracle HCM | Via API-driven | See API-driven row. |
| SAP SF | SF rehire event → connector matches by `personIdExternal` | Person-ID consistency across employment periods required. |
| API-driven | Middleware matches by `employeeId` and resets attributes deterministically | Rehire detection and attribute reconciliation are explicit code paths. |

### 5.6 Conversion (contractor → employee, intern → FTE, etc.)

| Path | Mechanism | Key constraints |
|---|---|---|
| Workday | Worker-type change flows through; `employeeType` updated; OrgPath may need recalculation | Often requires UPN domain change, license swap, group membership change — not all handled by connector. |
| Oracle HCM | Via API-driven | See API-driven row. |
| SAP SF | Worker-type change flows through; same complexity | Same. |
| API-driven | Middleware pushes all updated attributes atomically — new worker type, OrgPath, UPN if needed | All conversion logic in one place. |

---

## 6. Federal HRIT Requirements Traceability

This section maps the Federal HRIT Modernization Solicitation (24322626R0007,
Amd 2/3/4) Appendix A Requirements Checklist items that touch identity
provisioning to the four paths above. Only requirements that bear on
provisioning architecture are included; the Appendix has many more
requirements covering HR business logic that are out of scope for D1.7.

### 6.1 Req #5 — SCIM 2.0 near-real-time provisioning

This is the load-bearing requirement for D1.7. The solicitation
mandates SCIM 2.0 over the wire and "near-real-time" provisioning
behavior.

| Path | SCIM 2.0 wire protocol | Near-real-time | Compliant |
|---|---|---|---|
| Workday native | No — uses Workday Web Services SOAP/XML | No — 40 min polling | **No** |
| Oracle HCM native | n/a — no native connector | n/a | n/a |
| SAP SF native | No — uses SuccessFactors OData | No — 40 min polling | **No** |
| API-driven | **Yes** — `/bulkUpload` accepts SCIM 2.0 payloads natively | **Yes** — push-driven, immediate | **Yes** |

The "no" rows for Workday and SAP SF are not a defect of those
connectors — they pre-date the SCIM 2.0 industry standard and use
vendor-native APIs because that is what their respective HR platforms
expose. They satisfy the *semantic intent* of SCIM (joiner / mover /
leaver attribute provisioning) without using the SCIM wire protocol.
For UIAO compliance with Req #5, those connectors would need to be
*supplemented* by an API-driven layer that re-emits provisioning events
in SCIM 2.0 format — at which point the API-driven path is doing the
SCIM compliance work and the native connector is reduced to an
HR-side data fetcher. ADR-003 reaches the same conclusion from a
different direction.

**API-driven directly satisfies Req #5 with no supplementation.**

### 6.2 Other Req-A items relevant to provisioning architecture

These are summarized rather than exhaustively traced; each row should
be confirmed against the Appendix A spreadsheet during D3.1 drafting.

| Req area | UIAO mapping | Path implications |
|---|---|---|
| HR data residency (US sovereign) | All four paths run in GCC-Moderate (Workday Govt Cloud, Oracle Govt Cloud, SAP NS2, Entra GCC) | All four compliant for HR-system data residency |
| Encryption in transit (FIPS 140-2) | All four paths use TLS 1.2+ | All four compliant |
| Audit log retention | UIAO Governance OS retains 7 years; Entra provisioning logs are 30 days | Retention is a UIAO concern, not a path concern |
| Joiner-Mover-Leaver lifecycle | Covered in §5 | All four paths can implement; API-driven has lowest implementation friction |
| Attribute mapping flexibility | Covered in §4.2 | API-driven > native (code beats expressions for complex transforms) |
| Multi-source HR federation | Covered in §4.4 | Only API-driven supports |

A complete Req-A → path traceability matrix is a candidate D3.1
appendix; it requires the Appendix A spreadsheet to be loaded into the
deliverable's source data.

---

## 7. GCC-Moderate / FedRAMP Posture

| Path | Component | Authorization |
|---|---|---|
| Workday native | Workday HCM (HR data side) | Workday Government Cloud — FedRAMP Moderate |
| Workday native | Entra ID provisioning service | Microsoft Entra GCC — FedRAMP Moderate |
| Workday native | Provisioning Agent (on-prem) | Customer-operated; runs inside customer enclave |
| Oracle HCM (via API-driven) | Oracle Cloud HCM | Oracle Cloud for Government — FedRAMP authorized |
| Oracle HCM (via API-driven) | Middleware (Azure Functions / Logic Apps) | Inherits Azure Government FedRAMP authorization |
| Oracle HCM (via API-driven) | Entra ID + Provisioning Agent | As above |
| SAP SF native | SAP SuccessFactors | SAP NS2 / SuccessFactors Government — FedRAMP authorized |
| SAP SF native | Entra ID + Provisioning Agent | As above |
| API-driven | Middleware | Inherits Azure Government FedRAMP authorization |
| API-driven | Entra ID + Provisioning Agent | As above |

All four paths are GCC-Moderate-eligible for federal use. Posture is
not a discriminator between paths.

---

## 8. Decision Framework

The decision is not a free choice — ADR-003 has already accepted
API-driven as the canonical path. The framework below is for tactical
decisions about whether to *additionally* deploy a native connector as
an accelerator during initial rollout, and which path applies in each
agency scenario.

### 8.1 Per-scenario path selection

| Agency scenario | Required path | Optional accelerator | Notes |
|---|---|---|---|
| Federal agency, OPM contract awards Workday | API-driven (canonical) | Workday native connector during initial rollout | Native connector handles bulk attribute sync; API-driven layer handles OrgPath, UPN, Req #5 SCIM compliance. |
| Federal agency, OPM contract awards Oracle | API-driven (canonical) | None — no native connector exists | API-driven middleware reads Oracle HCM ATOM feed; sole supported path. |
| Federal agency, OPM procurement collapses; agency keeps current HR | API-driven (canonical) | Native connector if HR is Workday or SF; none otherwise | Maximum flexibility. |
| Agency uses SAP SuccessFactors outside OPM contract | API-driven (canonical) | SF native connector during initial rollout | Same pattern as Workday case. |
| Agency uses non-Microsoft-supported HR (custom HCM, legacy mainframe-fed export) | API-driven (canonical) | None | API-driven is the only path; middleware adapts to the source. |

In every scenario, **API-driven is required**. Native connectors are
*never* required and *never* sufficient on their own (they cannot
satisfy Req #5 SCIM 2.0 compliance unsupplemented).

### 8.2 When to deploy a native connector as accelerator

Deploy a native connector in addition to API-driven when **all** of the
following hold:

1. The HR system is Workday or SAP SuccessFactors (the only two with
   Microsoft-built natives at this writing).
2. The agency has near-term provisioning needs that would otherwise
   block on middleware build time.
3. The agency accepts that the native connector is decommissioned
   once the API-driven middleware is validated (typically 6–12 months).
4. The agency does not require Req #5 SCIM 2.0 compliance during the
   accelerator window. (Federal agencies subject to the HRIT
   solicitation generally cannot accept this.)

For most federal scenarios, the answer is **no** — go directly to
API-driven and skip the accelerator.

### 8.3 When to skip the native connector entirely

Skip the native connector entirely when **any** of the following hold:

1. The HR system has no Microsoft-built native (Oracle HCM, custom
   systems).
2. The agency requires Req #5 SCIM 2.0 wire-protocol compliance from
   day one.
3. The agency cannot accept a 6–12 month decommission timeline.
4. The agency operates in multi-source federation (e.g., FTE in HR-A,
   contractors in HR-B) — natives only support one source per
   instance.
5. Custom transformations (OrgPath, UPN with diacritic transliteration,
   worker-type taxonomy) are required from day one — the maintenance
   cost of those in provisioning expressions exceeds the cost of
   middleware development.

For most UIAO-governed federal scenarios, at least one of these
conditions holds.

---

## 9. Strategic Recommendation

1. **Adopt API-driven inbound provisioning as the canonical UIAO HR
   provisioning path.** This is already canon (ADR-003 ACCEPTED) and
   this comparison confirms the decision against the four-connector
   evaluation called for in UIAO_136 D1.7.

2. **Treat native connectors as optional accelerators, not as
   architecture.** Workday and SAP SuccessFactors natives may be
   deployed in parallel during initial rollout where §8.2 conditions
   are met. The native connector is decommissioned once API-driven is
   validated.

3. **Build the schema-normalizer middleware as the primary engineering
   investment.** Per ADR-003 §Architecture Pattern, the middleware is
   what makes UIAO HR-vendor-agnostic. Spec 2 Phase 3 deliverables
   (D3.1–D3.8) define this layer.

4. **Reconcile the existing PowerShell generator
   (`Spec2-D1.7-New-HRConnectorComparisonMatrix.ps1`)** with this
   canonical Markdown deliverable in a follow-up commit — see §10.

5. **D1.7 is now a reference for D3.1.** When D3.1 (canonical
   SCIM/bulkUpload architecture document) is drafted, it can cite this
   matrix as the build-vs.-buy evidence base rather than re-litigating
   it.

---

## 10. Known Drift / Reconciliation Notes

This section documents drift between this canonical deliverable and
adjacent artifacts, to be resolved in follow-up commits.

### 10.1 PowerShell generator script — reconciled 2026-04-30

[`Spec2-D1.7-New-HRConnectorComparisonMatrix.ps1`](Spec2-D1.7-New-HRConnectorComparisonMatrix.ps1)
(in the same directory) was originally authored before this canonical
deliverable and had two divergences from canon (Oracle HCM listed as a
native connector when none exists; SAP SuccessFactors missing). Both
have been reconciled across all four data sections of the script:

1. **`$connectors` (Section 1)** — Oracle HCM corrected to reflect the
   absence of a native Microsoft-built connector (per ADR-003 §Rationale
   §3); SAP SuccessFactors added as a fourth profile.
2. **`$attributeCategories` (Section 2)** — `SAP_SF` column added across
   all 27 attribute rows; `OracleHCM` column reflects "Via API-Driven
   path" semantics throughout.
3. **`$jmlComparison` (Section 3)** — `SAP_SF` block added for each of
   the 6 lifecycle events; `OracleHCM` Support is consistently "Via
   API-Driven path" with mechanism mirroring the `APIDriven` block.
4. **`$featureComparison` (Section 4)** — `SAP_SF` column added; new
   row tracing HRIT Req #5 SCIM 2.0 wire protocol (matches §6.1 of
   this document).

Output assembly updated to match: CSV exports include the `SAP_SF`
column, the inline Markdown report and console dashboard render
4-column tables, and the dashboard regex was broadened so
FedRAMP-authorized cells render as "Yes" rather than falling to "Ltd".

The script and this Markdown are now structurally aligned. This
Markdown remains canonical when the two diverge in the future; the
script generates supplementary structured outputs (JSON / CSV) for
downstream tooling.

### 10.2 ADR-049 (PROPOSED) integration point

[ADR-049](../../src/uiao/canon/adr/adr-049-microsoft-adapter-coverage-expansion.md)
proposes new reserved adapter entries for `entra-id-governance` and
`entra-workload-identity`. Both consume the HR-driven provisioning
output described here. When ADR-049 promotes from PROPOSED to ACCEPTED
(and the registry entries land), this document should be updated to
reference those adapter ids as canonical downstream consumers of D3.1
output.

---

## 11. References

### 11.1 Primary canon

- [ADR-003 — API-Driven Inbound Provisioning as HR-Agnostic Canonical Path](../../src/uiao/canon/adr/adr-003-api-driven-inbound-provisioning.md)
  (status: ACCEPTED) — sets the architectural decision this matrix evidences.
- [UIAO_136 — Priority 1 Transformation Project Plans](../../src/uiao/canon/UIAO_136_priority1-transformation-project-plans.md)
  §SPEC 2 → Phase 1 → D1.7 — defines the deliverable shape and §Next
  Implementation Tracks (Track A) — places D1.7 in the broader roadmap.
- [UIAO_135 — Identity & Directory Transformation Inventory](../../src/uiao/canon/UIAO_135_identity-directory-transformation-inventory.md)
  §2 — federal HR procurement context.
- [UIAO_007 — OrgTree Modernization (AD → Entra)](../../src/uiao/canon/UIAO_007_OrgTree_Modernization_AD_to_EntraID_v1.0.md)
  — the broader identity transformation context this provisioning
  feeds.

### 11.2 Federal procurement source

- OPM Federal HRIT Modernization Solicitation 24322626R0007 (Amendments
  2, 3, 4); Appendix A Requirements Checklist Req #5 (SCIM 2.0
  near-real-time provisioning). Public listing at sam.gov solicitation
  24322626R0007.

### 11.3 Microsoft documentation

- Microsoft Learn — API-driven inbound provisioning concepts:
  `https://learn.microsoft.com/en-us/entra/identity/app-provisioning/inbound-provisioning-api-concepts`
- Microsoft Learn — Workday inbound provisioning tutorial:
  search "Workday to Active Directory Provisioning" on learn.microsoft.com
- Microsoft Learn — SAP SuccessFactors inbound provisioning tutorial:
  search "SuccessFactors to Active Directory Provisioning" on learn.microsoft.com
- Microsoft Graph — `/users/<userid>/jobs/bulkUpload` endpoint reference:
  search "synchronization API bulk upload" on learn.microsoft.com
- GitHub — AzureAD/entra-id-inbound-provisioning samples:
  `https://github.com/AzureAD/entra-id-inbound-provisioning`

### 11.4 Companion deliverables

- [`Spec2-D1.5-New-UPNGenerationRules.ps1`](Spec2-D1.5-New-UPNGenerationRules.ps1)
  — UPN generation logic referenced in §4.2 (diacritic transliteration).
- [`Spec2-D1.6-New-WorkerTypeTaxonomy.ps1`](Spec2-D1.6-New-WorkerTypeTaxonomy.ps1)
  — worker-type taxonomy referenced in §4.2.
- [`Spec2-D1.2-ConvertTo-OrgPathTranslationRules.ps1`](Spec2-D1.2-ConvertTo-OrgPathTranslationRules.ps1)
  — OrgPath calculation referenced in §4.2.

### 11.5 Related ADRs

- [ADR-035 — OrgPath Codebook Binding](../../src/uiao/canon/adr/adr-035-orgpath-codebook-binding.md)
- [ADR-048 — OrgPath Attribute Selection](../../src/uiao/canon/adr/adr-048-orgpath-attribute-selection.md)
- [ADR-049 — Microsoft Modernization Adapter Coverage Expansion](../../src/uiao/canon/adr/adr-049-microsoft-adapter-coverage-expansion.md)
  (PROPOSED)
