---
document_id: MOD_W
title: "Appendix W — Canonical Error Taxonomy"
version: "1.0"
status: DRAFT
classification: CANONICAL
owner: Michael Stratton
created_at: 2026-04-18
updated_at: 2026-04-18
boundary: GCC-Moderate
namespace: MOD
parent_canon: UIAO_008
---

# Appendix W — Canonical Error Taxonomy

Purpose

This appendix defines all error codes and classifications used across the Governance OS. Every error condition has a unique code, a severity, a message template, and a recommended action.

Scope

Covers 10 error categories with a minimum of 5 codes per category, totaling 50 error codes. Applies to all validation, detection, execution, and workflow operations within M365 GCC-Moderate.

Canonical Structure

Error codes follow the format GOV-[CATEGORY]-[NUMBER] where CATEGORY is a three-letter code and NUMBER is a zero-padded three-digit integer.

Technical Scaffolding

Error Handling Rules

Propagation: Errors propagate upward through the governance layer stack. An Identity Layer error generates a Structure Layer alert, which may trigger a Governance Layer escalation.

Retry Logic: Auto-recoverable errors (marked Y) are retried up to 3 times with exponential backoff (1s, 4s, 16s). After 3 failures, the error is reclassified as non-recoverable.

Escalation: Non-recoverable Critical errors trigger immediate Level 2 escalation (Appendix Q). Non-recoverable High errors follow standard SLA escalation.

Dead Letter: Errors that cannot be resolved after Level 4 escalation are recorded in a dead-letter log for Governance Board review at the next scheduled session.

Correlation: All errors include a correlationId that links related errors across layers and operations.

Boundary Rules

Error codes GOV-BND-* specifically enforce the M365 GCC-Moderate boundary.

Error logging and tracking occurs within M365-accessible systems only.

Drift Considerations

An error condition that has no corresponding error code constitutes taxonomy drift. The taxonomy must be updated through Workflow 8.

Error codes are immutable once published; deprecated codes are retained with a "DEPRECATED" suffix in the message template.

Governance Alignment

This taxonomy implements Principle 1 (Deterministic State) for error handling: every error has exactly one code, one severity, and one recommended action. It supports Principle 3 (Provenance Traceability) by ensuring that every error is classifiable and traceable.
