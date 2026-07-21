---
adr_id: adr-130
title: "Non-Human SSOT Registry — Class SSOT Designations and the Human-Anchor Rule"
status: PROPOSED
decided: 2026-07-21
deciders: Michael Stratton
updated: 2026-07-21
next_review: 2027-01-21
review_trigger: the MACD-R Lifecycle Doctrine (OrgComp Vol 0 Book 00) is substantially revised; the sailpoint-machine-identity slot promotes from reserved to active; ADR-016 (human JML) or ADR-114 (AI JML) is substantially revised; a class SSOT designated here is re-platformed; a new non-human object class enters governance scope
impact: "Designates, per object class, the single source of truth that originates every non-human Move, Add, Change, Deletion, and Reset — and states the Human-Anchor Rule: every non-human item's ownership chain terminates in a human resolvable in the HR SSOT, or the item is orphaned and unauthorized by construction. Extends ADR-016 (human JML) and ADR-114 (AI JML) into a complete origination map; makes directories, CMDBs, and consoles projections by definition; names orphan detection as a drift class."
supersedes: null
superseded_by: null
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-130-nonhuman-ssot-registry.html
---

# ADR-130: Non-Human SSOT Registry — Class SSOT Designations and the Human-Anchor Rule

## Status

**PROPOSED** — 2026-07-21.

## Context

The MACD-R Lifecycle Doctrine (OrgComp Vol 0 Book 00, ratified into the
published corpus 2026-07-21) requires that every operational change — every
Move, Add, Change, Deletion, and Reset — **originates with the SSOT**
(clause 1) and **carries an authoritative authorization in the path**
(clause 2, resolved from SSOT-derived owner/manager routing).

For human identities both clauses are answered: ADR-016 designates the HR
system of record as the SSOT and defines the joiner/mover/leaver events it
fires. For non-human items the answers existed only in fragments:

- **IPAM/DDI** is designated authoritative for naming and addressing, and
  the naming-plane join key is designated authoritative asset identity
  (the OrgComp Closure Necessity Doctrine; CM-8; BOD 23-01). The CMDB is
  explicitly a projection.
- **AI systems** have a designated SSOT (the OMB Annual AI Use Case
  Inventory, ADR-112) and a full JML lifecycle (ADR-114 / UIAO_197).
- **Non-employee humans** have a designated registry (the NERM-class
  non-employee CIR, ADR-055 / ADR-059).
- **Service accounts** have a discovery scan (Spec3-D1.1
  Get-ServiceAccountScan) — which measures the estate but originates
  nothing. A scan is not a source of truth; it can only measure drift
  from one.

No designation existed for service accounts, workload identities, and app
registrations; devices as lifecycle objects; applications; or declared
infrastructure state. For those classes, clause 1 of the lifecycle doctrine
was unanswerable — and clause 2 unresolvable, because nothing recorded who
owns the item.

## Decision

### D1 — The class SSOT registry

Exactly one SSOT is designated per object class. The SSOT is where a MACD-R
operation for that class **originates**; everything downstream — directory
objects, CMDB records, management-console state — is a **projection** whose
divergence from the SSOT is drift, never an alternative truth.

| Object class | Designated SSOT | Projections (never truth) |
|---|---|---|
| Employees | HR system of record (ADR-016) | Directory accounts, mailboxes |
| Non-employee humans (contractors, vendors, partners) | Non-employee registry — NERM-class CIR (ADR-055 / ADR-059) | Guest accounts, sponsored credentials |
| Network names, addresses, segments | IPAM/DDI | DNS zone dumps, spreadsheets, scanner output |
| Assets / components (CM-8) | The authoritative inventory keyed on the naming-plane join key | CMDB (reconciled projection), per-stack consoles |
| Devices / endpoints (lifecycle) | Asset-lifecycle (ITAM/procurement) registry, keyed to the join key | MDM enrollment state (Intune/Autopilot — enforcement, not truth) |
| Service accounts, workload identities, app registrations | **The Non-Human Identity (NHI) Registry** — new designation, this ADR | Directory service principals, app registrations, key vault entries |
| AI systems | OMB Annual AI Use Case Inventory (ADR-112), JML per ADR-114 | Deployment manifests, model endpoints |
| Applications | Application portfolio registry | App registrations, service catalog entries |
| Certificates | The issuance ledger (CA + certificate transparency of the PKI plane) | Local cert stores, binding configs |
| Infrastructure declared state | The IaC repository (declared state in version control) | Deployed resources (estate); consoles |
| Organizational structure / physical location | OrgTree codebook / LocPath registry (ADR-035..040, ADR-102) | Directory OU trees, AD site topology |

