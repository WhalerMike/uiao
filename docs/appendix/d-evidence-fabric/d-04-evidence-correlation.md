---
title: "Appendix D-04: Evidence Correlation"
appendix: "D-04"
family: "Evidence Fabric"
status: DRAFT
version: "1.0"
last_updated: "2026-04-07"
related_adrs: ["ADR-011", "ADR-020", "ADR-024"]
---

# Appendix D-04: Evidence Correlation

## Purpose

This appendix defines the evidence correlation model for the UIAO Evidence Fabric. Correlation enables auditors and automated tools to trace relationships between evidence records — linking drift records to their originating claims, linking compliance attestations to their supporting evidence, and linking governance events to the adapters that produced them.

## Scope

Applies to all queries against the Evidence Fabric that span multiple records or multiple subjects. Correlation is a read-only operation — it does not modify evidence records.

## Correlation Dimensions

Evidence records can be correlated along four dimensions:

**1. Subject Correlation:** All evidence records for a given canonical subject (identified by their canonical_id in the Truth Fabric). Used to reconstruct the full history of a subject's identity, compliance status, and drift events.

**2. Adapter Correlation:** All evidence records produced by a given adapter. Used to audit an adapter's behavior, detect anomalies, and support adapter decommissioning.

**3. Control Correlation:** All evidence records that contribute to a given compliance control. Used to produce compliance packages and assess control satisfaction.

**4. Temporal Correlation:** All evidence records within a given time window. Used for incident investigation and governance reporting.

## Evidence Diffing

Per ADR-024, the Evidence Fabric supports evidence diffing — comparing the evidence state at two points in time for a given subject or control. An evidence diff shows:
- Records that existed at time T1 but not T2 (should be empty — evidence is never deleted, so this indicates a hash chain breach)
- Records that were added between T1 and T2
- Changes in control satisfaction status between T1 and T2

Evidence diffing is a key tool for continuous monitoring: run a diff against the previous reporting period to identify what changed.

## Multi-Adapter Correlation

Per ADR-011, the Evidence Fabric supports multi-adapter correlation queries: given a compliance control, find all evidence records from all adapters that contribute to satisfying that control, and assess the aggregate satisfaction level.

Multi-adapter correlation produces a Correlation Report that includes:
- The control ID and framework
- Each contributing adapter's evidence records
- The aggregate satisfaction level (full, partial, or compensating)
- Any gaps: adapters that were expected to contribute but have not produced a relevant record within the expected window

## Correlation Determinism

Per ADR-020, correlation queries are deterministic: the same query run at different times returns the same results (plus any new records added since the previous query). Results never shrink because evidence records are never deleted.

This determinism guarantee enables the Evidence Fabric to serve as a reliable foundation for continuous monitoring automation — the same automated check run repeatedly will produce consistent results, making it easy to detect changes.

## Correlation API

The Evidence Fabric exposes a correlation API with the following query types:
- `GET /evidence/subject/{canonical_id}` — all records for a subject
- `GET /evidence/adapter/{adapter_id}` — all records from an adapter
- `GET /evidence/control/{framework}/{control_id}` — all records for a control
- `GET /evidence/window?from={ts}&to={ts}` — all records in a time window
- `POST /evidence/diff` — diff evidence state between two timestamps

All API responses include a `correlation_id` that can be used to track a multi-step query session.

## Dependencies

- **ADR-011:** Multi-adapter correlation decision record
- **ADR-020:** Evidence correlation determinism decision record
- **ADR-024:** Evidence diffing decision record
- **Appendix D-01:** Evidence determinism
- **Appendix D-02:** Evidence lifecycle

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
