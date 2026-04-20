---
document_id: MOD_M
title: "Appendix M — Drift Detection Engine Specification"
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

# Appendix M — Drift Detection Engine Specification

Purpose

This appendix defines the complete specification for the automated drift detection engine, including its architecture, drift categories, detection rules, snapshot schema, comparison algorithm, and alert routing.

Scope

The engine monitors all identity objects, dynamic groups, and administrative units within the M365 GCC-Moderate boundary. It compares observed tenant state against the canonical baseline continuously.

Canonical Structure

The engine operates as a six-phase loop: Snapshot, Compare, Classify, Alert, Remediate, Verify.

Technical Scaffolding

Drift Categories

Detection Rules

Comparison Algorithm (Pseudocode)

FUNCTION CompareTenantToBaseline(baseline, current):     driftEntries = []      FOR EACH user IN current.users:         IF user.id NOT IN baseline.users:             ADD NewObject drift entry             CONTINUE         baseUser = baseline.users[user.id]         FOR EACH field IN [orgPath, department, lifecycleState, roleCode, manager]:             IF user[field] != baseUser[field]:                 entry = ClassifyDrift(field, baseUser[field], user[field])                 ADD entry TO driftEntries      FOR EACH user IN baseline.users:         IF user.id NOT IN current.users:             ADD DeletedObject drift entry      FOR EACH group IN current.groups:         IF group.id NOT IN baseline.groups:             ADD PhantomGroup drift entry         ELSE IF group.membershipRule != baseline.groups[group.id].membershipRule:             ADD RuleDrift entry      RETURN driftEntries

Alert Routing

Boundary Rules

The drift detection engine reads tenant state exclusively through Microsoft Graph API within M365 GCC-Moderate.

Alert routing uses M365 notification mechanisms (Teams, email) only.

Drift Considerations

The engine specification itself is a governance artifact subject to Workflow 8.

If the engine fails to detect a known drift condition, that constitutes an engine defect requiring immediate remediation.

Governance Alignment

This engine is the primary implementation of Principle 4 (Drift Resistance). It provides continuous, automated monitoring that makes drift a temporary condition rather than a permanent state.
