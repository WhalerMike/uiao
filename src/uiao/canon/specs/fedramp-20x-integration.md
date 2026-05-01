---
document_id: UIAO_133
title: "UIAO FedRAMP 20x Integration"
version: "0.1"
status: Draft
classification: CANONICAL
owner: "Michael Stratton"
created_at: "2026-04-27"
updated_at: "2026-04-27"
boundary: "GCC-Moderate"
mas-scope: "in-scope"
---

# UIAO FedRAMP 20x Integration

Operational specification for how the UIAO substrate satisfies FedRAMP
20x — the umbrella program comprising the Minimum Assessment Scope
Standard (RFC-0005), the Phase One / Phase Two Key Security Indicators
(RFC-0006 / RFC-0014), and the Rev5 Machine-Readable Packages standard
(RFC-0024). This document is the operational companion to
[ADR-047](../adr/adr-047-fedramp-20x-integration.md). ADR-047 records
the decision and rationale; UIAO_133 records the mechanics — which
adapter emits which KSI evidence, which workflow fans out which
staleness alert, and which canon artifact answers which KSI theme.

UIAO_133 sits beside [UIAO_132](./fedramp-rfc-0026-ca7-integration.md)
(FedRAMP RFC-0026 CA-7 Pathway Integration). Where UIAO_132 covers a
single Rev5 control's continuous-monitoring expectations, UIAO_133
covers the program-level evidence vocabulary and scope discipline that
the modernized RFC-0026 pathway rides on.

---

## 1. Scope

UIAO_133 covers four operational concerns:

1. **KSI emission tagging** — how substrate-emitted OSCAL artifacts
   carry KSI-theme metadata (ADR-047 D1).
2. **Minimum Assessment Scope classification** — how each canon
   component is tagged `in-scope`, `metadata-out-of-scope`, or
   `agency-side-out-of-scope` per RFC-0005 (ADR-047 D2).
3. **KSI staleness drift** — how the drift engine treats stale KSI
   evidence as a `DRIFT-EVIDENCE-STALE` class (ADR-047 D3).
4. **Pathway posture** — how the substrate runs the traditional
   pathway at 20x adoption start and pre-wires the modernized pathway
   (ADR-047 D4).

Out of scope for this document:

- CSP-side 20x package filings. Those are external-remedy items
  tracked in
  [FINDING-002 §4](../../../../docs/findings/fedramp-20x-moderate-pilot.md).
- Agency-side authorization sponsor selection and onboarding. Those
  are agency-program decisions; UIAO_133 covers only the substrate's
  emission-side surface that an authorization sponsor consumes.
- The full enumeration of every KSI in the Moderate catalog. UIAO_133
  references KSI **themes** (KSI-CNA, KSI-MLA, etc.) per ADR-047 D2's
  rationale; individual KSI IDs are catalog-version-dependent and
  tracked in companion mappings as the catalog stabilizes.

---

## 2. KSI emission tagging

### 2.1 Tagging contract

Every OSCAL artifact emitted by the substrate carries a structured
metadata block in its `props` array:

```yaml
props:
  - name: "fedramp:ksi-themes"
    ns: "https://fedramp.gov/ns/oscal"
    value: "KSI-MLA,KSI-CMT"
  - name: "fedramp:ksi-mapping-source"
    ns: "https://fedramp.gov/ns/oscal"
    value: "UIAO_022 §13.3 TBL-P2-011 row 2"
  - name: "fedramp:ksi-freshness-cadence"
    ns: "https://fedramp.gov/ns/oscal"
    value: "real-time-critical;daily-routine"
  - name: "fedramp:ksi-emitted-at"
    ns: "https://fedramp.gov/ns/oscal"
    value: "2026-04-27T14:32:18Z"
```

Four required props per emission:

| Prop name | Purpose |
|---|---|
| `fedramp:ksi-themes` | Comma-separated list of KSI themes the artifact backs (KSI-CNA, KSI-SVC, KSI-IAM, KSI-MLA, KSI-CMT, KSI-AFR). |
| `fedramp:ksi-mapping-source` | Pointer to the canon row that authorizes this mapping (Phase 2 TBL-P2-011 row reference). |
| `fedramp:ksi-freshness-cadence` | The cadence specified in TBL-P2-011 for this artifact's KSI(s). |
| `fedramp:ksi-emitted-at` | ISO-8601 timestamp of artifact generation; basis for staleness checks. |

### 2.2 Emission map (substrate output → OSCAL artifact + KSI tag)

This table is the canonical source of substrate-side KSI emissions.
It is the operational form of Phase 2 TBL-P2-011 (UIAO_022 §13.3),
adding the OSCAL artifact type and the responsible substrate
component.

