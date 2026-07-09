---
document_id: UIAO_205
title: "FedRAMP 20x Agency Registration and Sponsor Onboarding"
version: "0.1"
status: Draft
owner: "Michael Stratton"
created_at: "2026-06-25"
updated_at: "2026-06-25"
mas-scope: "agency-side-out-of-scope"
---

# UIAO_205 — FedRAMP 20x Agency Registration and Sponsor Onboarding

Specification for how an agency using UIAO as its identity governance
substrate initiates FedRAMP 20x registration, onboards an authorization
sponsor, and migrates from the traditional pathway to the modernized pathway
defined in [UIAO_133 §5](./fedramp-20x-integration.md).

This document fills the gap that UIAO_133 explicitly defers — "Agency-side
authorization sponsor selection and onboarding" (UIAO_133 §1 out-of-scope
item 2) — and specifies the gate-firing ceremony that [ADR-106
D4](../adr/adr-106-fedramp-20x-integration.md) pre-wires but does not
mechanize.

The intended readers are the agency program manager responsible for the 20x
registration, the agency's Authorization Officer (AO), and the UIAO
canon-steward coordinating the substrate-side readiness checks.

---

## 1. Scope

UIAO_205 covers four concerns:

1. **Registration prerequisites** — the substrate-side and agency-side
   conditions that must be true before FedRAMP 20x registration begins.
2. **Authorization sponsor intake** — the roles involved, the sponsor's
   KSI feed contract, and the delivery mechanism for continuous evidence.
3. **Pilot enrollment gates** — the ordered checklist that moves an agency
   deployment from traditional pathway to modernized pathway.
4. **Submission package assembly** — how `uiao fedramp 3pao-package` output
   maps to what FedRAMP PMO expects, and what the agency adds before filing.

Out of scope for this document:

- Internal substrate KSI emission mechanics (UIAO_133).
- 3PAO engagement interface for evidence review (UIAO_138).
- CSP-side P-ATO package filings (FINDING-PGM-001 §4 external remedies).
- The decision rationale for the 20x posture (ADR-106).

---

## 2. Registration prerequisites

An agency deployment must satisfy all of the following before beginning
FedRAMP 20x registration. Prerequisites are divided into substrate-side
(UIAO's responsibility) and agency-side (the agency program's responsibility).

### 2.1 Substrate-side prerequisites

| # | Condition | Verified by |
|---|---|---|
| S-1 | ADR-106 status is ACCEPTED | Check `src/uiao/canon/adr/adr-106-fedramp-20x-integration.md` frontmatter `status:` field |
| S-2 | ADR-061 status is ACCEPTED (CR26 snapshot vendored) | Check `src/uiao/canon/adr/adr-061-fedramp-cr26-catalog-vendoring.md` |
| S-3 | `uiao fedramp dryrun` passes against the agency's target baseline with zero P0/P1 events | Run and record per UIAO_138 §7; result recorded in FINDING-PGM-001 §4.7 |
| S-4 | UIAO_138 evidence artifact index (§2) is fully populated — all 11 artifact types present in the OSCAL store | Run `uiao fedramp staleness` and confirm zero missing artifact types |
| S-5 | All `in-scope` canon components carry a written MAS-scope justification | Canon-steward review; UIAO_133 §3.3 rubric |

S-3 is the critical gate. An agency should not initiate registration until a
clean dry-run is on record, because FedRAMP PMO will ask for the dry-run
result as evidence of substrate readiness. The run ID from `uiao fedramp
dryrun` is the artifact that satisfies this requirement.

### 2.2 Agency-side prerequisites

| # | Condition | Owner |
|---|---|---|
| A-1 | Agency ATO (or interim ATO) is current for the systems UIAO governs | Agency ISSO |
| A-2 | The agency has identified an Authorization Officer willing to act as 20x authorization sponsor | Agency AO / program manager |
| A-3 | The agency has reviewed the FedRAMP 20x pilot eligibility criteria at fedramp.gov/20x and confirmed the deployment qualifies | Program manager |
| A-4 | The agency's System Security Plan (SSP) identifies UIAO as the identity governance substrate and cites UIAO_133 / UIAO_138 as the KSI evidence interface | Agency ISSO |

A-4 is the SSP hook. FedRAMP 20x does not require a full SSP rewrite, but
the agency's existing SSP or system description must be updated to reference
the UIAO substrate as the source of KSI evidence, so reviewers know where
to look. If the agency is using UIAO_185 (SSP Template), the FedRAMP 20x
section in that template is the correct location for this citation.

---

## 3. Authorization sponsor intake

### 3.1 Role definitions

**Authorization Officer (AO).** The federal official with the authority to
authorize a system for operation. In the FedRAMP 20x modernized pathway, the
AO acts as the authorization *sponsor* — the party who consumes the KSI feed
from UIAO_133 §5.2 and validates KSI completeness continuously rather than
through a point-in-time assessment.

**3PAO.** In the modernized pathway, the 3PAO's role shifts from a
point-in-time assessor conducting a full Annual Assessment to a continuous
evidence validator. Under the traditional pathway (the current substrate
default), 3PAO engagement is unchanged. UIAO_138 covers the 3PAO interface
in both pathways.

