---
title: "ADR-027: Adapter Retirement"
adr: "ADR-027"
status: ACCEPTED
date: "2026-03-10"
deciders: ["UIAO Governance Board"]
---

# ADR-027: Adapter Retirement

## Status

ACCEPTED

## Context

Adapters have a finite useful life — integrated systems change, integrations are superseded, or mission requirements evolve. We needed a formal retirement process to ensure that retired adapters leave a clean audit trail and do not silently disappear from governance records.

## Decision

Adapter retirement requires:
1. **Governance Board vote** — formal decision documented in Evidence Fabric
2. **30-day notice period** — dependent systems have 30 days to migrate
3. **Drain phase** — adapter transitions to ACTIVE state with `retirement_pending: true`; no new claim registrations accepted; in-flight requests complete
4. **Final evidence bundle** — an Evidence Bundle is generated covering the adapter's complete governance history from registration to retirement
5. **RETIRED state** — adapter transitions to RETIRED; Truth Fabric archives its state record; sandbox is decommissioned

Retired adapters' evidence records are retained per the standard lifecycle guarantees (ADR-026). The adapter identity is never reused.

## Consequences

**Positive:**
- Clean audit trail through the complete adapter lifecycle
- 30-day notice prevents surprise service disruptions for dependent systems
- Final evidence bundle provides a point-in-time compliance record for the retired adapter

**Negative:**
- Retirement process has governance overhead — not suitable for emergency decommissioning
- For emergency decommissioning (security incident), the SUSPENDED → RETIRED path bypasses the notice period but still requires Governance Board vote

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
