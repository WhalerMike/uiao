---
id: ADR-074
title: "DRIFT-SSOT-CONTENTION — New Drift Class for Data-Plane Stewardship Authority"
status: proposed
date: 2026-05-18
deciders:
  - governance-steward
  - data-engineering-steward
  - identity-engineer
supersedes: []
related_adrs:
  - ADR-012
  - ADR-054
  - ADR-063
  - ADR-064
  - ADR-072
  - ADR-073
canon_refs:
  - UIAO_001_UIAO-SSOT
  - UIAO_151_OrgPath_Codebook
  - UIAO_153_Attribute_Mapping_Table
  - UIAO_163_Drift_Detection_Engine_Specification
  - UIAO_167_SLA_Escalation_Playbooks
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-074-drift-ssot-contention.html
---

# ADR-074: DRIFT-SSOT-CONTENTION — New Drift Class for Data-Plane Stewardship Authority

## Status

Proposed

## Context

[UIAO_001](../UIAO_001_UIAO-SSOT.md) defines the substrate's drift
taxonomy as six canonical classes: `DRIFT-SCHEMA`,
`DRIFT-SEMANTIC`, `DRIFT-PROVENANCE`, `DRIFT-AUTHZ`, `DRIFT-IDENTITY`,
and `DRIFT-BOUNDARY` (ADR-033). [ADR-012](adr-012-canonical-drift-taxonomy.md) is
explicit that this taxonomy can only be extended via Governance-
Plane-approved ADRs and that existing classes cannot be modified.
ADR-064 ratified the sub-class qualifier mechanism
(`DRIFT-SCHEMA::slot-occupied`); this ADR introduces a *new top-
level* class — `DRIFT-SSOT-CONTENTION` — because the condition it
detects has no parent in the existing five.

The MS SQL Estate Rationalization Process (the inbox draft at
`inbox/Modernization/sql-modernization-research/2026-05-17-orgpath-mssql-estate-rationalization-process.md`)
spec §7.2 identifies an operational pattern the substrate cannot
currently express:

> "After SSOT designation in Phase 3, every write to the demoted
> instances is a contention candidate. The detection mechanism:
> watch the SQL Server Audit log; for each write event whose
> target instance is in the demoted-instances list, classify
> writes to non-cache-eligible columns as `DRIFT-SSOT-CONTENTION`."

The pattern is **not specific to MS SQL**. The same shape applies to:

- HR data after OPM HCM rollout — the agency's legacy HR system
  remains operationally available but no longer canonical. Writes
  to the legacy system after the SSOT designation are contention.
- Finance data after a financial-system-of-record consolidation —
  legacy GL instances may still accept writes that conflict with
  the consolidated SSOT.
- Procurement data after a contract-system migration — vendor
  records may continue to be edited in the demoted system.
- *Any* data-domain consolidation per the rationalization process
  framework.

The existing drift classes cannot fit this condition:

| Existing class | Why it doesn't fit |
|---|---|
| `DRIFT-SCHEMA` | Schema is correct on the demoted instance; the *authority* is the issue, not the structure. |
| `DRIFT-SEMANTIC` | Semantics may be correct; the write is well-formed but to the wrong instance. |
| `DRIFT-PROVENANCE` | Provenance is intact on both instances; the question is which instance *should* be the source. |
| `DRIFT-AUTHZ` | Authorization may be granted; the granted writer is writing to the wrong place. |
| `DRIFT-IDENTITY` | Identity resolution is correct; the principal genuinely exists and is genuinely the writer. |
| `DRIFT-BOUNDARY` | Boundary is enforced correctly; the issue is *which instance* within the same boundary should be authoritative, not where the boundary itself sits. |

The condition is operationally distinct: a write that is structurally
correct, semantically correct, properly provenance-anchored,
authorized, and identity-resolved — but **directed at an instance
that has been canonically demoted in favor of an SSOT**. None of the
existing classes will fire; today the contention is invisible to
automation.

