---
id: systemic-drift-clustering-spec
title: Systemic Drift Clustering Algorithm Specification
owner: governance-steward
status: DRAFT
---

# UIAO Systemic Drift Clustering Algorithm Specification

## Canonical Method for Detecting Structural Drift Patterns

This algorithm identifies systemic drift by clustering drift events across documents, owners, and appendices.

---

## 1. Purpose

To detect structural governance failures early by grouping drift events into meaningful clusters.

---

## 2. Inputs

- Drift events (severity, timestamp, document, appendix)
- Drift type (structural, referential, ownership, semantic, automation)
- Owner metadata
- Schema version
- CI validator error signatures

---

## 3. Feature Vector Construction

For each drift event, construct:

X = [severity_weight, drift_type_id, appendix_id, owner_id, schema_version, ci_error_signature_hash]

Severity weights: critical = 4, high = 3, medium = 2, low = 1

---

## 4. Clustering Method

### Step 1 - Normalize Features

Min-max scaling across all dimensions.

### Step 2 - Apply Density-Based Clustering

Use DBSCAN or HDBSCAN:

- Detects arbitrary-shaped clusters
- Handles noise
- Identifies dense drift regions

### Step 3 - Cluster Classification

Clusters are labeled as:

- Owner-centric (same owner, multiple docs)
- Appendix-centric (same appendix)
- Schema-centric (same schema version)
- Error-centric (same CI signature)
- Cross-appendix systemic (multiple appendices)

---

## 5. Systemic Drift Thresholds

A cluster is systemic if:

- 5 or more drift events
- Across 2 or more documents
- Within 14 days or fewer
- With 60% or higher shared feature similarity

---

## 6. Outputs

- Cluster ID
- Drift type distribution
- Affected owners
- Affected appendices
- Root cause hypothesis
- Severity index

---

## 7. Governance Actions

- Schema review
- CI validator update
- Owner training
- Workflow update
- Governance intervention
