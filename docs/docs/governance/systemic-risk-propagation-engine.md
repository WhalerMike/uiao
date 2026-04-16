---
id: systemic-risk-propagation-engine
title: Governance Systemic-Risk Propagation Engine
owner: governance-steward
status: DRAFT
---

# UIAO Governance Systemic-Risk Propagation Engine

## Automated Modeling of How Governance Failures Spread Across the Corpus

The Systemic-Risk Propagation Engine (SRPE) predicts how local drift, SLA stress, schema divergence, and automation instability propagate into systemic governance failures.

---

## 1. Purpose

To forecast: drift spread across appendices, SLA cascade failures, schema divergence acceleration, automation-driven systemic drift, and cross-owner reliability collapse.

---

## 2. Inputs

### A. Drift Propagation Factors

- Structural coupling
- Referential coupling
- Ownership coupling
- Automation coupling

### B. SLA Stress Factors

- SLA-at-risk density
- SLA breach velocity
- Owner SLA trend slope

### C. Schema Factors

- Schema divergence
- Deprecated field reappearance
- Schema version fragmentation

### D. Automation Factors

- CI validator instability
- Webhook event loss
- Workflow failure probability

---

## 3. Propagation Model

### Step 1 - Compute Local Drift Pressure

LDP = DV_n + DSI_n + SDR_n

### Step 2 - Compute Coupling Pressure

CP = SC + RC + OC + AC

### Step 3 - Compute SLA Cascade Pressure

SCP = SLA_risk + SLA_trend + Owner_decline

### Step 4 - Compute Automation Instability

AI = 1 - AS

### Step 5 - Systemic-Risk Propagation Score

SRP = 0.30*LDP + 0.25*CP + 0.20*SCP + 0.25*AI

---

## 4. Outputs

- Propagation score (0-100)
- Drift propagation map
- SLA cascade forecast
- Schema divergence forecast
- Automation instability forecast
- Recommended governance intervention

---

## 5. Governance Actions

- Update schema
- Patch CI validator
- Patch workflows
- Reassign owners
- Trigger systemic drift review

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
