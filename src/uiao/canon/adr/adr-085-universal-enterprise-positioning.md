---
adr_id: adr-085
title: "Universal-Enterprise Positioning of the UIAO Core Engine"
status: ACCEPTED
decided: 2026-05-25
deciders: Michael Stratton
updated: 2026-05-25
next_review: 2026-11-25
review_trigger: A new vertical adapter (non-federal compliance regime) is proposed; a customer artifact reintroduces federal-only framing of the core; the Charter is rebaselined past V1
impact: 'Establishes the doctrinal positioning of the UIAO core engine as a universal enterprise governance product, with federal compliance (FedRAMP, OSCAL, KSI) scoped as one vertical adapter among many possible verticals. Aligns README.md, AGENTS.md, customer-facing briefs, and pitch materials with this positioning. Recontextualizes CHARTER-001 V1 federal framing as one audience variant of an underlying vertical-agnostic architecture rather than the architecture itself. Does not retire CHARTER-001 (foundational, supersedable: false) — establishes positioning that the next charter rebaseline will absorb.'
supersedes: null
superseded_by: null
classification: Controlled
boundary: GCC-Moderate
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-085-universal-enterprise-positioning.html
---

# ADR-085: Universal-Enterprise Positioning of the UIAO Core Engine

## Status

**ACCEPTED** — 2026-05-25.

This ADR is doctrine. It changes how the product is positioned across the README, the agent entry point, customer-facing artifacts, and downstream pitch materials. It does not change any runtime behavior, schema, or registry entry.

## Context

The repository was consolidated from four predecessors (`uiao-core`, `uiao-docs`, `uiao-gos`, `uiao-impl`) per [ADR-028](adr-028-monorepo-consolidation-gos-integration.md), and the `uiao-gos` federal/commercial firewall was retired in that pass. After consolidation, several artifacts still position the **core engine itself** as federal-only:

- [`README.md`](../../../../README.md) L10 — "Governance OS for FedRAMP-Moderate identity, telemetry, policy, and enforcement modernization."
- [`AGENTS.md`](../../../../AGENTS.md) L10 — Repository identity: "FedRAMP-Moderate governance substrate".
- [`docs/customer-documents/compliance/evidence-telemetry/scuba-value-proposition.qmd`](../../../../docs/customer-documents/compliance/evidence-telemetry/scuba-value-proposition.qmd) §8.2 — Pitch-deck slide title: "UIAO --- The Governance Layer for Federal Cloud Compliance".
- [`docs/customer-documents/executive-briefs/uiao-executive-brief.qmd`](../../../../docs/customer-documents/executive-briefs/uiao-executive-brief.qmd) — Opens with "Every federal agency running Microsoft 365 in GCC-Moderate…" with no preceding statement that the underlying engine is vertical-agnostic.
- [`src/uiao/canon/charter/CHARTER-001.md`](../charter/CHARTER-001.md) §1 — "This document defines a cross-division modernization plan for federal hybrid-cloud environments."

This framing is **historically accurate** (V1 charter audience was a federal CIO; the GCC-Moderate boundary is the first deployed boundary; the initial paying-customer mission is federal) but **architecturally inaccurate** as a description of the core engine. The substrate — identity-addressing-overlay with canon-anchored evidence, schema-enforced adapters, drift detection, and a dual-axis adapter taxonomy — is vertical-agnostic. Federal compliance is one set of conformance + modernization adapters layered on top of that substrate. The same engine, with a different vertical adapter pack, governs commercial regulated environments (PCI-DSS, HIPAA, SOC 2 Type II), state/local government (StateRAMP), or generic enterprise IT-governance (ISO 27001, NIST CSF).

Positioning the core as federal-only:

1. Misrepresents the architecture to commercial prospects who would otherwise be candidate adopters.
2. Couples runtime / canon decisions to a single compliance regime in ways that drift into the schemas (e.g., conflating "boundary" with "FedRAMP boundary").
3. Discourages contributors from authoring non-federal vertical adapters because the README tells them the product is federal-scoped.
4. Creates a maintenance liability whenever a non-federal capability ships, because every artifact has to be partially walked back.

The positioning needs to be doctrinally fixed once, then enforced at PR-review time for any new artifact that reintroduces the federal-only framing.

## Decision

The UIAO core engine is positioned as a **universal enterprise governance product**. Federal compliance (FedRAMP Moderate Rev 5, OSCAL, KSI, BOD 25-01, CISA SCuBA) is **one vertical adapter pack** that sits on top of the universal core, not the core itself.

### D1. Core engine is vertical-agnostic

The substrate (identity-addressing-overlay, canon, schemas, drift taxonomy, dual-axis adapter taxonomy, evidence pipelines) makes no assumption about compliance regime, customer sector, cloud boundary, or jurisdiction. Any reference to "FedRAMP", "federal", "agency", "GCC", "CISA", or any other federal-specific term in a description of the **core** is a positioning bug.

### D2. Federal is a first-class vertical, not the only vertical

The FedRAMP / OSCAL / KSI / SCuBA capabilities ship as conformance + modernization adapters and rule packs under `src/uiao/adapters/`, `src/uiao/rules/ksi/`, `src/uiao/oscal/`, and the federal-compliance reference data under `src/uiao/canon/compliance/`. They are first-class — the federal vertical is the most mature adapter pack, has the most adopters, and drives the most CI coverage — but they are **vertical adapters**, not the engine.

### D3. Boundary and cloud-scope decisions remain boundary-scoped