| # | Substrate output | OSCAL artifact (UIAO_022 §13.2) | Responsible component | KSI themes | Cadence |
|---|---|---|---|---|---|
| 1 | CanonicalBaseline (publish, version increment) | component-definition | `canon.baselines.publisher` | KSI-CNA, KSI-SVC | On baseline publish |
| 2 | DriftEvent (real-time) | assessment-results / finding | `drift.engine.realtime` | KSI-MLA, KSI-CMT | Real-time for critical |
| 3 | DriftEvent (scheduled) | assessment-results / finding | `drift.engine.scheduled` | KSI-MLA, KSI-CMT | Daily for routine |
| 4 | RemediationWorkflow (open) | poam-item (open) | `enforcement.workflows.opener` | KSI-CMT, KSI-AFR | On workflow open |
| 5 | RemediationWorkflow (resolved) | poam-item (closed) | `enforcement.workflows.closer` | KSI-CMT, KSI-AFR | On workflow close |
| 6 | ProvenanceRecord (per action) | assessment-plan / activity | `provenance.recorder` | KSI-MLA, KSI-AFR | Continuous (append-only) |
| 7 | Conditional Access policy evaluation | assessment-results / observation | `adapters.entra.ca-evaluator` | KSI-IAM | Continuous |
| 8 | Sentinel ingestion completeness | assessment-results / observation | `telemetry.sentinel.health` | KSI-MLA | Continuous |
| 9 | Adapter health (cross-plane) | assessment-results / observation | `adapters.registry.health` | KSI-MLA, KSI-CMT | Continuous |
| 10 | SCuBA conformance report | component-definition + assessment-results | `scuba.conformance.reporter` | KSI-CNA, KSI-SVC, KSI-IAM | On ScubaGear cycle |
| 11 | Aggregated cATO package (quarterly) | system-security-plan | `cato.package.aggregator` | KSI-AFR | Quarterly |

### 2.3 Tag injection point

Tags are injected by the OSCAL artifact generator at emission time
(Phase 2 §13.2 pipeline). No upstream substrate code changes; the
generator reads its row from §2.2 above and stamps the `props`. The
generator's existing OSCAL schema validation is extended to require
the four `fedramp:*` props on every emission.

### 2.4 Validation

Two checks are added to the existing OSCAL pipeline test harness
(UIAO_131 adapter test strategy):

1. **Schema check.** Every emitted artifact must carry all four
   `fedramp:*` props. Missing props fail the emission.
2. **Mapping-source check.** Every artifact's `fedramp:ksi-mapping-source`
   must resolve to a row that exists in §2.2 above. Orphaned mappings
   fail the emission.

---

## 3. Minimum Assessment Scope classification

### 3.1 The `mas-scope` frontmatter field

Every canonical document under `src/uiao/canon/` carries an `mas-scope`
field in its YAML frontmatter with one of three values:

- `in-scope` — the component handles federal information and/or
  likely impacts CIA of federal information. Full FedRAMP assessment
  applies.
- `metadata-out-of-scope` — the component handles only metadata
  about substrate operations (telemetry, health checks, performance
  counters, audit-of-audit) and does not handle federal information
  itself. Excluded under RFC-0005's metadata exclusion.
- `agency-side-out-of-scope` — the component is installed, managed,
  and operated on agency information systems. Excluded under
  RFC-0005 §D.

Every classification carries a justification stanza in the document
body explaining why the chosen value applies, citing the specific
data the component touches.

### 3.2 Initial classification rubric

This rubric is the first-pass classification for canon components as
of 2026-04-27. Re-classification is required at every canon-version
increment.

| Component class | Default `mas-scope` | Justification template |
|---|---|---|
| Canonical baselines (UIAO_002, UIAO_022, etc.) | `in-scope` | Baselines describe configuration that directly enforces CIA of federal information. |
| Drift engines (UIAO_110) | `in-scope` | Drift events identify CIA-impacting deviations. |
| Remediation workflows (UIAO_111) | `in-scope` | Remediation actions modify systems that handle federal information. |
| Provenance layer (UIAO_113) | `metadata-out-of-scope` | Provenance records who-changed-what-when about substrate operations; the provenance records themselves are metadata about governance actions, not federal information. |
| Adapter registry (UIAO_131) | `metadata-out-of-scope` | The registry catalogs adapters; it does not itself handle the federal information adapters touch. (Individual adapters are classified separately.) |
| OSCAL artifact generators (UIAO_022 §13.2) | `metadata-out-of-scope` | The generators emit metadata describing substrate compliance posture, not the underlying federal information. |
| Telemetry health observability | `metadata-out-of-scope` | Health observations measure substrate operations, not federal data. |
| CLI surface (UIAO_008) | `agency-side-out-of-scope` | The CLI runs on agency information systems per RFC-0005 §D; substrate-side endpoints it calls are classified separately. |
| Adapters touching federal data (Entra, Intune, Exchange, Purview, M365) | `in-scope` | These adapters read and act on federal information. |

