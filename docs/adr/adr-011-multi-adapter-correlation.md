---
title: "ADR-011: Multi-Adapter Correlation"
adr: "ADR-011"
status: ACCEPTED
date: "2026-01-28"
deciders: ["UIAO Governance Board"]
---

# ADR-011: Multi-Adapter Correlation

## Status

ACCEPTED

## Context

Some compliance controls require evidence from multiple systems to establish full satisfaction. For example, AC-2 (Account Management) might require evidence from both an identity provider and an HR system. No single adapter can satisfy this control alone. We needed a mechanism to combine evidence from multiple adapters into a single compliance determination.

## Decision

The Truth Fabric implements a **multi-adapter correlation engine** that can combine Canonical Claims from multiple adapters to produce a composite compliance determination. Claims from different adapters are linked via the canonical subject identity. Partial satisfaction is tracked until all required evidence is received. The correlation result is stored in the Evidence Fabric as a Compliance Attestation with an `evidence_claims` array listing all contributing claims.

## Consequences

**Positive:**
- Controls requiring multi-system evidence can be satisfied automatically
- Partial satisfaction is tracked transparently — auditors can see exactly which evidence is still outstanding
- Reduces manual compliance work

**Negative:**
- Correlation logic adds complexity to the Truth Fabric
- Timing gaps between adapter submissions can leave controls in partial-satisfaction state longer than expected
- Control mapping definitions must explicitly specify which adapters are required for full satisfaction
