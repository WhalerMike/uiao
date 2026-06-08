---
adr_id: adr-080
title: "Intune-First Scope Disambiguation — Three Programs, Three Names"
status: ACCEPTED
decided: 2026-05-22
deciders: Michael Stratton
updated: 2026-05-22
next_review: 2026-11-22
review_trigger: A new program is proposed that would share the "Intune-First" name; GPO Sunset Program is formally retired (no more legacy GPO fleets to migrate); a fourth meaning emerges that this ADR did not anticipate
impact: 'Reserves "Intune-First" as the canonical name for the Asset Onboarding doctrine at `src/uiao/modernization/intune-first-onboarding/` (net-new devices, procurement-time governance). Renames the existing-fleet GPO replacement program to "GPO Sunset Program" (currently in `docs/customer-documents/modernization/target-surface/intune-policy-templates.qmd`). Preserves "regenerate, not copy" as the philosophy governing the GPO Sunset Program''s policy-creation phase, and reframes the 50-row GPO mapping as a "GPO→Intune Semantic Translation Reference" — explicitly NOT a literal 1:1 copy. No directory renames; no code SSOT changes; resolution is naming + cross-doc clarification.'
supersedes: null
superseded_by: null
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-080-intune-first-scope-disambiguation.html
---

# ADR-080: Intune-First Scope Disambiguation — Three Programs, Three Names

## Status

**ACCEPTED** — 2026-05-24 (originally decided 2026-05-22).

## Context

The 2026-05-22 cross-surface review found "Intune-First" used as the canonical name for **three genuinely different things** across canon and customer-docs:

| Meaning | Where | What it is | Stakeholder |
|---|---|---|---|
| **1. Asset Onboarding doctrine** | Canon: `src/uiao/modernization/intune-first-onboarding/` (10 files: `doctrine.md`, `process.md`, `procurement-handoff.md`, `validation-and-evidence.md`, 5 platform annexes, README); customer page `docs/modernization/intune-first.qmd` | Net-new device procurement-time governance. Five-pillar doctrine, 5-phase Procure→Validate, "refuses the existence of any ungoverned device" (canon page L37). Procurement is the first governance step (L189). | Procurement + Operations |
| **2. GPO replacement program** | Customer: `docs/customer-documents/modernization/target-surface/intune-policy-templates.qmd` | Replacement of GPOs on the **existing** fleet. 7-phase plan (GPO Analysis → GP Analytics → Policy Creation → Co-Management → Pilot → Expand → GPO Sunset), 34-week timeline, ships a 50-row GPO-to-Intune mapping. | IT operations migrating existing endpoints |
| **3. "Regenerate, Not Copy" philosophy** | Customer: `docs/customer-documents/modernization/client-server-to-hybrid-cloud/05-policy-transformation.qmd` (L77) | Philosophical stance: "The correct pattern is **regenerate, not copy**. For each GPO category…" Rebuild from policy intent rather than mirror GPO behavior. 3-phase retire-legacy-GPOs (L339) at the policy-archival end. | Policy authors |

[ADR-076](adr-076-tier-conformance-model.md) noted this as a doctrinal conflict but resolved it weakly — "Tier 1 = procurement discipline / Tier 3 = active SLA validator / Tier 4 = Platform Server enforcement." That framing collapses Meanings 1 and 2 into a single "Intune-First with three tier-scoped expressions," which is wrong: Meanings 1 and 2 are about *different fleets at different times* (net-new vs existing), not different tier-scoped expressions of one doctrine. Meaning 3 is a *philosophy* governing how Meaning 2 is executed, not a separate program.

### Why the conflation matters

Three operational problems result from sharing the name:

1. **Procurement + ops + policy authors all read "Intune-First" docs and assume they cover their case** — and the canon doctrine page silently doesn't address GPO replacement, while the customer GPO-replacement page silently doesn't address net-new devices. Both fail by silent omission, not by error.
2. **The 50-row GPO→Intune mapping in target-surface looks like a flat contradiction** with the "regenerate, not copy" stance in client-server-to-hybrid-cloud ch.05 — both pages claim to govern policy creation. ADR-076 did not resolve this internal customer-doc contradiction; it remains live.
3. **Tier conformance declarations per ADR-076 cannot honestly describe an agency's Intune-First adoption** when "Intune-First" means three things — an agency at Tier 1 (procurement discipline adopted) might or might not also be running a GPO Sunset Program (Tier 3 program). The declaration form needs three separate checks.

