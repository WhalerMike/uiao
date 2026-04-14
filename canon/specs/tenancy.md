# UIAO Tenant & Environment Strategy Layer

## Overview

The UIAO Tenant & Environment Strategy Layer defines how UIAO becomes safe to change: how to separate dev/stage/prod, isolate tenants, run canaries, and evolve the system without breaking determinism or trust.

---

## 1. Environment Model

Three canonical environments:

| Environment | Characteristics |
|-------------|----------------|
| Dev | Fast iteration; feature flags on by default; synthetic tenants + synthetic evidence |
| Stage | Mirrors prod topology; limited real tenants (designated canaries); full HA, full CI/CD gating |
| Prod | All real tenants; only certified plugins, control packs, specs |

**Rule:** No direct dev -> prod; everything flows dev -> stage -> prod.

---

## 2. Tenant Classes

Four tenant classes:

| Class | Description | Channels | Environments |
|-------|-------------|----------|--------------|
| Internal | UIAO own orgs; used for dogfooding | Edge/Beta/Stable/LTS | All |
| Canary | Small, representative customers; opt-in to early features | Beta/Stable | Stage + Prod |
| Standard | Normal customers; only stable features | Stable | Prod |
| Regulated | GCC-M / high-assurance | LTS + FIPS-aligned only | Stage + Prod only |

Each tenant has a class label that drives which channel they see, which plugins/control packs are allowed, and which environments they can exist in.

---

## 3. Environment Separation and Data Boundaries

| Environment | Account Isolation | Data Policy |
|-------------|-------------------|-------------|
| Dev | Separate cloud account/subscription | No production data; synthetic evidence generators only |
| Stage | Separate account/subscription from prod | Limited real tenants; shorter retention than prod |
| Prod | Separate account/subscription | Strict tenant isolation; full retention and compliance policies |

**Data movement rule:** No cross-environment data movement except downward (e.g., anonymized patterns from prod -> stage/dev for testing).

---

## 4. Feature Flags and Rollout Strategy

All non-trivial changes are behind feature flags.

**Flags scoped by:**
- Environment
- Tenant class
- Individual tenant (for canaries)

**Rollout Pattern:**

| Phase | Scope |
|-------|-------|
| Dev | Flag on for all internal tenants |
| Stage | Flag on for canary tenants only |
| Prod Phase 1 | Canary tenants |
| Prod Phase 2 | Standard tenants |
| Prod Phase 3 | Regulated tenants (if applicable) |

**Every flag has:**
- Spec reference
- Owner
- Expiry date (must be removed or made permanent)

---

## 5. Migration and Sandbox Strategy

For breaking changes (CORE or SPEC version increments):

1. Create migration sandboxes per tenant class:
   - Clone of tenant configuration
   - Synthetic or sampled evidence
   - Run full pipeline with new version

2. Compare outputs:
   - KSI results
   - Drift classification
   - OSCAL artifacts

3. If differences are not spec-justified -> block migration

---

## 6. Multi-Tenant Safety Rules

**No cross-tenant queries in:**
- Evidence ingestion
- KSI evaluation
- Drift engine
- OSCAL generation

**Shared infrastructure only at:**
- Orchestrator
- API gateway
- Plugin registry (metadata only, not data)

**Every log, metric, and trace is:**
- Tenant-tagged
- Environment-tagged

---

## Summary: What This Layer Provides

| Component | Purpose |
|-----------|--------|
| Environment Model | Clear dev/stage/prod separation with no direct dev-to-prod path |
| Tenant Classes | Four classes mapping to channels, features, and environment access |
| Environment Data Boundaries | Account isolation and data movement rules |
| Feature Flags | Scoped by environment, tenant class, and individual tenant |
| Rollout Strategy | Phased canary rollout with spec-referenced flag lifecycle |
| Migration Sandboxes | Safe breaking-change validation per tenant class |
| Multi-Tenant Safety | No cross-tenant queries; shared infra limited to metadata only |

---

## Next Layer

The next layer is the **UIAO Commercialization & Packaging Layer**, covering:
- SKUs and editions
- Pricing levers
- How the architecture maps to sellable units
