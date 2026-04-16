---
title: "Appendix C-01: Drift Detection"
appendix: "C-01"
family: "Drift Fabric"
status: DRAFT
version: "1.0"
last_updated: "2026-04-07"
related_adrs: ["ADR-009", "ADR-012"]
---

# Appendix C-01: Drift Detection

## Purpose

This appendix defines the drift detection model for the UIAO Drift Fabric. Drift detection is the process by which the Drift Fabric compares an integrated system's observed state against its canonical state and computes a delta representing the deviation.

## Scope

Applies to all systems registered in the Truth Fabric. Drift detection operates on Canonical Claims and canonical state records — it does not directly access external systems.

## What Is Drift?

Drift occurs when an integrated system's observed state deviates from its canonical (expected) state. Drift may be:

- **Configuration drift:** A system's configuration settings deviate from the canonical configuration baseline
- **Identity drift:** A subject's identity attributes differ from the canonical identity record (e.g., role assignments changed outside the managed process)
- **Compliance drift:** A system that was previously compliant with a control is no longer compliant based on new observations
- **Relationship drift:** The relationships between subjects (e.g., group memberships, access assignments) deviate from the canonical model

## Drift Detection Algorithm

The Drift Fabric runs drift detection on a configurable schedule (default: every 15 minutes for HIGH-priority adapters, every 60 minutes for standard adapters). Detection can also be triggered on demand by the Governance Plane or automatically when a new Canonical Claim arrives.

The algorithm:
1. For each subject with a canonical state record in the Truth Fabric:
   a. Retrieve the most recent Canonical Claim(s) for the subject from each registered adapter
   b. Compare each claim's assertion fields against the corresponding fields in the canonical state record
   c. Compute the delta: the set of fields where the claim value differs from the canonical value
   d. If the delta is non-empty: generate a Drift Record

2. Classify the Drift Record by drift type and severity (see Appendix C-02 for the taxonomy)

3. Write the Drift Record to the Evidence Fabric

4. If drift severity is HIGH or CRITICAL: trigger the reconciliation workflow (see ADR-009) and notify the Governance Plane

## Drift Detection Scope Filters

Not all deviations are meaningful drift. The Drift Fabric supports scope filters that can exclude certain fields or adapters from drift detection:

- **Field exclusion:** Specific claim assertion fields can be excluded from drift comparison (e.g., last-login timestamps that are expected to change constantly)
- **Adapter exclusion:** Specific adapters can be temporarily excluded from drift detection (e.g., during planned maintenance windows)
- **Subject exclusion:** Specific subjects can be excluded (e.g., service accounts with known dynamic attributes)

Scope filters MUST be documented in a Governance Plane-approved configuration and recorded in the Evidence Fabric.

## Drift Detection Immutability

Per ADR-009, the Drift Ledger is immutable. Every Drift Record written to the Evidence Fabric is permanent. If drift is later determined to be a false positive, a correction record is appended — the original Drift Record is never modified or deleted.

## Dependencies

- **Truth Fabric (Appendix B):** Source of canonical state records and Canonical Claims
- **Evidence Fabric (Appendix D):** Destination for all Drift Records
- **ADR-009:** Drift ledger immutability decision record
- **ADR-012:** Canonical drift taxonomy decision record
- **Appendix C-02:** Drift taxonomy definitions

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
