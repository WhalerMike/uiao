---
title: "ADR-016: Evidence Bundle Lifecycle"
adr: "ADR-016"
status: ACCEPTED
date: "2026-02-10"
deciders: ["UIAO Governance Board"]
---

# ADR-016: Evidence Bundle Lifecycle

## Status

ACCEPTED

## Context

Compliance assessments and forensic investigations require collecting related evidence records into a coherent package. Without a formal bundle model, assembling evidence packages is ad hoc and inconsistent.

## Decision

The Evidence Fabric supports **Evidence Bundles**: named, governed collections of evidence records assembled for a specific purpose. Bundles pass through four lifecycle states: ASSEMBLING, SEALED, SUBMITTED, CLOSED. Once SEALED, no records may be added or removed. Bundles are immutable once sealed and are themselves recorded as Evidence Fabric entries.

## Consequences

**Positive:**
- Compliance packages are formally governed and reproducible
- Bundles can be submitted to external assessors with confidence in their integrity
- Bundle lifecycle is auditable

**Negative:**
- Bundle assembly requires explicit governance steps — cannot be assembled on the fly
- Sealed bundles cannot be corrected (only superseded by a new bundle)

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