**UIAO canon-steward.** Coordinates the substrate-side readiness checks
(§2.1), signs off on the dry-run result, and maintains the registration
record in FINDING-PGM-001.

### 3.2 Sponsor KSI feed contract

In the modernized pathway, UIAO_133 §5.2 defines a new emission target: an
**agency authorization sponsor KSI feed** that streams KSI-tagged OSCAL
artifacts continuously to the sponsor's intake endpoint. The feed contract
specifies:

| Field | Value |
|---|---|
| Format | OSCAL `assessment-results` with `fedramp:ksi-*` props per UIAO_133 §2.1 |
| Delivery mechanism | HTTPS POST to the sponsor's intake endpoint; or pull via authenticated REST from the OSCAL artifact store |
| Authentication | Agency-issued API key scoped to the OSCAL artifact store read endpoint |
| Freshness guarantee | Artifacts are streamed within the cadence specified in `fedramp:ksi-freshness-cadence`; real-time-critical artifacts within 60 seconds of emission |
| Coverage attestation | The quarterly cATO package (UIAO_133 §2.2 row 11) is delivered as a single `system-security-plan` aggregate and also pushed to the sponsor feed on its quarterly cadence |

The sponsor feed is implemented as the `fedramp-20x-sponsor-feed` adapter
described in UIAO_133 §5.3. It is not active until the modernized-pathway
migration ceremony (§4) completes.

### 3.3 Sponsor onboarding steps

1. Agency program manager designates the AO as authorization sponsor in
   writing (agency-internal memo; retained in the registration record).
2. UIAO canon-steward provisions an API key for the sponsor's intake
   endpoint and records the endpoint URL in the agency's UIAO deployment
   configuration.
3. Canon-steward activates the `fedramp-20x-sponsor-feed` adapter for the
   agency's deployment, targeting the provisioned endpoint.
4. Sponsor validates receipt of the initial feed push by confirming that
   all 11 artifact types (UIAO_138 §2) appear in their intake system within
   24 hours.
5. Both parties sign the sponsor intake checklist (Attachment A to this
   document) confirming endpoint configuration, artifact coverage, and
   freshness verification. The signed checklist is retained in FINDING-PGM-001
   §5.

---

## 4. Pilot enrollment gates

The following ordered gate sequence moves an agency from the traditional
pathway (UIAO_133 §5.1) to the modernized pathway (UIAO_133 §5.2). Each
gate must be satisfied in sequence; a gate that cannot be satisfied is
recorded as a blocking item in FINDING-PGM-001.

| Gate | Condition | Artifact |
|---|---|---|
| G-1 | Substrate prerequisites satisfied (§2.1, all five) | Canon-steward sign-off, recorded in FINDING-PGM-001 |
| G-2 | Agency prerequisites satisfied (§2.2, all four) | Agency program manager attestation |
| G-3 | Clean dry-run on record (UIAO_138 §7) | Run ID in FINDING-PGM-001 §4.7 |
| G-4 | Authorization sponsor onboarded (§3.3, steps 1–5) | Signed sponsor intake checklist in FINDING-PGM-001 §5 |
| G-5 | Traditional-pathway cATO package completed for at least one full quarter under the substrate | cATO package artifact from UIAO_133 §2.2 row 11 |
| G-6 | FedRAMP PMO pilot application submitted and accepted | PMO acceptance email / portal confirmation |
| G-7 | Migration ceremony sign-off (§4.1) | Countersigned ceremony record |

### 4.1 Migration ceremony

The migration ceremony is the governance event that formally closes the
traditional pathway and opens the modernized pathway for an agency deployment.
It requires three sign-offs in sequence:

1. **Canon-steward** confirms that S-1 through S-5 (§2.1) remain satisfied
   and that no new P0/P1 drift events are open against the FedRAMP evidence
   surface.
2. **Governance-steward** confirms that the agency's OrgPath deployment is
   at the maturity level required by the modernized pathway's automated
   KSI completeness validation (minimum: OrgPath positions populated for all
   in-scope personnel; Entra adapter active; SCuBA conformance reporter
   current).
3. **Agency AO (authorization sponsor)** countersigns, confirming the
   sponsor intake endpoint is receiving and validating the KSI feed without
   error and that the agency is prepared to operate under continuous
   authorization.

The ceremony record — a brief document capturing the three sign-offs, the
date, the dry-run run ID, and the current ADR-106 status — is committed to
`docs/findings/fedramp-20x-moderate-pilot.qmd` (FINDING-PGM-001) §5 and becomes
the authoritative record that the agency transitioned to the modernized
pathway.

---

## 5. Submission package assembly

The `uiao fedramp 3pao-package` CLI command produces the substrate-side
evidence package. The command outputs a directory containing:

