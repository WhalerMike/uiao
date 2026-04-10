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
