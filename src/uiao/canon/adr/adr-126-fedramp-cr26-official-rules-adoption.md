---
id: ADR-126
title: "FedRAMP CR26 Official Rules Adoption — Authority Upgrade and Coexistence with Palladium OSCAL Snapshot"
status: accepted
date: 2026-07-01
deciders:
  - canon-steward
  - governance-steward
  - Michael Stratton
supersedes: []
amends:
  - ADR-061
related_adrs:
  - ADR-043
  - ADR-061
  - ADR-106
canon_refs:
  - UIAO_133
  - UIAO_207
triggers:
  - "ADR-061 §Re-evaluation trigger #1"
related_issues:
  - WhalerMike/uiao#355
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-126-fedramp-cr26-official-rules-adoption.html
---

# ADR-126: FedRAMP CR26 Official Rules Adoption

## Status

**ACCEPTED — 2026-07-01.** Fires ADR-061 re-evaluation trigger #1:

> *FedRAMP publishes an official machine-readable CR26 catalog. At that point D1
> (authority posture) is reconsidered: the official catalog likely supersedes the
> Palladium snapshot, and the reference folder is repointed.*

On 2026-06-25, FedRAMP published the **Consolidated Rules for 2026** as a stable
release via `github.com/FedRAMP/rules`, version `2026.06.24.01`. This is the
official machine-readable rules surface anticipated by ADR-061 trigger #1. The
official JSON was retrieved and vendored under
`src/uiao/canon/compliance/reference/fedramp-cr26/official/` on 2026-07-01
(SHA-256: `48d1fb4c1674c15f1a966f94c9f519b246af377d2ff51845083131ad99da8c60`).

## Context

### The triggering event

FedRAMP's June 25, 2026 announcement ("Propelling Change: FedRAMP Launches
Consolidated Rules for 2026") formally launched CR26 as the mandatory framework
for all FedRAMP stakeholders effective 2027-01-01. The official machine-readable
representation is `fedramp-consolidated-rules.json` in the `FedRAMP/rules`
GitHub repository. This is a US Government work and is in the public domain (17
U.S.C. § 105).

### What the official JSON contains

The official JSON (`version: 2026.06.24.01`, `last_updated: 2026-06-24`) has
four top-level sections:

- **FRD** — 75 defined terms organized by tag (Stakeholder, Certification,
  Vulnerability, Assessment, Incident, Significant Changes, Information
  Resource, Accounts, Customer Effect).
- **FRR** — 17 rule categories, 29 total variants across `all`/`20x`/`rev5`
  paths, each specifying requirements for providers, agencies, assessors, and
  FedRAMP itself. Categories: AFC, AGU, CCM, CDS, CMU, CPO, FRC, IEC, IVV,
  MAS, MKT, REC, SCG, SCN, SDR, VDR, VER.
- **KSI** — 10 themes, 46 indicators total. Each indicator carries a name,
  statement, and list of NIST SP 800-53 control anchors. Themes: CED (1), CMT
  (4), CNA (8), IAM (6), INR (3), MLA (5), PIY (5), RPL (4), SCR (2), SVC (8).
- **CTL** — 14 NIST control families with control-level metadata (AC, AU, CA,
  CM, CP, IA, IR, MA, PS, RA, SA, SC, SI, SR).

### How this differs from the Palladium snapshot

The Palladium snapshot (`c31eb04`) under ADR-061 is an *OSCAL conversion* of an
earlier CR26 Public Preview — catalog, profile shells, and mapping collection in
OSCAL XML/JSON/YAML format. The official FedRAMP JSON is the *rules source
itself* — the canonical text, not an OSCAL derivative. They serve complementary
roles:

| Source | Format | Authority | Role in uiao |
|---|---|---|---|
| `FedRAMP/rules` JSON (this ADR) | Rules JSON (FRD/FRR/KSI/CTL) | **Official** — US Government | Rules text, KSI statements, definitions, timeframes |
| Palladium OSCAL snapshot (ADR-061) | OSCAL catalog/profile/mapping | Unofficial (CC0 1.0) | OSCAL-format KSI catalog; CR26 ↔ SP 800-53 rev5 mapping |

## Decision

### D1 — Authority posture: official JSON is the primary rules authority

The official `FedRAMP/rules` JSON is now the **primary authority** for CR26 rules
text, KSI indicator definitions, FRR requirements, and FRD definitions. Any
future conflict between the official JSON and the Palladium OSCAL snapshot is
resolved in favor of the official JSON.

The Palladium snapshot remains in place for OSCAL catalog/profile/mapping
consumption per ADR-061 D3 until FedRAMP publishes an official OSCAL derivation
(which ADR-061 trigger #1 also anticipated, but is not yet published as of
2026-07-01). ADR-061's authority posture classification of the Palladium snapshot
as "reference, not canon" is unchanged.

### D2 — Storage and update discipline for the official JSON

The official JSON lives at:

```
src/uiao/canon/compliance/reference/fedramp-cr26/official/fedramp-consolidated-rules.json
```

