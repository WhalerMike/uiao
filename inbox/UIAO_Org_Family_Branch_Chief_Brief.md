# UIAO and the Org Family — Two-Page Branch Chief Brief

> **Draft — inbox staging.** Not canon. Prepared 2026-09-01 against
> `WhalerMike/uiao` @ v0.7.1 (pre-1.0). Published companion: a formatted
> two-page HTML brief generated from this source.

## Bottom line

**UIAO** — Unified Identity-Addressing-Overlay Architecture — is a governance
substrate: one machine-checked source of truth for organizational identity,
addressing, evidence, and policy. Four pillars stand on it. **OrgPath** governs,
**OrgComp** proves federal compliance, **OrgMod** modernizes, and **OrgLink**
governs the seams between organizations. Each is adoptable on its own or with
the others. The canon, code, and documentation are real and continuously
integration-tested; *live-tenant validation is the outstanding gap*. The FedRAMP
20x machine-readable-evidence mandate on 1 January 2027 is what makes the timing
non-discretionary.

## The substrate — UIAO

UIAO's premise is that a governance claim is only worth as much as its
provenance. Every claim has exactly one canonical source; everything else is a
pointer citing the document ID and version it derives from. Machines enforce
that, not reviewers.

- **Canon.** 123 registered governance documents and 141 architecture decision
  records under version control, append-only with supersession markers.
- **Schema-first.** 40 JSON Schemas validate every registry, manifest, and
  document header in CI — a malformed governance edit fails the build instead of
  reaching production.
- **Adapters.** 66 registered: 28 change-making and 38 read-only, spanning Entra
  ID, M365, Intune, ServiceNow, CyberArk, Palo Alto, Infoblox, BlueCat,
  Terraform, CISA ScubaGear, and the federal attribute services (SAM, E-Verify,
  OFAC, DCSA clearance, USCIS, VA).
- **Drift as a first-class output.** Five named classes — schema, semantic,
  provenance, authorization, identity — scanned, classified, and exit-coded for
  CI rather than left for someone to notice.
- **Evidence.** Emits OSCAL (SSP, assessment plan and results, POA&M) and
  FedRAMP KSI packages — the machine-readable formats 20x requires — with a
  traversable provenance graph behind every assertion.
- **Surface.** One installable Python package, 89 CLI commands across 27
  domains, an optional REST API, ~80,000 lines of code, 297 test modules, 50+ CI
  workflows.

## Pillar I — OrgPath governs

OrgPath gives every user, device, and service principal a structured, governed
address instead of a position in a hand-maintained OU tree. Fifteen semantic
facets are stamped into Entra ID extension attributes: Region, Department,
Division, Role, CostCenter, Classification, HireDate, TermDate, ClearanceLevel,
AccountType, AdminTier, DeviceType, Environment, one reserved slot, and a
derived canonical path in slot 15 —

```
Region=NCR|Department=IT|Division=CyberOps|
```

That derived path is recomputed from the hierarchy facets on every write and
never hand-authored; a stored value that disagrees with the recomputation is
flagged as semantic drift.

**What it buys:** dynamic group membership, Administrative Unit delegation,
Conditional Access targeting, and Azure Policy scoping all compose against facts
with closed enumerations, so access follows the org chart automatically and
every membership decision is explainable. Companions: **OrgTree**
(organizational hierarchy) and **LocPath** (location and duty station).

## Pillar II — OrgComp proves

Federal Organization Compliance is an eleven-volume, sixty-book FedRAMP Moderate
program written generic to any agency: transport, data platform, security
operations, governance, training, implementation, ServiceNow automation,
multi-cloud DDI, and day-2 architecture. Its thesis is that federal compliance
debt is an architectural pattern mismatch, not a resource shortage — the
controls required under EO 14028, OMB M-22-09, TIC 3.0, and the FedRAMP 20x
Consolidated Rules cannot be satisfied by a perimeter architecture at any
budget.

It is deliberately **engine-neutral**, speaking only to an open Evidence &
Authorization Contract, so it stands alone without the rest of UIAO. It ships as
browsable pages, per-volume Word bundles, a two-track training program with labs
and rubrics, and deployable kits — a ServiceNow compliance application and a
day-2 operations catalog. Every federal date it cites resolves to a gated
registry re-verified against the issuing agency on a schedule; a stale citation
goes red in CI.

## Pillar III — OrgMod modernizes

