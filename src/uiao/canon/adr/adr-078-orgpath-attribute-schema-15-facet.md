---
adr_id: adr-078
title: "OrgPath Attribute Schema — 15-Facet Multi-Attribute Model Supersedes Composite Path"
status: ACCEPTED
decided: 2026-05-22
deciders: Michael Stratton
updated: 2026-05-22
next_review: 2026-11-22
review_trigger: First agency declares Model C adoption; Phase 1 schema rewrite ships; migration tooling ADR is proposed; reserved attribute 11-15 is claimed for a new facet
impact: 'Establishes Model C (15-facet multi-attribute) as the canonical OrgPath schema for new UIAO adoption. Supersedes Model A (composite-hyphen) and Model B (composite-slash) for new adoption while explicitly grandfathering existing tenants per the ADR-076 strict-subset rule. Triggers a 7-phase implementation rewrite of `codebook.yaml`, `codebook.schema.json`, `UIAO_151`, the 12 canon `/modernization/` pages, downstream UIAO_152/154/158/163, and adapters reading `extensionAttribute1`.'
supersedes: null
superseded_by: null
classification: Controlled
boundary: GCC-Moderate
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-078-orgpath-attribute-schema-15-facet.html
---

# ADR-078: OrgPath Attribute Schema — 15-Facet Multi-Attribute Model Supersedes Composite Path

## Status

**ACCEPTED** — 2026-05-24 (originally decided 2026-05-22).

> **2026-05-24 implementation note.** Phase 1 (Model C SSOT) shipped
> with **no legacy preservation**. The grandfathering language below
> ("existing tenants on Model A are explicitly grandfathered",
> `UIAO_151_LEGACY_MODEL_A.md`, "Demoted to legacy Tier 1 support",
> etc.) was written assuming real Model A tenants existed. UIAO has
> no production adopters at ADR ratification time, so the speculative
> Model A consumer modules (`policy_targets.py`, `dynamic_groups.py`,
> `device_planes.py`, `admin_units.py`, the matching Entra-side
> adapter wrappers, and the drift-engine + drift-engine-config that
> consumed them) were deleted outright rather than preserved. Their
> Model C rebuilds will be authored in a follow-up Phase 5 PR. The
> "Grandfathered Tier 1 reference" preservation paths described
> below in §Supersession remain reserved for future use if a real
> Model A tenant emerges before Phase 5 ships.

## Context

A cross-surface review on 2026-05-22 found **three coexisting OrgPath attribute models** across canon and customer-documents, all calling themselves "OrgPath" or "canonical":

| Model | Where | Example |
|---|---|---|
| **A. Composite-hyphen** | Current canon: `codebook.yaml`, `UIAO_151`, `docs/modernization/codebook.qmd` | `extensionAttribute1 = "ORG-FIN-AP-EAST"` |
| **B. Composite-slash** | `docs/customer-documents/modernization/identity-orgtree/ad-to-entraid-tree.qmd` (8,572 lines) | `extensionAttribute1 = "CORP/US/EAST/BALTIMORE/IT"` |
| **C. 15-facet multi-attribute** | `docs/customer-documents/modernization/identity-orgtree/identity-modernization.qmd` (1,802 lines) | `attr1=Region (NCR), attr2=Department (IT), attr3=Division (CyberOps), attr4=Role (Engineer), attr5=CostCenter (CC-4100), attr6=Classification (Employee), attr7=HireDate, attr8=TermDate, attr9=ClearanceLevel, attr10=AccountType, attr11-15=Reserved` |

Model A (current canon) is internally consistent — the YAML SSOT (`codebook.yaml`), JSON Schema (`codebook.schema.json`), narrative spec (`UIAO_151`), and the modernization page (`docs/modernization/codebook.qmd`) all describe a single-attribute composite-hyphen path validated by the regex `^ORG(-[A-Z0-9]{2,6}){0,8}$`. The drift engine, dynamic group rule library, and Administrative Unit mapping all assume this model.

Model B uses a different separator (`/`) and a different prefix (`CORP`) but otherwise occupies the same architectural slot — single attribute, composite path. The `ad-to-entraid-tree.qmd` page explicitly states "One attribute only (extensionAttribute1 recommended)" at line 775.

Model C is structurally different. It distributes identity facets across all 15 `onPremisesExtensionAttribute` slots: each attribute carries one semantic field rather than a path segment. Dynamic group rules compose multiple facets via boolean AND:

```
(user.onPremisesExtensionAttributes.extensionAttribute1 -eq "NCR") and
(user.onPremisesExtensionAttributes.extensionAttribute4 -in ["Manager","Director"]) and
(user.accountEnabled -eq true)
```

