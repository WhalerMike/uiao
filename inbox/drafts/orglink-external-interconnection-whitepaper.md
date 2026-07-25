# Governed Links: External Interconnection, the Federal Identity Mesh, and SSOT with Due Process

> **Status: DRAFT — inbox scratch surface. Not canon. Not published.**
> Authored 2026-07-25 as the seed narrative for the OrgLink candidate
> pillar (ADR-132 / UIAO_145). Publication is deferred until the OrgLink
> surface is developed, per ADR-132 D6; when it publishes, it is a
> candidate first work toward the D3 elevation conditions.
>
> Provenance note: external facts below are cited inline to their
> sources per the ADR-000 sourcing rule. Statistics are point-in-time
> as of mid-2026 and must be re-verified before publication.

## 1. The claim

Every consequential exchange between organizations — an agency consuming
another agency's HR feed, a hospital billing a health plan, a bank
verifying an SSN, a state checking a voter's death record — already runs
on an implicit object: **the link**. Two parties, a declared authority
relationship over some data domain, an interface, and an agreement
artifact that makes the exchange lawful. The United States federal
ecosystem operates thousands of these links today. What it does not have
is a governance substrate that treats them as first-class, drift-detected,
provenance-anchored objects.

This paper makes three arguments:

1. **The link pattern is already proven and already statutorily
   mandated** — the federal identity-verification mesh runs on it, and
   the Computer Matching and Privacy Protection Act has required a
   written-agreement regime for eligibility matching since 1988.
2. **Single-source-of-truth (SSOT) discipline over that mesh is a real
   anti-fraud and anti-corruption instrument** — and an honest accounting
   of its limits makes the case stronger, not weaker.
3. **The corrective is federated, provenance-anchored, contention-detected
   SSOT — not centralization** — and a governance substrate that
   registers links, renders their compliance evidence, and surfaces
   authority disputes as detectable drift is the practical form of it.

The UIAO substrate's Link object class (UIAO_145, established under
ADR-132) is the org-altitude implementation of that corrective: it
governs *one organization's* external interconnections. This paper is
the over-horizon narrative — what the same discipline looks like at
ecosystem scale, and why the org-altitude object is the right first
brick.

## 2. The federal identity mesh that already exists

The U.S. deliberately has no single national identity database. What it
has instead is a **mesh of attribute-scoped authorities**, each the
source of truth for a narrow domain, each exposing verification links to
the others:

