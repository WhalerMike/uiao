# UIAO Go-To-Market Layer

## Overview

The UIAO Go-To-Market (GTM) Layer is the commercial and narrative layer that transforms UIAO from a compliance platform into a market-ready, category-defining product. This layer defines UIAO's category, positioning, messaging, competitive landscape, pricing, and buyer personas.

---

## 1. UIAO Category Definition

**UIAO is not:**
- SSPM
- CSPM
- GRC
- SIEM/SOAR
- Compliance documentation generator
- SCuBA wrapper
- OSCAL exporter

**UIAO is:**
A **deterministic compliance control plane**.

### Category Name (Canonical)
**Compliance Control Plane (CCP)**

### Category Definition

A Compliance Control Plane is a deterministic system that ingests configuration evidence, evaluates it against formal control logic, enforces policy where allowed, and emits auditor-ready OSCAL artifacts with full provenance and drift-to-POA&M linkage.

This is the new category that UIAO owns. It is distinct because:

- It is evidence-centric, not policy-centric
- It is deterministic, not heuristic
- It is OSCAL-native, not OSCAL-compatible
- It is enforcement-aware, not read-only
- It is drift-driven, not snapshot-driven
- It is provenance-backed, not trust-based

---

## 2. UIAO Positioning & Messaging Framework

### 2.1 Positioning Statement (External)

UIAO is the first Compliance Control Plane — a deterministic, evidence-centric platform that automates SCuBA, maps results to NIST/FedRAMP controls, enforces policy where allowed, and generates OSCAL-native ATO artifacts with full provenance.

### 2.2 Messaging Pillars

**Pillar 1 — Deterministic Compliance**
- No heuristics
- No guesswork
- No "interpretation"
- Every output is reproducible

**Pillar 2 — Evidence-First Architecture**
- Evidence → IR → KSI → Evidence Bundle → OSCAL
- Every object hashed
- Every object provenance-backed

**Pillar 3 — Enforcement-Aware**
- Conditional Access
- DLP
- Defender
- Zero-trust identity

**Pillar 4 — OSCAL-Native**
- SSP
- SAP
- SAR
- POA&M
- Catalogs
- Profiles

**Pillar 5 — Drift → POA&M Automation**
- Continuous monitoring
- Drift detection
- Auto-generated POA&M
- Remediation workflows

---

## 3. UIAO Competitive Landscape Map

### 3.1 Adjacent Categories

UIAO is not competing with these, but will be compared to them:

| Category | Vendors |
|----------|---------|
| SSPM | AppOmni, Obsidian, Adaptive Shield |
| CSPM | Wiz, Prisma, Lacework |
| GRC | Archer, ServiceNow, OneTrust |
| SIEM/SOAR | Splunk, Sentinel, Cortex |
| OSCAL Tools | GovReady, OpenControl |

### 3.2 Competitive Axes

| Axis | UIAO | Others |
|------|------|--------|
| Determinism | Deterministic | Heuristic, rule-based, ML-based |
| Evidence Binding | First-class evidence objects | Logs, alerts, snapshots |
| OSCAL Native | Full OSCAL generation | Export partial OSCAL or none |
| Enforcement | Enforcement adapters | Read-only |
| Drift → POA&M | Automated | Manual |

**UIAO wins on all five axes.**

---

## 4. UIAO Pricing & Packaging Strategy

### 4.1 Pricing Model

UIAO is priced on:
- Tenant count
- Evidence volume
- Control pack complexity
- Enforcement adapters enabled
- Retention period

### 4.2 Pricing Tiers

| Tier | Price | Capabilities |
|------|-------|--------------|
| UIAO Core | Free | Evidence ingestion, KSI evaluation, evidence bundles, CLI — no OSCAL, no enforcement |
| UIAO Standard | $ | Everything in Core + OSCAL SSP/SAP/SAR/POA&M, M365 baseline controls, single-tenant |
| UIAO Professional | $$ | Everything in Standard + enforcement adapters, zero-trust integration, multi-tenant, plugin marketplace |
| UIAO Enterprise | $$$ | Everything in Professional + FedRAMP Moderate control pack, ATO package generator, auditor delegation, 1–7 year retention, SLA-backed support |

---

## 5. UIAO Buyer Personas & Sales Motions

### 5.1 Buyer Personas

**Persona 1 — Federal CISO**
- Pain: ATO cost, drift, evidence sprawl
- Value: OSCAL automation, provenance, drift → POA&M

**Persona 2 — Enterprise Compliance Director**
- Pain: Manual evidence collection
- Value: Deterministic evidence bundles

**Persona 3 — Zero-Trust Program Lead**
- Pain: Identity enforcement gaps
- Value: Identity-only SKU

**Persona 4 — SaaS Security Lead**
- Pain: SaaS misconfigurations
- Value: SSPM-style SKU

### 5.2 Sales Motions

**Motion 1 — Compliance Modernization**
- Lead with OSCAL
- Show drift → POA&M
- Show provenance

**Motion 2 — Zero-Trust Identity**
- Lead with Conditional Access enforcement
- Show identity drift

**Motion 3 — FedRAMP Acceleration**
- Lead with SSP/SAP/SAR/POA&M automation
- Show ATO package generator

**Motion 4 — SaaS Security Posture**
- Lead with multi-SaaS evidence collectors
- Show control pack extensibility

---

## Summary

The UIAO Go-To-Market Layer establishes:

- A named, defensible category: **Compliance Control Plane (CCP)**
- A differentiated positioning statement
- Five messaging pillars
- A competitive landscape with five winning axes
- A four-tier pricing model
- Four buyer personas and four sales motions

This is the layer that makes UIAO **sellable**, **deployable**, and **positionable** in the federal and enterprise compliance market.
