---
title: "Appendix A-02: Adapter Sandbox Execution"
appendix: "A-02"
family: "Adapter Plane"
status: DRAFT
version: "1.0"
last_updated: "2026-04-07"
related_adrs: ["ADR-017"]
---

# Appendix A-02: Adapter Sandbox Execution

## Purpose

This appendix defines the sandbox execution model for UIAO adapters. All adapters MUST execute within an isolated sandbox environment to prevent unauthorized access to host resources, cross-adapter contamination, and uncontrolled side effects on external systems.

## Scope

Applies to all adapter execution environments within the UIAO Adapter Plane. The sandbox model applies regardless of whether the adapter is deployed on-premises, in a cloud environment, or in a hybrid configuration.

## Sandbox Architecture

Each adapter executes within a dedicated sandbox that enforces the following isolation boundaries:

**Process Isolation:** Each adapter runs in a separate process with a dedicated PID namespace. Adapters cannot inspect or signal other adapter processes.

**Network Isolation:** Each adapter is assigned a virtual network interface with explicit ingress/egress rules. Default-deny outbound policy applies — adapters may only communicate with endpoints explicitly whitelisted in their registration schema.

**Filesystem Isolation:** Each adapter has a read-only view of shared canonical schemas and a writable ephemeral scratch space. The scratch space is wiped on adapter shutdown or restart. No adapter may write to the host filesystem.

**Memory Isolation:** Adapters are subject to memory limits defined in their registration schema. Exceeding the limit triggers a SUSPENDED lifecycle transition and an Evidence Fabric audit event.

**CPU Isolation:** Adapters are subject to CPU quotas. Sustained CPU overuse triggers throttling followed by SUSPENDED transition if not resolved within the configured window.

## Sandbox Boundaries and the Truth Fabric

An adapter in sandbox execution may only interact with the Truth Fabric through the canonical API. Direct database access or schema manipulation is prohibited. All Truth Fabric interactions are mediated by the Adapter Plane orchestration layer, which validates requests against the canonical schema before forwarding.

## Sandbox Escape Detection

The Drift Fabric monitors sandbox boundary violations. A sandbox escape — any attempt by an adapter to access resources outside its defined boundaries — is classified as a CRITICAL drift event and triggers:
1. Immediate ACTIVE → SUSPENDED lifecycle transition
2. Evidence Fabric audit event with CRITICAL severity
3. Governance Plane notification
4. Forensic snapshot of adapter state at time of detection

## Adapter Testing in Sandbox

Before promotion to ACTIVE, adapters MUST pass a sandbox validation suite that tests:
- Schema conformance with the canonical schema
- Network boundary compliance (no unauthorized outbound connections)
- Idempotency of all operations
- Correct handling of malformed inputs (no crashes, no data leakage)
- Memory and CPU usage within declared limits

## Dependencies

- **Truth Fabric (Appendix B):** Target of adapter canonical API calls
- **Drift Fabric (Appendix C):** Monitors sandbox boundary violations
- **Evidence Fabric (Appendix D):** Records sandbox violations and audit events
- **ADR-017:** Decision record for sandbox execution model