Unlike the Palladium snapshot (which uses immutable sibling directories per ADR-061
D2), the official JSON uses **in-place versioned updates**:

- The `version` field inside the JSON (`info.version`) is the immutability
  identifier. It is quoted verbatim in `PROVENANCE.md` and `SHA256SUMS`.
- When FedRAMP publishes a new version, the file is updated in-place in a single PR
  that also updates `PROVENANCE.md` and `SHA256SUMS`. No sibling-directory
  rotation is required because the official JSON is a US Government work (public
  domain), not a third-party contribution requiring the CC0-gate of ADR-061 D2.
- PRs that update `official/fedramp-consolidated-rules.json` trigger the
  `fedramp-cr26-catalog` conformance adapter run (ADR-061 D3) to surface
  `DRIFT-SCHEMA` and `DRIFT-PROVENANCE` findings.

### D3 — KSI anchor surface

The official JSON's `KSI` section is now the **canonical KSI ID and statement
surface** for `fedramp:ksi-mapping-source` props in emitted OSCAL artifacts.

- The 46 official KSI indicator IDs (`KSI-{theme}-{code}`) replace the
  Palladium-derived IDs as the navigational anchor in emitted props.
- The UIAO KSI rule scaffolds in `src/uiao/ksi/rules/` (KSI-001 through KSI-014)
  carry forward-mapping annotations to official KSI IDs per UIAO_207.
- The `fedramp-cr26-catalog` adapter (ADR-061 D3) is updated to read from
  `official/fedramp-consolidated-rules.json` for KSI ID resolution, falling back
  to the Palladium snapshot for OSCAL catalog shape until an official OSCAL
  derivation is available.

### D4 — FRR rules mapped to existing UIAO capabilities

The 17 FRR rule categories are mapped to existing UIAO capabilities in UIAO_207.
No new adapter or CLI command is required in this PR; UIAO_207 serves as the
assessment record. Capability gaps identified in UIAO_207 are tracked as
findings.

### D5 — Effective date tracking

The CR26 effective dates are:

| Milestone | Date |
|---|---|
| Optional adoption opens | 2026-07-04 |
| 20x Class B/C pipelines open | 2026-08-31 |
| **Mandatory for all stakeholders** | **2027-01-01** |
| No new Rev5 certifications | 2027-06-11 |

The 2027-01-01 mandatory date is the substrate's hard compliance target for all
CR26-governed capabilities. UIAO_207 tracks gap-closure items against this date.

## Consequences

### Positive

- **Official authority replaces informal dependency.** uiao's KSI anchoring
  surface now points to a US Government public-domain source, eliminating the
  trust-shape concern (ADR-061 Negative §"Trust shape") entirely.
- **46 official KSI IDs are stable.** The `2026.06.24.01` launch version is
  the mandated framework — these IDs are no longer draft.
- **FRR rules surface is complete.** All 17 categories with MUST/SHOULD/MAY
  requirements, timeframes, and class-differentiated variants are now vendored
  for offline consumption.

### Negative / risks

- **In-place update vs. sibling-directory immutability.** The official JSON
  uses version-in-place rather than ADR-061's sibling-directory pattern.
  Reviewers must read `PROVENANCE.md` and `SHA256SUMS` to confirm version
  identity. Mitigation: the version field is checked by the conformance adapter.
- **Palladium OSCAL/official JSON divergence.** The Palladium snapshot was
  generated from a Public Preview; the official JSON may have diverged in KSI
  IDs or counts. The `fedramp-cr26-catalog` adapter's drift surface detects this.
  Mitigation: UIAO_207 §4 documents the comparison between the two sources.
- **No official OSCAL publication yet.** FedRAMP has not yet published an official
  OSCAL catalog derived from this JSON. The Palladium snapshot remains the only
  OSCAL surface. This is tracked as a re-evaluation trigger (see §Re-evaluation
  triggers below).

## Re-evaluation triggers

1. **FedRAMP publishes an official OSCAL CR26 catalog.** The Palladium snapshot
   is then retired per ADR-061 D2 (one-cycle retention) and the official OSCAL
   source takes its place under `snapshot/<sha>/`.
2. **CR26 is versioned to `2027.xx.xx.xx` or later.** A major version change
   re-opens D2 (update discipline) and D3 (KSI anchor surface) to confirm the
   in-place update pattern remains appropriate.
3. **The FedRAMP/rules repository changes license.** The public-domain posture
   in D2 depends on the US Government authorship; a relicensing event (e.g., GSA
   adding a CC-BY restriction) forces re-evaluation.

## Related

- [ADR-061 — FedRAMP CR26 Catalog Vendoring](./adr-061-fedramp-cr26-catalog-vendoring.md) (amended by this ADR)
- [ADR-106 — FedRAMP 20x Integration](./adr-106-fedramp-20x-integration.md)
- [ADR-043 — FedRAMP RFC-0026 CA-7 Integration](./adr-043-fedramp-rfc-0026-ca7-integration.md)
- UIAO_207 — FedRAMP CR26 Rules Assessment
- UIAO_133 — FedRAMP 20x Integration spec
