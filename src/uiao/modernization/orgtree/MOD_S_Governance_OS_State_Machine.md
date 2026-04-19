---
document_id: MOD_S
title: "Appendix S — Governance OS State Machine"
version: "1.0"
status: DRAFT
classification: CANONICAL
owner: Michael Stratton
created_at: 2026-04-18
updated_at: 2026-04-18
boundary: GCC-Moderate
namespace: MOD
parent_canon: UIAO_008
---

# Appendix S — Governance OS State Machine

Purpose

This appendix defines the complete state machine for the lifecycle of governance artifacts within the Governance OS. Every canonical document, schema, and configuration artifact follows this state machine.

Scope

Covers eight states, all valid transitions, guard conditions, transition actions, and invariants. Applies to every governance artifact in the canonical repository.

Canonical Structure

The state machine has eight states and governed transitions. Forbidden transitions are explicitly enumerated.

Technical Scaffolding

States

Draft: Initial authoring state. Artifact is being written or modified.

Proposed: Author has submitted the artifact for review.

Under Review: Artifact is being reviewed by designated reviewers per CODEOWNERS.

Approved: Reviewers have approved; awaiting merge.

Canonical: Artifact is merged and is the authoritative source of truth.

Deprecated: Artifact is superseded but retained for reference during transition period.

Archived: Artifact is permanently stored but no longer active.

Rejected: Artifact did not pass review and was declined.

Transition Table

State Diagram

+-------+           +-------->| DRAFT |<---------+<---------+           |         +---+---+           |           |           |             |               |           |           |         submit PR       withdraw   revise after           |             v               |       rejection           |        +----------+         |           |           |        | PROPOSED |         |           |           |        +----+-----+         |           |           |             |               |           |           |     CI pass | CI fail       |           |           |        v         v          |           |      modify   +--------+ +----------+  |           |           |   | UNDER  | | REJECTED |--+-----------+           |   | REVIEW | +----------+           |   +--+--+--+           |      |  |           |   approve reject           |      v     v           |  +--------+ +----------+           +--| APPROVED | REJECTED |              +----+---+ +----------+                   |               merge                   v             +-----------+             | CANONICAL |             +-----+-----+                   |              deprecate                   v             +------------+             | DEPRECATED |             +-----+------+                   |              after 90 days                   v             +----------+             | ARCHIVED |             +----------+

Invariants

Every Canonical artifact has exactly one designated owner.

At most one version of any artifact may be in Canonical state at any time.

Every transition is logged with actor, timestamp, and reason.

No artifact may exist in a state without a recorded entry transition.

Forbidden Transitions

Archived → Canonical (must go through Draft → Proposed → Under Review → Approved → Canonical)

Rejected → Canonical (must go through Draft first)

Draft → Canonical (must pass through Proposed, Under Review, and Approved)

Any state → Archived (only Deprecated → Archived is valid)

Boundary Rules

State transitions are tracked within M365-accessible systems.

CI automation for state validation runs within the repository platform.

Drift Considerations

An artifact in an undefined state (not one of the eight listed) constitutes state machine drift.

A forbidden transition that occurs constitutes governance violation. Severity: Critical.

Governance Alignment

This state machine implements Principle 1 (Deterministic State) for governance artifacts: every artifact has exactly one state at any time, and every transition is governed and logged.
