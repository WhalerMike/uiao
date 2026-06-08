---
adr_id: adr-081
title: "Directory Migration Phase Canonical Model — 6 Phases (adds Decommission)"
status: ACCEPTED
decided: 2026-05-22
deciders: Michael Stratton
updated: 2026-05-22
next_review: 2026-11-22
review_trigger: A new adapter migration guide is authored with a phase scheme that doesn't map cleanly; a customer-doc guide is updated and the canon phase mapping table goes stale; the adapter registry schema is changed to enforce phase enum
impact: 'Adds **Phase 6 Decommission** to the canon Directory Migration model (currently 5 phases: Discover/Normalize/Map/Migrate/Validate per `docs/modernization/directory-migration.qmd` L101). Establishes the canon 6-phase model as the universal scaffold. Customer adapter-specific guides (DNS 11-phase, PKI 6-phase, future DHCP/RADIUS/LDAP guides) keep their existing detailed phase lists but add a "Canon Phase Mapping" table at the top citing which canon phase each customer phase refines. Resolves the canon-vs-customer phase-count conflict surfaced by the 2026-05-22 review (canon=5, DNS=11, PKI=6 — none refines another).'
supersedes: null
superseded_by: null
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-081-directory-migration-phase-canonical-model.html
---

# ADR-081: Directory Migration Phase Canonical Model — 6 Phases (adds Decommission)

## Status

**ACCEPTED** — 2026-05-24 (originally decided 2026-05-22).

## Context

The 2026-05-22 cross-surface review found the Directory Migration program expressed in **three different phase models**, none refining another:

| Source | Phases | Detail |
|---|---|---|
| **Canon `docs/modernization/directory-migration.qmd`** (L101) | **5** | Discover → Normalize → Map → Migrate → Validate. **No Decommission phase.** Described as "the same five-phase governance-driven migration" that "every adapter follows." |
| **Customer DNS Modernization Guide** (`docs/customer-documents/modernization/network-transformation/dns-modernization.qmd`) | **11** | Phase 0 Assessment → Phase 1 Deploy Azure DNS Private Resolver → Phase 2 Create Private DNS Zones → Phase 3 Configure Forwarding Rulesets → Phase 4 Migrate Conditional Forwarders → Phase 5 Migrate GlobalNames Zone → Phase 6 Configure Private Endpoint DNS Zones → Phase 7 Migrate Reverse Lookup Zones → Phase 8 Gradual Client DNS Server Migration → Phase 9 AD SRV Record Validation → **Phase 10 Decommission Legacy DNS Servers** |
| **Customer PKI Modernization Guide** (`docs/customer-documents/modernization/pki-modernization.qmd`) | **6** | Phase 1 Assessment (weeks 1–4) → Phase 2 Foundation (5–8) → Phase 3 Pilot (9–16) → Phase 4 Scale (17–28) → Phase 5 Cutover (29–36) → **Phase 6 Decommission (37–44)** |

[ADR-076](adr-076-tier-conformance-model.md) noted this as "level of detail" — canon 5 = plan-generator output; customer DNS/PKI = runbook detail — but did not formalize the mapping and did not address the **gap where both customer guides have a Decommission phase but canon does not.**

### Why the gap matters

The canon's 5-phase model ending at Validate implies migration is complete when validation passes. Both customer guides — and every realistic AD modernization program — require an explicit Decommission phase: the legacy infrastructure (legacy DNS server, legacy CA, legacy AD service account) must be formally retired AFTER validation confirms the new system is operational. The customer DNS guide ships an explicit 30-day validation + 90-day parallel operation gate before Phase 10. The PKI guide ships a 30-day rollback window before Phase 6.

Without Decommission as a named canon phase, agencies and adapter authors have no canonical guidance on when/how to retire legacy systems, and the mapping from customer detail to canon scaffold breaks at the last step.

### Pattern visible across both customer guides

