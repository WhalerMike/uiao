---
title: "ADR-007: Multi-Cloud Adapter Model"
adr: "ADR-007"
status: ACCEPTED
date: "2026-01-20"
deciders: ["UIAO Governance Board", "ARB"]
---

# ADR-007: Multi-Cloud Adapter Model

## Status

ACCEPTED

## Context

UIAO integrates with systems across multiple cloud platforms (Azure, AWS, GCP) and on-premises environments. Each cloud platform has different identity models, APIs, and data formats. We needed to decide whether to build cloud-specific adapters or a unified multi-cloud adapter.

## Decision

We adopt the **cloud-specific adapter** model: each cloud platform has its own dedicated adapter rather than a single multi-cloud adapter.

Key design decisions:
- Azure adapter handles all Azure/Entra ID identity constructs
- AWS adapter handles all AWS IAM/SSO constructs
- GCP adapter handles all Google Cloud identity constructs
- On-premises AD adapter handles Active Directory
- Each adapter translates its platform's native constructs to Canonical Claims independently
- Cross-cloud identity correlation is handled by the Truth Fabric's identity anchoring model, not by the adapters

This decision was reviewed and approved by the ARB because it has cross-organizational architectural implications.

## Consequences

**Positive:**
- Each adapter team can develop and maintain their adapter independently
- Platform-specific failures are isolated — an AWS adapter failure does not affect Azure adapter
- Each adapter can be optimized for its platform's specific APIs and rate limits
- Simpler adapter development: each team only needs to understand one platform

**Negative:**
- More adapters to maintain (one per cloud platform)
- Cross-cloud identity correlation requires explicit effort in the Truth Fabric
- The Multi-Cloud Identity Matrix (Appendix B-03) must be maintained as platforms evolve
