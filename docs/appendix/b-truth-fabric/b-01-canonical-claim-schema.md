---
title: "Appendix B-01: Canonical Claim Schema"
appendix: "B-01"
family: "Truth Fabric"
status: DRAFT
version: "1.0"
last_updated: "2026-04-07"
related_adrs: ["ADR-005"]
---

# Appendix B-01: Canonical Claim Schema

## Purpose

This appendix defines the Canonical Claim Schema — the authoritative data structure for representing adapter state, integration assertions, and governance claims within the UIAO Truth Fabric. All data entering or leaving the UIAO framework MUST be expressed as a Canonical Claim.

## Scope

Applies to all data structures consumed by or produced by the Truth Fabric. Adapter schemas in `uiao-core` MUST validate against the Canonical Claim Schema.

## What Is a Canonical Claim?

A Canonical Claim is a structured, versioned, and typed assertion about a specific aspect of an integrated system's state. Claims are:

- **Typed** — every claim has a `claim_type` drawn from the Canonical Claim Type Registry
- **Versioned** — every claim carries a schema version identifier
- **Signed** — claims produced by authorized adapters carry a digital signature
- **Traceable** — every claim carries a `source_adapter_id` and `source_system_id`
- **Timestamped** — every claim carries an `observed_at` timestamp (when the adapter observed the state) and a `recorded_at` timestamp (when the Truth Fabric received the claim)

## Canonical Claim Structure

```json
{
  "claim_id": "<uuid>",
  "claim_type": "<string from Claim Type Registry>",
  "schema_version": "1.0",
  "source_adapter_id": "<registered adapter ID>",
  "source_system_id": "<external system identifier>",
  "observed_at": "<ISO 8601 timestamp>",
  "recorded_at": "<ISO 8601 timestamp>",
  "subject": {
    "type": "<subject type>",
    "id": "<subject identifier>",
    "namespace": "<optional namespace>"
  },
  "assertion": {
    "<claim-type-specific fields>"
  },
  "signature": {
    "algorithm": "RS256",
    "value": "<base64-encoded signature>"
  },
  "metadata": {
    "confidence": "<high|medium|low>",
    "tags": ["<optional tags>"]
  }
}
```

## Claim Type Registry

The Claim Type Registry is maintained in `uiao-core` as a machine-readable JSON file. Human-readable descriptions are maintained here. Core claim types:

| Claim Type | Description |
|---|---|
| `identity.verified` | Subject identity has been verified by the source adapter |
| `state.observed` | A state observation for a subject has been recorded |
| `compliance.asserted` | Source adapter asserts compliance with a named control |
| `drift.detected` | Drift between observed state and canonical state has been detected |
| `access.granted` | Access to a resource was granted to a subject |
| `access.denied` | Access to a resource was denied to a subject |
| `lifecycle.transition` | A lifecycle state transition has occurred |

## Claim Validation

The Truth Fabric validates every incoming claim against:
1. The Canonical Claim Schema (structural validation)
2. The Claim Type Registry (claim_type must exist)
3. The adapter's registered signing key (signature verification)
4. The adapter's authorized claim types (an adapter may only assert claim types it is authorized for in its registration)

Claims failing validation are rejected and an Evidence Fabric audit event is generated.

## Dependencies

- **ADR-005:** Decision record for the Canonical Claim Schema design
- **uiao-core:** Machine-readable Canonical Claim Schema and Claim Type Registry
- **Appendix B-02:** Identity anchoring for subject identifiers

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
