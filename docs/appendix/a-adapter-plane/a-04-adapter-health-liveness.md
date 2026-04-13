---
title: "Appendix A-04: Adapter Health and Liveness"
appendix: "A-04"
family: "Adapter Plane"
status: DRAFT
version: "1.0"
last_updated: "2026-04-07"
related_adrs: ["ADR-025"]
---

# Appendix A-04: Adapter Health and Liveness

## Purpose

This appendix defines the health and liveness monitoring requirements for UIAO adapters. Health monitoring detects degraded adapters before they cause failures. Liveness probing detects adapters that have hung or crashed and triggers automatic recovery.

## Scope

Applies to all adapters in ACTIVE state. Adapters in REGISTERED state are subject to health checks during sandbox validation only.

## Health vs. Liveness

**Health** refers to the adapter's ability to process requests correctly. An unhealthy adapter is running but producing incorrect, slow, or incomplete outputs.

**Liveness** refers to whether the adapter process is alive and responsive at all. An unlive adapter has crashed, hung, or stopped responding to its management interface.

## Health Check Protocol

Each adapter MUST expose a health endpoint at the path configured in its registration schema. The Adapter Plane polls this endpoint on a configurable interval (default: 30 seconds).

A health check response MUST include:
- `status`: "healthy" | "degraded" | "unhealthy"
- `latency_p99_ms`: 99th percentile request latency in milliseconds
- `error_rate_pct`: Percentage of requests resulting in errors over the last 5 minutes
- `queue_depth`: Number of requests currently queued

**Thresholds for automatic lifecycle action:**

| Condition | Action |
|---|---|
| `status: degraded` for 3 consecutive checks | Evidence Fabric WARN event; Governance Plane notification |
| `status: unhealthy` for 2 consecutive checks | ACTIVE → SUSPENDED transition |
| `error_rate_pct > 10` for 5 minutes | Evidence Fabric WARN event |
| `error_rate_pct > 25` for 2 minutes | ACTIVE → SUSPENDED transition |
| `latency_p99_ms > 5000` for 3 consecutive checks | Evidence Fabric WARN event |

## Liveness Probe Protocol

The Adapter Plane sends a liveness ping to each ACTIVE adapter every 10 seconds. If an adapter fails to respond within 5 seconds, the ping is retried once. If the retry also fails, the adapter is classified as UNLIVE and the following sequence is triggered:

1. ACTIVE → SUSPENDED lifecycle transition
2. Evidence Fabric CRITICAL audit event
3. Governance Plane notification
4. Adapter process restart attempt (configurable: enabled/disabled per adapter)
5. If restart succeeds: health check validation before re-promoting to ACTIVE
6. If restart fails: adapter remains SUSPENDED pending manual investigation

## Truth Fabric Health Records

All health check results are written to the Truth Fabric as part of the adapter's canonical state record. The Truth Fabric retains the last 100 health check results per adapter. Older results are archived to the Evidence Fabric.

## Adapter Self-Reporting

Adapters MAY proactively report their own health status to the Adapter Plane management interface without waiting for a poll. Self-reported status overrides the previous polled status until the next scheduled poll. This enables adapters to report degradation immediately on detection rather than waiting for the next poll interval.

## Dependencies

- **Truth Fabric (Appendix B):** Stores health check results in adapter state records
- **Drift Fabric (Appendix C):** Correlates health degradation with drift events
- **Evidence Fabric (Appendix D):** Archives health audit events
- **ADR-025:** Health and liveness decision record

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
