---
id: ADR-061
title: "FedRAMP CR26 Catalog Vendoring — Authority Posture, Pin Discipline, and Optional `oscal-cli` Round-Trip"
status: proposed
date: 2026-05-10
deciders:
  - canon-steward
  - governance-steward
  - Michael Stratton
supersedes: []
related_adrs:
  - ADR-043
  - ADR-047
canon_refs:
  - UIAO_022
  - UIAO_132
  - UIAO_133
related_findings:
  - FINDING-002
related_issues:
  - WhalerMike/uiao#355
related_discussions:
  - https://github.com/Palladium-Innovations/fedramp-cr26-oscal
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-061-fedramp-cr26-catalog-vendoring.html
---

# ADR-061: FedRAMP CR26 Catalog Vendoring

## Status

**PROPOSED — 2026-05-10.** Records the policy that lets uiao consume
machine-readable FedRAMP CR26 OSCAL artifacts produced by an unofficial
upstream generator without conferring canon authority on the upstream.
Ratification to ACCEPTED is gated on (a) a snapshot landing under
`src/uiao/canon/compliance/reference/fedramp-cr26/snapshot/<sha>/` and
(b) the conformance adapter described in D3 below being registered.
Until then, the only artifact in-tree is the provenance pointer landed
in PR #355.

## Context

