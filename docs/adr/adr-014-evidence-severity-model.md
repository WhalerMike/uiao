---
title: "ADR-014: Evidence Severity Model"
adr: "ADR-014"
status: ACCEPTED
date: "2026-02-05"
deciders: ["UIAO Governance Board"]
---

# ADR-014: Evidence Severity Model

## Status

ACCEPTED

## Context

Not all evidence records are equally important. A routine adapter health check event is very different from a CRITICAL compliance drift event. Without severity classification, every alert would have the same urgency, leading to alert fatigue and missed critical events.

## Decision

The Evidence Fabric adopts a five-level severity model: INFO, LOW, MEDIUM, HIGH, CRITICAL. Each level has defined characteristics:

- **INFO:** Routine operations, no action required
- **LOW:** Minor anomalies, included in next governance report
- **MEDIUM:** Requires review within 24 hours, Governance Plane notification
- **HIGH:** Significant impact, immediate notification, reconciliation triggered
- **CRITICAL:** Active violation or security incident, immediate alert, adapter suspension, incident response

Severity affects signing requirements, retention periods, and escalation paths (see Appendix D-03).

## Consequences

**Positive:**
- Clear escalation paths matched to event severity
- Reduces alert fatigue — INFO and LOW events do not page governance staff
- Compliance packages can filter to HIGH/CRITICAL for focused review

**Negative:**
- Severity misclassification is possible — an INFO event that should have been HIGH will not trigger appropriate escalation
- Severity model must be kept current as the governance landscape evolves
