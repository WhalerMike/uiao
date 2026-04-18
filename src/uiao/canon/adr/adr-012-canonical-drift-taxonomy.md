---
title: "ADR-012: Canonical Drift Taxonomy"
adr: "ADR-012"
status: ACCEPTED
date: "2026-02-01"
deciders: ["UIAO Governance Board"]
---

# ADR-012: Canonical Drift Taxonomy

## Status

ACCEPTED

## Context

Without a canonical taxonomy for drift types, different adapters and teams would use inconsistent terminology when reporting drift events. This would make it impossible to aggregate drift statistics, set consistent severity thresholds, or produce meaningful governance reports.

## Decision

The Drift Fabric adopts a canonical drift taxonomy with five drift types (DT-01 through DT-05) and five severity levels (INFO, LOW, MEDIUM, HIGH, CRITICAL). The taxonomy is defined in Appendix C-02 and is machine-readable in `uiao-core`. All Drift Records MUST use a taxonomy-defined drift type and severity.

The taxonomy can only be extended (new types added) — existing types cannot be modified or removed. Extensions require Governance Plane approval and a new ADR entry.

## Consequences

**Positive:**
- Consistent drift classification across all adapters
- Enables meaningful drift aggregation and trending
- Severity levels drive consistent automated actions

**Negative:**
- Taxonomy evolution requires governance overhead
- Some drift events may not fit neatly into a single taxonomy type — multi-type classification is allowed but adds complexity

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
