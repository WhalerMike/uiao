---
adr_id: adr-076
title: "UIAO Five-Tier Capability Conformance Model"
status: PROPOSED
decided: 2026-05-22
deciders: Michael Stratton
updated: 2026-05-22
next_review: 2026-11-22
review_trigger: Material change to a capability's tier definition; first agency conformance declaration; introduction of conformance schema validator
impact: 'Establishes a five-tier capability model (Passive Observation → Embedded Libraries), per-capability tier declarations (Identity / Compliance / KYC / Substrate / Platform), a headline tier for procurement, and the GitHub-source / Platform-Server-release lifecycle distinction. Resolves canon-vs-customer doctrinal conflicts surfaced by the 2026-05-22 cross-surface review. Adds an optional `conformance_tier` frontmatter field permitted by the existing metadata schema (`additionalProperties: true`). No existing doc is retired; tier annotation is deferred to a follow-up sweep.'
supersedes: null
superseded_by: null
classification: Controlled
boundary: GCC-Moderate
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-076-tier-conformance-model.html
---

# ADR-076: UIAO Five-Tier Capability Conformance Model

## Status

**PROPOSED** — 2026-05-22.

## Context

A cross-surface review of the published site on 2026-05-22 compared
the canon index at `/modernization/`, the customer portal at
`/customer-documents/`, and the deployment guidance at
`/customer-documents/platform/`. The review found doctrinal conflicts
on shared subjects, not merely organizational differences:

1. **Status labels contradict.** Canon `/modernization/` blanket-labels
   OrgTree, Directory Migration, and Intune-First Asset Onboarding as
   "Aspirational — canonically declared, not yet fully adopted." The
   customer-side guides on the same subjects ship as **v1.0** with
   quantitative success criteria (e.g., "100% SRV resolution for 30
   consecutive days", "object count in Entra matches expected count
   (±1%)"). A federal reader using both gets opposite authority signals.

2. **Governance principles count disagrees across documents.** Canon
   `/modernization/` declares **seven** non-negotiable principles.
   The customer Governance OS Executive Brief declares **three**. The
   OrgPath Narrative chapter 15 names only **one** explicitly. These
   are not different vocabularies for the same set — they are
   different conceptual models.

3. **"Intune-First" has two non-overlapping meanings.** Canon
   `intune-first-onboarding` is net-new asset doctrine with a 14-day
   procurement-to-production SLA. Customer `intune-policy-templates`
   is a 7-phase library replacing GPOs on the existing fleet. Same
   name, different scope.

4. **Phase counts disagree on the same migration.** Canon
   `directory-migration` specifies 5 phases. Customer DNS Modernization
   Guide specifies 10. Customer PKI Modernization Guide specifies 6.
   None refines another.

5. **OrgPath attribute semantics differ.** Canon `orgtree` example:
   `extensionAttribute1: FIN-BUD-EAST` (composite path in a single
   slot). Customer Identity Modernization Guide:
   `extensionAttribute1=Region, extensionAttribute2=Department,
   extensionAttribute3=Division` (one facet per slot). These produce
   mutually incompatible dynamic-group rules in production.

The root cause is that UIAO has no explicit conformance model.
Different documents assume different adoption levels and present them
as universal. Customer-side guides describe what a fully deployed
agency operates; canon-side framing describes the source repository's
declared-but-not-yet-adopted state. The two are both true of different
adoption levels but produce contradictions when treated as describing
the same thing.

Federal IT already adopts software at varying maturity levels. NIST
CSF defines four Tiers (Partial → Adaptive); CMMC defines three Levels;
FedRAMP defines Low/Moderate/High impact baselines; Microsoft 365
defines E3/E5/G5 license tiers. Agencies are accustomed to declaring
conformance levels per capability and to recognizing that lower-tier
adopters consume a strict subset of higher-tier capabilities.

UIAO needs an analogous model.

## Decision

UIAO is a **five-tier capability model**. Agencies declare a tier
**per capability** (not a single monolithic tier). For procurement and
exec-brief use, agencies may publish a **headline tier** equal to the
maximum tier reached across declared capabilities, accompanied by the
per-capability breakdown. Tier N+1 schemas are a **strict superset**
of Tier N schemas — upgrading does not require re-stamping existing
state, re-running migrations, or breaking dynamic group rules
authored at the lower tier.

The GitHub repository is the **source** of UIAO; the Platform Server
is the **released, signed, revision-controlled artifact** that
agencies deploy. These are two distinct lifecycle stages of the same
code, with distinct authority for "what is shipped."

### The Five Tiers

| Tier | Name | Mutates agency systems? | Runs where | Typical artifacts |
|---:|---|---|---|---|
| **1** | Passive Observation | No | Anywhere with read credentials | Discovery scanners, drift detectors, validators, query CLI (`uiao query orgpath user@agency.gov`), OSCAL evidence emitters |
| **2** | Transformative Authoring | No (writes files, not live systems) | CI, operator workstation | Schema and document generators, AD-OU-to-OrgPath translators, GPO-to-Intune translators, migration plan generators |
| **3** | Active Substrate | Yes — writes agency tenant state | Agency service account | Dynamic group writers, OrgPath value stampers, Conditional Access policy publishers, in-bounds drift remediators |
| **4** | Active Services | Yes — owns its own state | Agency-deployed UIAO server | Platform Server (Windows Server 2025 + Gitea + IIS + OrgTree), KYC broker, operator web console, orchestrator daemon, evidence-fabric signing service |
| **5** | Embedded Libraries | N/A — consumed by other code | Inside customer applications and adapters | PowerShell module, adapter SDK, policy-as-code DSL, validation libraries published to PyPI / NuGet |

A higher tier always *includes* the lower tiers as a strict subset.
An agency at Tier 4 for Identity is also implicitly conformant at
Tiers 1, 2, and 3 for Identity.

### The Five Capabilities

A capability is a coherent UIAO surface against which conformance is
declared independently. The initial capability set is fixed at five:

| Capability | Scope |
|---|---|
| **Identity** | OrgTree, OrgPath, dynamic groups, delegation, identity-related drift |
| **Compliance** | SCuBA, FedRAMP, CISA, OSCAL evidence, control mapping, ConMon |
| **KYC** | Citizen↔agency and inter-agency identity verification, SSN-equivalent SSOT brokering |
| **Substrate** | Operational tooling, PowerShell module, CLI, Quarto pipeline, generators |
| **Platform** | Platform Server, deployed UIAO services, release artifacts, HA topology |

Capabilities may be added in future ADRs; existing capabilities may
not be removed or merged without a superseding ADR. The set is fixed
to prevent unbounded matrix growth.

### Declaration Format

An agency conformance declaration is structured as:

```yaml
# Example: an agency mid-adoption
agency: Example Federal Agency
declared: 2026-05-22
conformance:
  Identity: 3      # Active Substrate — UIAO writes Entra
  Compliance: 2    # Transformative — UIAO generates OSCAL evidence locally
  KYC: 0           # Not declared
  Substrate: 2     # Transformative — agency runs UIAO CLI in CI
  Platform: 0      # Not declared — no Platform Server deployed
headline_tier: 3
headline_basis: Identity
```

Tier `0` denotes "not declared / not adopted." It is not a
conformance level; it is the absence of one.

The headline tier MUST cite the capability that justifies it.
"Headline Tier 4" without a per-capability breakdown is not a valid
declaration.

### Strict Subset Rule (Backward Compatibility)

Tier N+1 schemas, frontmatter fields, and artifact contracts MUST be
a strict superset of Tier N. Specifically:

- A Tier 1 agency's OrgPath values MUST remain valid input to Tier 3
  tooling without re-stamping.
- A Tier 2 agency's generated artifacts (translation outputs, plan
  documents) MUST remain valid input to Tier 4 tooling.
- A schema change that breaks this rule requires a new major version
  of the Platform Server and explicit migration tooling shipped with
  it.
