---
adr_id: adr-079
title: "Governance Principle Reconciliation — 3 Universal + 3 Tier-Specific"
status: ACCEPTED
decided: 2026-05-22
deciders: Michael Stratton
updated: 2026-05-22
next_review: 2026-11-22
review_trigger: Substrate-manifest.yaml gains or loses a principle; a new tier-specific principle is proposed; agency conformance declarations expose a gap in the principle set
impact: 'Formalizes 3 universal substrate principles (SSOT, Canon-anchored evidence, Drift is explicit — already declared in `substrate-manifest.yaml` UIAO_200) as universal across all 5 conformance tiers, and maps 3 tier-specific principles (Boundary Enforcement → Tier 4, Two-Brain Execution → Tier 3+, Tenant Agnosticism → Tier 5) from the canon narrative. Supersedes the canon `/modernization/index.qmd` "Seven Non-Negotiable Principles" framing as a flat list, and formalizes ADR-076 tier-mapping hints. Code impact: `substrate-manifest.yaml` gets a `tier_specific_principles` section.'
supersedes: null
superseded_by: null
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-079-governance-principle-reconciliation.html
---

# ADR-079: Governance Principle Reconciliation — 3 Universal + 3 Tier-Specific

## Status

**ACCEPTED** — 2026-05-24 (originally decided 2026-05-22).

## Context

The 2026-05-22 cross-surface review found three sources making **different claims about UIAO's governance principles**:

| Source | Principles | Where |
|---|---|---|
| **Customer Governance OS Executive Brief** | **3**: (1) Single Source of Truth, (2) Canon-anchored evidence, (3) Drift is explicit | Cites `src/uiao/canon/substrate-manifest.yaml` (UIAO_200) as authority — **code is the SSOT** |
| **Canon `/modernization/` index** | **7**: Deterministic State, Schema Fixity, Provenance Traceability, Drift Resistance, Boundary Enforcement, Two-Brain Execution, Tenant Agnosticism | Narrative prose in `docs/modernization/index.qmd` — not bound to any code/manifest |
| **UIAO OrgPath ch15** | **1**: "Assessment Before Action" | Operational discipline (don't act without observing first), not a substrate-wide principle |

[ADR-076](adr-076-tier-conformance-model.md) noted the conflict and mapped the customer/canon overlap informally — "Customer's SSOT ≈ canon's Deterministic State + Schema Fixity; customer's Drift is explicit ≈ canon's Drift Resistance; customer's Canon-anchored evidence ≈ canon's Provenance Traceability" — but did not name a canonical set or formalize the mapping. Three of the canon's 7 (Boundary Enforcement, Two-Brain Execution, Tenant Agnosticism) had **no customer-side counterpart** and were noted as gaps.

### Why this matters

Without a canonical principle set, every cross-surface review surfaces the same conflict ("are there 3 or 7?"). Worse, the canon `/modernization/` framing of "Seven Non-Negotiable Principles" implies the 3 in the substrate-manifest are incomplete — which is wrong: those 3 ARE the substrate's executing contract. The canon's extra 4 are either redundant (collapse into the 3) or scope-specific (apply only at certain conformance tiers, not universally).

### Code-is-SSOT direction

Per [`feedback_code_is_ssot`](memory pattern), when canon narrative and code disagree, code wins. `substrate-manifest.yaml` (UIAO_200) is the executable substrate contract — it ships principles to the runtime. The narrative `docs/modernization/index.qmd` describes intent but does not bind behavior. Therefore the customer-doc 3-principle declaration is correct; the canon narrative drifted to add 4 unbacked principles.

## Decision

UIAO declares **6 governance principles in two scopes**:

### 3 Universal Substrate Principles (apply at all 5 conformance tiers)

These are the existing `substrate-manifest.yaml` declarations. No code change to add them — they're already there.

1. **Single Source of Truth (SSOT).** Canonical governance artifacts under `src/uiao/canon/` define structure, policy intent, and registry authority exactly once. Downstream systems consume those artifacts via `importlib.resources` rather than duplicating policy logic.
2. **Canon-anchored evidence.** Every artifact the substrate produces — SSP, POA&M, KSI dashboards, component definitions — cites the canon document ID and version it derives from. Reviewers trace findings back to requirements deterministically.
3. **Drift is explicit.** Five-class taxonomy (`DRIFT-SCHEMA`, `DRIFT-SEMANTIC`, `DRIFT-PROVENANCE`, `DRIFT-AUTHZ`, `DRIFT-IDENTITY`) surfaces structural and provenance mismatch as first-class findings, not exception reports.

### 3 Tier-Specific Principles (apply only at named tiers per ADR-076)

These are promoted from the canon `/modernization/` narrative into the manifest, scoped to the conformance tiers where they become operational.

| Principle | Applies at tier | Rationale for tier scope |
|---|---|---|
| **Two-Brain Execution** — Copilot governs (canonical review, policy enforcement, validation); Execution Substrate executes (PowerShell, Graph API, tenant provisioning); governance logic and execution logic never co-mingle | **Tier 3+** (Active Substrate) | At Tiers 1–2 there is no active runtime to split between governance and execution. The principle becomes operational only when UIAO writes agency state. |
| **Boundary Enforcement** — No governance artifact may extend beyond the M365 GCC-Moderate SaaS boundary. Out-of-scope references are non-canonical and rejected at validation | **Tier 4** (Active Services / Platform Server) | At Tiers 1–3, boundary is a documented scope; at Tier 4 it becomes an enforced runtime contract on agency-deployed UIAO services. |
| **Tenant Agnosticism** — All artifacts are portable across any M365 GCC-Moderate tenant. No tenant-specific identifiers, UPNs, or GUIDs. All environment values are injected at deployment time | **Tier 5** (Embedded Libraries) | At Tiers 1–4, UIAO runs agency-side and may carry tenant-local context. At Tier 5, code shipped to third parties (PyPI, NuGet, adapter SDK) MUST be portable. |

### Collapsed mappings (4 canon-narrative principles already in the 3 universal)

The canon narrative's other 4 principles are not separate — they are partial expressions of the 3 universal substrate principles:

- **Deterministic State** + **Schema Fixity** → both express **SSOT** (deterministic state means a single canonical state per object; schema fixity means the canon defines structure once). Both subsumed.
- **Provenance Traceability** → identical to **Canon-anchored evidence** (same property, different label). Subsumed.
- **Drift Resistance** → identical to **Drift is explicit** (same property, different label; the customer formulation adds the 5-class taxonomy as the canonical drift surface). Subsumed.

These 4 names are retired from canonical use. The canon `/modernization/` narrative should describe the **substrate's** 3 universal principles using the customer-facing names, with the canon labels listed only as historical aliases in a footnote.

### "Assessment Before Action" (UIAO OrgPath ch15)

Treated as an **operational discipline**, not a substrate-wide principle. It is a corollary of "Drift is explicit" (you cannot remediate what you have not observed) and "Canon-anchored evidence" (action must cite its evidence baseline). Not promoted to first-class principle.

## Rationale

1. **Code is the SSOT for principles, same as for everything else.** `substrate-manifest.yaml` ships the 3 principles to the runtime; the canon narrative was prose that drifted. Reconciling toward the code is mandatory per the [`feedback_code_is_ssot`](memory pattern) rule. Reconciling toward the narrative would require code changes to UIAO_200 that have no operational justification.

2. **The 3 + 3 split honors all architectural intent without inflating the universal set.** Tenant Agnosticism is genuinely important — but only at Tier 5. Forcing every UIAO adopter to declare Tenant Agnosticism even when they're at Tier 1 (passive observation, no Platform Server) is performative. Scoping principles to the tiers where they apply makes conformance declarations honest.

3. **ADR-076 already hinted at this.** "Two-Brain Execution applies Tier 3+. Boundary Enforcement applies Tier 4." This ADR formalizes that hint as the explicit doctrine, with `substrate-manifest.yaml` as the binding declaration.

4. **The "Seven Non-Negotiable Principles" framing is a marketing flourish, not architecture.** Calling 7 things "non-negotiable" sounds strong, but 4 of them were already in the substrate-manifest under different names. The actual non-negotiable substrate contract has always been 3.

5. **UIAO OrgPath ch15's "Assessment Before Action" is good operating advice but not a principle.** It tells you what to *do* (observe before acting), not what *is true* about the system. Substrate principles describe properties of the system; operational disciplines describe practices. Don't conflate them.

## Consequences

### Positive

- One canonical principle source: `substrate-manifest.yaml`. Code is the SSOT for principles.
- Per-capability conformance declarations (per ADR-076) become more honest — agencies at Tier 1 don't have to declare Boundary Enforcement or Tenant Agnosticism, because those aren't binding at their tier.
- Cross-surface review stops re-surfacing "are there 3 or 7?" as a conflict.
- The customer Governance OS Exec Brief stays as-is (already correct).
- The canon narrative gets simpler — 3 substrate principles + 3 tier-specific commitments + clear collapse table for the prior 4 names.

### Negative

- Existing audit artifacts and presentations citing "Seven Non-Negotiable Principles" become out-of-date. Mitigation: the collapse table in the rewritten `docs/modernization/index.qmd` shows the 4 retired names mapping into the 3 universal, so anyone reading old material can resolve the lineage.
- Slight loss of marketing impact ("3 + 3 tier-specific" doesn't have the same rhetorical weight as "seven non-negotiable"). Mitigation: substrate-manifest.yaml has always been the authoritative source; presentations were already drifting from it.
- New `tier_specific_principles` section in `substrate-manifest.yaml` (Phase 1) is an additive change — minor schema impact on UIAO_200.

### Risks

- **Agencies may continue citing "seven principles" out of habit.** Mitigation: keep the collapse table in the rewritten canon narrative; reference this ADR in any deprecated-doc redirect.
- **Reviewers may propose adding more tier-specific principles in the future.** Risk that the tier-specific list grows without governance. Mitigation: tier-specific principles are governed by the same ADR process as universal ones; this ADR establishes 3 as the initial set, future additions require their own ADR.
- **"Assessment Before Action" demotion may be controversial.** It's a frequently-quoted line. Mitigation: this ADR preserves it as a named operational discipline in the rewritten canon — just not as a first-class principle on the same shelf as SSOT.

## Implementation phases

This ADR is doctrine. The implementation is sequenced across follow-up PRs:

| Phase | Branch | Scope |
|---|---|---|
| **0** | `charter/adr-079-principle-reconciliation` (this PR) | Doctrine ADR. No code changes. |
| **1** | `code/substrate-manifest-tier-principles` | Add a `tier_specific_principles:` section to `src/uiao/canon/substrate-manifest.yaml` declaring the 3 tier-specific principles with their tier scopes; update UIAO_200 schema if needed |
| **2** | `canon/modernization-index-principles-rewrite` | Rewrite the "Seven Governance Principles" section of `docs/modernization/index.qmd` to "3 Universal + 3 Tier-Specific" with the collapse table for the 4 retired names |
| **3** | `canon/exec-brief-tier-principles-note` | Update customer Governance OS Exec Brief to note the 3 tier-specific principles (audience-aware: light footnote, not centerpiece) |
| **4** | `canon/principle-references-sweep` | Search the corpus for "seven principles" / "7 principles" / "Non-Negotiable" references and update to the new framing |
| **5** | `code/conformance-template-principle-check` | Extend the conformance declaration template from ADR-076 to include a principle-scope check (which tier-specific principles apply per declared tier) |

Phases 1–5 are not strictly blocked on each other beyond the listed sequencing. Phase 1 (code SSOT) should land before Phase 2 (canon narrative) so the narrative describes shipped code.

## Verification Sources

| Source | Reference | Last Verified |
|---|---|---|
| 3-principle code SSOT | [`src/uiao/canon/substrate-manifest.yaml`](../substrate-manifest.yaml) (UIAO_200) — referenced by `docs/customer-documents/executive-briefs/governance-os-overview.qmd` lines 27–43 | 2026-05-22 |
| 7-principle canon narrative | [`docs/modernization/index.qmd`](../../../../docs/customer-documents/reference-architecture/index.qmd) "Seven Governance Principles" section | 2026-05-22 |
| 1-principle OrgPath narrative | `docs/customer-documents/orgpath-narrative/15-uiao-governance-os-complete-narrative.qmd` | 2026-05-22 (ADR-076 context) |
| ADR-076 tier-mapping hints | [`adr-076-tier-conformance-model.md`](adr-076-tier-conformance-model.md) — "Two-Brain Execution applies Tier 3+; Boundary Enforcement applies Tier 4" | 2026-05-22 |
| ADR-078 supersession pattern | [`adr-078-orgpath-attribute-schema-15-facet.md`](adr-078-orgpath-attribute-schema-15-facet.md) — template for "code SSOT wins; narrative reconciles toward code" | 2026-05-22 |

## Review Triggers

This ADR must be re-evaluated when any of the following occur:

- [ ] `substrate-manifest.yaml` gains or loses a principle entry — review whether the universal/tier-specific split still maps cleanly
- [ ] A new tier-specific principle is proposed — review the principle-addition process and whether tier scoping is still the right factor
- [ ] An agency conformance declaration exposes a gap in the principle set (a principle they need that isn't named) — review whether to add or whether the gap is properly an operational discipline
- [ ] ADR-076 tier definitions change (5 tiers becomes 4 or 6) — review the tier-scoping table here
- [ ] 2026-11-22 — scheduled six-month review

## Related Documents

- [ADR-000 — ADR Process and Lifecycle](adr-000-adr-process.md)
- [ADR-076 — Five-Tier Capability Conformance Model](adr-076-tier-conformance-model.md) — provides the tier model used for principle scoping; ADR-076's informal tier-mapping hints become explicit doctrine here
- [ADR-078 — OrgPath Attribute Schema — 15-Facet Multi-Attribute Model](adr-078-orgpath-attribute-schema-15-facet.md) — same pattern: code SSOT wins over narrative drift
- [`src/uiao/canon/substrate-manifest.yaml`](../substrate-manifest.yaml) — code SSOT for the 3 universal principles; Phase 1 adds tier-specific section
- [`docs/customer-documents/executive-briefs/governance-os-overview.qmd`](../../../../docs/customer-documents/executive-briefs/governance-os-overview.qmd) — customer-facing 3-principle declaration; stays as-is
- [`docs/modernization/index.qmd`](../../../../docs/customer-documents/reference-architecture/index.qmd) — narrative source of the "Seven Principles" framing; rewritten in Phase 2
