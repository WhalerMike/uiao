---
document_id: MOD_T
title: "Appendix T — Identity Risk Scoring Model"
version: "1.0"
status: DRAFT
classification: CANONICAL
owner: Michael Stratton
created_at: 2026-04-18
updated_at: 2026-04-18
boundary: GCC-Moderate
namespace: MOD
parent_canon: UIAO_008
---

# Appendix T — Identity Risk Scoring Model

Purpose

This appendix defines a quantitative risk scoring model for identity objects based on their compliance with governance rules. The risk score drives prioritized remediation and resource allocation.

Scope

Covers 10 risk factors, the scoring formula, four risk tiers, and a response matrix. Applies to all user objects within the M365 GCC-Moderate boundary.

Canonical Structure

Each identity object receives a composite risk score from 0 (no risk) to 100 (maximum risk) based on weighted risk factors.

Technical Scaffolding

Risk Factors

Scoring Formula

RiskScore = (Sum(Weight_i * Value_i) / Sum(Weight_i)) * 100

Where Weight_i is the weight for factor i and Value_i is the assessed value (0 to 1) for factor i.

Maximum possible score: 100 (all factors at maximum value). Minimum: 0 (no risk factors present).

Risk Tiers

Sample Calculation

A user has: Missing Manager (RF-06, weight 5, value 1), Stale Account (RF-04, weight 6, value 1), and 3 drift events in 30 days (RF-07, weight 7, value 0.6).

RiskScore = ((5*1 + 6*1 + 7*0.6) / (5+6+7)) * 100 = ((5 + 6 + 4.2) / 18) * 100 = (15.2 / 18) * 100 = 84.4

This user scores 84.4 → Critical tier. Required action: immediate remediation within 4 hours by Security Steward.

Boundary Rules

All risk factor data is collected from Entra ID via Microsoft Graph within M365 GCC-Moderate.

Risk scores are stored in governance telemetry systems within M365.

Drift Considerations

Risk factor weights and thresholds are governance artifacts; changes require Workflow 8.

A consistently high average risk score across the tenant indicates systemic governance drift.

Governance Alignment

This model implements Principle 4 (Drift Resistance) by quantifying risk and mandating action thresholds, and Principle 1 (Deterministic State) by providing a single, calculable score for each identity object.
