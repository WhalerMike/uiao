# Command: /dashboard
## Description
Export documentation health metrics to structured dashboard format with cross-repo alignment tracking.
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
1. Collect current documentation state metrics:
- Run metadata validation (count compliant vs total)
- Run cross-repo drift scan (count aligned vs total derived)
- Run appendix audit (count valid vs total, Copy compliance)
- Run article format check (count compliant vs total)
- Count stale provenance references
- Count open remediation items
2. Extract owner-level metrics from frontmatter
3. Compute docs health score (weighted average)
4. If `--trends` > 0, compute rolling averages from Git history
5. Validate export against `schemas/dashboard-schema.json`
6. Write export to `--output` directory
## Agent
Delegates to `docs-dashboard-exporter`
> **SSOT Reference:** See /ssot/UIAO-SSOT.md