The **NHI Registry** is the genuinely new designation: every service
account, workload identity, and app registration exists in the registry
*first* — with purpose, scope, expiry, and owner — and the directory object
is provisioned from it. A service principal with no registry record is an
orphan (D4). The `sailpoint-machine-identity` slot reserved by ADR-059 is
the conformance surface for this registry; the registry itself is a
data-model designation, not a product selection.

### D2 — The Human-Anchor Rule

**Every non-human item anchors to a human owner resolvable in the HR
SSOT.** The ownership chain of any service account, device, application,
certificate, AI system, or infrastructure module terminates in a person
(with a deputy path for continuity), or the item is **orphaned**: MACD-R
clause 2 cannot resolve an approver for it, so no operation against it can
carry an authoritative authorization — it is unauthorized by construction,
and unattestable. The HR SSOT is therefore not merely the human SSOT; it is
the **root of the ownership chain for every governed object**. A leaver
event against an owner triggers ownership transfer for everything anchored
to them — the leaver's non-human estate is part of their offboarding
surface (ADR-016 extended; ADR-114 §deprovisioning is the AI-class worked
example).

### D3 — One SSOT per class

Split-brain is drift. Two systems both claiming origination authority for
one class is the same defect as two authoritative DNS sources — the
condition the Closure Necessity Doctrine already prohibits on the naming
plane, generalized to every class. Where two candidate systems exist, one
is designated and the other becomes a projection with a reconciliation
path.

### D4 — Orphan detection is a drift class

An item present in the estate with no SSOT record, or with an owner not
resolvable in the HR SSOT, is an **orphan finding** in the canonical drift
taxonomy (ADR-012 family; binding of the finding type identifier follows
in the implementing spec). Orphans are the highest-value scan output:
Spec3-D1.1's service-account scan becomes an orphan detector the moment
the NHI Registry exists to diff against.

### D5 — Non-humans get JML

Every class in D1 has lifecycle events: **provision = joiner, rescope /
re-owner = mover, decommission = leaver** — with **Reset** (credential,
secret, and key rotation) called out as the high-risk verb for non-human
identities, because rotation is where standing privilege hides. ADR-114 /
UIAO_197 is the worked pattern (AI class); per-class specs generalize it.

## Consequences

- Clause 1 and clause 2 of the MACD-R Lifecycle Doctrine become answerable
  for every governed object class, not only humans.
- The NHI Registry becomes a required substrate component; until it
  exists, service-account governance is scan-only (measurement without
  origination) and every NHI is formally an orphan candidate.
- Offboarding scope grows: a human leaver event fans out to their anchored
  non-human estate.
- The CMDB's projection status (already doctrine for assets) now applies
  uniformly: no console, directory, or CMDB may originate a MACD-R for any
  class.
- OrgComp Vol 0 Book 00 carries the engine-neutral statement of this
  registry; OrgPath applies it to identity and addressing classes; OrgMod
  applies it to devices, applications, and declared infrastructure state.

## References

- ADR-016 — human JML; ADR-055 / ADR-059 — non-employee registry and the
  machine-identity slot; ADR-012 — drift taxonomy; ADR-035..040 / ADR-102
  — OrgTree / LocPath; ADR-092 — actuation ladder; ADR-112 / ADR-114 /
  UIAO_197 — AI system identity and JML; Spec3-D1.1 —
  Get-ServiceAccountScan.
- OrgComp Vol 0 Book 00 — the MACD-R Lifecycle Doctrine and Closure
  Provenance Doctrine (engine-neutral statements).
