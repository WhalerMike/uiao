---
title: "Appendix A-03: Adapter Hot-Swap and Rollback"
appendix: "A-03"
family: "Adapter Plane"
status: DRAFT
version: "1.0"
last_updated: "2026-04-07"
related_adrs: ["ADR-021"]
---

# Appendix A-03: Adapter Hot-Swap and Rollback

## Purpose

This appendix specifies the hot-swap and rollback protocol for UIAO adapters. Hot-swap enables zero-downtime adapter version upgrades. Rollback enables rapid recovery when a new adapter version introduces regressions.

## Scope

Applies to all version transitions for adapters in ACTIVE state. The hot-swap protocol is mandatory for mission-critical adapters. Non-mission-critical adapters may use a simpler retire-and-replace pattern if downtime is acceptable.

## Hot-Swap Protocol

The hot-swap protocol proceeds in five phases:

### Phase 1: Register New Version
Register the new adapter version alongside the existing version. Both versions are now in REGISTERED state. The Truth Fabric records both with distinct version identifiers but the same adapter identity.

### Phase 2: Authorize New Version
Authorize the new version to ACTIVE. The Adapter Plane now has two ACTIVE versions of the same adapter. Traffic continues to flow 100% to the old version.

### Phase 3: Incremental Traffic Shift
Route traffic to the new version incrementally:
- Step 1: 10% to new version, 90% to old version — observe for 5 minutes
- Step 2: 50% to new version, 50% to old version — observe for 10 minutes
- Step 3: 100% to new version, 0% to old version

At each step, the Evidence Fabric records a traffic shift event. The Drift Fabric monitors for anomalies. If anomalies exceed the configured threshold at any step, rollback is triggered automatically.

### Phase 4: Drain Old Version
Once traffic is 100% on the new version, the Adapter Plane waits for all in-flight requests to the old version to complete. The Evidence Fabric confirms zero in-flight requests before Phase 5 proceeds.

### Phase 5: Retire Old Version
Initiate the ACTIVE → RETIRED transition for the old version. The Truth Fabric archives its state record.

## Rollback Protocol

Rollback is triggered when:
- Anomaly threshold exceeded during traffic shift
- Manual governance action from the Governance Plane
- Evidence Fabric reports CRITICAL audit event on new version

Rollback steps:
1. Restore 100% traffic to old version immediately
2. Move new version to SUSPENDED state
3. Evidence Fabric records rollback event with timestamp, trigger reason, and traffic metrics at rollback point
4. Governance Plane receives notification
5. Investigation proceeds on the SUSPENDED new version before any re-promotion attempt

## Rollback Guarantee

The old version MUST remain in ACTIVE state with its sandbox intact until Phase 5 is reached. This is the rollback guarantee. No hot-swap operation may retire the old version before Phase 4 (drain) is complete.

## Concurrency Constraints

Only one hot-swap operation may be in progress for a given adapter identity at a time. A second hot-swap request for the same adapter is rejected while a previous operation is in progress. See ADR-023 for the adapter concurrency decision.

## Dependencies

- **Truth Fabric (Appendix B):** Manages dual-version state records
- **Drift Fabric (Appendix C):** Monitors anomalies during traffic shift
- **Evidence Fabric (Appendix D):** Records all hot-swap and rollback events
- **ADR-021:** Hot-swap and rollback decision record
- **ADR-023:** Adapter concurrency constraints

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