### Code-is-SSOT direction

Per the `feedback_code_is_ssot` memory pattern, canonical names should anchor in code where possible. `src/uiao/modernization/intune-first-onboarding/` is a real directory with 10 canonical files. Renaming it would be a code change. Reserving "Intune-First" for what that directory already names (Asset Onboarding doctrine) honors the SSOT without code churn. The other two meanings get fresh names that do not collide.

## Decision

**The name "Intune-First" is reserved for the canon Asset Onboarding doctrine.** The other two meanings get distinct names. The internal customer-doc contradiction (50-row mapping vs regenerate-not-copy) is resolved by reframing the mapping as a *reference*, not a *prescription*.

### Three named programs

| Canonical name | Scope | Canon source / customer-doc page |
|---|---|---|
| **Intune-First Asset Onboarding** | Net-new device procurement-time governance. Five-pillar doctrine, 5-phase Procure→Validate process. Applies from the moment a device first powers on. No retroactive scope on existing fleet. | Canon: `src/uiao/modernization/intune-first-onboarding/` (unchanged); customer page: `docs/modernization/intune-first.qmd` (clarified scope) |
| **GPO Sunset Program** | Existing-fleet GPO replacement. 7-phase plan ending in formal GPO retirement. Applies to GPOs currently in production; does NOT apply to net-new devices (which never had GPOs to sunset). | Customer page: `docs/customer-documents/modernization/target-surface/intune-policy-templates.qmd` (renamed in Phase 1; URL preserved or redirected) |
| **Policy Transformation Pattern** (a.k.a. "Regenerate, Not Copy") | The philosophy that governs HOW the GPO Sunset Program authors replacement policies — start from policy intent, not GPO mechanics. Not a separate program; applies within the GPO Sunset Program's policy-creation phase. | Customer page: `docs/customer-documents/modernization/client-server-to-hybrid-cloud/05-policy-transformation.qmd` (clarified relationship in Phase 3) |

### Resolution of the internal customer-doc contradiction

The 50-row GPO→Intune mapping in `intune-policy-templates.qmd` is **reframed as a "GPO→Intune Semantic Translation Reference"** — engineers' lookup table for "what's the closest Intune equivalent for this GPO setting." It is **not** a prescription to literally copy GPO behavior. The "regenerate, not copy" stance from ch.05 applies to the *policy authoring decision* (what should the policy be in the new system?), which uses the translation reference as one input among several (compliance baseline, persona model, conditional access strategy, etc.). The translation reference and the regenerate philosophy operate at different layers and do not contradict.

### Tier mapping (refines ADR-076)

Per ADR-076's tier-conformance model, each of the three programs has its own tier expression:

| Program | Tier scoping |
|---|---|
| Intune-First Asset Onboarding | **Tier 1+** doctrine. Tier 1 = procurement-discipline awareness; Tier 3 = active validation of procurement→production SLA; Tier 4 = Platform Server enforcement (e.g., quarantine on policy failure). |
| GPO Sunset Program | **Tier 3+** program. Cannot operate at Tier 1/2 (passive observation does not retire policies). Tier 3 = the program itself; Tier 4 = Platform Server enforces sunset deadlines as policy gates. |
| Policy Transformation Pattern | **All tiers** as guidance. It's a philosophy, not an executing program. |

ADR-076's wording on "Intune-First scope by tier" is formally superseded by this ADR. ADR-076's underlying tier-conformance model is unchanged; only the application to Intune-First is corrected.

## Rationale

1. **Names should match the SSOT.** `src/uiao/modernization/intune-first-onboarding/` is a real directory shipping a real doctrine. Reserving "Intune-First" for what that directory names matches the code SSOT and avoids renaming canon paths.

2. **Lowest blast radius reconciliation.** Option A (this choice) requires zero code/directory renames. Phases 1–5 are page edits and cross-references. By contrast, Option C (drop "Intune-First" entirely; rename the canon directory) would touch every consumer of that directory path and every ADR that links to it.