This is not expressible in Models A or B without regex hacks on a single string. Model C also enables lifecycle workflow triggers off attributes 7/8 (HireDate/TermDate), classification-based persona policies (attr 6), clearance-gated application access (attr 9), and cost-center chargeback reporting (attr 5) — none of which are first-class in Models A/B.

The 15-facet model in `identity-modernization.qmd` is the most recent and most comprehensive expression of UIAO's OrgPath intent. [ADR-076](adr-076-tier-conformance-model.md) acknowledged this conflict but resolved it weakly — "composite-path is a Tier 1 expression of intent; single-facet-per-attribute is the Tier 3 storage contract" — preserving the ambiguity rather than naming a primary model.

## Decision

**Model C — the 15-facet multi-attribute model — is the canonical OrgPath attribute schema for new UIAO adoption.** Models A and B are explicitly superseded for new adoption.

### Canonical attribute assignments

| Attribute | Semantic | Example values |
|---|---|---|
| `extensionAttribute1` | **Region** | `NCR`, `WESTUS`, `EMEA` |
| `extensionAttribute2` | **Department** | `IT`, `HR`, `Finance`, `Legal`, `Engineering` |
| `extensionAttribute3` | **Division** | `CyberOps`, `InfraOps`, `AppDev`, `GRC` |
| `extensionAttribute4` | **Role** | `Analyst`, `Engineer`, `Manager`, `Director`, `CISO` |
| `extensionAttribute5` | **CostCenter** | `CC-4100`, `CC-5200`, `CC-8300` |
| `extensionAttribute6` | **Classification** | `Employee`, `Contractor`, `Intern`, `Executive` |
| `extensionAttribute7` | **HireDate** | ISO 8601 date (`2024-01-15`) |
| `extensionAttribute8` | **TermDate** | ISO 8601 date, or empty for active employees |
| `extensionAttribute9` | **ClearanceLevel** | `None`, `Public Trust`, `Secret`, `Top Secret` |
| `extensionAttribute10` | **AccountType** | `Standard`, `Privileged`, `Service`, `SharedMailbox` |
| `extensionAttribute11`–`15` | **Reserved** | Available for organization-specific extensions; codebook MUST declare facet semantics in a governed PR before use |

Each facet has its own enumeration (per-facet codebook section). The drift engine validates each attribute against its facet enumeration independently. Dynamic group rules and Administrative Unit memberships compose facets via boolean operators rather than text-parsing the value of a single attribute.

### Greenfield-only migration

Per the ADR-076 strict-subset backward-compatibility rule, this is a **Tier 3+ doctrine for new adoption only.** Existing tenants on Model A (composite-hyphen) or Model B (composite-slash) are **explicitly grandfathered** — UIAO continues to support them at Tier 1 (passive observation), and the migration to Model C is voluntary. Migration tooling is the subject of a separate future ADR (see Implementation Phases below).

For new (Tier 3+) tenants, the canon ships only Model C tooling. Adapters, drift engine, dynamic group library, Administrative Unit scoping, and Conditional Access targeting all assume Model C.

### Supersession

- **Model A (composite-hyphen):** Demoted to **legacy Tier 1 support**. Existing tenants keep it; new adoption MUST NOT use it. `UIAO_151_OrgPath_Codebook.md` is rewritten to describe Model C; the prior Model A description is preserved as `UIAO_151_LEGACY_MODEL_A.md` for grandfathered tenants and historical reference.
- **Model B (composite-slash):** Demoted to **historical reference**. The `CORP/US/EAST/...` style in `ad-to-entraid-tree.qmd` is rewritten to Model C in Phase 4; the legacy form is preserved only as a "Historical Alternative" callout.
- **ADR-076's tier-coexistence wording on attribute semantics:** Explicitly superseded by this ADR. The "different tiers for different storage models" framing was a stopgap. Model C is now the unambiguous primary storage model for Tier 3+; Model A is legacy-grandfathered for existing Tier 1 adopters only.

## Rationale

1. **Model C is the only model that expresses the full identity surface UIAO governs.** Lifecycle workflows need HireDate/TermDate as separate attributes — not embedded in a composite path. Persona-based Conditional Access needs Classification as a queryable facet. PIM eligibility benefits from AccountType being independently filterable. Models A and B require text parsing inside dynamic-group rules to extract these — fragile, non-standard, and not expressible in Entra dynamic membership syntax without `-match` regex tricks.

2. **Boolean composition is fundamental to federal access policy.** Federal CA policies routinely combine clearance, role, region, and account type. Model C makes this trivial: `(attr9 -in ["Secret","Top Secret"]) and (attr1 -eq "NCR") and (attr10 -eq "Privileged")`. Model A would require regex hacks on `extensionAttribute1` that don't compose well and are nearly impossible to audit.

