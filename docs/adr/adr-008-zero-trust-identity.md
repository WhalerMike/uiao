---
title: "ADR-008: Zero-Trust Identity Anchoring"
adr: "ADR-008"
status: ACCEPTED
date: "2026-01-22"
deciders: ["UIAO Governance Board"]
---

# ADR-008: Zero-Trust Identity Anchoring

## Status

ACCEPTED

## Context

UIAO receives identity claims from adapters across multiple systems. Without explicit verification, an adapter could assert a false identity anchor (e.g., claiming that a user in System A is the same person as a user in System B). This could lead to unauthorized access escalation or incorrect compliance attestations.

## Decision

The Truth Fabric adopts a **zero-trust identity anchoring** model: no anchor binding is trusted by default, regardless of the source. Every anchor binding requires at least one of: cryptographic proof from the subject, cross-system corroboration from two independent adapters, or manual Governance Plane authorization. Unverified anchors are marked PENDING and treated as low-confidence.

## Consequences

**Positive:**
- Prevents false identity correlations that could lead to privilege escalation
- Provides a clear verification audit trail
- Compliant with zero-trust architecture principles

**Negative:**
- New anchor bindings require verification before they can be used in HIGH-confidence compliance attestations
- Initial onboarding of multi-system identities requires more effort
- PENDING anchors add complexity to compliance queries
