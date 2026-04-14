---
document_id: UIAO_102
title: "UIAO Platform Services Layer"
version: "1.0"
status: Current
classification: CANONICAL
owner: "Michael Stratton"
created_at: "2026-04-14"
updated_at: "2026-04-14"
boundary: "GCC-Moderate"
---

# UIAO Platform Services Layer

This layer defines the extensibility and marketplace infrastructure that transforms UIAO from a compliance engine into a compliance platform.

---

## 1. UIAO Plugin System

**Goal:** Allow third parties and internal teams to extend UIAO without modifying core.

### Plugin Types
- **Evidence plugins** — new collectors (e.g., another SaaS)
- **Control plugins** — new control packs (e.g., CIS, ISO)
- **Enforcement plugins** — new adapters (e.g., Zscaler, Okta)

### Contract
Each plugin implements: `register()`, `capabilities()`, `execute()`, `health()`

### Isolation
- Run in separate process/container
- Strict input/output schema (IR in, IR/evidence out)

---

## 2. UIAO Control Pack SDK

**Goal:** Let teams build and distribute new control frameworks as first-class UIAO artifacts.

### A Control Pack Contains
- Control definitions (YAML/JSON)
- KSI rules
- Evidence binding templates
- OSCAL profile reference
- Mapping table (source field → control)

### Tooling
- Scaffolding CLI: `uiao control-pack init`
- Validation tool: `uiao control-pack validate`
- Pack registry metadata (version, owner, scope)

---

## 3. UIAO Evidence Marketplace

**Goal:** Treat evidence sources as pluggable commodities.

### Concept
Each evidence plugin advertises: `source`, `controls_covered`, `cost` (latency/complexity), `frequency`

### Marketplace View
"To cover AC-21, you can enable: SCuBA, M365 Sharing API, DLP logs"

### Selection
- Operator selects evidence sources per control
- UIAO orchestrator routes collection accordingly
- Cost/coverage tradeoffs visible to operators

---

## 4. UIAO Enforcement Marketplace

**Goal:** Same idea, but for actions instead of signals.

### Enforcement Adapters Advertise
- `controls_supported`, `side_effects`, `blast_radius`, `rollback_capable`

### EPL Can Express Preferences
"Use low-blast-radius enforcement first; escalate only if drift persists."

### Governance
Some adapters marked "advisory only" (no changes, just recommendations)

---

## 5. UIAO Tenant Provisioning Service

**Goal:** Make onboarding a new tenant deterministic.

### Provisioning Steps
1. Create tenant namespace in data lake
2. Assign encryption keys
3. Configure job queue
4. Register evidence collectors
5. Apply default control pack
6. Schedule nightly SCuBA run
7. Generate initial OSCAL SSP stub

### Artifacts
- `Tenant-Provisioning-Runbook.md`
- `uiao tenant create` CLI command
- Idempotent provisioning script

---

## What This Layer Unlocks

With the Platform Services Layer, UIAO becomes:
- **Extensible** — any team can add evidence collectors, control packs, or enforcement adapters
- **Marketable** — evidence and enforcement surfaces are composable offerings
- **Scalable** — new tenants can be provisioned deterministically
- **Governable** — all plugins run in isolation with strict contracts