### 3.3 Classification audit cadence

- **Per-canon-version review.** Any canon-version increment that
  changes a component's data surface re-evaluates `mas-scope`. The
  re-evaluation lands as a frontmatter update with a justification
  delta in the changelog.
- **Annual rubric review.** The classification rubric in §3.2 is
  reviewed annually by canon-steward + governance-steward. RFC-0010
  best-practices guidance (when published) is the trigger for an
  immediate out-of-cycle review.
- **3PAO disagreement procedure.** A 3PAO that disagrees with a
  classification raises the disagreement on the canon document's
  thread; canon-steward and governance-steward adjudicate. If the
  disagreement persists, the component is re-classified `in-scope`
  pending resolution.

---

## 4. KSI staleness drift

### 4.1 Drift class definition

A new drift class is added to the drift engine taxonomy
(UIAO_110 §3):

| Drift class | Trigger | Default severity |
|---|---|---|
| `DRIFT-EVIDENCE-STALE` | An OSCAL artifact's `fedramp:ksi-emitted-at` timestamp is older than its `fedramp:ksi-freshness-cadence` budget by ≥ 1.0× the budget. | P2 |
| `DRIFT-EVIDENCE-STALE-AGGREGATE` | The aggregate quarterly cATO package (row 11 of §2.2) is missing required KSI coverage for the agency's Moderate baseline. | P1 |

### 4.2 Detection

The drift engine adds a `staleness-monitor` that runs every 60 seconds
and inspects the `fedramp:ksi-emitted-at` prop on every artifact in
the OSCAL artifact store. Stale artifacts emit a
`DRIFT-EVIDENCE-STALE` event with:

- `subject` = the substrate component from §2.2 column "Responsible component"
- `expected_cadence` = the value of `fedramp:ksi-freshness-cadence`
- `actual_age` = `now - fedramp:ksi-emitted-at`
- `ksi_themes` = the value of `fedramp:ksi-themes`

### 4.3 Remediation routing

`DRIFT-EVIDENCE-STALE` events route through the standard
RemediationWorkflow opener (UIAO_111). The default routing table:

| Responsible component (substrate) | Default workflow owner |
|---|---|
| Adapter (any) | Adapter author per UIAO_131 |
| Drift engine (real-time / scheduled) | drift-engine-steward |
| Provenance recorder | provenance-steward |
| OSCAL generator | governance-steward |
| Sentinel ingestion health | telemetry-steward |
| Adapter registry health | adapter-registry-steward |
| SCuBA conformance reporter | scuba-steward |
| cATO package aggregator | canon-steward |

Workflow SLAs are inherited from the existing UIAO_111 SLA framework.

---

## 5. Pathway posture

### 5.1 Traditional pathway (substrate default at 20x adoption start)

- OSCAL artifacts are generated per Phase 2 §13.2 with `fedramp:*` tag
  injection per §2.3 above.
- Staleness drift is detected per §4 and routed to remediation.
- KSI completeness is presented to AOs as a quarterly cATO Acceptance
  Package element (Phase 3 §4.1.1, fifth element added by ADR-047).
- AO/3PAO review is **manual**: a human reads the KSI completeness
  certification and the underlying OSCAL artifacts.

### 5.2 Modernized pathway (gated migration)

- OSCAL artifacts continue to be generated identically to the
  traditional pathway.
- A new emission target is added: an **agency authorization sponsor
  KSI feed** that streams KSI-tagged OSCAL artifacts continuously to
  the sponsor's intake endpoint.
- AO/3PAO review is **automated**: the sponsor's intake validates
  KSI completeness and freshness against the agency's Moderate
  baseline catalog without human intermediation.

### 5.3 Migration gate

The substrate moves from §5.1 to §5.2 when the ADR-047 ratification
gate fires (RFC-0010 publication + stable Moderate KSI catalog +
clean dry-run + steward signoff). The migration is implemented as a
new adapter (`fedramp-20x-sponsor-feed`) that reads from the existing
OSCAL artifact store; no upstream substrate code changes.

---

## 6. Interaction with existing canon

### 6.1 With UIAO_022 (Phase 2 Governance OS)

- UIAO_022 §13.3 (KSI Emission Surface) defines TBL-P2-011, the
  human-readable map of substrate output → KSI theme.