```
3pao-package/
  oscal-artifact-index.json       # UIAO_138 §2 artifact types + freshness status
  ksi-coverage-map.json           # Which KSI themes are covered, per UIAO_137
  mas-scope-classification.json   # Per-component MAS scope + justifications, per UIAO_133 §3
  dry-run-results.json            # Latest dry-run result from FINDING-PGM-001 §4.7
  poam-open-items.json            # Open POA&M items, per UIAO_133 §4.3
  cato-package-latest.oscal       # Most recent quarterly cATO package (OSCAL SSP aggregate)
  README.md                       # Cover sheet with run metadata
```

This package satisfies the substrate-side evidence requirements. Before
filing with FedRAMP PMO, the agency adds:

| Addition | Source |
|---|---|
| Agency System Security Plan or system description (updated per A-4) | Agency ISSO |
| Authorization sponsor designation memo (§3.3 step 1) | Agency program manager |
| Signed sponsor intake checklist (§3.3 step 5) | Canon-steward + agency AO |
| Boundary diagram for the systems UIAO governs | Agency ISSO, consistent with UIAO_139 (GCC-Moderate boundary impact) |
| Any open scope disputes (UIAO_138 §4.3) and their current status | Canon-steward |

The complete package — UIAO substrate output plus agency additions — is the
artifact the agency submits to FedRAMP PMO as its 20x pilot application.

---

## 6. Interaction with existing canon

### 6.1 With UIAO_133 (FedRAMP 20x Integration)

UIAO_205 is the agency-facing complement to UIAO_133's substrate-internal
emission mechanics. UIAO_133 §5.3 describes the `fedramp-20x-sponsor-feed`
adapter; UIAO_205 §3.2 specifies the contract that adapter satisfies. The
two documents are consistent: where UIAO_133 says "a new emission target is
added," UIAO_205 §3.3 specifies who provisions it and when.

### 6.2 With UIAO_138 (3PAO Evidence Interface)

UIAO_138 covers the 3PAO's view of the evidence surface; UIAO_205 covers the
agency's path to producing and submitting that surface. The dry-run
specification in UIAO_138 §7 is the substrate-side procedure; UIAO_205 §2.1
S-3 is the registration gate that depends on a passing result from that
procedure.

### 6.3 With ADR-106 (FedRAMP 20x Integration decision)

ADR-106 D4 states that the substrate moves from traditional to modernized
pathway when a set of conditions is met, and that the migration is implemented
as a new adapter. UIAO_205 §4 is the gate sequence that determines when those
conditions are satisfied; §4.1 is the ceremony that makes the migration
official.

### 6.4 With FINDING-PGM-001 (FedRAMP 20x Moderate Pilot)

FINDING-PGM-001 is the tracking document for the 20x pilot. UIAO_205 references
it as the artifact store for: the dry-run run ID (§4.7), open scope disputes
(§5), and the migration ceremony record. FINDING-PGM-001 §5 (added as part of
this spec) is the "registration record" section where these artifacts land.

---

## 7. Validation and acceptance

UIAO_205 moves from Draft to Current when:

1. At least one agency deployment has completed the §4 gate sequence and
   filed a FedRAMP 20x pilot application using the §5 submission package.
2. FedRAMP PMO has accepted the application (Gate G-6 satisfied).
3. The migration ceremony record (§4.1) is committed to FINDING-PGM-001 §5 with
   all three sign-offs.

Until condition 1 is met, this spec is a pre-operational template. Sections
may be updated as the FedRAMP 20x pilot program publishes additional guidance
(particularly RFC-0010, which is not yet published at time of writing).

---

## 8. References

### UIAO canon

- [ADR-106 — FedRAMP 20x Integration decision](../adr/adr-106-fedramp-20x-integration.md)
- [ADR-061 — FedRAMP CR26 Catalog Vendoring](../adr/adr-061-fedramp-cr26-catalog-vendoring.md)
- [UIAO_133 — FedRAMP 20x Integration spec (substrate-internal)](./fedramp-20x-integration.md)
- [UIAO_138 — FedRAMP 3PAO Evidence Interface (assessor-facing)](./fedramp-3pao-evidence-interface.md)
- [UIAO_137 — FedRAMP CR26 KSI Mapping](./fedramp-cr26-ksi-mapping.md)
- [UIAO_185 — System Security Plan Template](./system-security-plan.md)
- [UIAO_139 — FedRAMP GCC-Moderate Realtime Boundary Impact](./fedramp-gcc-moderate-realtime-boundary-impact.md)
- [FINDING-PGM-001 — FedRAMP 20x Moderate Pilot active](../../../../docs/findings/fedramp-20x-moderate-pilot.md)

### FedRAMP primary sources

- [FedRAMP 20x Overview](https://www.fedramp.gov/20x/)
- [FedRAMP 20x Documentation](https://www.fedramp.gov/docs/20x/)
- [RFC-0005 Minimum Assessment Scope Standard](https://www.fedramp.gov/rfcs/0005/)
- [RFC-0006 Phase One KSIs](https://www.fedramp.gov/rfcs/0006/)
- [RFC-0014 Phase Two KSIs](https://www.fedramp.gov/rfcs/0014/)
- [RFC-0024 Rev5 Machine-Readable Packages](https://www.fedramp.gov/rfcs/0024/)
