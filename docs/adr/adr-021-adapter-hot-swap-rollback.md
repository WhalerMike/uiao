---
title: "ADR-021: Adapter Hot-Swap and Rollback"
adr: "ADR-021"
status: ACCEPTED
date: "2026-02-22"
deciders: ["UIAO Governance Board"]
---

# ADR-021: Adapter Hot-Swap and Rollback

## Status

ACCEPTED

## Context

Adapter version upgrades require downtime under a simple retire-and-replace model. For mission-critical adapters, downtime is unacceptable. We needed a zero-downtime upgrade mechanism with a reliable rollback guarantee.

## Decision

The Adapter Plane supports **hot-swap**: the new adapter version is registered and authorized alongside the old version, traffic is incrementally shifted (10% → 50% → 100%), and the old version is retired only after all in-flight requests complete (drain phase). If anomalies exceed configured thresholds during traffic shift, rollback is triggered automatically: traffic is restored 100% to the old version, the new version is SUSPENDED.

**Rollback guarantee:** The old version MUST remain in ACTIVE state until Phase 4 (drain) completes. See Appendix A-03 for the full protocol.

## Consequences

**Positive:**
- Zero downtime for adapter upgrades
- Automatic rollback on anomaly detection
- The old version is always available as a fallback until explicit retirement

**Negative:**
- Dual-version operation during upgrade increases resource consumption
- Only one hot-swap operation per adapter identity may proceed at a time (see ADR-023)
