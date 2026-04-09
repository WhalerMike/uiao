# Command: /dashboard
## Description
Export governance metrics to structured dashboard format with SLA heatmaps and trend indicators.
## Usage
```
/dashboard [--export <json|csv|markdown>] [--trends <days>] [--output <path>]
```
## Parameters
| Parameter | Default | Description |
|-----------|---------|-------------|
| `--export` | `json` | Export format: json, csv, or markdown |
| `--trends` | `0` | Number of days for rolling trend computation (0 = no trends) |
| `--output` | `dashboard/exports/` | Output directory for exported files |
## Behavior
1. Collect current repository state metrics:
- Run metadata validation (count compliant vs total)
- Run drift scan (count drift-free vs total)
- Run appendix audit (count valid vs total)
- Compute boundary exception count
- Count open remediation items
2. Extract owner-level metrics from frontmatter
3. Compute canon health score (weighted average)
4. If `--trends` > 0, compute rolling averages from Git history
5. Validate export against `schemas/dashboard-schema.json`
6. Write export to `--output` directory
## Agent
Delegates to `dashboard-exporter`
## Example
```
/dashboard --export json --trends 30
```
Output:
```
Dashboard Export — 2026-04-09T07:00:00
Canon Health Score: 87/100
Metrics:
Metadata Compliance: 95.2%
Drift-Free Rate: 91.4%
Appendix Integrity: 100.0%
Boundary Exceptions: 2
Open Remediation: 7
30-Day Trends:
Health: ↑ +3.2
Drift: ↓ -2 instances
Compliance: ↑ +1.8%
Export written to: dashboard/exports/dashboard-2026-04-09.json
Schema validation: ✅ PASS
```