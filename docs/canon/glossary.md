---
title: "UIAO Glossary"
status: ACTIVE
version: "1.0"
last_updated: "2026-04-07"
---

# UIAO Glossary

This glossary defines authoritative terminology for the Universal Integration Adapter Orchestration (UIAO) framework. All documentation, ADRs, and implementation artifacts MUST use these terms consistently.

---

## A

**Adapter** — A bounded software component that translates between an external system's native protocol/schema and the UIAO canonical schema. Adapters are registered in the Truth Fabric and MUST be idempotent and stateless.

**Adapter Plane** — The layer of the UIAO architecture that hosts all registered adapters. The Adapter Plane is responsible for inbound and outbound translation, schema validation, and adapter lifecycle management. See Appendix A.

**Adapter Registration** — The process by which an adapter declares its identity, schema version, capabilities, and endpoint configuration to the Truth Fabric. Registration is a prerequisite for any adapter to participate in orchestration.

**Attestation** — A cryptographically signed record produced by the Evidence Fabric confirming that a specific governance event occurred at a specific time. Attestations are immutable once written.

**Audit Event** — Any governance-relevant action recorded by the Evidence Fabric. Includes adapter state changes, drift detections, reconciliation completions, and Canon rule evaluations.

---

## B

**Bypass Rules** — A GitHub branch protection mechanism that allows authorized users (Governance Plane members) to commit directly to a protected branch without a pull request. Used for urgent Canon updates that cannot wait for a PR review cycle.

---

## C

**Canon** — The authoritative body of UIAO governance rules, definitions, and decisions. The Canon consists of: Canonical Rules (CR-001 through CR-005), the Glossary, ADRs ADR-005 through ADR-027, and the Canon Master Document (DOCX).

**Canon DOCX** — The UIAO Governance Canon Master Document in Microsoft Word format. The single authoritative source for all governance content. All published documentation MUST be traceable to the Canon DOCX.

**Canonical Rules** — The five immutable governance constraints (CR-001 through CR-005) that all UIAO artifacts must conform to. See `docs/canon/canonical-rules.md`.

**Canonical Schema** — The UIAO-internal data schema to which all adapter inputs and outputs are normalized. The canonical schema is owned by the Truth Fabric and versioned in `uiao-core`.

**Compliance Attestation** — An Evidence Fabric record confirming that a system or component was found to be in compliance with a specific Canonical Rule at a specific point in time.

---

## D

**Delta** — The computed difference between a system's current observed state and its canonical (expected) state, as determined by the Drift Fabric.

**Deterministic Separation** — The principle (CR-001) that machine artifacts and human artifacts are stored in separate repositories with no overlap. The separation is enforced at scaffold time and by CI checks.

**Drift** — Any deviation of a system's observed state from its canonical state. Drift is detected by the Drift Fabric and triggers reconciliation.

**Drift Detection** — The process by which the Drift Fabric compares observed state against canonical state and computes a delta. Drift detection runs on a configurable schedule or on demand.

**Drift Fabric** — The UIAO subsystem responsible for detecting, quantifying, and triggering remediation of state drift. The Drift Fabric consumes canonical state from the Truth Fabric and produces drift records for the Evidence Fabric. See Appendix C.

---

## E

**Evidence Fabric** — The UIAO subsystem responsible for recording, storing, and attesting to governance events. All audit events, drift records, and compliance attestations are written to the Evidence Fabric. Evidence records are immutable. See Appendix D.

**Evidence Manifest** — A machine-readable index of all Evidence Fabric records for a given time window or governance scope. Stored in `uiao-core`.

---

## F

**Fabric** — One of the three operational subsystems of UIAO: Truth Fabric, Drift Fabric, or Evidence Fabric. Each fabric operates orthogonally (CR-004) and has a defined ownership domain.

**Fabric Orthogonality** — The principle (CR-004) that the three fabrics operate independently with no cross-fabric schema or orchestration dependencies.

**Frontmatter** — YAML metadata at the top of a Markdown document (between `---` delimiters) that records title, status, version, and other governance fields. Required on all UIAO documentation files.

---

## G

**Governance Board** — The human authority responsible for ratifying Canon changes, accepting ADRs, and promoting artifact status. Constitutes the human component of the Governance Plane.

**Governance Plane** — The UIAO subsystem responsible for policy enforcement, ADR ratification, and Canon authority. Consists of the Governance Board (human), the Canon DOCX (document), and the Canonical Rules file (machine-readable policy). See Appendix E.

---

## H

**Human Artifact** — Any UIAO artifact intended for human interpretation: governance documents, ADRs, appendices, diagrams, glossaries, migration plans. Stored exclusively in `uiao-docs`.

---

## I

**Idempotent** — A property of adapters and orchestration operations: applying the same operation multiple times produces the same result as applying it once. Required for all UIAO adapter operations.

**Immutable** — A record or field that cannot be changed after it is written. Evidence Fabric records, accepted ADR Decision fields, and compliance attestations are immutable.

---

## M

**Machine Artifact** — Any UIAO artifact consumed directly by automated processes: adapter schemas, orchestration logic, drift-detection algorithms, evidence manifests. Stored exclusively in `uiao-core`.

**Migration Plan** — The structured plan for transitioning the UIAO documentation structure from a flat layout to a hierarchical canonical layout. See `docs/canon/migration-plan.md`.

---

## O

**Orchestration** — The process by which the UIAO framework coordinates adapter invocations, fabric interactions, and governance event recording to fulfill an integration request.

---

## R

**Ratification** — The formal process by which the Governance Plane reviews and approves a governance artifact (Canon change, ADR, or stub promotion). Ratified artifacts are promoted from DRAFT to ACTIVE status.

**Reconciliation** — The process of correcting a system's state to match its canonical state after drift is detected. Triggered by the Drift Fabric and recorded by the Evidence Fabric.

**Registration** — See *Adapter Registration*.

---

## S

**Schema** — A formal definition of the structure, types, and constraints of a data artifact. The canonical schema is the UIAO-internal normalized form; adapter schemas define translation mappings.

**Stub** — A documentation file created by `Initialize-UIAOCanonStructure.ps1` with `status: MISSING` frontmatter. Stubs are placeholders awaiting content population from the Canon DOCX.

**Supersession** — The process by which a new ADR formally replaces an accepted ADR. The superseding ADR carries `supersedes: ADR-NNN` and the superseded ADR is updated with `superseded_by: ADR-MMM`.

---

## T

**Truth Fabric** — The UIAO subsystem responsible for maintaining the authoritative canonical state of all registered adapters and integrated systems. Owns the canonical schema, adapter registration, and state records. See Appendix B.

---

## U

**UIAO** — Universal Integration Adapter Orchestration. The enterprise governance framework for managing, auditing, and orchestrating integration adapters across heterogeneous systems.

**uiao-core** — The GitHub repository containing all UIAO machine artifacts: adapter schemas, orchestration logic, drift algorithms, evidence manifests, and the Canon Pointer.

**uiao-docs** — The GitHub repository containing all UIAO human artifacts: governance documents, ADRs, appendices, diagrams, glossaries, migration plans, and the MkDocs site configuration.
