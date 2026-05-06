---
id: governance-corpus-index
title: "Governance Corpus Index"
owner: governance-board
status: DRAFT
---

# UIAO Governance Corpus Index

## Complete Structured Index of All Governance Artifacts

This index catalogs every governance artifact in the UIAO corpus, organized into nine canonical domains matching the architecture of the governance operating system.

---

## 1. Systemic-Risk Domain

Artifacts that detect, model, forecast, or propagate systemic governance failures.

- Systemic-Risk Forecasting Model: governance/systemic-risk-forecasting-model.md
- Systemic-Risk Early-Warning Dashboard: governance/dashboard-systemic-risk-early-warning.md
- Systemic-Risk Early-Warning Engine: governance/systemic-risk-early-warning-engine.md
- Systemic-Risk Propagation Engine: governance/systemic-risk-propagation-engine.md
- Systemic-Risk Propagation Engine Visual: governance/systemic-risk-propagation-engine-visual.md
- Systemic-Risk Propagation Simulator: governance/systemic-risk-propagation-simulator.md
- Systemic-Risk Propagation Heatmap: governance/systemic-risk-propagation-heatmap.md
- Systemic-Risk Diagnostic Engine: governance/systemic-risk-diagnostic-engine.md

---

## 2. Drift Domain

Artifacts that detect, classify, remediate, or contain metadata drift.

- Metadata Drift Heatmap Spec: governance/metadata-drift-heatmap-spec.md
- Metadata Drift Propagation Model: governance/metadata-drift-propagation-model.md
- Metadata Drift Propagation Heatmap: governance/metadata-drift-propagation-heatmap.md
- Metadata Drift Containment Playbook: governance/metadata-drift-containment-playbook.md
- Metadata Drift Anomaly-Detection Model: governance/metadata-drift-anomaly-detection-model.md
- Drift Root-Cause Analysis Template: governance/drift-root-cause-analysis-template.md
- Systemic Drift Early-Warning Playbook: governance/systemic-drift-early-warning-playbook.md
- Systemic Drift Clustering Spec: governance/systemic-drift-clustering-spec.md
- Metadata Drift Resilience Index: governance/metadata-drift-resilience-index.md

---

## 3. Metadata Quality and Reliability Domain

Artifacts that measure, score, or visualize metadata quality and reliability.

- Metadata Lifecycle Diagram: governance/metadata-lifecycle-diagram.md
- Metadata Quality Remediation Diagram: governance/metadata-quality-remediation-diagram.md
- Metadata Governance Simulation Model: governance/metadata-governance-simulation-model.md
- Metadata Governance Monte Carlo: governance/metadata-governance-monte-carlo.md
- Metadata Governance RL Model: governance/metadata-governance-rl-model.md
- Metadata Governance Reliability Index: governance/metadata-governance-reliability-index.md
- Metadata Governance Reliability Index Visual: governance/metadata-governance-reliability-index-visual.md
- Metadata Governance Drift-Resilience Index: governance/metadata-drift-resilience-index.md
- Metadata Governance Reliability Heatmap: governance/metadata-governance-reliability-heatmap.md
- Reliability Score Decomposition Diagram: governance/reliability-score-decomposition-diagram.md
- Reliability Scorecard Visual: governance/reliability-scorecard-visual.md
- Reliability Early-Warning Heatmap: governance/reliability-early-warning-heatmap.md

---

## 4. Schema and Normalization Domain

Artifacts that enforce schema alignment and corpus normalization.

