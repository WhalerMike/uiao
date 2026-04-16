---
title: "Appendix E-01: Architecture Review Board Coordination"
appendix: "E-01"
family: "Governance Plane"
status: DRAFT
version: "1.0"
last_updated: "2026-04-07"
related_adrs: ["ADR-018"]
---

# Appendix E-01: Architecture Review Board Coordination

## Purpose

This appendix defines how the UIAO Governance Plane coordinates with the Architecture Review Board (ARB) for decisions that require cross-organizational governance. The ARB is the enterprise-level authority for architectural decisions; the UIAO Governance Board is the domain-specific authority for UIAO governance. This appendix clarifies their interaction.

## Scope

Applies to all UIAO governance decisions that have cross-organizational architectural implications: changes to the Canonical Claim Schema, new fabric introductions, cross-fabric dependency exceptions, and mission channel enforcement changes.

## ARB vs. Governance Board Authority

| Decision Type | Authority |
|---|---|
| UIAO Canonical Rules changes | Governance Board (required) + ARB (advisory) |
| New fabric introduction | Governance Board (required) + ARB (required) |
| Cross-fabric dependency exception (CR-004 waiver) | Governance Board (required) + ARB (required) |
| New adapter registration (standard) | Governance Board only |
| New adapter registration (mission-critical) | Governance Board (required) + ARB (advisory) |
| ADR acceptance (standard) | Governance Board only |
| ADR acceptance (architectural impact) | Governance Board (required) + ARB (required) |
| Mission channel enforcement changes | Governance Board + ARB (required) |

## ARB Escalation Process

When a UIAO governance decision requires ARB involvement:
1. The Governance Board prepares an ARB briefing package containing: the proposed change, impact analysis, relevant ADRs, and supporting evidence from the Evidence Fabric
2. The briefing package is submitted to the ARB at least 10 business days before the required decision date
3. The ARB reviews and provides one of: APPROVED, APPROVED_WITH_CONDITIONS, DEFERRED, or REJECTED
4. The Governance Board records the ARB decision in the Evidence Fabric as a governance event
5. If APPROVED or APPROVED_WITH_CONDITIONS: the Governance Board proceeds with the change per the ARB's conditions
6. If DEFERRED or REJECTED: the Governance Board documents the outcome in the relevant ADR and does not proceed

## Mission Channel Enforcement

Per ADR-018, mission channels are designated integration pathways that carry mission-critical data and require elevated governance oversight. Changes to mission channel enforcement rules require ARB approval. Mission channel definitions are maintained in `uiao-core` and referenced in this documentation.

## ARB Representation

The UIAO Governance Board maintains a designated ARB liaison responsible for:
- Preparing ARB briefing packages
- Attending ARB meetings on behalf of the Governance Board
- Tracking ARB decisions and ensuring they are recorded in the Evidence Fabric
- Reporting ARB decisions to the Governance Board

## Dependencies

- **ADR-018:** Mission channel enforcement decision record
- **Appendix E-02:** Mission partner corridors (cross-org channel governance)
- **Appendix E-03:** Cross-fabric consistency (requires ARB for exceptions)

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