The strategy paper companion to this work (the merged `2026-05-17-sql-modernization-strategy-expansion.md`)
proposed a related class `DRIFT-PERSISTENCE` with sub-class
`::stacked-sor` to detect "two databases both claim authority for
the same data domain". This ADR ratifies a *narrower* and operationally
sharper class: `DRIFT-SSOT-CONTENTION` fires on a specific
*event* (a write to a demoted instance), not on a *configuration*
(two SoRs declared). `DRIFT-PERSISTENCE::stacked-sor` belongs in
its own future ADR; the two classes are peers, not parent-child.

## Decision

1. **New top-level drift class.** Add `DRIFT-SSOT-CONTENTION` as the
   seventh canonical drift class in the substrate's taxonomy. Per
   ADR-012's extension protocol, the existing five classes are
   unchanged.

   The class is **additive**; existing consumers that switch only
   on the original five class names continue to function. Consumers
   that route on the new class must reference this ADR in their
   case-coverage assertion.

2. **Class definition.** A `DRIFT-SSOT-CONTENTION` finding fires when
   all of the following hold:

   1. A canon-blessed **SSOT roster** declares an authoritative
      instance for a data domain (e.g., the rationalization spec's
      `src/uiao/canon/data/mssql-rationalization/ssot-roster.yaml`,
      ratification PR pending).
   2. The same roster declares a non-empty list of **demoted
      instances** for the domain.
   3. A **write event** is observed against a demoted instance.
   4. The write's target table or column is **not** declared in the
      roster's `cache_eligible_columns` allowlist.
   5. The write occurred **within the roster's cutover window**
      (after SSOT ratification, before retirement).

   The finding's payload carries:

   - `claim_id`: the demoted-instance identifier.
   - `domain`: the data domain from the roster (e.g., `HR`,
     `Finance`, `Procurement`).
   - `authoritative_instance`: the SSOT instance the roster points at.
   - `write_event`: the observed write (target table, target column,
     write timestamp, write principal).
   - `reason`: machine-readable code (`"write-outside-cache-allowlist"`).
   - `severity`: P2 default; P1 when the roster's
     `remediation_window_days` has been exceeded.

3. **Severity bands.**

   | Condition | Severity |
   |---|---|
   | First-observed contention; within roster's `remediation_window_days` | P2 |
   | Contention persists past `remediation_window_days` | P1 |
   | Contention against an SSOT in a higher-impact boundary classification | P1 |
   | Contention during a planned cutover-validation window | P3 (informational; expected) |

   The default `remediation_window_days` is 30 days; rosters may
   override per-domain. P3 (informational) findings during planned
   cutover validation are still recorded for audit but do not page.

4. **Detection mechanism (substrate side).** The drift engine
   (UIAO_163) gains a new sub-evaluator
   `SSOTContentionEvaluator` that:

   1. Loads the SSOT roster(s) under `src/uiao/canon/data/*/ssot-roster.yaml`.
   2. Subscribes to write-event sources declared per-domain (e.g.,
      SQL Server Audit logs via the Tier-A2 adapter; HR-system audit
      logs via the HR adapter; ITSM-system audit logs via the GRC
      adapter).
   3. For each write event, evaluates predicates (1)-(5) above.
   4. Emits a `DriftFinding` with `drift_class="DRIFT-SSOT-CONTENTION"`.

   Implementation tracking item: this evaluator does not yet exist
   in the substrate; sizing is captured in the rationalization spec
   §7.5 (Adapter Emission).

5. **Remediation paths.** Per the rationalization spec §7.3, three
   operator decisions close a contention finding:

   - **Re-ratify.** The demoted instance has organically become
     the new authority; swap the roster's authoritative and
     demoted; new PR; governance review; merge.
   - **Re-direct.** The demoted instance is incorrectly
     authoritative; update application connection strings or extend
     the linked-server abstraction's write path to route to the SSOT.
   - **Retire.** The contention is overdue retirement; execute the
     decommission step on the demoted instance per the merge
     playbook.

   Each remediation generates a `remediation_event` row in the
   roster that closes the finding. The finding remains in the audit
   trail indefinitely per the substrate's FedRAMP retention policy.

6. **Audit-trail requirements.** Every `DRIFT-SSOT-CONTENTION`
   finding writes:

   1. The finding itself to the substrate's evidence graph
      (UIAO_113) with the canonical `DriftFinding` schema.
   2. A cross-reference from the finding to the SSOT roster
      entry that defined the demotion (for traceability — *why*
      was this instance demoted? The roster PR is the answer).
   3. A reciprocal-anchor citation (ADR-054 / UIAO_140) when the
      domain in question is also part of an inter-agency
      reciprocity bundle.

