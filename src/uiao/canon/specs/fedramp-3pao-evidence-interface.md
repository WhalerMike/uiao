---
document_id: UIAO_138
title: "FedRAMP 3PAO Evidence Interface — How External Assessors Engage with UIAO's Continuous Evidence Surface"
version: "0.1"
status: Draft
owner: "Michael Stratton"
created_at: "2026-06-25"
updated_at: "2026-06-25"
mas-scope: "metadata-out-of-scope"
---

# UIAO_138 — FedRAMP 3PAO Evidence Interface

Specification for how a Third Party Assessment Organization (3PAO) engages
with the UIAO substrate's continuous evidence surface under FedRAMP Rev 5
and FedRAMP 20x. This document answers three questions an assessor must
be able to answer before an engagement starts:

1. **What evidence does the substrate produce, and where does it live?**
2. **What does a compliant evidence payload look like vs. a failure?**
3. **How are classification disputes — scope disagreements between the
   substrate and the 3PAO — formally adjudicated?**

UIAO_138 is the *assessor-facing* companion to:

- [`UIAO_133`](./fedramp-20x-integration.md) — KSI emission mechanics
  (substrate-internal operational spec)
- [`UIAO_137`](./fedramp-cr26-ksi-mapping.md) — local KSI rule ↔ CR26
  control mapping
- [`ADR-106`](../adr/adr-106-fedramp-20x-integration.md) — the decision
  that defines `mas-scope` classification and KSI staleness as a drift class

The intended readers are 3PAO lead assessors, agency Authorization Officers
(AOs), and UIAO canon-steward / governance-steward when adjudicating scope
disputes.

---

## 1. Scope and non-scope

**In scope for this document:**

- Evidence artifact types the substrate emits, their OSCAL format, and
  the KSI themes they back
