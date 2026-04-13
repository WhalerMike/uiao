# Skill: Dashboard Export (Documentation Layer)
## Purpose
Extract documentation health metrics, validate against dashboard schema, and export structured data for operational dashboards tracking documentation freshness and cross-repo alignment.
## When to Use
- After any documentation integrity check completes
- During `/dashboard` command execution
- As part of the CI dashboard-export workflow
- On-demand for leadership reporting on documentation health
## Export Pipeline
```
COLLECT → COMPUTE → VALIDATE → EXPORT
│ │ │ │
│ │ │ └─ Write to dashboard/exports/
│ │ └─ Validate against schemas/dashboard-schema.json
│ └─ Calculate derived metrics (scores, trends, alignment rates)
└─ Gather raw data from all docs tool outputs and frontmatter
```
## Metrics Catalog
### Repository-Level Metrics
| Metric | Computation | Type |
|--------|-------------|------|
| `docs_health_score` | Weighted average of all sub-scores | 0–100 |
| `metadata_compliance_rate` | (compliant files / total files) × 100 | percentage |
| `cross_repo_alignment_rate` | (aligned docs / total derived docs) × 100 | percentage |
| `appendix_integrity_rate` | (valid appendices / total appendices) × 100 | percentage |
| `copy_section_compliance` | (appendices with Copy / total appendices) × 100 | percentage |
| `article_format_compliance` | (compliant articles / total articles) × 100 | percentage |
| `stale_provenance_count` | Count of docs with outdated provenance refs | integer |
| `open_remediation_count` | Count of unresolved BLOCKING + WARNING findings | integer |
### Publication Metrics
| Metric | Computation | Type |
|--------|-------------|------|
| `articles_published` | Count of articles with status: Current | integer |
| `articles_in_draft` | Count of articles with status: Draft | integer |
| `publication_readiness_rate` | (ready articles / total articles) × 100 | percentage |
## Execution
```bash
# Validate schema
python tools/dashboard_exporter.py --schema schemas/dashboard-schema.json --validate
# Export JSON
python tools/dashboard_exporter.py --schema schemas/dashboard-schema.json --export json --output dashboard/exports/
# Export with 30-day trends
python tools/dashboard_exporter.py --schema schemas/dashboard-schema.json --export json --trends 30
```
> **SSOT Reference:** See /ssot/UIAO-SSOT.md
