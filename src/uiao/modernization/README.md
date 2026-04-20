---
document_id: MOD_INDEX
title: "Microsoft Identity Modernization Bridge"
version: "1.0"
status: DRAFT
classification: OPERATIONAL
owner: Michael Stratton
created_at: 2026-04-18
updated_at: 2026-04-18
boundary: GCC-Moderate
parent_canon: UIAO_008
---

# Microsoft Identity Modernization Bridge

**Mapping Client/Server-Era Active Directory into Modern Hybrid-Cloud Entra ID**

---

## Purpose

This module provides the complete, deterministic, drift-resistant architecture for modernizing legacy Active Directory (AD) organizational hierarchies into Microsoft Entra ID within the M365 GCC-Moderate boundary.

Federal agencies are overwhelmingly frozen in a Client/Server-era AD model circa 2003 — x.500-style Organizational Units (OUs), Group Policy-linked delegation, and manual identity lifecycle management. Microsoft's deprecation lifecycle is driving an inevitable transition. This corpus provides the strategy, tooling, schemas, and operational runbooks to execute that transition without governance collapse.

## Core Concept: The OrgTree

The **OrgTree** replaces legacy OU-based hierarchy with a portable, attribute-driven hierarchy encoded in Entra ID extension attributes. Each identity object carries an **OrgPath** — a deterministic, codebook-validated string (e.g., `ORG-IT-SEC-SOC`) — that encodes its exact position in the organizational hierarchy.

- **Dynamic Groups** replace OUs as the "virtual container" layer
- **Administrative Units** replace OU-scoped delegation
- **HR-driven provisioning** replaces manual identity management
- **Drift detection** ensures the canonical OrgPath structure remains authoritative

## Architecture: Four-Layer Governance Stack

```
┌─────────────────────────────────────┐
│       Governance Layer              │  ← Policy enforcement, SLA tracking
├─────────────────────────────────────┤
│       Policy Layer                  │  ← Conditional Access, compliance rules
├─────────────────────────────────────┤
│       Structure Layer               │  ← Dynamic Groups, AUs, delegation
├─────────────────────────────────────┤
│       Identity Layer                │  ← OrgPath attributes, HR sync
└─────────────────────────────────────┘
```

## Relationship to Core UIAO Canon

This module is a **separate canon within UIAO** — it uses the `MOD_xxx` namespace and has its own `document-registry.yaml`. It is **not** core UIAO canon (which uses `UIAO_xxx` IDs) but is governed by the same principles:

- **Canon Supremacy** — `orgtree/` is the single source of truth for identity modernization
- **Schema is fixed; values are flexible** — OrgPath structure is immutable; codebook values change through governed workflows
- **Drift Resistance** — every attribute, group, and delegation mapping is continuously validated

### Core Canon Touchpoints

| MOD Artifact | Core Canon | Relationship |
|---|---|---|
| MOD_D (Delegation Matrix) | UIAO_004 (Governance Framework) | Maps AD OU delegation → EntraID AUs |
| MOD_I (PowerShell Validation) | UIAO_106 (Compliance CLI) | Extends CLI for OrgPath validation |
| MOD_L (SLA Models) | UIAO_117 (Recovery Layer) | Defines migration-specific SLAs |
| MOD_M (Drift Detection) | UIAO_110 (Drift Engine) | Uses UIAO_110 patterns for OrgPath drift |
| MOD_S (State Machine) | UIAO_001 (Architecture) | OrgTree-specific state machine |

## Document Corpus

The corpus consists of 27 artifacts:

- **MOD_001** — Executive Summary & Architecture (Sections 1–7)
- **Appendices A–Z** — 26 standalone governance artifacts covering codebooks, schemas, runbooks, tests, decision trees, telemetry, and glossary

See [`document-registry.yaml`](orgtree/document-registry.yaml) for the complete registry with scope descriptions and cross-references.

## Boundary Rules

- **GCC-Moderate** — M365 SaaS services only; does not include Azure services
- **Commercial Cloud** as governed by FedRAMP unless specifically noted
- **Tenant-agnostic** — no tenant-specific IDs in any artifact
- **HR-driven** — identity lifecycle tied to HR system of record via Entra ID provisioning connectors

## Getting Started

1. Read `MOD_001_Executive_Summary.md` for the architectural overview
2. Review `MOD_A_OrgPath_Codebook.md` to understand the OrgPath encoding
3. Follow `MOD_F_Migration_Runbook_OU_to_Entra.md` for the 8-phase migration sequence
4. Use `MOD_I_PowerShell_Validation_Module.md` for automated validation
