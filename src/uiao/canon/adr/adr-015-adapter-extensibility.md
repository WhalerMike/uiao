---
title: "ADR-015: Adapter Extensibility"
adr: "ADR-015"
status: ACCEPTED
date: "2026-02-08"
deciders: ["UIAO Governance Board"]
---

# ADR-015: Adapter Extensibility

## Status

ACCEPTED

## Context

New systems will be integrated with UIAO over time. The adapter model must support adding new adapters without modifying the core UIAO framework. We also needed to decide whether third parties (mission partners) could develop and register their own adapters.

## Decision

The UIAO Adapter Plane supports **open extensibility**: any authorized party can develop and register an adapter, provided it conforms to the Canonical Claim Schema and passes the sandbox validation suite. There is no closed list of permitted adapters.

Extensibility constraints:
- All adapters must be registered and pass schema validation before operating
- Mission-critical adapters require Governance Plane approval in addition to standard validation
- Third-party adapters from mission partners require a Mission Partner Corridor (Appendix E-02)
- The Canonical Claim Schema and Claim Type Registry in `uiao-core` define the boundary of what adapters can express

## Consequences

**Positive:**
- New integrations can be added without UIAO framework changes
- Mission partners can develop their own adapters
- The adapter ecosystem can grow organically

**Negative:**
- Open registration requires robust sandbox validation to prevent malicious adapters
- Third-party adapter quality is outside UIAO's direct control
- Claim type registry must evolve to support new claim types needed by new adapters

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