| Pattern | DNS expression | PKI expression |
|---|---|---|
| **Assessment** | Phase 0 | Phase 1 (Assessment) |
| **Foundation / Plan** | Phase 1 (Deploy resolver) — infrastructure prerequisites | Phase 2 (Foundation) |
| **Execute (adapter-specific, variable detail)** | Phases 2–7 (zone, forwarding, endpoint, reverse-lookup work) | Phases 3–4 (Pilot → Scale) |
| **Cutover + Validate** | Phases 8–9 | Phase 5 (Cutover) |
| **Decommission** | Phase 10 | Phase 6 |

This pattern maps cleanly onto a 6-phase canon scaffold once Decommission is added.

### Code-is-SSOT direction

Per the `feedback_code_is_ssot` memory pattern, canon should express the universal framework that customer-specific guides refine. The 5-phase canon was incomplete (missing Decommission); customer guides added it independently because they had to. Reconciling toward a 6-phase canon honors both the existing canon scaffold and the empirical evidence that Decommission is a real phase agencies execute.

## Decision

**The canon Directory Migration model is 6 phases.** Adds Phase 6 Decommission to the existing 5. Customer-specific adapter guides (DNS, PKI, and any future DHCP/RADIUS/LDAP/etc. guides) keep their own detailed phase lists and add a **Canon Phase Mapping** table at the top citing which canon phase each customer phase refines.

### The canon 6-phase model

| Phase | What Happens | Governance Gate |
|---|---|---|
| **1. Discover** | Complete inventory of what AD encodes for this service | Inventory signed off by service owner |
| **2. Normalize** | Rationalize decades of organic growth into a clean model | Normalized model reviewed against OrgPath codebook |
| **3. Map** | Translate AD governance constructs to modern equivalents | Mapping validated — no governance gaps, no orphaned objects |
| **4. Migrate** | Execute with continuous validation | Every step validated before proceeding — no big-bang cutover |
| **5. Validate** | Confirm governance integrity is preserved post-migration | Full drift scan, telemetry confirmation, user experience validation |
| **6. Decommission** *(new)* | Formally retire legacy infrastructure after validation passes a stability window | Legacy systems offline; rollback window expired with no incidents; provenance archived for audit |

### Customer-side phase mapping (illustrative)

Customer-specific guides MUST publish a "Canon Phase Mapping" table at the top. The example mappings for the two existing customer guides:

**DNS Modernization Guide (11 phases → 6 canon):**

| Customer phase | Canon phase |
|---|---|
| Phase 0 — Assessment | 1. Discover |
| Phase 1 — Deploy Azure DNS Private Resolver | 4. Migrate (infrastructure prerequisite) |
| Phase 2 — Create Private DNS Zones / Import non-AD zones | 3. Map + 4. Migrate |
| Phase 3 — Configure DNS Forwarding Rulesets | 3. Map + 4. Migrate |
| Phase 4 — Migrate Conditional Forwarders | 4. Migrate |
| Phase 5 — Migrate GlobalNames Zone | 4. Migrate |
| Phase 6 — Configure Private Endpoint DNS Zones | 4. Migrate |
| Phase 7 — Migrate Reverse Lookup Zones | 4. Migrate |
| Phase 8 — Gradual Client DNS Server Migration | 4. Migrate + 5. Validate |
| Phase 9 — AD SRV Record Validation and Monitoring | 5. Validate |
| Phase 10 — Decommission Legacy DNS Servers | 6. Decommission |

**PKI Modernization Guide (6 phases → 6 canon):**

| Customer phase | Canon phase |
|---|---|
| Phase 1 — Assessment (weeks 1–4) | 1. Discover |
| Phase 2 — Foundation (weeks 5–8) | 2. Normalize + 3. Map |
| Phase 3 — Pilot (weeks 9–16) | 4. Migrate (initial cohort) |
| Phase 4 — Scale (weeks 17–28) | 4. Migrate (rollout) |
| Phase 5 — Cutover (weeks 29–36) | 4. Migrate + 5. Validate |
| Phase 6 — Decommission (weeks 37–44) | 6. Decommission |

Both customer guides keep their existing detailed phase lists, week-counts, and operational gates unchanged. They add a mapping table at the top so readers see how the detail rolls up to canon.

### Adapter registry schema