- The conformance schema validator (future ADR) enforces this rule
  at CI time.

### Repository vs Platform Server

| Surface | Role | Authority |
|---|---|---|
| **GitHub repository** | Source. Pre-release. Architecture and tooling under active development. | Authoritative for "what UIAO is becoming." |
| **Platform Server** | Released artifact. Versioned. Signed. Revision-controlled. Agency-deployed. | Authoritative for "what UIAO IS, at version X.Y.Z." |

Canon documents in the repository legitimately label themselves
"Aspirational" because the repository is by definition pre-release.
Customer-side guides describing Platform Server v1.0 behavior
legitimately label themselves "v1.0 shipped." These are not
contradictions — they are correct claims about different lifecycle
stages.

This boundary requires release engineering machinery that does not
yet exist in the repository: tagged releases with cryptographic
signatures, SLSA-style provenance from build to deployed binary, a
release channel agencies subscribe to (distinct from `git pull`),
release notes declaring schema compatibility across versions, and a
rollback path. Closing this gap is itself a Tier-4 code-surface
investment and is the subject of a follow-up ADR.

## Rationale

1. **Per-capability tier is more honest than monolithic.** An agency
   may be mature in Identity (UIAO writes Entra) while not having
   declared KYC adoption at all. A single tier label hides this and
   produces unrealistic claims.

2. **Strict-subset upgrade is the only model that supports
   progressive adoption.** Agencies will not adopt Tier 1 if the
   upgrade to Tier 3 requires re-stamping every user's OrgPath
   values. Backward-compatibility discipline is the cost of being
   adoptable at lower tiers.

3. **The repository / Platform Server distinction resolves the
   "aspirational vs shipped" status conflict without rewriting any
   existing label.** Canon labels are correct at the repository level
   ("not yet adopted"). Customer guides are correct at the release
   level ("v1.0 shipped"). The conflict only appeared because the
   two lifecycles were unstated.

4. **The "Two-Brain" canon doctrine and the "not a standalone
   product" customer framing are both correct at different tiers.**
   Tier 1 + 2 adopters consume UIAO as a discipline + CLI; UIAO is
   not a standalone product to them. Tier 4 adopters deploy a
   Platform Server; UIAO is a product to them. Both descriptions are
   true; neither is universal.

5. **Federal procurement already understands tier models.** NIST
   CSF, CMMC, and FedRAMP have trained agency procurement and
   security staff to think in capability tiers. UIAO meets them
   where they are.

6. **Five tiers is enough and not too many.** Three would collapse
   the meaningful distinction between Active Substrate (mutates
   agency tenant) and Active Services (UIAO owns its own state).
   Seven would over-specify and invite micro-tier debates.

## Consequences

### Positive

- Canon and customer surfaces can stop contradicting each other on
  status. Status labels become tier-anchored.
- Agencies can declare incremental adoption honestly.
- "Intune-First" disambiguates by tier: Tier 1 = procurement
  discipline, Tier 3 = SLA validator, Tier 4 = Platform Server
  enforcement. **(Superseded by [ADR-080](adr-080-intune-first-scope-disambiguation.md).** The tier-scoping above
  collapsed three genuinely different programs — Intune-First Asset
  Onboarding (net-new), GPO Sunset Program (existing fleet), and the
  Policy Transformation Pattern (philosophy) — into one tier ladder.
  Per ADR-080 each program has its own independent tier expression:
  Intune-First Asset Onboarding is Tier 1+; GPO Sunset Program is
  Tier 3+; Policy Transformation Pattern applies as guidance at all
  tiers.)
- "OrgPath attribute semantics" disambiguates by tier: composite-path
  is a Tier 1 expression of intent; single-facet-per-attribute is the
  Tier 3 storage contract.
- Principles count disambiguates by tier: a small core set is
  universal; additional principles attach at higher tiers (e.g.,
  Two-Brain Execution applies Tier 3+; Boundary Enforcement applies
  Tier 4).
