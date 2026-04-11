# UIAO Organizational Operating Model Layer

## Overview

The UIAO Organizational Operating Model Layer defines how the company behind UIAO becomes a mirror of the product: deterministic, drift-resistant, modular, and governed by explicit contracts. This layer covers team structure, decision-making, execution rhythm, and how the organization scales without losing coherence.

---

## 1. Org Topology: Teams as Planes

UIAO internal structure mirrors the product four-plane architecture:

| Team | Responsibilities |
|------|----------------|
| Plane 1 Team (Evidence & Integrations) | Evidence collectors, SaaS/cloud integrations, schema ingestion, plugin onboarding |
| Plane 2 Team (IR, KSI, Drift Engine) | IR model, KSI semantics, drift classification, rule correctness |
| Plane 3 Team (Evidence Bundles & Provenance) | Evidence bundle generation, provenance manifests, hashing and signing |
| Plane 4 Team (OSCAL & Reporting) | OSCAL generation, SSP/SAP/SAR/POA&M, auditor-facing artifacts |
| Enforcement Team (cross-plane) | Enforcement adapters, EPL language, safety model, rollback logic |
| Platform Team | CI/CD, test harness, determinism engine, sandbox |
| Ecosystem Team | Marketplace, control packs, plugin certification |

This topology ensures no functional silos - only pipeline stages.

---

## 2. Charters & Boundaries

Every team has a versioned charter containing:
- Purpose
- Inputs
- Outputs
- SLAs
- Non-goals
- Interfaces
- Invariants

Charters are:
- Stored in Git
- Version-pinned
- Reviewed quarterly
- Drift-checked

This prevents organizational drift the same way UIAO prevents governance drift.

---

## 3. Decision-Making Model

UIAO uses a deterministic decision model.

### 3.1 Decision Types

| Decision Type | Approvers |
|---------------|-----------|
| Spec decisions | Cross-plane approval |
| Product decisions | PM + architect |
| Architecture decisions | Architecture council |
| Operational decisions | Team-level |

### 3.2 Decision Artifacts

Every decision produces:
- A Decision Record (DR)
- Version pin
- Impact analysis
- Rollback plan

### 3.3 Decision Invariants

- No decision without a DR
- No DR without a rollback
- No rollback without provenance

This creates organizational determinism.

---

## 4. Execution Rhythm

UIAO runs on a four-layer execution cadence:

| Cadence | Activities |
|---------|----------|
| Daily | Standups, drift checks, blocker resolution |
| Weekly | Cross-plane sync, spec alignment review, marketplace updates |
| Monthly | Release train, control pack updates, plugin certification batch |
| Quarterly | Charter review, architecture review, category narrative update |

This cadence keeps the organization synchronized and drift-free.

---

## 5. Cross-Team Contracts

Teams interact through explicit contracts, not meetings.

### 5.1 API Contracts

- Evidence API
- IR API
- KSI API
- OSCAL API

### 5.2 SLA Contracts

- Evidence freshness
- Drift detection latency
- OSCAL regeneration latency
- Enforcement safety

### 5.3 Governance Contracts

- Version pins
- Spec compliance
- Determinism guarantees

Contracts are machine-verifiable.

---

## 6. Internal Quality Gates

UIAO applies the same rigor internally as externally.

| Gate | Requirement |
|------|-------------|
| Spec Compliance Gate | No change merges unless spec-aligned, schema-valid, and deterministic |
| Golden-File Gate | All golden files must match expected outputs |
| Provenance Gate | All artifacts must be signed, hashed, and version-pinned |
| Drift Gate | Org-level drift detected in charters, processes, and decisions |

This makes the organization self-correcting.

---

## 7. Leadership Model

UIAO leadership is based on stewardship, not hierarchy.

### 7.1 Stewards, Not Managers

Stewards:
- Own invariants
- Maintain boundaries
- Protect determinism
- Ensure drift resistance

### 7.2 Architecture Council

Responsible for:
- Spec evolution
- KSI semantics
- Drift model
- Enforcement safety

### 7.3 Governance Council

Responsible for:
- Category narrative
- Standards alignment
- Regulatory influence

Leadership is modular, not hierarchical.

---

## Summary: What This Layer Provides

| Component | Purpose |
|-----------|--------|
| Org Topology | Seven teams mirroring the four-plane architecture |
| Charters & Boundaries | Versioned, git-stored, drift-checked team contracts |
| Decision-Making Model | Deterministic DRs with rollback and provenance |
| Execution Rhythm | Daily/Weekly/Monthly/Quarterly synchronized cadence |
| Cross-Team Contracts | Machine-verifiable API, SLA, and governance contracts |
| Internal Quality Gates | Spec, golden-file, provenance, and drift gates |
| Leadership Model | Stewardship-based councils, not functional hierarchy |

This layer makes the organization itself a Governance OS - drift-resistant, deterministic, and provenance-aware.