`src/uiao/modernization/directory-migration/migration-adapter-registry.yaml` declares each adapter's current `Migration phase` (per canon page L119). The phase enum in the schema must be updated to include `Decommission` as a valid value.

## Rationale

1. **The Decommission gap was real and operational.** Both customer guides shipped Decommission because real AD modernization programs need it. Canon missing it was an oversight, not a design choice. Adding it costs almost nothing and closes a real gap.

2. **Universal scaffold + adapter-specific detail is the cleanest pattern.** Canon 6 phases describe what every adapter does (Discover → Normalize → Map → Migrate → Validate → Decommission). DNS 11-phase and PKI 6-phase describe HOW their specific adapters execute the Migrate/Validate/Decommission work. Mapping table makes the relationship explicit; neither side has to collapse to the other.

3. **Customer guides keep their operational detail.** DNS Phase 7 "Migrate Reverse Lookup Zones" doesn't need to disappear into a generic "canon Migrate" label — it stays as detailed runbook material. The mapping just notes "this refines canon Migrate."

4. **No customer-page rename or restructure required.** Phase 3 of the implementation adds one table to each customer page. Existing operational content is preserved verbatim. Lowest blast radius approach to the conflict.

5. **Lessons from ADR-080 apply.** Like the Intune-First disambiguation, this is fundamentally a naming-and-cross-reference fix, not a doctrine rewrite. The customer guides already do good work; the canon just needs to acknowledge their full scope.

## Consequences

### Positive

- Canon Directory Migration model becomes complete (6 phases including Decommission).
- Customer DNS and PKI guides become navigable from the canon — readers know which canon phase each customer phase refines.
- Future adapter guides (DHCP, RADIUS, LDAP, sync engines, devices, NTP, DFS — the other 6 of the 8 Directory Migration adapter interfaces) have a clear template: publish your own phase detail, add a Canon Phase Mapping table.
- ADR-076's "level of detail" framing is formalized: customer detail refines canon scaffold, with an explicit mapping mechanism.
- Adapter registry's `Migration phase` enum gains a new valid value (`Decommission`) — minor schema impact.

### Negative

- **Canon page update needed** — `docs/modernization/directory-migration.qmd` Phase table grows from 5 rows to 6.
- **Customer page updates** — DNS and PKI guides each get a new "Canon Phase Mapping" table at the top. Mechanical addition.
- **Adapter registry schema change** — `migration-adapter-registry.yaml` schema enum needs the new `Decommission` value. If the schema validator enforces enum, any existing adapter records may need re-validation.
- **Future adapter guides need to follow the template.** Documented as a review gate, but reviewers have to enforce it.

### Risks

- **Some adapter migrations may have no Decommission phase** (e.g., adapters that add new capability without retiring legacy). Risk: forcing all adapters to declare Phase 6 may produce empty or N/A entries. Mitigation: phase enum allows `Decommission: N/A — net-new capability` as a valid value with a brief justification.
- **Customer guide authors may copy the mapping table without thinking** and produce misaligned mappings. Mitigation: review gate when customer guide PRs land; mapping table is part of the PR template.
- **Phase 4 Migrate can become a catch-all** (many customer sub-phases map to it). That's an honest reflection of where most adapter-specific work lives, but if Phase 4 becomes 80% of every customer mapping, it may be worth a finer canon granularity in a future ADR. Mitigation: flagged as a review trigger.

## Implementation phases

| Phase | Branch | Scope |
|---|---|---|
| **0** | `charter/adr-081-dm-phase-model` (this PR) | Doctrine ADR. No page/code edits. |
| **1** | `canon/directory-migration-add-decommission` | Update `docs/modernization/directory-migration.qmd` Phase table from 5 rows to 6 (add Decommission). Update the prose preamble that says "the same five-phase governance-driven migration" to "the same six-phase…". |
| **2** | `code/migration-adapter-registry-decommission-enum` | Update `migration-adapter-registry.yaml` schema (or the JSON Schema that validates it) to include `Decommission` as a valid `Migration phase` enum value. Add `N/A — net-new capability` as the documented opt-out for adapters that don't decommission anything. |
| **3** | `canon/dns-modernization-canon-phase-mapping` | Add a "Canon Phase Mapping" table at the top of `docs/customer-documents/modernization/network-transformation/dns-modernization.qmd` (the 11→6 mapping in the Decision section above). |
| **4** | `canon/pki-modernization-canon-phase-mapping` | Same for PKI: add Canon Phase Mapping table at the top of `docs/customer-documents/modernization/pki-modernization.qmd` (6→6 mapping). |
| **5** | `canon/dm-adapter-template-mapping-required` | Update the directory-migration adapter template / contributor guidance so future adapter guides (DHCP, RADIUS, LDAP, etc.) include a Canon Phase Mapping table as a required section. |