7. **Placement in taxonomy.** The seven-class taxonomy after this
   ADR:

   | Class | Detects |
   |---|---|
   | `DRIFT-SCHEMA` | Structural divergence from declared schema |
   | `DRIFT-SEMANTIC` | Semantic correctness violation (freshness, value-domain, referential integrity) |
   | `DRIFT-PROVENANCE` | Source-attribution chain broken or malformed |
   | `DRIFT-AUTHZ` | Authorization grants or denials diverged from policy |
   | `DRIFT-IDENTITY` | Identity-attribution failure (unattributed instance, missing OrgPath cascade) |
   | `DRIFT-BOUNDARY` | GCC-Moderate boundary enforcement divergence (ADR-033) |
   | **`DRIFT-SSOT-CONTENTION`** (new) | **Write directed at a canonically-demoted instance** |

   The new class sits at the same level as the original six; it is
   not a sub-class of any of them.

## Consequences

**Positive.**

- The MS SQL rationalization process's load-bearing drift finding
  (spec §7.2) becomes detectable end-to-end. Without this class,
  the process can ratify SSOT rosters but cannot enforce them.
- The same machinery applies across domains (HR, Finance,
  Procurement, Logistics, Records-Management, etc.) — not just
  MS SQL. The class is product-neutral.
- The class is operationally sharper than `DRIFT-PERSISTENCE::stacked-sor`
  proposed in the strategy paper: it fires on an *event* (a write)
  rather than a *configuration* (two SoRs declared). Both classes
  can coexist; this one is the runtime detector.
- Provides a clean audit signal for FedRAMP authorizers asking
  "how does this system enforce its declared authoritative source"?
  Today the answer is operational discipline; after this ADR the
  answer is a continuous-monitoring finding.

**Negative.**

- Adds a sixth class to a taxonomy ADR-012 deliberately constrained
  to five. The decision to add (vs. sub-class within an existing
  class) is justified by the absence of a fitting parent — see the
  Context section's coverage table — but it does increase taxonomy
  cardinality. Future drift classes will reuse the sub-class
  mechanism wherever possible.
- Detection requires the substrate to ingest write-event audit
  logs from data-plane systems. This is a new ingestion contract;
  each adapter that surfaces a domain's write events implements it
  independently (Tier-A2 MS SQL adapter, HR-system adapter, GRC
  adapter, etc.). The contract is sketched in §4 above and refined
  per-adapter.
- Introduces a hard dependency on the SSOT roster being canon-
  anchored. Without a ratified roster the evaluator has nothing to
  match against; findings cannot fire. This is intentional — drift
  detection presupposes a declared baseline — but it does mean the
  class is operationally inert until the first roster lands.

**Neutral.**

- The class is **additive**; existing consumers that key on the
  original five class names continue working. Consumers that route
  on `DRIFT-SSOT-CONTENTION` must reference this ADR explicitly.
- The class supersedes nothing. Existing `DRIFT-AUTHZ`,
  `DRIFT-PROVENANCE`, and `DRIFT-SCHEMA` findings on the same
  instance continue to fire independently — they detect different
  conditions and remain orthogonal signals.

## Implementation Tracking

The following items must land for this ADR to be operationally
realized. None block ADR acceptance; they are the post-acceptance
work plan.

| Item | Target | Status |
|---|---|---|
| `DriftFinding` schema accepts new `drift_class` enum value | `src/uiao/schemas/drift-engine-config/drift-engine-config.schema.json` (or equivalent) | Pending PR |
| `SSOTContentionEvaluator` implementation | `src/uiao/governance/drift/ssot_contention_evaluator.py` | Pending PR |
| `ssot-roster.yaml` schema | `src/uiao/schemas/ssot-roster/ssot-roster.schema.json` | Pending PR (sized in rationalization spec §9.6-9.8) |
| First production roster (MS SQL, HR domain) | `src/uiao/canon/data/mssql-rationalization/ssot-roster.yaml` | Pending PR (per rationalization spec §9) |
| Drift Detection Standard updated | `docs/docs/16_DriftDetectionStandard.qmd` | Updated in this PR |
| `Drift class registry` (if present) updated | TBD per substrate walker convention | Pending verification |
| Adapter emission for MS SQL | `MSSQLContentAdapter` (Tier-A2) — DM_090 amendment | Pending PR (per rationalization spec §9.3) |

