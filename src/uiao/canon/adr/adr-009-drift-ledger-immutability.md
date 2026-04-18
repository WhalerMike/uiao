---
title: "ADR-009: Drift Ledger Immutability"
adr: "ADR-009"
status: ACCEPTED
date: "2026-01-22"
deciders: ["UIAO Governance Board"]
---

# ADR-009: Drift Ledger Immutability

## Status

ACCEPTED

## Context

The Drift Fabric detects deviations between observed state and canonical state. Some detected drift events may later be determined to be false positives (e.g., a correctly-authorized change that wasn't tracked). The question was: should drift records be deletable or modifiable after the fact?

## Decision

All Drift Records are **immutable**. They are written to the Evidence Fabric and cannot be modified or deleted. If a drift event is later determined to be a false positive, a correction record is appended — the original record remains. This applies equally to false positives, authorized deviations, and superseded drift events.

## Consequences

**Positive:**
- The drift ledger is a reliable audit trail — no one can retroactively remove evidence of drift
- Compliance assessors can trust that drift records represent what actually happened
- Forensic investigations can reconstruct the complete drift history

**Negative:**
- False positive drift records accumulate — queries must filter them using correction record status
- Storage grows monotonically
- Developers cannot "clean up" test drift records from production environments

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