3. **Customer-documents has already moved here.** The 1,802-line `identity-modernization.qmd` is the most recent and most comprehensive treatment of identity modernization in the corpus. Telling the customer-doc to roll back to Model A would invalidate hundreds of lines of customer-facing prescription (lifecycle workflows, persona CA policies, dynamic group examples, AD-to-Entra attribute flow tables at lines 1687–1717).

4. **Greenfield-only protects existing tenants.** No agency on Model A is forced to migrate. The ADR-076 strict-subset rule is honored: Tier N+1 (Model C) doesn't break Tier N (Model A) — they coexist as supported alternatives, with Model C being the default for new adoption and Model A being grandfathered indefinitely.

5. **Model B is a footnote, not a contender.** The slash-separator path appears only in `ad-to-entraid-tree.qmd`, mostly as illustrative examples. It was never canonized in code (no `codebook.yaml` ever used it). Demoting it costs nothing — `ad-to-entraid-tree.qmd` simply gets rewritten to Model C in Phase 4.

6. **The cost is justified by the irreducible complexity of federal identity.** Federal IT manages identity across regions × departments × divisions × roles × clearances × account types × lifecycle dates simultaneously. Pretending this collapses into a single composite path was always a simplification that broke at scale. Model C admits the multi-dimensional reality and gives each dimension its own first-class attribute.

## Consequences

### Positive

- Single canonical attribute model for new adoption — no more "which OrgPath does this doc mean?"
- Dynamic group rules become first-class boolean compositions across semantic facets, not text-parsing hacks
- Lifecycle workflows (joiner/leaver via HireDate/TermDate), persona-based CA (via Classification), clearance-gated app access (via ClearanceLevel), cost-center reporting (via CostCenter) — all natively expressible
- Customer-documents `identity-modernization.qmd` becomes the authoritative narrative; canon `UIAO_151` is rewritten as a slimmer technical reference that defers to it
- Conformance per ADR-076: Tier 1 adopters stay on Model A; Tier 3+ adopters use Model C — both are valid and coexist

### Negative

- **Significant code rewrite.** `codebook.yaml` and `codebook.schema.json` must restructure from a single enumeration of composite codes to a multi-section schema (one section per facet, each with its own enumeration). Subject of Phase 1 PR below.
- **Canon narrative rewrite.** `UIAO_151_OrgPath_Codebook.md` is rewritten; the existing v3.0 doc becomes `UIAO_151_LEGACY_MODEL_A.md` for grandfathered tenants. Same for the 12 canon `/modernization/` pages.
- **Adapter changes.** Adapters that read `extensionAttribute1` need to read multiple attributes. API change for adapter consumers.
- **Downstream canon rewrites.** UIAO_152 (dynamic groups), UIAO_154 (admin units), UIAO_158 (JSON schema), UIAO_163 (drift engine) all reference the attribute model and need updating.

### Risks

- **`ad-to-entraid-tree.qmd` (Model B) and `identity-modernization.qmd` (Model C) are both in customer-documents and contradict each other today.** Until `ad-to-entraid-tree.qmd` is rewritten to Model C in Phase 4, customers reading both will see two "canonical" models. Mitigation: prioritize the Phase 4 rewrite; consider a temporary "Historical Note" banner on `ad-to-entraid-tree.qmd` immediately after this ADR ratifies.
- **15-facet per-attribute enumeration explosion.** Each facet's enumeration is per-tenant; codebook ships starter enumerations but expects per-tenant customization. Risk: codebook becomes unwieldy if every tenant declares 15 different enumerations. Mitigation: ship a starter codebook with sensible federal/enterprise defaults; document the customization path; allow tenant overrides via a layered codebook (canon defaults + tenant overlay).
- **Migration tooling for existing Model A tenants is not in scope of this ADR.** Future migration ADR must define the value-mapping (how does `ORG-FIN-AP-EAST` decompose into Region/Department/Division/Unit?). Until that ships, Model A tenants are frozen on Model A — adoption of Model C-only Tier 3+ features requires a fresh migration project they cannot self-serve.
- **Reserved attributes 11-15** may collide with existing tenant uses (some tenants already use these for HR-flow custom fields, mailbox routing, etc.). Mitigation: codebook declaration MUST validate that the tenant's prior use is null before assigning facet semantics; the migration runbook MUST audit current attribute use as a precondition.

## Implementation phases

This ADR is doctrine. The implementation is sequenced across follow-up PRs:

