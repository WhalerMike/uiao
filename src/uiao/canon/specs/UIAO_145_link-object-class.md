---
document_id: UIAO_145
title: "UIAO Link Object Class — External Interconnection Governance"
version: "1.0"
status: Current
owner: "Michael Stratton"
created_at: "2026-07-25"
updated_at: "2026-07-25"
publish_to_site: true
---

# UIAO Link Object Class — External Interconnection Governance

## 1. Overview

This spec defines the **Link**: the governed record of one interconnection
between the org and one outside party — **interface + agreement artifact +
regime overlay**, one per external relationship. It is the ADR-132 Phase 1
deliverable: the object model, the registry that carries it, and the
substrate-walker hygiene rules that keep it honest.

Established under ADR-132 (`src/uiao/canon/adr/adr-132-orglink-link-object-class.md`),
which fixes the doctrine: the Link follows the LocPath / non-human-SSOT
overlay pattern (a substrate object class serving every pillar, not a new
pillar), OrgComp remains the sole assessor-facing flow, and boundary-attached
compliance regimes ride as vertical adapter packs.

**Motivating finding.** The control library's CA-3 (Information Exchange)
entry declares its evidence as DOCX/PDF documents in SharePoint folders —
unmanaged, undrifted, provenance-free. This registry is the substrate-side
replacement for that pattern: Phase 1 registers the links; Phase 2 renders
CA-3 / CA-9 / SA-9 / AC-20 evidence from registry state.

## 2. Object model

Each link in the registry carries:

| Facet | Field(s) | Content |
|---|---|---|
| Identity | `id`, `name` | Stable kebab-case identifier; human-readable name |
| Counterparty | `counterparty.name`, `counterparty.class` | Who the outside party is, and which taxonomy class it belongs to |
| Direction | `direction` | `inbound`, `outbound`, or `bidirectional`, relative to the org |
| SSOT stance | `ssot-stance` | `we-are-source`, `they-are-source`, or `contended` for the exchanged data domain |
| Interface | `interface.*` | Transport, identity binding (workload identity federation per ADR-004 where applicable), description |
| Agreement | `agreement.*` | Artifact class, location, provenance anchoring, review cadence |
| Regime overlay | `regime-overlays` | Boundary-attached regimes riding the link (each satisfied by a vertical adapter pack) |
| Control bindings | `controls` | Controls this link evidences (CA-3, CA-9, SA-9, AC-20, …) |
| Authorization | `authorized-by` | Repo-relative ADR/spec paths authorizing the interconnection |

### 2.1 Counterparty taxonomy

| Class | Covers |
|---|---|
| `federal-agency` | Executive-branch agencies and their systems |
| `federal-branch` | Legislative / judicial branch bodies |
| `state` | State governments and state-run programs |
| `local` | County / municipal governments |
| `tribal` | Tribal governments |
| `regulated-commercial` | Regime-bound sectors: banks (GLBA), hospitals (HIPAA), insurers |
| `general-commercial` | Commercial vendors and partners without a sector regime |
| `consortium` | Membership bodies (AAMVA-shaped verification consortia, ERIC-shaped compacts) |
| `public` | Citizen / customer-facing service surfaces |

### 2.2 SSOT stance

The stance declares the authority relationship for the data domain the link
exchanges. It wires directly into the ADR-074 contention machinery: a
counterparty asserting authority over data the org stewards is a detected
`DRIFT-SSOT-CONTENTION` event, never a silent overwrite. `contended`
declares a known contention honestly instead of hiding it; an *undeclared*
stance on an active link is itself a drift finding (§4), because an
undeclared stance is a latent contention.

### 2.3 Agreement artifact

The agreement is the compliance object every regime already requires for an
interconnection — ISA/MOU per CA-3, computer matching agreement (CMA) per
the Computer Matching and Privacy Protection Act, BAA per HIPAA, DUA for
data sharing. Two fields keep the registry honest during migration:

- `type: unrecorded` — no agreement artifact is registered for the link
  yet. This is the CA-3 gap made explicit; Phase 2 retires it.
- `provenance-anchored: false` — the artifact exists but lives outside the
  substrate (the SharePoint-pointer state). Phase 2 migrates these to
  repo-anchored, hash-tracked artifacts.

## 3. Registry

