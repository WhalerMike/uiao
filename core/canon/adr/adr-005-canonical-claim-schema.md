---
title: "ADR-005: Canonical Claim Schema"
adr: "ADR-005"
status: ACCEPTED
date: "2026-01-15"
deciders: ["UIAO Governance Board"]
---

# ADR-005: Canonical Claim Schema

## Status

ACCEPTED

## Context

UIAO adapters integrate with heterogeneous external systems that use different data formats, schemas, and identity models. Without a canonical schema, the Truth Fabric would need to understand each external system's native format, making it fragile and difficult to extend. We needed a single, typed, versioned, and signed data structure that all adapter outputs must conform to before entering the UIAO framework.

## Decision

We adopt the **Canonical Claim** as the fundamental data structure for all UIAO adapter outputs. A Canonical Claim is a structured, versioned, typed, and digitally signed assertion about a specific aspect of an integrated system's state.

Key design decisions:
- Claims are typed via a Claim Type Registry (not free-form)
- Claims are versioned (schema_version field)
- Claims carry two timestamps: observed_at (adapter observation time) and recorded_at (Truth Fabric write time)
- Claims carry digital signatures from the originating adapter
- Claims are immutable once accepted by the Truth Fabric

The Canonical Claim Schema is stored as a machine artifact in `uiao-core`.

## Consequences

**Positive:**
- The Truth Fabric only needs to understand one schema — all adapter complexity is hidden behind the canonical schema
- Claims are auditable and non-repudiable because they are signed
- New adapters only need to learn one output format
- The claim type registry provides a controlled vocabulary for governance assertions

**Negative:**
- Adapter developers must translate their native data into the canonical schema (added adapter complexity)
- Schema evolution requires careful versioning to avoid breaking existing adapters
- The claim type registry must be maintained as governance vocabulary evolves

**Neutral:**
- The Canonical Claim Schema must be versioned independently of the UIAO framework version

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