## Review Triggers

This ADR is re-evaluated when any of the following occur:

1. **First-observed contention class collision** — a real-world
   finding turns out to fit one of the original five classes
   better; surface the case at quarterly review.
2. **Strategy paper's `DRIFT-PERSISTENCE` ADR ratifies** — verify
   the two classes remain peers without overlap. If overlap
   emerges, one becomes a sub-class of the other.
3. **Schema-version change to `DriftFinding`** — typically a
   yearly check; this ADR is updated if the finding payload's
   shape evolves.
4. **OPM HCM rollout achieves its first agency cutover** — the
   class's HR-domain applicability is validated against
   production traffic; cutover-window severity bands tuned if
   needed.
5. **UIAO_001 (SSOT) revision adds or removes a drift class** —
   re-anchor this ADR to the revised baseline.

## Open Questions

1. **Sub-class qualifiers.** Should `DRIFT-SSOT-CONTENTION` admit
   sub-class qualifiers (per the ADR-064 mechanism) — e.g.,
   `::pre-cutover`, `::mid-cutover`, `::post-cutover-window`? Not
   ratified here; future ADR if the operational triage queue
   benefits from finer-grained routing.
2. **Multi-tenant SSOT rosters.** ADR-058 (HRIT productization)
   contemplates multi-tenant UIAO deployments. The class definition
   here assumes a single-tenant roster. The multi-tenant case is
   listed in this ADR's Open Questions section but resolved in a
   separate ADR when the multi-tenancy doctrine lands.
3. **Cross-domain contention.** When a write to a demoted
   *HR-domain* instance is observed but the principal is a
   *Finance-domain* steward — does the finding belong to HR's
   roster or Finance's? Default: HR's (the *receiving* domain
   owns the contention). Reviewable.
4. **Read-side contention.** This ADR scopes only to *writes*. A
   consumer that reads from a demoted instance after the SSOT is
   reachable is also a form of contention (it perpetuates the
   stale cache). The strategy paper's `DRIFT-PERSISTENCE::stacked-sor`
   may be the better home for read-side contention; not ratified
   here.

## Relationship to ADR-073 and the Identity-Authority Triad

ADR-073 extended OrgPath policy targeting to a third transport
(NAC). It established that *enforcement-point selection* across
multiple transports must be governed by a single canonical roster
(`policy-targets.yaml`). `DRIFT-SSOT-CONTENTION` extends the same
pattern to *data-plane authority*: enforcement-point selection
(ADR-073) and authoritative-source selection (this ADR) are the
two halves of the substrate's "canonical-choice" doctrine.

A future ADR may unify them under a single
`DRIFT-CANONICAL-CHOICE-CONTENTION` parent class with sub-classes
`::enforcement-point` and `::authoritative-source`. Not ratified
here; flagged for review when the third overlap case arrives.

## Related ADRs

- [ADR-012](adr-012-canonical-drift-taxonomy.md) — Canonical Drift
  Taxonomy (the extension protocol this ADR follows).
- [ADR-054](adr-054-reciprocity-evidence-anchor.md) — Reciprocity
  Evidence Anchor (the audit-trail citation in §6.3).
- [ADR-063](adr-063-orgpath-storage-slot-binding.md) — OrgPath
  Storage Slot (the cascade that this class's `claim_id`
  references inherit).
- [ADR-064](adr-064-drift-schema-slot-occupied-subclass.md) — The
  sub-class qualifier mechanism (this ADR adds a top-level class,
  not a sub-class, but the precedent for taxonomy extension is
  honored).
- [ADR-072](adr-072-canon-publication-policy.md) — Canon
  Publication Policy (this ADR's wrapper qmd and publication
  status follow the policy).
- [ADR-073](adr-073-policy-targeting-nac-third-transport.md) —
  Policy Targeting NAC (the enforcement-point half of the
  canonical-choice doctrine; see §Relationship to ADR-073).