| Authority | SSOT for | Exchange services |
|---|---|---|
| Social Security Administration | SSN ↔ name ↔ DOB; death | SVES/SOLQ (states), SSOLV (motor-vehicle agencies), CBSV/eCBSV (consent-based, private sector), Death Master File ([SSA data exchange](https://www.ssa.gov/dataexchange/)) |
| State vital-records offices | Birth and death *events* | EVVE — real-time verification against the issuing jurisdiction's records ([NAPHSIS](https://www.naphsis.org/evve/)) |
| DHS / USCIS | Immigration status; work eligibility | SAVE (benefits/licensing agencies), E-Verify (employers) |
| State motor-vehicle agencies | License identity + photo | SSOLV front-end; State-to-State (S2S) one-driver-one-license deduplication ([AAMVA](https://www.aamva.org/technology/systems/driver-licensing-systems/s2s-frequently-asked-questions)) |
| CMS | Program eligibility | Federal Data Services Hub — one query fans out to SSA, DHS, and IRS for Medicaid/marketplace determinations; PARIS catches cross-state dual enrollment |
| Treasury | Payment eligibility | Do Not Pay portal — pre-payment screening against death and exclusion data |
| HHS / OCSE | Wages and new hires | National Directory of New Hires |
| ERIC (state consortium) | Voter-roll hygiene | Member states cross-match voter, motor-vehicle, and SSA death data on a 60-day cycle |

Two structural facts matter:

**Everything joins on SSA.** The SSN is the de facto join key of the
mesh; SSA's verification services are the most-consumed links in the
system. This is why every downstream integrity property inherits SSA's
data quality — for better and worse.

**REAL ID is a derived credential, not a new root.** A REAL ID-compliant
license exists because, at issuance, the state *consumed the mesh*:
SSN verified against SSA (SSOLV), lawful status against DHS (SAVE),
uniqueness against other states (S2S), increasingly birth records
against EVVE. Enforcement began May 7, 2025
([TSA](https://www.tsa.gov/realid/realid-faqs)); mobile driver's
licenses extend the same chain under the 6 CFR Part 37 waiver framework
([eCFR](https://www.ecfr.gov/current/title-6/chapter-I/part-37)).
"Anchor on the latest REAL ID license" therefore means "leverage a
credential whose issuance already performed the multi-SSOT join" — a
strong dedup signal precisely because it is downstream of the mesh, and
only as strong as the links it chains through.

## 3. The statutory precedent: links already require agreements

The mesh's exchanges are not informal. The **Computer Matching and
Privacy Protection Act of 1988** requires, for computerized eligibility
matching between agencies: a written matching agreement, a cost-benefit
analysis, Data Integrity Boards in the participating agencies, Federal
Register publication, and — critically — independent verification plus
30 days' notice before any adverse action against an individual
([CRS R47325](https://www.congress.gov/crs-product/R47325);
[DOJ CMA inventory](https://www.justice.gov/opcl/computer-matching-agreements-and-notices)).

Read as architecture, the CMPPA is a **legally mandated link registry
with due process built in**. Every element of the UIAO Link object —
counterparty, purpose, data elements, direction, agreement artifact,
review cycle, oversight — has a named counterpart in a CMA. NIST SP
800-53's CA-3 (Information Exchange) requires the same object class for
system interconnections generally; HIPAA's business associate
agreements, CJIS management control agreements, and IRS Publication 1075
safeguard agreements are the same shape wearing regime-specific dress.

The gap is administrative, not doctrinal: these link-objects live as
PDFs, Federal Register notices, and document-library folders. They are
not queryable, not drift-detected, not provenance-anchored, and their
review clocks are enforced by memory and audit finding rather than by
machine.

## 4. SSOT as an anti-fraud and anti-corruption instrument

The integrity case is quantitative. GAO estimates federal improper
payments at roughly a quarter-trillion dollars in a single recent fiscal
year, cumulatively trillions since tracking began; pandemic-era
unemployment-insurance fraud alone is estimated in the $100B+ range.
The recurring vectors map directly onto mesh gaps:

- **Payments to the deceased** — death-data coverage gaps between state
  vital records, SSA's file, and paying agencies.
- **Dual enrollment** — the same person enrolled in two states'
  programs; PARIS exists because this happens at scale.
- **Synthetic identity** — fabricated identities exploiting the seams
  between SSA, IRS, and state records, where no single authority sees
  the whole picture.
- **Duplicate registration** — one person on multiple states' rolls;
  ERIC's cross-state matching exists precisely to catch it.

The common denominator: **fraud and corruption live in reconciliation
gaps** — the space where two systems disagree and no one is accountable
for the difference, where "the paperwork was lost" is unfalsifiable.
SSOT discipline with verified links shrinks exactly that space, and
provenance makes every eligibility decision traceable to an
authoritative record, a timestamp, and an agreement. Integrity becomes
auditable instead of asserted.

## 5. The honest limits — and why they strengthen the design

An SSOT program that ignores its failure modes becomes one. Four limits
are load-bearing:

1. **Error amplification.** Matching on name/DOB produces false
   positives and negatives; the Death Master File erroneously marks
   thousands of living people dead each year. In a naive SSOT, one bad
   record propagates everywhere at machine speed. This is why the
   CMPPA's independent-verification-and-notice requirement is not red
   tape — it is a drift gate expressed as law, and any technical SSOT
   must reproduce it structurally.
2. **Coverage gaps.** REAL ID is not universal — non-drivers, the
   elderly, religious exemptions; TSA maintains alternative
   identity-verification paths for exactly this reason. A hard REAL ID
   key on any entitlement excludes eligible people alongside fraudsters.
   Derived credentials are dedup *signals*, never sole keys.
3. **The links are the fragile part.** The authorities are stable; the
   *agreements* churn. Consortium memberships lapse for political
   reasons (ERIC's membership changes are the proof case), CMAs expire,
   interconnection reviews slip. The governance object that most needs
   SSOT treatment is the link itself.
4. **Federalism is a feature to design for, not around.** States own
   vital records, licenses, and voter rolls by constitutional design.
   Any workable integrity architecture is federated: per-attribute
   authority, reciprocal verification, no single database to capture.

Which yields the thesis: **the anti-corruption property comes from
provenance-anchored, contention-detected, federated SSOT — not from
centralization.** A single national database would concentrate exactly
the corruption surface it claims to remove (whoever controls the
database controls the truth). A mesh of declared authorities whose
*links* are governed objects — registered, agreement-backed,
review-clocked, with every authority dispute surfacing as a detectable
contention event rather than a silent overwrite — delivers the
integrity without the capture risk, and reproduces the CMPPA's due
process as architecture.

## 6. What the substrate already operationalizes (org altitude)

UIAO implements the corrective at the altitude where it is deployable
today: one organization's external boundary. As of ADR-132 Phases 1–2:

- **The Link object class** (UIAO_145): counterparty taxonomy (federal
  agency through public, with regulated-commercial and consortium
  classes), direction, declared **SSOT stance** per link — wired to the
  substrate's `DRIFT-SSOT-CONTENTION` class (ADR-074), so a counterparty
  asserting authority over data the org stewards is a detected event.
- **The link registry** as a schema-validated pair registry, holding
  metadata about exchanges — never payload, never entity resolution
  (ADR-132 D1 boundaries).
- **Evidence rendered from registry state**: CA-3/CA-9/SA-9/AC-20
  inventories generated deterministically, retiring the
  document-library-pointer pattern; Link nodes on the Evidence Graph;
  `SHOW LINKS` in the compliance query language; an
  external-interconnections panel on the ConMon dashboard.
- **The link-gap scanner**: unrecorded agreements, unanchored
  artifacts, past-due reviews, regime overlays with no active
  conformance pack, and control narratives that claim agreements the
  registry cannot produce — each a computable finding. The CA-3
  annual-review parameter is machine-enforceable for the first time.
- **Regime overlays as vertical packs** (ADR-085/ADR-129): HIPAA
  (via NIST SP 800-66r2), GovRAMP — formerly StateRAMP — reciprocity
  (riding the UIAO_140 single-ATO model), CJIS, IRS 1075, GLBA — each a
  conformance pack that binds at the link, not a fork of the engine.

Every mechanism above generalizes: a Data Integrity Board's CMA
inventory, an agency's CA-3 interconnection portfolio, a state's
verification-service links, a hospital system's BAA estate — all are
link registries waiting to be governed. The org-altitude object is the
same object.

## 7. What this paper is not

Boundaries, stated plainly because the subject invites overreach:

- **Not an entity-resolution system.** The substrate governs
  agreements, flows, and authority stances. It does not match or
  deduplicate people; matching quality remains the authorities' domain.
- **Not a national identity proposal.** The analysis argues *against*
  centralization; the design object is the governed link between
  existing authorities.
- **Not an eligibility policy position.** Who should receive what is
  legislation's question. This architecture makes whatever the answer
  is *auditable* — and protects eligible people from silent error
  through structural due process.
- **Not federal-only.** The same link discipline serves a hospital
  network's payer exchanges or a bank's verification services; the
  federal mesh is the worked example because its precedents (CMPPA,
  CA-3) are public.

## 8. Sources

- SSA data exchange services: https://www.ssa.gov/dataexchange/ ; CBSV: https://www.ssa.gov/cbsv/
- NAPHSIS EVVE: https://www.naphsis.org/evve/
- AAMVA S2S: https://www.aamva.org/technology/systems/driver-licensing-systems/s2s-frequently-asked-questions ; SSOLV: https://www.aamva.org/technology/systems/verification-systems/ssolv
- REAL ID: https://www.tsa.gov/realid/realid-faqs ; 6 CFR Part 37: https://www.ecfr.gov/current/title-6/chapter-I/part-37 ; mDL waiver rule: https://www.federalregister.gov/documents/2024/10/25/2024-23881/minimum-standards-for-drivers-licenses-and-identification-cards-acceptable-by-federal-agencies-for
- CMPPA: CRS R47325: https://www.congress.gov/crs-product/R47325 ; DOJ CMA inventory: https://www.justice.gov/opcl/computer-matching-agreements-and-notices ; SSA model CMPPA agreement: https://www.ssa.gov/dataexchange/documents/2013%20CMPPA%20State%20Model.pdf
- CMS Federal Data Services Hub (explainer): https://responsivegov.org/research/the-federal-data-services-hub-the-eligibility-engine-powering-medicaid-health-insurance-marketplaces/ ; dual enrollment: https://www.cms.gov/files/document/cpi-dual-enrollment-fast-facts.pdf
- ERIC: https://en.wikipedia.org/wiki/Electronic_Registration_Information_Center
- NIST SP 800-66r2 (HIPAA Security Rule guidance): https://csrc.nist.gov/pubs/sp/800/66/r2/final
- Internal: ADR-132, UIAO_145, UIAO_140, ADR-074, ADR-085, ADR-129, CHARTER-003 FILE 4 (inter-agency source-of-authority doctrine).
