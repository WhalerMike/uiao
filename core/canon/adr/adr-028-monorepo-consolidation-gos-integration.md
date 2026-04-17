---
title: "ADR-028: Monorepo Consolidation and Integration of uiao-gos"
adr: "ADR-028"
status: ACCEPTED
date: "2026-04-17"
deciders: ["WhalerMike"]
supersedes: ["ADR-025 §D7 (federal/commercial firewall with uiao-gos)"]
---

# ADR-028: Monorepo Consolidation and Integration of `uiao-gos`

## Status

ACCEPTED

## Context

Through ADR-025 (2026-04-14), UIAO operated as a four-repository ecosystem with
a hard federal/commercial firewall isolating `uiao-gos` (the Governance OS for
Enterprise Directory Migration product) from the FedRAMP-Moderate federal pair
(`uiao-core` + `uiao-docs`) and the `uiao-impl` Python layer. D7 of that ADR
established the firewall contract: no shared canon, no shared secrets, no
cross-referenced artifacts, no shared workflows, no shared branding, enforced
via a planned `firewall-check.yml` CI gate.

Since that decision, two material changes occurred:

1. **Repository consolidation** (2026-04-17). The four repositories were merged
   into a single `WhalerMike/uiao` monorepo with full history preserved
   (`core/`, `docs/`, `gos/`, `impl/` as top-level subdirectories). Operating
   a firewall between directories of the same repository is an order of
   magnitude harder than between repositories: the CI model, secret scope,
   branch-protection surface, and commit visibility are shared by default.

2. **Review of `uiao-gos` contents**. The `uiao-gos` subsystem contains 50
   files implementing a provider framework, drift engine, governance engine,
   evidence store, and two IPAM adapters (BlueCat, Infoblox NIOS). These
   overlap substantially with `uiao-impl`'s existing
   `src/uiao_impl/adapters/` (Entra, M365, Infoblox, ServiceNow) and
   `src/uiao_impl/governance/drift.py`. The two IPAM adapters slot cleanly
   into the existing `modernization-registry.yaml` under
   `mission-class: integration`.

The firewall was designed to prevent federal scope creep into a commercial
product with uncontrolled governance. In the consolidated monorepo with a
single FedRAMP-Moderate boundary posture, that failure mode inverts: the
firewall itself creates scope drift because it invites the commercial product
to diverge from the federal invariants (`gcc-boundary: gcc-moderate`,
`ssot-mutation: never`, `certificate-anchored: true`,
`object-identity-only: true`) rather than inherit them.

## Decision

The firewall established in ADR-025 §D7 is **retired**. `uiao-gos` as a
separate commercial product is dissolved. Its contents are integrated into
the canonical UIAO substrate:

1. **Adapter canon entries.** The BlueCat and Infoblox NIOS adapters are
   registered in `core/canon/modernization-registry.yaml` as
   `bluecat-address-manager` and `infoblox` respectively, both conforming to
   `core/schemas/adapter-registry/adapter-registry.schema.json`. The former
   custom `adapter-manifest.json` schema is retired.

2. **Reference implementation.** The Python code under `gos/core/*` is
   relocated to `impl/src/uiao_impl/directory_migration/*`, preserving the
   subsystem identity under a neutral (non-commercial) name. Full file
   history is preserved via git rename detection.

3. **Narrative documentation.** The former `gos/README.md` is preserved as
   `docs/narrative/governance-os-directory-migration.md` for historical
   context; the commercial-firewall framing in the header is retired.

4. **Canon invariants apply uniformly.** Every directory-migration adapter
   is subject to the same invariants as any other modernization adapter:
   `gcc-boundary: gcc-moderate`, `ssot-mutation: never`,
   `certificate-anchored: true`, `object-identity-only: true`.

5. **`firewall-check.yml` is withdrawn.** The planned CI gate is no longer
   needed because there is nothing to firewall against. The controls that
   prevent federal scope creep are now the ordinary canon gates
   (`metadata-validator`, `drift-scan`, `canon-validation`) applied
   uniformly across the monorepo.

## Consequences

**Positive.**

- **One canon, one boundary, one audit trail.** Every adapter in the
  monorepo is governable with the same schemas, registries, and drift-scan
  machinery.
- **No firewall maintenance burden.** No parallel CI, no parallel
  architecture document, no firewall-check enforcement logic to build and
  maintain.
- **Commercial-variant adapters are first-class.** BlueCat (not
  FedRAMP-authorized) sits next to Infoblox NIOS (FedRAMP-authorized,
  CDM-integrated, federal-preferred) in the same registry. Consumers choose
  by manifest field, not by repository.

**Negative / tradeoffs.**

- **ADR-025 §D7 is now stale.** It remains in the canon as the historical
  record of the firewall decision but is explicitly superseded by this ADR.
  The text is not rewritten; instead, this ADR's `supersedes` frontmatter
  field captures the relationship.
- **`core/ARCHITECTURE.md` §2.2 and scope statements require a coordinated
  UPDATE.** Retained as follow-up edits in the same PR that introduces this
  ADR.
- **Commercial-branding cleanup.** The strings "commercial product",
  "federal pair", and "firewalled from the federal pair" remain embedded in
  older canon documents (roadmap, retrospectives, changelog entries). They
  are historical artifacts, not live doctrine, and will be corrected
  opportunistically under the version-isolation principle.

**Neutral.**

- **Code reconciliation is out of scope for this ADR.** The overlap between
  `impl/src/uiao_impl/adapters/*.py` and
  `impl/src/uiao_impl/directory_migration/providers/*/` (e.g. two
  `entra_adapter.py` files) is tracked as follow-up and governed by a
  subsequent ADR if a doctrinal decision is required; the mechanical
  de-duplication itself is ordinary engineering.

## References

- ADR-025 §D7 (superseded)
- `core/ARCHITECTURE.md` §2.2 (updated in the same PR as this ADR)
- `core/CONMON.md` (updated in the same PR)
- PR #3 — `gos/` dissolution and adapter integration
- PR #4 — substrate initialization (UIAO_200 manifest)
- `core/canon/modernization-registry.yaml` — `bluecat-address-manager`,
  `infoblox` entries
- `core/canon/substrate-manifest.yaml` — UIAO_200 declares the 3-module
  post-integration layout