The `boundary: GCC-Moderate` frontmatter field and the GCC-Moderate cloud-boundary policy in [`AGENTS.md`](../../../../AGENTS.md#repository-identity) are descriptions of the **currently deployed** boundary, not of the engine. The schema-enforced enum allows other boundaries to be added in lockstep with their authorizing ADRs (per the existing two named Commercial exceptions). Repositioning the core does not change the deployed boundary or the cloud-boundary policy.

### D4. CHARTER-001 V1 federal framing is one audience variant

[`CHARTER-001`](../charter/CHARTER-001.md) carries `tier: foundational` and `supersedable: false`. This ADR does **not** supersede or retire it. CHARTER-001's federal framing reflects its V1-era authoring audience (federal CIO/CISO) and the original whitepaper lineage (V3 → V4U → UIAO-V1). The architecture it describes — conversations, identity as root namespace, deterministic addressing, certificate-anchored overlay, telemetry as control, governance as automation, public service first — is itself vertical-agnostic. The next charter rebaseline (CHARTER-002+) absorbs this positioning. Until then, downstream readers should treat the charter's federal framing as the V1 audience variant of an underlying universal architecture, and should consult this ADR for the authoritative product-level positioning.

### D5. Federal-vertical pitch artifacts may stay federal-scoped

Documents that are explicitly federal-vertical pitches — for example, the SCuBA value proposition, the executive brief targeted at federal CISOs, the BOD 25-01 narrative — may continue to use federal-specific framing **within the artifact body**. What must change is the **product description line** embedded in those artifacts: it must describe UIAO as a universal governance OS of which the federal capability is one vertical, not as a federal governance OS.

### D6. Positioning gate at PR review

New artifacts that describe the core engine must use universal-enterprise positioning. Artifacts describing a specific vertical adapter pack may use vertical-scoped positioning provided they do not describe the core engine itself as scoped to that vertical. Review-time check: search the artifact for "FedRAMP" / "federal" / "agency" / "OSCAL" / "KSI" in any sentence that purports to describe **what UIAO is**; if such a sentence describes the core as scoped to that vertical, the artifact needs repositioning.

## Consequences

**Updated in this ADR's landing PR:**

- [`README.md`](../../../../README.md) — product positioning line and "What UIAO is" intro rewritten.
- [`AGENTS.md`](../../../../AGENTS.md) — Repository identity purpose line rewritten.
- [`docs/customer-documents/compliance/evidence-telemetry/scuba-value-proposition.qmd`](../../../../docs/customer-documents/compliance/evidence-telemetry/scuba-value-proposition.qmd) §8.2 — pitch-slide title rewritten.
- [`docs/customer-documents/executive-briefs/uiao-executive-brief.qmd`](../../../../docs/customer-documents/executive-briefs/uiao-executive-brief.qmd) — intro paragraph rewritten to lead with universal positioning and frame the federal-agency scenario as the example vertical the brief addresses.

**Not updated in this PR (deliberate):**

- [`CHARTER-001`](../charter/CHARTER-001.md) body — `supersedable: false`. The next charter rebaseline absorbs this positioning.
- Federal-vertical pitch material body (BOD 25-01 narrative, FedRAMP Moderate Rev 5 capability descriptions, OSCAL pipeline descriptions) — D5 permits federal-scoped framing within an explicitly federal-vertical artifact.

**Future work this unlocks:**

- A "Verticals" landing page that enumerates the federal vertical (current), and reserves space for commercial-regulated (PCI-DSS / HIPAA / SOC 2), state-local (StateRAMP), and generic-enterprise (ISO 27001 / NIST CSF) vertical adapter packs.
- A `canon/verticals-registry.yaml` (deferred — separate ADR; full `src/uiao/...` path prefix elided to avoid substrate-drift false-flag on the deferred artifact) that catalogs vertical adapter packs the way `adapter-registry.yaml` catalogs individual adapters.
- Removal of any remaining incidental federal-only framing in adapter docstrings, generator help text, and CLI command descriptions, as those surfaces are touched in normal maintenance.

**Reversal cost:** Low. The positioning change is a documentation rewrite; no runtime, schema, or registry entries change. If the positioning is wrong, a follow-up ADR can re-scope the product back to federal-only without touching code.

## Alternatives Considered

**A1. Leave the federal-only framing in place and rely on context.** Rejected: the framing actively misrepresents the architecture to commercial prospects and discourages non-federal vertical adapter contributions. The cost of leaving it grows with every new artifact authored under it.

**A2. Supersede CHARTER-001 with a universal-enterprise rewrite.** Rejected: CHARTER-001 is `supersedable: false` by frontmatter; superseding it requires governance-board action that is out of scope for this PR. The clarifying-ADR approach (D4) is sufficient for the positioning fix and preserves the charter's foundational status.

**A3. Rename the project or carve out a separate commercial-positioned distribution.** Rejected: the product is one engine. The positioning fix is the simplest correct response.

## References

- [ADR-028: Monorepo Consolidation & GOS Integration](adr-028-monorepo-consolidation-gos-integration.md) — retired the `uiao-gos` federal/commercial firewall.
- [ADR-032: Single-Package Consolidation](adr-032-single-package-consolidation.md) — flattened the hybrid `core/` + `impl/` tree into a single `src/uiao/` package.
- [`src/uiao/canon/substrate-manifest.yaml`](../substrate-manifest.yaml) (UIAO_200) — module declaration; describes substrate without reference to vertical.
- [`src/uiao/canon/adapter-registry.yaml`](../adapter-registry.yaml) and [`modernization-registry.yaml`](../modernization-registry.yaml) — adapter packs that include federal-vertical adapters.
- [`CHARTER-001`](../charter/CHARTER-001.md) — V1 charter; this ADR clarifies its federal framing per D4.