- The `mas-scope` classification rubric and how a 3PAO reads and disputes it
- The `DRIFT-EVIDENCE-STALE` signal and what it means to an assessor
- The boundary between substrate-side evidence (UIAO's responsibility)
  and CSP-side inherited control evidence (Microsoft's responsibility)
- The formal dispute path for scope disagreements

**Not in scope:**

- The substrate's internal emission pipeline (see UIAO_133)
- Per-control CR26 ↔ local-rule mapping (see UIAO_137)
- CSP-side P-ATO package artifacts (tracked in FINDING-PGM-001 §4)
- Agency-side ATO narrative authoring; UIAO produces evidence, not the
  narrative the agency uses to present it

---

## 2. Evidence artifact index

The substrate emits eleven artifact types per UIAO_133 §2.2. This table
is the assessor's entry point: it maps each artifact type to the OSCAL
element, the KSI theme(s) it backs, the freshness cadence, and the
responsible substrate component the assessor holds accountable.

| # | Artifact | OSCAL element | KSI themes | Cadence | Responsible component |
|---|---|---|---|---|---|
| 1 | Canonical baseline publish | `component-definition` | KSI-CNA, KSI-SVC | On baseline publish | `canon.baselines.publisher` |
| 2 | Drift event — real-time | `assessment-results/finding` | KSI-MLA, KSI-CMT | Real-time (critical) | `drift.engine.realtime` |
| 3 | Drift event — scheduled | `assessment-results/finding` | KSI-MLA, KSI-CMT | Daily (routine) | `drift.engine.scheduled` |
| 4 | Remediation workflow open | `poam-item` (open) | KSI-CMT, KSI-AFR | On workflow open | `enforcement.workflows.opener` |
| 5 | Remediation workflow resolved | `poam-item` (closed) | KSI-CMT, KSI-AFR | On workflow close | `enforcement.workflows.closer` |
| 6 | Provenance record | `assessment-plan/activity` | KSI-MLA, KSI-AFR | Continuous (append-only) | `provenance.recorder` |
| 7 | Conditional Access evaluation | `assessment-results/observation` | KSI-IAM | Continuous | `adapters.entra.ca-evaluator` |
| 8 | Sentinel ingestion completeness | `assessment-results/observation` | KSI-MLA | Continuous | `telemetry.sentinel.health` |
| 9 | Adapter health | `assessment-results/observation` | KSI-MLA, KSI-CMT | Continuous | `adapters.registry.health` |
| 10 | SCuBA conformance report | `component-definition` + `assessment-results` | KSI-CNA, KSI-SVC, KSI-IAM | On ScubaGear cycle | `scuba.conformance.reporter` |
| 11 | Quarterly cATO package | `system-security-plan` (aggregate) | KSI-AFR | Quarterly | `cato.package.aggregator` |

Each emitted artifact carries four machine-readable `props` (per UIAO_133
§2.1):

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
    value: "2026-06-25T14:32:18Z"
```

A valid artifact must carry all four props. Missing props constitute an
emission failure (see §5 below).

---

## 3. Minimum Assessment Scope (MAS) classification

### 3.1 What MAS classification means

Under RFC-0005, every substrate component carries a `mas-scope` frontmatter
field with one of three values:

| Value | Meaning | FedRAMP assessment obligation |
|---|---|---|
| `in-scope` | Component handles federal information or likely impacts CIA of federal information | Full FedRAMP assessment applies |
| `metadata-out-of-scope` | Component handles only metadata about substrate operations; does not handle federal information itself | Explicitly excluded per RFC-0005 metadata exclusion |
| `agency-side-out-of-scope` | Component is installed and operated on agency information systems per RFC-0005 §D | Explicitly excluded per RFC-0005 §D |

Every classification carries a written justification in the component's
body citing the specific data the component touches.

### 3.2 Default classification by component class

| Component class | Default `mas-scope` | Justification basis |
|---|---|---|
| Canonical baselines (UIAO_002, UIAO_022, etc.) | `in-scope` | Directly enforce CIA of federal information |
| Drift engines (UIAO_110) | `in-scope` | Identify CIA-impacting deviations |
| Remediation workflows (UIAO_111) | `in-scope` | Modify systems handling federal information |
| Provenance layer (UIAO_113) | `metadata-out-of-scope` | Records who-changed-what-when about governance actions, not federal data |
| Adapter registry (UIAO_131) | `metadata-out-of-scope` | Catalogs adapters; does not handle data adapters touch |
| OSCAL artifact generators (UIAO_022 §13.2) | `metadata-out-of-scope` | Emits compliance posture metadata, not underlying federal information |
| Telemetry health observability | `metadata-out-of-scope` | Measures substrate operations, not federal data |
| CLI surface (UIAO_008) | `agency-side-out-of-scope` | Runs on agency information systems per RFC-0005 §D |
| Adapters touching federal data (Entra, Intune, Exchange, Purview, M365) | `in-scope` | Read and act on federal information |

### 3.3 How a 3PAO reads a classification

For any substrate component a 3PAO wishes to assess:

1. Read the `mas-scope` value in the component's YAML frontmatter.
2. Read the justification stanza immediately following — it cites the
   specific data the component touches and the RFC-0005 prong it satisfies
   or invokes.
3. If the classification is `metadata-out-of-scope` or
   `agency-side-out-of-scope`, the component is out of the 3PAO's
   assessment scope under RFC-0005.

A 3PAO that accepts the classification needs no further action on that
component. A 3PAO that disagrees invokes §4 below.

---

## 4. Scope dispute procedure

RFC-0005's "likely impact" prong is intentionally broad; a 3PAO may
reasonably disagree with a `metadata-out-of-scope` classification. The
dispute procedure ensures the disagreement is structured and adjudicable
rather than a blocking argument.

### 4.1 Step 1 — 3PAO raises a written dispute

The 3PAO raises the dispute on the canon component's GitHub issue thread
(or, for engagements without direct GitHub access, in writing to the
canon-steward contact on file). The dispute must include:

- The component path and its current `mas-scope` value
- The specific RFC-0005 prong the 3PAO believes applies (handles federal
  information; or likely impacts CIA)
- The 3PAO's articulation of what federal information the component
  handles, or what CIA impact the 3PAO asserts

### 4.2 Step 2 — canon-steward and governance-steward review

Canon-steward and governance-steward review the written dispute within
10 business days. They compare the 3PAO's assertion against the component's
justification stanza and the MAS rubric (§3.2).

If they agree with the 3PAO: the component's `mas-scope` is updated to
`in-scope` with a justification delta in the changelog. The update lands
as a PR with the 3PAO dispute cited in the commit message.

If they do not agree: they provide a written response citing the specific
RFC-0005 language that supports the existing classification.

### 4.3 Step 3 — escalation default

If the disagreement persists after step 2:

- The component is **re-classified `in-scope` pending resolution** —
  the substrate takes the conservative position.
- The dispute is documented in FINDING-PGM-001 §5 (open scope disputes) with
  the component path, both arguments, and the date of escalation.
- Resolution requires either (a) the 3PAO withdrawing the dispute in
  writing, or (b) FedRAMP PMO guidance that resolves the classification
  question.

---

## 5. Evidence compliance and failure signals

### 5.1 What a compliant evidence payload looks like

A substrate deployment passes 3PAO evidence review when:

1. All eleven artifact types in §2 are present in the OSCAL artifact store.
2. Each artifact carries all four `fedramp:*` props (schema check per
   UIAO_133 §2.4).
3. Each artifact's `fedramp:ksi-mapping-source` resolves to a row in
   UIAO_133 §2.2 (mapping-source check).
4. No artifact's `fedramp:ksi-emitted-at` is older than its
   `fedramp:ksi-freshness-cadence` budget (freshness check).
5. The quarterly cATO package (artifact 11) covers all KSI themes for
   the agency's Moderate baseline with zero missing themes.

### 5.2 Failure signals and their severity

The substrate surfaces these signals; the 3PAO uses them as the primary
evidence of non-compliance during an assessment:

| Signal | Class | Severity | Meaning |
|---|---|---|---|
| `DRIFT-EVIDENCE-STALE` | Drift | P2 | A single artifact's `ksi-emitted-at` exceeds its cadence budget by ≥ 1× |
| `DRIFT-EVIDENCE-STALE-AGGREGATE` | Drift | P1 | The quarterly cATO package is missing required KSI coverage for the agency's Moderate baseline |
| Missing `fedramp:*` prop | Emission failure | P0 (blocks emission) | An emitted artifact was rejected by the OSCAL pipeline schema check |
| Orphaned `ksi-mapping-source` | Emission failure | P0 (blocks emission) | An artifact cited a mapping row that no longer exists in UIAO_133 §2.2 |

P0 failures block the emission entirely — the artifact does not enter the
OSCAL store, so the 3PAO observes a missing artifact (condition 1 in §5.1
fails) rather than a stale one.

P1/P2 drift events appear in the OSCAL store as `assessment-results/finding`
entries with the drift class in the `finding.description` field.

### 5.3 POA&M surface

Every P1/P2 drift event that is not remediated within its SLA appears in
the substrate's POA&M (`poam-item` entries, artifacts 4 and 5 in §2).
The 3PAO uses the POA&M as the record of open compliance gaps. A clean
POA&M (all items resolved or within SLA) is a prerequisite for cATO
package sign-off.

---

## 6. Boundary with CSP-side inherited controls

UIAO's evidence surface covers the substrate layer. A GCC-Moderate
deployment also depends on inherited controls from Microsoft's P-ATO
package. The boundary is:

| Layer | Responsible party | Evidence artifact |
|---|---|---|
| Substrate (drift, baselines, workflows, provenance, OSCAL pipeline) | UIAO | Artifacts 1–11 in §2 |
| Entra ID / M365 platform configuration | Agency (via substrate adapters) | Artifacts 7, 10 — Conditional Access evaluation + SCuBA conformance |
| GCC-Moderate P-ATO inherited controls | Microsoft | Microsoft's P-ATO package (external; tracked in FINDING-PGM-001 §4) |

The 3PAO's substrate-side engagement covers rows 1 and 2. Row 3 (Microsoft
P-ATO) is outside UIAO's evidence surface. Where a KSI requires inherited
control evidence from Microsoft and Microsoft has not yet filed a 20x-aligned
GCC-Moderate package, UIAO marks the gap in FINDING-PGM-001 §4 and the 3PAO
records it as a CSP-external-remedy item — not a substrate failure.

---

## 7. Dry-run execution (ADR-106 ratification gate 3)

ADR-106's third ratification condition requires a dry-run KSI completeness
check against a representative agency Moderate baseline producing zero P0/P1
staleness events. This section specifies how to execute that dry-run.

### 7.1 Baseline construction

Construct the representative baseline from:

- The GCC-Moderate boundary assessment at
  `src/uiao/canon/compliance/reference/gcc-moderate-boundary-assessment/`
- The CR26 Moderate profile shell in the pinned snapshot at
  `src/uiao/canon/compliance/reference/fedramp-cr26/snapshot/<sha>/`
- The KSI theme coverage map in UIAO_137 §4 (which themes the local rule
  corpus addresses)

The baseline is a list of KSI themes required for a GCC-Moderate
authorization. As of UIAO_137 v0.2, the required themes are all ten
CR26 KSI themes: KSI-CMT, KSI-CNA, KSI-CED, KSI-IAM, KSI-INR, KSI-MLA,
KSI-PIY, KSI-RPL, KSI-SVC, KSI-SCR.

### 7.2 Pass criteria

The dry-run passes when:

1. Every required KSI theme has at least one artifact in the OSCAL store
   carrying that theme in `fedramp:ksi-themes`.
2. No artifact is stale (zero `DRIFT-EVIDENCE-STALE` events at P0 or P1).
3. The cATO package (artifact 11) lists all required KSI themes in its
   coverage attestation.

### 7.3 Recording results

Dry-run results are recorded in FINDING-PGM-001 §4 (internal-remedy items)
with:

- Date of run
- Baseline used (SHA of the CR26 snapshot)
- Pass/fail per criterion in §7.2
- Any P0/P1 events observed, with responsible component and remediation status

A passing dry-run result in FINDING-PGM-001 is the artifact that satisfies
ADR-106 ratification condition 3.

---

## 8. Validation and acceptance

UIAO_138 moves from Draft to Current when:

1. ADR-106 moves from PROPOSED to ACCEPTED (all four ratification
   conditions met).
2. At least one 3PAO engagement has used this document as the interface
   specification and confirmed the artifact index (§2) and dispute procedure
   (§4) are complete and accurate.
3. Canon-steward and governance-steward sign off on the dry-run results
   recorded per §7.3.

---

## 9. References

### UIAO canon

- [`ADR-106`](../adr/adr-106-fedramp-20x-integration.md) — FedRAMP 20x
  integration decision; defines `mas-scope`, KSI staleness as drift class,
  and the ratification gate this document helps satisfy
- [`ADR-061`](../adr/adr-061-fedramp-cr26-catalog-vendoring.md) — CR26
  catalog vendoring policy
- [`ADR-043`](../adr/adr-043-fedramp-rfc-0026-ca7-integration.qmd) — CA-7
  continuous monitoring integration
- [`UIAO_133`](./fedramp-20x-integration.md) — substrate-internal KSI
  emission mechanics (operational companion)
- [`UIAO_137`](./fedramp-cr26-ksi-mapping.md) — local KSI rule ↔ CR26
  control mapping
- [`UIAO_132`](./fedramp-rfc-0026-ca7-integration.md) — RFC-0026 CA-7
  pathway integration
- [`FINDING-PGM-001`](../../../../docs/findings/fedramp-20x-moderate-pilot.md) — FedRAMP 20x Moderate Pilot active; CSP external-remedy tracker

### FedRAMP primary sources

- [RFC-0005 Minimum Assessment Scope Standard](https://www.fedramp.gov/rfcs/0005/)
- [RFC-0006 Phase One KSIs](https://www.fedramp.gov/rfcs/0006/)
- [RFC-0014 Phase Two KSIs](https://www.fedramp.gov/rfcs/0014/)
- [RFC-0024 Rev5 Machine-Readable Packages](https://www.fedramp.gov/rfcs/0024/)
- [FedRAMP 20x Overview](https://www.fedramp.gov/20x/)