- Schema Change Impact Analysis Template: governance/schema-change-impact-analysis-template.md
- Schema Evolution Simulator: governance/schema-evolution-simulator.md
- Corpus Normalization Roadmap: governance/corpus-normalization-roadmap.md
- Corpus Normalization Maturity Model: governance/corpus-normalization-maturity-model.md
- Corpus Normalization Audit Template: governance/corpus-normalization-audit-template.md
- Corpus Normalization Enforcement Engine: governance/corpus-normalization-enforcement-engine.md
- Corpus Normalization Enforcement Engine Visual: governance/corpus-normalization-enforcement-engine-visual.md
- Corpus Normalization Enforcement Dashboard: governance/corpus-normalization-enforcement-dashboard.md
- Corpus Normalization Enforcement Dashboard Visual: governance/corpus-normalization-enforcement-dashboard-visual.md
- Corpus Normalization Enforcement Playbook: governance/corpus-normalization-enforcement-playbook.md
- Corpus Integrity Verification Protocol: governance/corpus-integrity-verification-protocol.md

---

## 5. Runtime and Automation Domain

Artifacts governing CI, workflows, webhooks, API, DB, and dashboard behavior.

- Runtime Dependency Map: governance/runtime-dependency-map.md
- Runtime Dependency Failure Matrix: governance/runtime-dependency-failure-matrix.md
- Runtime Dependency Chaos Matrix: governance/runtime-dependency-chaos-matrix.md
- Runtime Dependency Observability Map: governance/runtime-dependency-observability-map.md
- Runtime Dependency Resilience Model: governance/runtime-dependency-resilience-model.md
- Runtime Observability Plan: governance/runtime-observability-plan.md
- Runtime Observability Dashboard: governance/runtime-observability-dashboard.md
- Runtime Failure-Mode Dependency Graph: governance/runtime-failure-mode-dependency-graph.md
- Runtime Failure-Mode Simulation Suite: governance/runtime-failure-mode-simulation-suite.md
- Runtime Chaos Engineering Test Plan: governance/runtime-chaos-engineering-test-plan.md
- Runtime Chaos Resilience Dashboard: governance/runtime-chaos-resilience-dashboard.md
- Runtime SLO SLI Spec: governance/runtime-slo-sli-spec.md
- Dashboard Runtime SLO SLI Panel Spec: governance/dashboard-runtime-slo-sli-panel-spec.md
- Dashboard Reliability Early Warning Spec: governance/dashboard-reliability-early-warning-spec.md
- Dashboard Systemic Risk Panel Spec: governance/dashboard-systemic-risk-panel-spec.md
- Runtime Resilience Dashboard Visual: governance/runtime-resilience-dashboard-visual.md
- Runtime Resilience Heatmap: governance/runtime-resilience-heatmap.md

---

## 6. SLA and Owner Reliability Domain

Artifacts that measure and enforce SLA compliance and owner performance.

- Maturity Progression Roadmap: governance/maturity-progression-roadmap.md
- Automation Maturity Model: governance/automation-maturity-model.md
- Automation Backlog: governance/automation-backlog.md
- Quarterly Executive Briefing Outline: governance/quarterly-executive-briefing-outline.md

---

## 7. Governance Controls and Intervention Domain

Artifacts defining governance actions, escalation, and enforcement.

- Intervention Severity Ladder: governance/intervention-severity-ladder.md
- Charter Compliance Audit Checklist: governance/charter-compliance-audit-checklist.md
- Charter Modernization Proposal: governance/charter-modernization-proposal.md
- Risk Early-Warning Model: governance/risk-early-warning-model.md

---

## 8. Architecture and Index Domain

Master architecture, index, and atlas artifacts.

- Governance Corpus Index: governance/governance-corpus-index.md
- Governance Visual Atlas: governance/governance-visual-atlas.md
- Governance OS Architecture: governance/governance-os-architecture.md

---

## 9. Corpus Dependency Map

The runtime-to-governance control plane dependency chain:

    Runtime Layer: CI Validator -> Webhook Handler -> Governance API -> PostgreSQL -> Dashboards
    Detection Layer: Drift Detection, SLA Detection, Systemic-Risk Detection
    Prediction Layer: Propagation Models, Simulators, RL Governance Model
    Enforcement Layer: Normalization Engine, SLA Enforcement, Automation Alignment
    Governance Control Plane: Schema, Automation, Owner, Systemic-Risk Governance

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