3. **The three programs are genuinely different.** Net-new procurement governance and existing-fleet GPO replacement are not two faces of one doctrine — they're two separate programs with different stakeholders, different timelines, different success criteria. ADR-076's "different tier expressions" framing was wrong because it tried to unify them; this ADR splits them and assigns each a tier expression on its own merits.

4. **The internal customer-doc contradiction (50-row vs regenerate) was a layer confusion, not a doctrine conflict.** The 50-row table is a *translation reference* (engineering tactic). "Regenerate, not copy" is a *policy authoring stance* (engineering strategy). They operate at different layers. ADR-076 didn't catch this; this ADR resolves it without retiring either.

5. **No retroactive renames.** The canon `intune-first-onboarding/` directory keeps its name. The customer page `intune-policy-templates.qmd` keeps its filename (to preserve URL stability for any external links); only its TITLE and content reframe to "GPO Sunset Program."

## Consequences

### Positive

- Three programs each have a name that doesn't lie about what they cover.
- Procurement teams reading "Intune-First Asset Onboarding" get only what applies to them (net-new). IT ops reading "GPO Sunset Program" get only what applies to them (existing fleet). Policy authors reading "Policy Transformation Pattern" understand it's philosophy, not a program.
- ADR-076 tier conformance declarations become honest — agencies can declare per-program tier adoption independently.
- The internal customer-doc 50-row-vs-regenerate contradiction is resolved by layer-clarification (reference vs stance), not by retiring either.
- Code SSOT preserved — no `src/uiao/modernization/intune-first-onboarding/` rename.

### Negative

- **Customer page title rename** (`intune-policy-templates.qmd` page title → "GPO Sunset Program"). The filename stays; only the displayed title changes. URLs unaffected.
- **Cross-reference sweep** — any doc referring to "Intune-First" meaning GPO replacement needs to be updated to say "GPO Sunset Program." Estimated low (Phase 5 sweep work).
- **ADR-076 amendment** — the specific clause about Intune-First tier-scoping needs a "superseded by ADR-080" note. Mechanical change.
- **Marketing-vs-canon distinction** — external pitch decks may have called the whole space "Intune-First." Those decks now use three named terms. Mitigation: ADR-080 publication can include a one-page "translation guide" footer for slide-deck authors.

### Risks

- **Habit lag.** Internal stakeholders may continue saying "Intune-First" when they mean "GPO Sunset." Mitigation: the rewritten canon pages link the three names prominently in their intros; reviewers can challenge ambiguous uses in PRs.
- **A fourth meaning may emerge.** If a future program ("Intune-First Reporting Dashboard"? "Intune-First Co-Management"?) tries to claim the name, this ADR's review-trigger flags it for re-examination.
- **The Policy Transformation Pattern is not a "program" in the conformance sense** — agencies don't "adopt" a philosophy. Risk that the third name doesn't fit the program-tier conformance model cleanly. Mitigation: per Decision table, it's marked "All tiers as guidance" — not a conformance dimension.

## Implementation phases

| Phase | Branch | Scope |
|---|---|---|
| **0** | `charter/adr-080-intune-first-disambiguation` (this PR) | Doctrine ADR. No code/page edits. |
| **1** | `canon/intune-policy-templates-rename-to-gpo-sunset` | Update page title + frontmatter of `customer-documents/modernization/target-surface/intune-policy-templates.qmd` to "GPO Sunset Program." Add a one-paragraph intro disambiguating from Intune-First Asset Onboarding. Filename stays for URL stability. |
| **2** | `canon/intune-policy-templates-mapping-reframe` | Update the 50-row GPO→Intune mapping section in the same page: reframe as "GPO→Intune Semantic Translation Reference"; explicit note that this is engineers' lookup, not a literal-copy prescription; cross-link to the Policy Transformation Pattern as the governing stance. |
| **3** | `canon/policy-transformation-clarify-relationship` | Update `customer-documents/modernization/client-server-to-hybrid-cloud/05-policy-transformation.qmd` to explicitly name the relationship: "Regenerate, Not Copy" is the philosophy; "GPO Sunset Program" is the program that follows it; the Semantic Translation Reference is a tool, not a contradiction. |
| **4** | `canon/intune-first-canon-clarify-scope` | Update `docs/modernization/intune-first.qmd` and `src/uiao/modernization/intune-first-onboarding/doctrine.md` to clarify: this is Asset Onboarding (net-new) only; for existing-fleet GPO replacement see GPO Sunset Program. |
| **5** | `canon/intune-first-references-sweep` | Sweep the corpus for "Intune-First" usages that actually mean GPO replacement and redirect to "GPO Sunset Program." Update ADR-076's Intune-First tier-scoping clause with a "see ADR-080" note. |