- **Location:** `src/uiao/canon/link-registry.yaml`
- **Schema:** `src/uiao/schemas/link-registry/link-registry.schema.json`
  (JSON Schema Draft 2020-12), enforced by the schema-validation CI
  workflow alongside the adapter and reciprocal-consumption registries.
- **Status lifecycle:** `proposed` → `active` → `retired`. Only `active`
  links are subject to the full hygiene scan (§4); `proposed` and
  `retired` entries are recorded but not enforced.
- **Pair-registry convention:** like `adapter-registry.yaml` and
  `modernization-registry.yaml`, this is a pair registry — it catalogs
  governed objects, not documents, so entries do not receive UIAO_NNN
  allocations; the registry itself is governed by this spec.

## 4. Drift integration (substrate walker)

The walker scans the registry as part of `uiao substrate walk` / `drift`.
The file is optional (its absence is not a finding); declared entries are
held to these rules:

| Condition | Drift class | Severity |
|---|---|---|
| Active link with missing or empty `ssot-stance` | DRIFT-SCHEMA | P2 (undeclared stance is a latent DRIFT-SSOT-CONTENTION) |
| Unknown `ssot-stance`, `direction`, or `counterparty.class` value | DRIFT-SCHEMA | P3 (schema hygiene; CI schema gate is the blocking check) |
| Active link with no `agreement` block | DRIFT-SCHEMA | P2 (CA-3 evidence cannot render for this link) |
| Active link with `agreement.type: unrecorded` | DRIFT-SCHEMA | P3 (advisory; Phase 2 migration target) |
| `agreement.next-review` malformed (not ISO-8601 date) | DRIFT-SCHEMA | P3 |
| `authorized-by` path does not resolve | DRIFT-PROVENANCE | P2 (link claims an authorization the repo cannot produce) |

Past-due `next-review` detection is deliberately **not** a walker rule: the
walker stays deterministic (no wall-clock comparisons). Review-currency
enforcement belongs to the Phase 2 link-gap scanner.

## 5. Boundaries

Per ADR-132 D1, restated here as operating constraints:

1. **No entity resolution.** The registry governs agreements, flows, and
   authority stances. It does not deduplicate or match records across
   parties.
2. **Metadata, never payload.** No person-level payload attributes enter
   the registry. A proposal that would put exchanged data content here is
   out of scope for this class and requires its own ADR.
3. **Published at elevation.** This spec published when ADR-134 elevated
   the OrgLink pillar; its narrative rendering is the OrgLink shelf's
   first work, which cites this spec as its object-model authority.

## 6. Backfilled links (Phase 1 worked examples)

The registry ships with the five interconnections the repo already
operates, registered as they exist today — including honest `unrecorded` /
`provenance-anchored: false` agreement states:

| Link id | Counterparty class | Direction | Stance | Authorized by |
|---|---|---|---|---|
| `opm-apim-federal-gateway` | federal-agency | inbound | they-are-source | ADR-053 |
| `hr-inbound-provisioning` | federal-agency | inbound | they-are-source | ADR-003, ADR-088 |
| `federal-hrit-integration` | federal-agency | bidirectional | we-are-source | UIAO_140, Spec2-D6.1, UIAO_144 |
| `conmon-reporting-egress` | federal-agency | outbound | we-are-source | ADR-128 |
| `sailpoint-nerm-nonemployee` | general-commercial | bidirectional | they-are-source | ADR-059, ADR-130 |

The `federal-hrit-integration` link is the reference case for the target
state: its agreement artifact is the substrate-governed
reciprocal-consumption registry (`provenance-anchored: true`). The other
four demonstrate the migration-pending state Phase 2 retires.

## 7. Roadmap position

This spec completes ADR-132 D6 **Phase 1** (spec + registry + schema +
walker integration + backfill). Next:

- **Phase 2** — evidence rendering (CA-3/CA-9/SA-9/AC-20 from registry
  state), Evidence Graph and CQL surfacing, ConMon dashboard panel, and
  the link-gap scanner (counterparty × regime matrix, expired reviews,
  stance gaps, control-narrative mismatches).
- **Phase 3** — HIPAA and GovRAMP vertical adapter packs (ADR-132 D5),
  each under its own authorizing ADR.
- **Phase 4** — OrgLink pillar elevation when the ADR-132 D3 conditions
  hold.
