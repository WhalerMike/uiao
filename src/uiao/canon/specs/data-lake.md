---
document_id: UIAO_109
title: "UIAO Compliance Data Lake Model"
version: "1.0"
status: Current
classification: CANONICAL
owner: "Michael Stratton"
created_at: "2026-04-14"
updated_at: "2026-04-14"
boundary: "GCC-Moderate"
---

# UIAO Compliance Data Lake Model

## Zones
- **Raw Zone**
  - SCuBA raw output
  - Native logs (Azure AD, M365, Defender)
  - Format: JSON, CSV, NDJSON
- **Normalized Zone**
  - UIAO IR objects
  - Normalized evidence snapshots
  - Drift snapshots
- **Curated Zone**
  - KSI results
  - Control status views
  - POA&M views
  - OSCAL exports (SSP/SAP/SAR/POA&M)

## Partitioning
- By tenant_id
- By date (YYYY/MM/DD)
- By evidence_source

## Governance
- Immutable writes (append-only)
- Hash + provenance per object
- Access via CQL and Auditor API
