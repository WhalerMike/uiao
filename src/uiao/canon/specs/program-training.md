---
document_id: UIAO_125
title: "UIAO Training Program — Unified Internal & External Curriculum"
version: "1.0"
status: Current
classification: CANONICAL
owner: "Michael Stratton"
created_at: "2026-04-17"
updated_at: "2026-04-17"
boundary: "GCC-Moderate"
---

# UIAO Training Program

Unified curriculum covering both **internal contributors** (developers,
governance engineers, reviewers) and **external consumers** (agency
operators, auditors, integrators) of the UIAO substrate. This
document is the single entry point for anyone learning UIAO. It
supersedes the adapter-developer-only scope of UIAO_122 by folding
that program into the modules below as the **Adapter Contributor**
track.

---

## 1. Program Structure

The training program is one program with two tracks that share a
common core. A learner picks a track based on their relationship to
the substrate; the shared modules are taken by everyone.

| Track | Audience | Outcome |
|---|---|---|
| **Contributor** | Internal developers, canon stewards, CI engineers | Can land a canon-compliant PR without review blockers |
| **Operator** | Agency users, auditors, integrators | Can run the substrate against their own environment and interpret outputs |

### 1.1 Shared core (required for both tracks)

1. **Substrate Orientation** — what the UIAO substrate is, module
   topology (`core/` authority, `docs/` consumer, `impl/`
   consumer), and the canon-consumer rule.
2. **Vocabulary** — SSOT, canon, provenance, drift (5 classes),
   KSI, OSCAL, mission-class × class taxonomy.
3. **Artifact literacy** — reading the document registry, the two
   adapter registries, and the substrate manifest (UIAO_200).
4. **Governance flow** — how a canon change lands: propose → ADR →
   schema validation → drift scan → merge.

### 1.2 Contributor track

1. Canon change workflow (ADR-first for doctrinal changes).
2. Schema authoring and validation (`core/schemas/` patterns).
3. CI gate topology (6 blocking workflows) and how to make them
   pass locally with `make test` / `make schemas`.
4. Adapter development — architecture, patterns, tooling,
   conformance tests. Materials from the prior UIAO_122 program
   are folded into this module and kept current here.
5. Release engineering — version bumps, tag-triggered release,
   SBOM, sigstore signing, release-drafter categories.

### 1.3 Operator track

1. Substrate walker (`uiao substrate walk`) — first tool to run on
   any environment.
2. Drift interpretation — mapping findings to P1–P4 and to a
   remediation path.
3. Evidence pipeline — how vendor data enters an adapter and exits
   as OSCAL (SAR, POA&M, SSP).
4. Canon-safe customization — what you may change without forking
   (overlays, configuration) versus what requires a canon PR.
5. KSI attestation — generating and verifying evidence bundles.

---

## 2. Delivery Modes

1. **Self-serve written modules** under `core/canon/specs/` and
   `docs/docs/` for reference.
2. **Narrative-led walkthroughs** under `docs/narrative/` using the
   UIAO narrative comics as the top-of-funnel explainer. Comics
   live in `docs/publications/series-assets/`.
3. **Workshop runbooks** for live-facilitated sessions (internal
   onboarding, agency kickoff). Runbooks reference this document
   as the authoritative syllabus.
4. **CLI demonstrations** via `uiao` CLI commands and short
   scripted paths that a learner can execute against the
   repository fixtures.

---

## 3. Assessment

Contributor track completion is demonstrated by landing a
conformance-passing PR that touches at least one canon artifact,
one schema, and one test. Operator track completion is demonstrated
by running `uiao substrate walk` and `uiao substrate drift` against
a fresh clone and correctly interpreting the exit code and any
DRIFT-SCHEMA / DRIFT-PROVENANCE findings.

---

## 4. Maintenance

This program is maintained alongside the substrate it describes.
When a blocking CI workflow is added or removed, when a new drift
class is promoted from roadmap to active, or when a new adapter
mission-class is defined, the corresponding module is updated in
this document in the same PR as the substrate change. Drift between
the training program and the substrate is itself a
DRIFT-PROVENANCE finding.

---

## 5. Cross-References

- UIAO_003 — Adapter Segmentation Overview (taxonomy)
- UIAO_100–UIAO_120 — subsystem specifications
- UIAO_121 — Adapter Conformance Test Plan — Template
- UIAO_122 — Adapter Developer Training Program (folded into
  Contributor track; retained as historical canonical spec)
- UIAO_123 — Adapter Integration & Test Plan — Canonical Template
- UIAO_124 — Adapter Operations Runbook
- UIAO_126 — Test Plans Program
- UIAO_127 — Project Plans Program
- UIAO_128 — Education Program (agency-facing, narrative-led)
- UIAO_200 — Substrate Manifest
- UIAO_201 — Workspace Contract
