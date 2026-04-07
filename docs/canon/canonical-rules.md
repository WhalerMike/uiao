---
title: "UIAO Canonical Rules"
status: ACTIVE
version: "1.0"
last_updated: "2026-04-07"
---

# UIAO Canonical Rules

The Canonical Rules define the immutable governance constraints for the Universal Integration Adapter Orchestration (UIAO) framework. All architecture decisions, adapter implementations, and fabric configurations MUST conform to these rules.

## CR-001 — Deterministic Artifact Separation

**Rule:** All UIAO artifacts MUST be classified as either *machine* artifacts or *human* artifacts. No artifact may belong to both classifications.

**Machine artifacts** are stored exclusively in the `uiao-core` repository. These include adapter schemas, orchestration logic, drift-detection algorithms, evidence manifests, and any artifact consumed directly by automated processes.

**Human artifacts** are stored exclusively in the `uiao-docs` repository. These include governance documents, architectural decision records, appendices, diagrams, glossaries, migration plans, and any artifact intended for human interpretation.

**Rationale:** Mixing machine and human artifacts creates ambiguity in ownership, versioning, and deployment pipelines. Deterministic separation ensures that `uiao-core` can be consumed by CI/CD tooling without inadvertently pulling human-readable governance prose, and that `uiao-docs` can be published as a documentation site without exposing executable logic.

**Enforcement:** The `Initialize-UIAOCanonStructure.ps1` script enforces directory separation at scaffold time. CI checks validate that no `.md` governance files land in `uiao-core` outside of `docs/`, and that no `.ps1`, `.json`, or `.yaml` machine artifacts land in `uiao-docs` outside of `scripts/` or `data/`.

---

## CR-002 — Single Source of Truth (Canon DOCX)

**Rule:** The UIAO Governance Canon Master Document (DOCX) is the authoritative source for all governance content. Any content published to `uiao-docs` MUST be traceable to a specific section, appendix, or ADR in the Canon DOCX.

**Corollary:** Content labeled `[NEW (Proposed)]` has been generated for structural completeness and has NOT yet been ratified against the Canon DOCX. Such content MUST be reviewed and either confirmed, revised, or rejected before the document is considered ACTIVE.

**Rationale:** Without a single authoritative source, governance documents drift. Multiple partially-correct versions proliferate, creating confusion about which rules apply. The Canon DOCX serves as the ratification anchor.

**Enforcement:** All stub files created by `Initialize-UIAOCanonStructure.ps1` carry `status: MISSING` in their frontmatter. Files are promoted to `status: DRAFT` when placeholder content is inserted and `status: ACTIVE` only after explicit ratification against the Canon DOCX.

---

## CR-003 — ADR Immutability

**Rule:** Once an Architectural Decision Record (ADR) is marked `status: ACCEPTED`, its **Context**, **Decision**, and **Date** fields are immutable. Amendments require a new superseding ADR.

**Supersession pattern:** The superseding ADR MUST include a `supersedes: ADR-NNN` field in its frontmatter, and the superseded ADR MUST be updated to include `superseded_by: ADR-MMM` in its frontmatter.

**Rationale:** ADRs serve as an audit trail for architectural decisions. Retroactively modifying accepted ADRs destroys the integrity of the audit trail and makes it impossible to reconstruct why the system was built as it was.

**Enforcement:** Branch protection on `uiao-docs/main` prevents direct edits to accepted ADRs without a bypass. Governance review is required to approve any bypass that touches an accepted ADR's immutable fields.

---

## CR-004 — Fabric Orthogonality

**Rule:** The three operational fabrics — **Truth Fabric**, **Drift Fabric**, and **Evidence Fabric** — MUST operate orthogonally. A change to one fabric's schema or orchestration logic MUST NOT require changes to another fabric's schema or orchestration logic.

**Truth Fabric** owns: canonical state records, adapter registration, schema definitions.  
**Drift Fabric** owns: deviation detection, delta computation, reconciliation triggers.  
**Evidence Fabric** owns: audit events, immutable log entries, compliance attestations.

**Rationale:** Orthogonality ensures that each fabric can be scaled, versioned, and deployed independently. It also ensures that failures in one fabric do not cascade into others, preserving the isolation guarantees required for enterprise governance.

**Enforcement:** ADR-007 (Fabric Schema Isolation) and ADR-008 (Drift Trigger Protocol) formalize the interface contracts between fabrics. Any cross-fabric dependency MUST be documented as an ADR and reviewed by the Governance Plane authority.

---

## CR-005 — Governance Plane Authority

**Rule:** The Governance Plane is the sole authority for ratifying Canon changes, accepting ADRs, and promoting artifact status from DRAFT to ACTIVE.

**Governance Plane** consists of: the UIAO Governance Board (human), the Canon DOCX (document), and this Canonical Rules file (machine-readable policy).

**Rationale:** Without a clear authority structure, governance decisions are made ad hoc and inconsistently. The Governance Plane provides a formal ratification path that is auditable and traceable.

**Enforcement:** All PRs touching `docs/canon/` or any ADR with `status: ACCEPTED` require Governance Plane sign-off before merge.
