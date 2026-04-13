---
id: governance-canon-glossary
title: "Governance Canon Glossary"
owner: governance-board
status: DRAFT
---

# UIAO Governance Canon Glossary

## Canonical Terms Across All Governance Volumes

This glossary defines every canonical term used across the UIAO Governance OS volumes. All governance artifacts must use these definitions exactly.

---

## A

**Automation Alignment** — The state in which CI validators, workflows, and webhooks match the current governance schema and rules. Any deviation triggers an automation violation.

**Automation Instability** — Failures, errors, or degraded performance in CI validators, workflows, or webhooks that increase systemic governance risk.

**Automation Stability (AS)** — A composite metric (0-1) measuring CI, webhook, and workflow uptime and correctness over a rolling 30-day window.

---

## C

**Chaos-Resilience Index (CRI)** — A composite score measuring runtime stability under injected failure conditions. Target: above 0.85 for production.

**Control Plane** — The governance authority layer that manages schema evolution, automation governance, owner governance, and systemic-risk governance. It is the apex decision layer of the governance OS.

**Corpus Normalization** — The process of enforcing structural, referential, semantic, and schema consistency across all documents in the governance corpus.

---

## D

**DG-RI (Drift-Resilience Index)** — A composite 0-100 score measuring how resistant the corpus is to future drift. Components: MQS, DF, DSI, SDR, AS, OR.

**Drift** — Any deviation of a document from its canonical metadata state, schema alignment, or governance rules.

**Drift Cluster** — A group of drift events that share a common structural, referential, or automation cause.

**Drift Velocity** — The rate at which drift events accumulate, measured as events per 30-day rolling window.

---

## E

**Enforcement Engine** — The automation that applies fixes, opens remediation PRs, or triggers governance interventions in response to detected violations.

---

## F

**Federated Governance** — A governance model in which multiple tenants share governance signals, schema contracts, and systemic-risk alerts while maintaining local autonomy.

**Fault Isolation** — The design property that ensures a failure in one runtime component does not propagate to other components.

---

## G

**GR-RI (Governance Runtime Resilience Index)** — A composite score measuring runtime stability across CI, webhooks, workflows, API, DB, and dashboards.

**Governance Emergency** — A systemic-risk condition requiring merge freeze and runtime audit, declared when the systemic-risk score exceeds 80 or schema divergence exceeds 10%.

**Governance Emergency Council** — A temporary authority convened for Severity 4 and 5 incidents, composed of schema, automation, runtime, systemic-risk, and owner governance stewards.

---

## M

**MG-RI (Metadata Governance Reliability Index)** — The primary governance health indicator. A composite 0-100 score aggregating MQS, DF, DSI, SLA compliance, AS, and OR.

**MQS (Metadata Quality Score)** — A 0-100 score measuring the correctness and completeness of document metadata fields.

**Merge Freeze** — An emergency governance action that blocks all merges to main, preventing drift amplification and schema corruption during a governance emergency.

---

## N

**Normalization Integrity Score** — A 0-100 score representing corpus-wide normalization health. Below 60 triggers a normalization emergency.

---

## O

**OR (Owner Reliability Score)** — A composite metric tracking an owner's 30-day performance on drift remediation, SLA compliance, and schema alignment.

---

## P

**Propagation Vector** — A structural link, referential link, ownership coupling, or automation dependency that can transmit drift or failure from one document or component to another.

**Provenance** — The complete traceable history of a document: origin, all transformations, all owners, and all schema versions applied.

---

## R

**Runtime Pipeline** — The canonical event flow: CI Validator -> Webhook Handler -> Governance API -> PostgreSQL -> Dashboards.

---

## S

**Schema Divergence** — The percentage of governance documents not aligned with the current canonical schema version. Must remain below 1%.

**SLA Breach** — A condition in which an owner has not remediated a drift event within the defined SLA window.

**SLA Timer** — A governance timer set at the moment a drift event is detected, counting toward the SLA deadline.

**Systemic-Risk Score** — A composite 0-100 score aggregating drift pressure, SLA cascade pressure, schema divergence, and automation instability.

---

## T

**Trust Indicator** — Any metric (MG-RI, DG-RI, GR-RI, schema divergence, SLA stability) that signals the trustworthiness of a governance artifact or the governance OS state.

---

## Z

**Zero-Trust Governance** — A governance security model in which no metadata, automation action, schema change, or identity is trusted by default. All must be verified.

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
