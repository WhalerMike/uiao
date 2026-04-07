---
title: "ADR-025: Adapter Health and Liveness"
adr: "ADR-025"
status: ACCEPTED
date: "2026-03-05"
deciders: ["UIAO Governance Board"]
---

# ADR-025: Adapter Health and Liveness

## Status

ACCEPTED

## Context

Degraded or hung adapters may continue in ACTIVE state while producing incorrect or no output. Without explicit health and liveness monitoring, degraded adapters may go undetected until a compliance gap is discovered. We needed proactive monitoring with automatic lifecycle actions.

## Decision

Each adapter must expose a health endpoint polled every 30 seconds. Health responses include status, p99 latency, error rate, and queue depth. Liveness pings are sent every 10 seconds — two consecutive missed pings trigger SUSPENDED transition. Automatic thresholds for lifecycle actions are defined in the health check protocol (Appendix A-04). Adapters may also self-report health proactively.

## Consequences

**Positive:**
- Degraded adapters are detected and acted upon before causing compliance gaps
- Liveness probing detects hung adapters that are not actively crashing
- Self-reporting enables immediate response to adapter-detected issues

**Negative:**
- Health endpoint implementation is required for all adapters — adds to adapter development requirements
- Poll frequency (30s health, 10s liveness) generates monitoring overhead