PR #355 seeded a provenance pointer at
`src/uiao/canon/compliance/reference/fedramp-cr26/README.md` for
[`Palladium-Innovations/fedramp-cr26-oscal`](https://github.com/Palladium-Innovations/fedramp-cr26-oscal),
a CC0 1.0 Node.js generator that converts FedRAMP Consolidated Rules
2026 (CR26) Public Preview JSON into OSCAL catalogs, profile shells
(20x and rev5), and a CR26 ↔ NIST SP 800-53 rev5 mapping collection.

The pointer closed a gap [`UIAO_133 §1`](../specs/fedramp-20x-integration.md)
explicitly leaves open:

> *individual KSI IDs are catalog-version-dependent and tracked in
> companion mappings as the catalog stabilizes.*

The pointer alone does not give substrate emitters anything to anchor
against — it just names the upstream. Closing the loop requires three
discrete decisions that this ADR records, before any artifact is
vendored or any code consumes it.

### What makes this non-trivial

1. **The upstream is unofficial.** The Palladium repository explicitly
   disclaims affiliation with FedRAMP, GSA, NIST, or the OSCAL project
   and labels its output "experimental, draft analysis aids." Under
   `AGENTS.md` Operating Principle 2 (canon-anchored evidence), every
   artifact uiao emits cites the canon document ID and version it
   derives from. A CR26-catalog-keyed `fedramp:ksi-mapping-source` prop
   that points at an unofficial upstream is a different authority
   shape than the existing rev5 references.
2. **CR26 is Public Preview.** The source data backing the catalog is
   itself in flux. Pinning to a Palladium commit pins to a snapshot of
   a snapshot.
3. **Format mismatch.** Palladium emits XML primary, with JSON/YAML
   derived via NIST `oscal-cli`. uiao's emitters operate on JSON/YAML.
   Round-tripping is either a vendor-time concern (the snapshot ships
   pre-converted JSON/YAML; reviewers trust Palladium's `oscal-cli`
   pass) or a CI concern (a workflow re-runs `oscal-cli` against the
   pinned XML and compares).

## Decision

### D1 — Authority posture: reference, not canon

Vendored CR26 artifacts live under
`src/uiao/canon/compliance/reference/fedramp-cr26/` and are explicitly
**reference material**, parallel to `fedramp-rev5/`. They confer no
canon authority. The doctrinal decisions about KSI emission, scope
classification, and drift remain governed by `UIAO_133` and `ADR-047`.
No row in `document-registry.yaml` is allocated for a CR26 artifact;
the snapshot is data under a reference folder, not a `UIAO_NNN`
governance document.

`fedramp:ksi-mapping-source` props in emitted OSCAL **may** cite a
CR26 control ID resolved through the vendored snapshot, but the
authoritative mapping source remains the UIAO_NNN row that names the
KSI theme. The CR26 ID is a navigational aid, not the authority.

### D2 — Snapshot pin discipline

A vendored snapshot lives at
`src/uiao/canon/compliance/reference/fedramp-cr26/snapshot/<upstream-sha>/`
and is **immutable** once landed. Updating the snapshot means landing a
new sibling directory under a new `<upstream-sha>` and updating the
top-level README's `Pinned commit` row in the same PR. The prior
snapshot directory is retained for one snapshot cycle to keep the
`DRIFT-SCHEMA` and `DRIFT-PROVENANCE` comparison surface alive, then
removed in a follow-up.

A snapshot is in-bounds for vendoring only if the upstream commit:

- Carries a CC0 1.0 dedication (or compatible permissive license) on
  the LICENSE file at that SHA.
- Includes a complete `out/FedRAMP/` tree (catalog, both profile
  shells, mapping collection).
- Has not been force-pushed away from its parent. (Verified by the
  vendoring PR description quoting the parent SHA.)

Snapshot files are not edited in-place. Local modifications are
expressed as overlays under
`fedramp-cr26/overlays/<purpose>/` — paralleling
`canon/data/overlays/` — and overlay PRs cite the snapshot SHA they
target.

### D3 — Conformance adapter registration

A new conformance adapter slot is reserved:

| Field | Value |
|---|---|
| Adapter ID | `fedramp-cr26-catalog` |
| Class | conformance |
| Mission-class | policy |
| Registry | `src/uiao/canon/adapter-registry.yaml` |

The adapter's responsibility is read-only reconciliation between the
vendored CR26 snapshot and `src/uiao/ksi/rules/*.yaml`. It emits two
drift findings:

- `DRIFT-SCHEMA` if the snapshot's catalog shape diverges from the
  prior snapshot in a way that breaks the existing emitter contracts
  (control element changes, namespace shifts, deleted fields).
- `DRIFT-PROVENANCE` if a KSI theme cited in any
  `fedramp:ksi-mapping-source` prop, or any CR26 control ID resolved
  through the snapshot, no longer resolves in the new snapshot.

Adapter registration is a separate PR. This ADR reserves the slot;
the adapter PR adds the registry row and the implementation under
`src/uiao/adapters/fedramp_cr26_catalog/` with happy-path + failure-mode
tests per `AGENTS.md` Operating Rules.

### D4 — `oscal-cli` round-trip is optional and CI-gated

uiao **does not require** `oscal-cli` at runtime. The vendored
snapshot ships the pre-converted JSON/YAML alongside the XML, and
substrate code reads JSON/YAML directly. The `oscal-cli` round-trip
exists in one place only:

- A non-blocking CI job that, when present, re-converts the snapshot's
  XML through `oscal-cli` and asserts byte-equivalence against the
  pinned JSON/YAML. The job is non-blocking for two reasons: (a)
  `oscal-cli` is a Java toolchain that adds runner cost, and (b) minor
  serialization differences (whitespace, attribute order) are routine
  and not actionable.

If the round-trip job is added later, it lives at
`.github/workflows/fedramp-cr26-roundtrip.yml` and runs only on PRs
that touch `fedramp-cr26/snapshot/**`.

## Consequences

### Positive

- **Closes the `UIAO_133 §1` enumeration gap** without claiming
  authority for unofficial upstream content.
- **Stable KSI / control-ID surface** for `fedramp:ksi-mapping-source`
  props, satisfying `UIAO_133 §2.1`.
- **Drift surface is preserved.** The retention-of-prior-snapshot rule
  in D2 keeps the `DRIFT-SCHEMA` / `DRIFT-PROVENANCE` comparison
  meaningful across snapshot cycles.
- **No runtime dependency on a Java toolchain.** uiao stays
  Python-only.

### Negative

- **CR26 churn cost.** Each Public Preview revision that meaningfully
  changes the catalog requires a snapshot-update PR plus reconciliation
  of any drift findings the adapter raises.
- **Storage cost.** XML + JSON + YAML triplicates of the catalog,
  profile shells, and mapping collection are non-trivial repository
  weight. The retain-one-prior-snapshot rule doubles that briefly.
- **Trust shape.** Reviewers must hold in mind that a CR26-keyed prop
  in an OSCAL artifact does not represent FedRAMP authority. The README
  and this ADR are the only mechanisms enforcing that distinction.

### Out of scope

- The full enumeration of which CR26 control IDs map to which uiao KSI
  rule. That mapping is the adapter's responsibility (D3) and lives in
  code + adapter-test fixtures, not in this ADR.
- Tailoring the CR26 20x profile shell into a Low / Moderate / High
  baseline. The Palladium profile output is a shell. uiao's GCC-Moderate
  baseline tailoring lives under `canon/compliance/reference/gcc-
  moderate-boundary-assessment/` and is unaffected by this ADR.
- Any 20x-package-filing logic. Filing is a CSP-side concern tracked
  in [`FINDING-002 §4`](../../../docs/findings/fedramp-20x-moderate-pilot.md);
  this ADR covers only the substrate's emission-side anchoring surface.

## Re-evaluation triggers

This ADR is re-opened when any of the following occur:

1. FedRAMP publishes an official machine-readable CR26 catalog. At
   that point D1 (authority posture) is reconsidered: the official
   catalog likely supersedes the Palladium snapshot, and the reference
   folder is repointed.
2. The Palladium repository is archived, deleted, or relicensed off
   CC0 1.0. D2 (pin discipline) requires CC0; a license change forces
   re-evaluation.
3. The FedRAMP 20x KSI catalog reaches a stable release that closes
   the `UIAO_133 §1` enumeration gap directly. At that point the CR26
   reference may be retired in favor of the canonical 20x catalog.
4. CR26 Public Preview is withdrawn or replaced.