- Phase counts disambiguate as level-of-detail: canon's 5-phase DM
  view is the Tier-2 plan-generator output; customer DNS 10-phase
  and PKI 6-phase are Tier-3 runbooks that refine specific phases
  for specific adapters.
- Procurement gets a defensible model that matches FedRAMP / CMMC /
  NIST CSF idioms.

### Negative

- **Existing doc backfill.** Canon docs and customer guides need
  tier annotations (a `conformance_tier` frontmatter field plus a
  visible banner). Defaults can cover the common case (a doc
  describing Platform Server behavior is Tier 4 by default), but
  explicit declarations are preferred for auditability. Backfill is
  a follow-up sweep, not a precondition.
- **Conformance schema validator does not yet exist.** The
  strict-subset rule is binding doctrine but has no automated
  enforcement until a follow-up ADR introduces the validator.
- **Release engineering gap is now explicit.** The repository /
  Platform Server distinction names a layer of code that does not
  yet exist (tagged releases, signed artifacts, release channel).
  The gap is real today; this ADR makes it visible.

### Risks

- **Per-capability matrix can fragment.** If capabilities multiply
  beyond five without discipline, conformance declarations become
  unparseable. Mitigation: the capability set is fixed at five;
  changes require an ADR.
- **Headline tier can be gamed.** An agency at Tier 4 for KYC and
  Tier 0 elsewhere could publish "Headline Tier 4." Mitigation:
  every headline MUST cite the capability that justifies it; the
  per-capability breakdown is required, not optional.
- **Strict-subset rule is hard to maintain.** Real-world schema
  evolution will be tempted to break the rule for clarity.
  Mitigation: a schema-diff CI gate in a follow-up ADR; until then,
  reviewer discipline.
- **Tier inflation.** Customer-facing material may drift toward
  describing everything as Tier 3+ even when Tier 1 is the honest
  level. Mitigation: tier annotations require frontmatter and
  visible banners; reviewers can challenge unsupported claims.

## Verification Sources

| Source | Reference | Last Verified |
|---|---|---|
| Cross-surface review identifying the five conflicts | This conversation, 2026-05-22 (live audit of `/modernization/`, `/customer-documents/`, `/customer-documents/platform/` pages) | 2026-05-22 |
| Metadata schema | [`src/uiao/schemas/metadata-schema.json`](../../schemas/metadata-schema.json) — `additionalProperties: true` already permits the new `conformance_tier` field | 2026-05-22 |
| ADR-072 frontmatter precedent | [`adr-072-canon-publication-policy.md`](adr-072-canon-publication-policy.md) | 2026-05-22 |
| Federal tier-model precedent | NIST CSF Tiers 1–4; CMMC Levels 1–3; FedRAMP Low/Mod/High | (external) |

## Review Triggers

This ADR must be re-evaluated when any of the following occur:

- [ ] A first agency publishes a conformance declaration — review
      whether the declaration format works in practice
- [ ] A capability is proposed for addition to or removal from the
      fixed five-capability set
- [ ] A schema change is proposed that would violate the strict-subset
      rule between tiers
- [ ] The Platform Server release engineering layer ships — review
      whether the source / release distinction holds up under
      versioned release operations
- [ ] A conformance schema validator ADR is proposed
- [ ] 2026-11-22 — scheduled six-month review

## Related Documents

- [ADR-000 — ADR Process and Lifecycle](adr-000-adr-process.md)
- [ADR-072 — Canon Publication Policy](adr-072-canon-publication-policy.md) — provides the `publish_to_site` frontmatter machinery that the new `conformance_tier` field plugs into
- [ADR-071 — Intune-First Asset Onboarding](adr-071-intune-first-asset-onboarding.md) — recipient of the Tier 1 / Tier 3 / Tier 4 disambiguation
- [`docs/conformance/index.qmd`](../../../../docs/conformance/index.qmd) — human-readable explainer for the five-tier model
- [`src/uiao/schemas/metadata-schema.json`](../../schemas/metadata-schema.json) — schema accepts the new optional `conformance_tier` field