- UIAO_133 §2.2 is the operational implementation of TBL-P2-011 with
  responsible-component and OSCAL-artifact columns added.
- The two tables must agree on KSI theme assignments. Discrepancy is
  a canon-integrity bug; canon-steward owns reconciliation.

### 6.2 With UIAO_023 (Phase 3 cATO)

- UIAO_023 §4.1.1 (FedRAMP 20x KSI Crosswalk) defines P3-T-001a, the
  mapping of cATO row → KSI theme + Phase 3 optimization.
- UIAO_133 §2.2 supplies the substrate-side emission identity for
  each cATO row.
- Phase 3 cATO Acceptance Package's fifth element (KSI completeness
  certification) is generated by the `cato.package.aggregator`
  component (§2.2 row 11).

### 6.3 With UIAO_132 (RFC-0026 CA-7)

- UIAO_132 covers a single Rev5 control's continuous-monitoring
  expectations.
- UIAO_133 covers the program-level evidence vocabulary
  (KSI-tagged OSCAL).
- The modernized RFC-0026 pathway adapters (`vdr-bir`, `ccm-bir` per
  UIAO_132 D1) emit OSCAL artifacts that pass through the §2.3 tag
  injection point, so RFC-0026 modernized-pathway evidence is also
  20x KSI evidence by construction.

### 6.4 With FINDING-001 and FINDING-002

- FINDING-001 (INR unavailable in GCC-Moderate) is unaffected by
  UIAO_133. INR's external remedy still requires Microsoft product
  action regardless of substrate-side KSI readiness.
- FINDING-002 (20x Moderate Pilot active) §4 internal-remedy items
  are the substrate-side reconfiguration UIAO_133 implements. CSP
  external-remedy items in FINDING-002 §4 are independent.

---

## 7. Validation and acceptance

UIAO_133 acceptance requires:

1. ADR-047 ratification (the four conditions in ADR-047 §"Ratification
   gate").
2. §2.2 emission map dry-run produces zero schema-check failures and
   zero mapping-source-check failures across at least 30 days of
   normal substrate operation.
3. §3.2 classification rubric passes a canon-steward +
   governance-steward review including written justifications for
   every component classified `metadata-out-of-scope` or
   `agency-side-out-of-scope`.
4. §4 staleness-monitor observes zero P0 events and < 5 P1 events
   over a 30-day continuous run.
5. §5.1 traditional pathway operates end-to-end through one full cATO
   acceptance package quarter without human intervention beyond
   AO/3PAO sign-off.

Until all five conditions are met, this spec stays at status `Draft`.

---

## 8. References

### FedRAMP primary sources

- [FedRAMP 20x Overview](https://www.fedramp.gov/20x/)
- [FedRAMP 20x Documentation](https://www.fedramp.gov/docs/20x/)
- [Key Security Indicators](https://www.fedramp.gov/docs/20x/key-security-indicators/)
- [RFC-0005 Minimum Assessment Scope Standard](https://www.fedramp.gov/rfcs/0005/)
- [RFC-0006 Phase One KSIs](https://www.fedramp.gov/rfcs/0006/)
- [RFC-0014 Phase Two KSIs](https://www.fedramp.gov/rfcs/0014/)
- [RFC-0024 Rev5 Machine-Readable Packages](https://www.fedramp.gov/rfcs/0024/)
- [RFC-0005 community discussion (closed)](https://github.com/FedRAMP/community/discussions/2)

### UIAO related canon

- [ADR-047 — FedRAMP 20x Integration decision](../adr/adr-047-fedramp-20x-integration.md)
- [ADR-043 — FedRAMP RFC-0026 CA-7 Integration decision](../adr/adr-043-fedramp-rfc-0026-ca7-integration.md)
- [UIAO_132 — FedRAMP RFC-0026 CA-7 Pathway Integration spec](./fedramp-rfc-0026-ca7-integration.md)
- [Phase 2 §13.3 KSI Emission Surface (UIAO_022)](../../../../docs/customer-documents/modernization/uiao-modernization-program/03-phase2-governance-os.qmd)
- [Phase 3 §4.1.1 20x KSI Crosswalk (UIAO_023)](../../../../docs/customer-documents/modernization/uiao-modernization-program/04-phase3-optimization-cato.qmd)
- [FINDING-001 — FedRAMP GCC-Moderate INR unavailability](../../../../docs/findings/fedramp-gcc-moderate-informed-network-routing.md)
- [FINDING-002 — FedRAMP 20x Moderate Pilot active](../../../../docs/findings/fedramp-20x-moderate-pilot.md)
