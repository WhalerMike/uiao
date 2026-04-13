---
title: "Appendix B-02: Identity Anchoring"
appendix: "B-02"
family: "Truth Fabric"
status: DRAFT
version: "1.0"
last_updated: "2026-04-07"
related_adrs: ["ADR-008"]
---

# Appendix B-02: Identity Anchoring

## Purpose

This appendix defines the identity anchoring model used by the UIAO Truth Fabric to establish and maintain authoritative subject identities across heterogeneous integrated systems. Identity anchoring ensures that claims from different adapters about the same real-world subject are correctly correlated and stored under a single canonical identity.

## Scope

Applies to all Canonical Claims that include a `subject` field. Identity anchoring is a prerequisite for claim correlation, drift detection, and compliance attestation.

## The Identity Anchoring Problem

Each external system may use a different identifier for the same real-world subject. For example:
- An identity provider uses a UUID
- An HR system uses an employee number
- A cloud platform uses an email address
- A physical access system uses a badge ID

Without anchoring, claims from these four systems about the same person cannot be correlated. Drift detection across systems becomes impossible.

## Canonical Identity Records

The Truth Fabric maintains a Canonical Identity Record (CIR) for each real-world subject. A CIR consists of:
- `canonical_id`: A UIAO-assigned UUID that is stable for the lifetime of the subject
- `identity_type`: The subject type (person, device, service, organization, etc.)
- `anchors`: A list of anchor bindings, each consisting of a source system ID and the local identifier used by that system
- `created_at`: Timestamp when the CIR was first created
- `updated_at`: Timestamp of last anchor update

## Anchor Binding Process

When an adapter submits a claim with a subject identifier, the Truth Fabric:
1. Looks up the subject identifier in the anchor index for the source system
2. If a CIR exists for that anchor: routes the claim to the existing CIR
3. If no CIR exists: creates a new CIR and registers the anchor binding
4. If the adapter provides explicit correlation hints (e.g., a cross-system identifier): merges the anchor with an existing CIR if one exists for the correlated identity

## Zero-Trust Identity Anchoring

Per ADR-008, the UIAO identity anchoring model is zero-trust: no anchor is trusted by default simply because it comes from a reputable source. Every anchor binding MUST be verified through at least one of:
- Cryptographic proof from the subject (e.g., a signed challenge response)
- Cross-system corroboration (two independent adapters asserting the same anchor binding)
- Manual Governance Plane authorization

Unverified anchor bindings are flagged with `verification_status: PENDING` and treated as low-confidence until verification is complete.

## Dependencies

- **ADR-008:** Zero-trust identity anchoring decision record
- **Appendix B-01:** Canonical Claim Schema (subject field definition)
- **Appendix B-03:** Multi-cloud identity matrix (cross-cloud anchor patterns)

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
