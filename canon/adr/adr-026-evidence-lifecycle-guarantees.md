---
title: "ADR-026: Evidence Lifecycle Guarantees"
adr: "ADR-026"
status: ACCEPTED
date: "2026-03-08"
deciders: ["UIAO Governance Board"]
---

# ADR-026: Evidence Lifecycle Guarantees

## Status

ACCEPTED

## Context

Compliance obligations (FedRAMP, CMMC) require evidence to be retained for specific minimum periods. Without formal lifecycle guarantees, evidence could be inadvertently purged before a compliance assessment. We needed to codify the lifecycle guarantees as a governance commitment.

## Decision

The Evidence Fabric provides the following lifecycle guarantees:

1. Evidence records are **never deleted** — they may be ARCHIVED and COMPRESSED but not removed
2. Minimum retention periods: 3 years for standard audit events; 7 years for compliance attestations and CRITICAL events
3. SEALED records are permanently immutable — even correction records cannot be appended after sealing
4. Retention periods may only be increased, never decreased, without regulatory review
5. Evidence Bundles submitted to external assessors are SEALED and retained for 7 years minimum

These guarantees are codified as Governance Plane policy and referenced in all compliance attestations.

## Consequences

**Positive:**
- Compliance obligations are met with documented retention guarantees
- Governance commitment is explicit — auditors can reference this ADR
- No inadvertent evidence purges

**Negative:**
- Storage is a permanent cost — no escape hatch for reducing retention of older records
- Sealing SEALED records is irreversible — errors in sealed records require a new superseding bundle

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
