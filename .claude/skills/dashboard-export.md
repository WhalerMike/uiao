# Skill: Dashboard Export
## Purpose
Extract governance metrics from repository state, validate against the dashboard schema, and export structured data for operational dashboards and SLA heatmaps.
## When to Use
- After any canon integrity check completes
- During `/dashboard` or `/canon` command execution
- As part of the CI dashboard-export workflow
- On-demand for leadership reporting
## Export Pipeline
```
COLLECT → COMPUTE → VALIDATE → EXPORT
│ │ │ │
│ │ │ └─ Write to dashboard/exports/ in chosen format
│ │ └─ Validate against schemas/dashboard-schema.json
│ └─ Calculate derived metrics (scores, trends, heatmaps)
└─ Gather raw data from all tool outputs and frontmatter
```
## Metrics Catalog
### Repository-Level Metrics
| Metric | Computation | Type |
|--------|-------------|------|
| `canon_health_score` | Weighted average of all sub-scores | 0–100 |
| `metadata_compliance_rate` | (compliant files / total files) × 100 | percentage |
| `drift_free_rate` | (drift-free files / total files) × 100 | percentage |
| `appendix_integrity_rate` | (valid appendices / total appendices) × 100 | percentage |
| `boundary_exception_count` | Count of files with `boundary-exception: true` | integer |
| `open_remediation_count` | Count of unresolved BLOCKING + WARNING findings | integer |
### Owner-Level Metrics
| Metric | Computation | Type |
|--------|-------------|------|
| `sla_compliance_rate` | (on-time responses / total assignments) × 100 | percentage |
| `reliability_score` | 30-day rolling SLA compliance average | 0–100 |
| `owned_artifact_count` | Number of artifacts with this owner | integer |
| `open_findings_count` | BLOCKING + WARNING findings on owned artifacts | integer |
### Trend Indicators
| Indicator | Computation |
|-----------|-------------|
| `health_trend` | Δ health score over last N commits |
| `drift_trend` | Δ drift count over last N commits |
| `compliance_trend` | Δ compliance rate over last N commits |
## Execution
```bash
# Validate schema only
python tools/dashboard_exporter.py --schema schemas/dashboard-schema.json --validate
# Export JSON
python tools/dashboard_exporter.py --schema schemas/dashboard-schema.json --export json --output dashboard/exports/
# Export with 30-day trends
python tools/dashboard_exporter.py --schema schemas/dashboard-schema.json --export json --trends 30
# Export CSV for spreadsheet consumption
python tools/dashboard_exporter.py --schema schemas/dashboard-schema.json --export csv --output dashboard/exports/
# Export Markdown for human review
python tools/dashboard_exporter.py --schema schemas/dashboard-schema.json --export markdown --output dashboard/exports/
```