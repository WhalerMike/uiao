---
document_id: UIAO_112
title: "UIAO Multi-Tenant Isolation Model"
version: "1.1"
status: Current
classification: CANONICAL
owner: "Michael Stratton"
created_at: "2026-04-14"
updated_at: "2026-05-04"
boundary: "GCC-Moderate"
---

# UIAO Multi-Tenant Isolation Model

## Isolation Dimensions

- **Data Isolation**
  - Per-tenant namespaces in data lake
  - Per-tenant evidence graphs
  - Tenant-scoped encryption keys
- **Execution Isolation**
  - Per-tenant job queues
  - Per-tenant SCuBA runs
  - No cross-tenant process reuse for privileged actions
- **Access Isolation**
  - Tenant claims in JWT
  - All queries filtered by tenant_id
  - Auditor API is tenant-scoped

## Models

- **Single-Tenant Deployment**
  - One UIAO instance per customer
- **Multi-Tenant Deployment**
  - Shared control plane
  - Strict tenant boundaries in:
    - Storage
    - Identity
    - Logs

## Authorization Boundary Model

Multi-tenant deployments share isolation primitives but may differ in their
**authorization boundary**. Two patterns are recognized:

- **Per-tenant authorization** — each tenant runs its own ATO against its
  own SSP. This is the historical UIAO default and remains supported.
- **Single-ATO with reciprocity** — one federal authorizing official issues
  a controlling ATO that covers all consuming tenants under documented
  reciprocity. The controlling SSP enumerates the configuration latitude
  available to consuming tenants; per-tenant SSPs are not produced. Defined
  authoritatively in **UIAO_140** (`single-ato-reciprocity-model.md`),
  established by ADR-054. Reference instance: OPM Federal HRIT Modernization
  (Solicitation 24322626R0007).

Drift between the controlling SSP and per-tenant runtime configuration is
classified per the existing UIAO drift taxonomy; UIAO_140 §5 enumerates the
tenant-scoped semantics.
