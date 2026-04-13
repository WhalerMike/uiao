---
title: "ADR-018: Mission Channel Enforcement"
adr: "ADR-018"
status: ACCEPTED
date: "2026-02-15"
deciders: ["UIAO Governance Board", "ARB"]
---

# ADR-018: Mission Channel Enforcement

## Status

ACCEPTED

## Context

Some integration pathways carry mission-critical data that requires elevated governance controls. These pathways (Mission Channels) need to be explicitly defined, governed, and monitored at a higher standard than ordinary adapter integrations.

## Decision

The Governance Plane maintains a registry of **Mission Channels** — designated integration pathways with elevated governance requirements. Mission Channels require ARB approval to establish or change. Adapters operating in a Mission Channel are subject to:
- Elevated evidence recording (all events recorded at HIGH or CRITICAL severity)
- Dedicated drift detection rules
- Mandatory Governance Plane notification for any MEDIUM or higher event
- Annual Mission Channel review

Mission Channels are a superset of Mission Partner Corridors (which require inter-organizational agreements) — an internal mission-critical pathway can be a Mission Channel without being a Corridor.

## Consequences

**Positive:**
- Critical pathways receive proportionate governance oversight
- Mission Channel status is explicit and auditable
- ARB involvement ensures cross-organizational awareness of critical channels

**Negative:**
- Mission Channel designation requires ARB overhead
- Elevated evidence recording for Mission Channels increases storage volume

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