| Phase | Branch | Scope |
|---|---|---|
| **0** | `charter/adr-078-orgpath-15-facet` (this PR) | Doctrine ADR. No code changes. |
| **1** | `code/orgpath-15-facet-schema` | Restructure `codebook.yaml` + `codebook.schema.json` for 15 facets; bump major `schema_version` to 2.0.0; codebook becomes one section per facet (`facets.region`, `facets.department`, etc.) each with its own enumeration of valid values |
| **2** | `canon/uiao-151-rewrite-15-facet` | Rewrite `UIAO_151_OrgPath_Codebook.md` to describe Model C; preserve current content as `UIAO_151_LEGACY_MODEL_A.md` with a "Grandfathered Tier 1 reference" banner |
| **3** | `canon/modernization-15-facet-restructure` | Rewrite 12 `docs/modernization/*.qmd` pages for Model C; restructure flat layout to nested layout mirroring customer-doc (`identity-orgtree/`, `network-transformation/`, `target-surface/`, etc.) |
| **4** | `canon/customer-docs-reconciliation-model-c` | Rewrite `ad-to-entraid-tree.qmd` (Model B → Model C); update remaining customer-doc OrgPath references to Model C |
| **5** | `code/adapters-15-facet` | Update adapters reading `extensionAttribute1` to read multi-attribute Model C; bump adapter API major version |
| **6** | `canon/downstream-15-facet` | Update UIAO_152, UIAO_154, UIAO_158, UIAO_163 to reference Model C as primary and Model A as grandfathered |
| **7 (future)** | `tooling/orgpath-model-a-to-c-migration` | Migration tooling for Model A tenants — out of scope for this ADR; will require its own ADR defining the value decomposition rules |

Phases 1-6 are not strictly blocked on each other beyond their listed sequencing — they can ship in parallel branches as long as each declares its dependency on the prior phase having merged. Phase 1 (code SSOT) should land before Phase 2 (canon narrative) so the narrative describes shipped code.

## Verification Sources

| Source | Reference | Last Verified |
|---|---|---|
| Three-model cross-surface review | The 146-line extract at `inbox/_identity-orgtree-extract.md` (generated 2026-05-22) | 2026-05-22 |
| Model A canon | [`codebook.yaml`](../data/orgpath/codebook.yaml), [`UIAO_151_OrgPath_Codebook.md`](../UIAO_151_OrgPath_Codebook.md), [`docs/modernization/codebook.qmd`](../../../../docs/modernization/codebook.qmd) | 2026-05-22 |
| Model B example | `docs/customer-documents/modernization/identity-orgtree/ad-to-entraid-tree.qmd` lines 96, 466, 775, 1484 | 2026-05-22 |
| Model C example | `docs/customer-documents/modernization/identity-orgtree/identity-modernization.qmd` lines 192, 384–404, 1689–1717 | 2026-05-22 |
| ADR-076 tier-coexistence wording (superseded clause) | [`adr-076-tier-conformance-model.md`](adr-076-tier-conformance-model.md), "OrgPath attribute semantics" section | 2026-05-22 |

## Review Triggers

This ADR must be re-evaluated when any of the following occur:

- [ ] Phase 1 schema rewrite ships — review whether per-facet enumeration structure scales without becoming unwieldy
- [ ] First agency declares Model C adoption — review whether the 10 named facets cover their identity surface, or whether they need to claim reserved attributes 11-15
- [ ] Migration tooling ADR is proposed — review whether `UIAO_151_LEGACY_MODEL_A.md` is still useful or can be archived
- [ ] A reserved attribute (11-15) is claimed for a new facet — review whether the codebook declaration process is sufficient or needs an additional review gate
- [ ] An agency on Model A or Model B reports operational friction caused by the new doctrine — review whether the grandfather clause is being honored in practice
- [ ] 2026-11-22 — scheduled six-month review

## Related Documents

- [ADR-000 — ADR Process and Lifecycle](adr-000-adr-process.md)
- [ADR-076 — Five-Tier Capability Conformance Model](adr-076-tier-conformance-model.md) — establishes the Tier 1/3 split this ADR uses for greenfield-only migration; the "attribute semantics" clause of ADR-076 is superseded by this ADR
- [ADR-072 — Canon Publication Policy](adr-072-canon-publication-policy.md) — `publish_to_site` machinery the new schema fields will plug into
- [ADR-035 — OrgPath Codebook Binding](adr-035-orgpath-codebook-binding.md) — current binding of `codebook.yaml`; this ADR restructures the binding target in Phase 1
- [ADR-048 — OrgPath Attribute Selection](adr-048-orgpath-attribute-selection.md) — predecessor decision on which single attribute to use; this ADR supersedes its single-attribute conclusion for new adoption
- [`docs/customer-documents/modernization/identity-orgtree/identity-modernization.qmd`](../../../../docs/customer-documents/modernization/identity-orgtree/identity-modernization.qmd) — the Model C source narrative
- [`src/uiao/canon/data/orgpath/codebook.yaml`](../data/orgpath/codebook.yaml) — current Model A code SSOT (will be restructured in Phase 1)
