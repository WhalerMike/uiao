---
title: "ADR-024: Evidence Diffing"
adr: "ADR-024"
status: ACCEPTED
date: "2026-03-03"
deciders: ["UIAO Governance Board"]
---

# ADR-024: Evidence Diffing

## Status

ACCEPTED

## Context

Continuous monitoring requires comparing the governance state at two points in time: "What changed between last month's report and this month's?" Without a formal diff capability, compliance teams manually compare reports — an error-prone and time-consuming process.

## Decision

The Evidence Fabric provides a **diff API** that compares evidence state between two timestamps. A diff shows: records added between T1 and T2, changes in control satisfaction status between T1 and T2, and any hash chain gaps (which would indicate tampering). Records that existed at T1 and not T2 are flagged as anomalies (should be empty — evidence is never deleted).

The diff is a first-class API operation, not a client-side computation. This ensures consistency and efficiency.

## Consequences

**Positive:**
- Continuous monitoring automation becomes straightforward: run a diff against the previous reporting period
- Anomaly detection: hash chain gaps are visible in diffs
- Reduces manual compliance comparison work

**Negative:**
- Diff computation at scale (large time windows, many subjects) can be resource-intensive
- Time-bounded diffs are recommended — full diff across all time is impractical

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