5 phases. Smaller than ADR-078 (7), comparable to ADR-079/080. ~1 week of work.

## Verification Sources

| Source | Reference | Last Verified |
|---|---|---|
| Canon 5-phase model | `docs/modernization/directory-migration.qmd` lines 101–111 ("The Five Migration Phases" table) | 2026-05-22 |
| Customer DNS 11-phase model | `docs/customer-documents/modernization/network-transformation/dns-modernization.qmd` lines 782–942 (Phase 0 through Phase 10) | 2026-05-22 |
| Customer PKI 6-phase model | `docs/customer-documents/modernization/pki-modernization.qmd` lines 815–1005 (Phase 1 Assessment through Phase 6 Decommission, weeks 1–44) | 2026-05-22 |
| Adapter registry phase enum | `src/uiao/modernization/directory-migration/migration-adapter-registry.yaml` (per canon page L128) | 2026-05-22 (path; content not directly re-read for this ADR) |
| ADR-076 "level of detail" framing | [`adr-076-tier-conformance-model.md`](adr-076-tier-conformance-model.md) — Directory Migration phase-count clause | 2026-05-22 |

## Review Triggers

This ADR must be re-evaluated when any of the following occur:

- [ ] A new adapter migration guide is authored with a phase scheme that doesn't map cleanly to the canon 6
- [ ] A customer-doc guide is updated and the Canon Phase Mapping table goes stale
- [ ] The adapter registry schema is changed to enforce phase enum strictly (rather than as a documentation field)
- [ ] Phase 4 Migrate becomes 80%+ of every customer mapping — review whether finer canon granularity is needed
- [ ] An adapter migration completes with no Decommission phase — review whether the `N/A — net-new capability` opt-out is sufficient
- [ ] 2026-11-22 — scheduled six-month review

## Related Documents

- [ADR-000 — ADR Process and Lifecycle](adr-000-adr-process.md)
- [ADR-076 — Five-Tier Capability Conformance Model](adr-076-tier-conformance-model.md) — provides the "level of detail" framing for canon-vs-customer phasing; this ADR formalizes the mapping mechanism
- [ADR-078 — OrgPath Attribute Schema — 15-Facet](adr-078-orgpath-attribute-schema-15-facet.md) — same pattern: doctrinal reconciliation surfaced by 2026-05-22 review
- [ADR-079 — Governance Principle Reconciliation](adr-079-governance-principle-reconciliation.md) — same pattern: canon-vs-customer reconciliation
- [ADR-080 — Intune-First Scope Disambiguation](adr-080-intune-first-scope-disambiguation.md) — same pattern: naming reconciliation
- [`docs/modernization/directory-migration.qmd`](../../../../docs/modernization/directory-migration.qmd) — canon source; Phase 1 of implementation updates Phase table to 6 rows
- [`docs/customer-documents/modernization/network-transformation/dns-modernization.qmd`](../../../../docs/customer-documents/modernization/network-transformation/dns-modernization.qmd) — Phase 3 of implementation adds Canon Phase Mapping table
- [`docs/customer-documents/modernization/pki-modernization.qmd`](../../../../docs/customer-documents/modernization/pki-modernization.qmd) — Phase 4 of implementation adds Canon Phase Mapping table
- [`src/uiao/modernization/directory-migration/migration-adapter-registry.yaml`](../../modernization/directory-migration/migration-adapter-registry.yaml) — Phase 2 of implementation updates phase enum