An assessment engine enumerates what the legacy estate actually does before
anyone decides what replaces it; vendor-neutral adapter interfaces then cover
directory, device, PKI, RADIUS, DNS/DHCP/IPAM, and overlay-adjacent control
surfaces. The leading worked path is Active Directory to Entra ID, where eight
adapter interfaces stand in for the eleven roles AD quietly performs today.

It also carries GPO parse-and-crosswalk onto the governed path, Intune and Azure
Arc modernization for endpoints and servers, an HR-driven joiner/mover/leaver
pipeline against Federal HR 2.0 (Oracle Core HCM), and a worked SQL Server
migration off Windows Authentication. Changes OrgMod makes land on the plane
OrgPath governs, and the evidence they emit is what OrgComp proves.

## Pillar IV — OrgLink connects

Elevated in July 2026, OrgLink governs the seams between organizations —
reciprocity packs, HR inbound provisioning, gateway federations, reporting
egress — as schema-validated, drift-scanned link objects. Registry and scanners
are operational; the narrative shelf is one work deep.

## The common law — MACD-R

Every Move, Add, Change, Deletion, and Reset travels the same five-clause path:

1. It **originates with the designated source of truth** for its object class.
2. It carries an **authoritative authorization**.
3. It executes under **least privilege with just-in-time elevation**.
4. It **closes with provenance** — no closure counts unless it carries its proof.
5. It **emits verified evidence automatically** to continuous monitoring.

The registry answering clause 1 covers non-human classes too — service accounts,
devices, AI systems, declared infrastructure — each anchored to a human owner in
the HR system of record. An ownerless principal is an orphan finding, not a
governed identity.

## Where it actually stands (v0.7.1)

The program publishes its own gap map rather than a maturity claim.

| Layer | State | Evidence |
|---|---|---|
| Canon & schema governance | Operating | 123 documents, 141 ADRs, 40 schemas; last substrate walk clean except 3 informational findings |
| Code & CLI | Operating | 89 commands, 297 test modules, full suite blocking in CI |
| Evidence pipeline | Working | OSCAL and KSI generation end-to-end; not yet exercised against an accredited tenant |
| Adapter conformance | Partial | **No adapter has completed live-tenant validation.** Three tier-1 workflows exist with stub test bodies pending credentials |
| Documentation | Operating | 1,362 published pages, link-checked and provenance-gated |
| Production adoption | None | No production adopters at the current OrgPath model's ratification |
| Deferred by decision | Specified | High availability, performance engineering, collector interface — specified, deliberately deferred |

## The clock

| Date | What happens |
|---|---|
| 21 Sep 2026 | FIPS 140-2 validations move to the NIST CMVP Historical List |
| 17 Nov 2026 | FedRAMP Rev5 Ready status must convert to a Certification |
| 07 Dec 2026 | BOD 26-04 remediation timelines in force; VDR/VER adoption mandatory |
| 01 Jan 2027 | **CR26 mandatory — all continuous-monitoring evidence must be machine-readable KSI** |

BOD 25-01's continuous SCuBA assessment obligation is already in force and its
scope is living, not a static snapshot. The FedRAMP 20x Class B and C pipelines
opened 31 August 2026. Dates trace to
`docs/customer-documents/orgcomp-series/orgcomp-authority-deadlines.yml`, the
gated registry that is SSOT for every federal date the series cites.

## What this asks of leadership

- **Endorse or redirect the doctrine.** This work has not been reviewed or
  endorsed by OIS or the CIO. That review is a prerequisite to any build or
  procurement commitment — the authoring team does not hold that authority.
- **Close the live-tenant gap.** Access to a non-production tenant is the single
  largest credibility gap in the program; everything else is testable without it.
- **Choose the adoption shape.** The pillars are independent by design. One
  pillar is a legitimate answer — OrgComp in particular stands alone.

## Provenance

Derived from: `AGENTS.md`; `src/uiao/canon/UIAO_151_OrgPath_Codebook.md`
(ADR-078 / ADR-127 Model C); `src/uiao/canon/adr/adr-131-academy-org-family-umbrella.md`;
`src/uiao/canon/adr/adr-134-orglink-pillar-elevation.md`; `docs/orgpath/index.qmd`;
`docs/orgmod/index.qmd`; `docs/customer-documents/orgcomp-series/index.qmd` and
`Vol_0_Book_00a_OrgComp_Executive_Brief.qmd`; `docs/docs/substrate-status.qmd`;
`orgcomp-authority-deadlines.yml`; and live counts from `uiao substrate walk`
plus the canon registries at commit time.
