---
title: "Appendix A-01: Adapter Lifecycle Management"
appendix: "A-01"
family: "Adapter Plane"
status: DRAFT
version: "1.0"
last_updated: "2026-04-07"
related_adrs: ["ADR-021", "ADR-025"]
---

# Appendix A-01: Adapter Lifecycle Management

## Purpose

This appendix defines the complete lifecycle of a UIAO adapter — from initial registration through active operation to graceful retirement. It establishes the state machine that governs adapter transitions and the governance checkpoints required at each stage.

## Scope

Applies to all adapters registered with the UIAO Adapter Plane, regardless of the external system they integrate with. This includes first-party adapters developed by the UIAO team and third-party adapters onboarded by mission partners.

## Adapter Lifecycle States

An adapter passes through six canonical states:

**UNREGISTERED** → The adapter software exists but has not been submitted to the Adapter Plane. No governance obligations apply.

**PENDING_REGISTRATION** → The adapter has been submitted for registration and is awaiting schema validation and identity verification.

**REGISTERED** → The adapter has passed schema validation. It is known to the Truth Fabric but is not yet authorized to process live data.

**ACTIVE** → The adapter has been authorized and is processing live integration requests. The Truth Fabric maintains its canonical state record.

**SUSPENDED** → The adapter has been temporarily removed from active operation due to a detected policy violation, drift event, or manual governance action. The Truth Fabric retains its state record with `status: SUSPENDED`.

**RETIRED** → The adapter has been permanently decommissioned. Its state record in the Truth Fabric is archived (not deleted) for audit purposes per the Evidence Fabric retention policy.

## State Transition Rules

| From | To | Trigger | Governance Checkpoint |
|---|---|---|---|
| UNREGISTERED | PENDING_REGISTRATION | Adapter submits registration request | Adapter schema must conform to canonical schema |
| PENDING_REGISTRATION | REGISTERED | Schema validation passes | Governance Plane approval required for mission-critical adapters |
| REGISTERED | ACTIVE | Authorization granted | Automated CI check + Governance Plane sign-off |
| ACTIVE | SUSPENDED | Drift event or policy violation detected | Automatic (Drift Fabric trigger) or manual |
| SUSPENDED | ACTIVE | Remediation verified by Evidence Fabric | Governance Plane sign-off required |
| SUSPENDED | RETIRED | Governance decision to retire | Governance Board vote |
| ACTIVE | RETIRED | Planned decommission | Governance Board vote + 30-day notice |

## Hot-Swap and Rollback

When an adapter version must be updated without service interruption, the hot-swap protocol defined in ADR-021 applies:

1. Register the new adapter version alongside the existing version (both in REGISTERED state)
2. Authorize the new version to ACTIVE
3. Route traffic to the new version incrementally (10% → 50% → 100%)
4. Retire the old version after the Evidence Fabric confirms no in-flight requests remain
5. If anomalies are detected at any routing stage, trigger rollback: restore 100% traffic to old version, move new version to SUSPENDED for investigation

## Dependencies

- **Truth Fabric (Appendix B):** Maintains adapter state records
- **Drift Fabric (Appendix C):** Triggers ACTIVE → SUSPENDED transitions on drift detection
- **Evidence Fabric (Appendix D):** Records all lifecycle transitions as audit events
- **ADR-021:** Hot-swap and rollback decision record
- **ADR-025:** Adapter health and liveness requirements