Smaller scope than ADR-078 or ADR-079 — no code SSOT changes, no schema migrations. Estimated 1 week of work across the 5 phases.

## Verification Sources

| Source | Reference | Last Verified |
|---|---|---|
| Asset Onboarding canon | `src/uiao/modernization/intune-first-onboarding/` (10 files); `docs/modernization/intune-first.qmd` lines 22, 37, 63, 189 | 2026-05-22 |
| GPO replacement (current "intune-policy-templates") | `docs/customer-documents/modernization/target-surface/intune-policy-templates.qmd` Phase 1-7 (lines 1186–1317), GPO Sunset at Phase 7 | 2026-05-22 |
| "Regenerate, Not Copy" philosophy | `docs/customer-documents/modernization/client-server-to-hybrid-cloud/05-policy-transformation.qmd` line 77 ("The correct pattern is regenerate, not copy"); retire-legacy-GPOs Phase 1-3 at line 339 | 2026-05-22 |
| ADR-076 superseded clause | [`adr-076-tier-conformance-model.md`](adr-076-tier-conformance-model.md) — Intune-First tier-scoping wording | 2026-05-22 |

## Review Triggers

This ADR must be re-evaluated when any of the following occur:

- [ ] A new program is proposed that would share the "Intune-First" name (e.g., "Intune-First Reporting") — review whether the reservation rule still applies
- [ ] GPO Sunset Program is formally retired in all customer tenants (no more legacy GPO fleets) — review whether the program still warrants canon doc real estate
- [ ] The Policy Transformation Pattern grows enough operational substance to become its own program — review whether "All tiers as guidance" still describes it
- [ ] A fourth meaning of "Intune-First" emerges that this ADR did not anticipate
- [ ] ADR-076 conformance declaration template (Phase 5 of ADR-079) lands — review whether per-program tier checks need explicit accommodation here
- [ ] 2026-11-22 — scheduled six-month review

## Related Documents

- [ADR-000 — ADR Process and Lifecycle](adr-000-adr-process.md)
- [ADR-076 — Five-Tier Capability Conformance Model](adr-076-tier-conformance-model.md) — provides the tier model used in the per-program tier mapping; this ADR supersedes ADR-076's specific Intune-First tier-scoping clause
- [ADR-078 — OrgPath Attribute Schema — 15-Facet](adr-078-orgpath-attribute-schema-15-facet.md) — same pattern: doctrinal disambiguation surfaced by 2026-05-22 review
- [ADR-079 — Governance Principle Reconciliation](adr-079-governance-principle-reconciliation.md) — same pattern: name reconciliation across surfaces
- [ADR-071 — Intune-First Asset Onboarding](adr-071-intune-first-asset-onboarding.md) — the ADR that established the canon Asset Onboarding doctrine being reserved here
- [`src/uiao/modernization/intune-first-onboarding/`](../../modernization/intune-first-onboarding/) — canon directory whose name "Intune-First" is reserved as the canonical doctrine name
- [`docs/customer-documents/modernization/target-surface/intune-policy-templates.qmd`](../../../../docs/customer-documents/modernization/target-surface/intune-policy-templates.qmd) — Phase 1 target for rename to "GPO Sunset Program"
- [`docs/customer-documents/modernization/client-server-to-hybrid-cloud/05-policy-transformation.qmd`](../../../../docs/customer-documents/modernization/client-server-to-hybrid-cloud/05-policy-transformation.qmd) — Phase 3 target for relationship clarification
