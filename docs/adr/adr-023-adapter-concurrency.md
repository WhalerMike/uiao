---
title: "ADR-023: Adapter Concurrency"
adr: "ADR-023"
status: ACCEPTED
date: "2026-03-01"
deciders: ["UIAO Governance Board"]
---

# ADR-023: Adapter Concurrency

## Status

ACCEPTED

## Context

Multiple governance operations (hot-swap, suspension, retirement) could be requested concurrently for the same adapter. Without concurrency controls, concurrent operations could leave the adapter in an inconsistent state.

## Decision

The Adapter Plane enforces concurrency constraints using an adapter-identity-level lock:
- Only one lifecycle operation (hot-swap, suspend, retire) may be in progress for a given adapter identity at a time
- Concurrent operation requests for the same adapter identity are rejected with a CONFLICT response
- The lock is released when the operation completes, is rolled back, or times out (configurable timeout, default: 30 minutes)
- Individual claim submissions are not subject to the lifecycle lock — claims can continue to flow during a lifecycle operation

## Consequences

**Positive:**
- No adapter state inconsistencies from concurrent operations
- Clear conflict responses allow callers to retry after the operation completes

**Negative:**
- Long-running lifecycle operations (e.g., a slow hot-swap traffic shift) block other operations on the same adapter
- Lock timeout must be configured appropriately — too short causes premature lock release; too long causes unacceptable blocking
