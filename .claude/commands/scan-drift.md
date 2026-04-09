# Command: /drift
## Description
Scan the repository for metadata drift between canonical sources and derived artifacts.
## Usage
```
/drift [--path <target>] [--mode <full|targeted|diff>] [--base <ref>] [--head <ref>]
```
## Parameters
| Parameter | Default | Description |
|-----------|---------|-------------|
| `--path` | `.` | Target directory or file to scan |
| `--mode` | `full` | Scan mode: full, targeted, or diff |
| `--base` | `main` | Base ref for diff mode |
| `--head` | `HEAD` | Head ref for diff mode |
## Behavior
1. Determine scan scope based on `--mode`
2. For each file in scope:
a. Parse frontmatter and classify drift category
b. Resolve provenance chains for DERIVED artifacts
c. Scan content body for boundary violations
d. Check version references for prior-epoch references
3. Correlate findings across files (e.g., cascading drift from a single canon change)
4. Generate structured drift report with root cause analysis
5. Assign remediation priority
## Agent
Delegates to `drift-detector`
## Example
```
/drift --mode diff --base main --head feature/update-canon
```
Output:
```
Drift Report — 2026-04-09T06:59:00
Files scanned: 12 (diff scope)
Drift instances found: 3
Blocking: 1 | Warning: 1 | Info: 1
| # | File | Category | Severity | Detail | Root Cause | Remediation |
|---|------|----------|----------|--------|------------|-------------|
| 1 | derived/ops-guide.md | PROVENANCE_DRIFT | BLOCKING | Source hash mismatch | canon/UIAO_005.md updated in abc1234 | Re-derive from updated source |
| 2 | canon/UIAO_012.md | VERSION_DRIFT | WARNING | References v1.2 (deprecated) | Manual edit in def5678 | Update to v2.0 reference |
| 3 | playbooks/onboard.md | COSMETIC_DRIFT | INFO | Header formatting inconsistency | — | Auto-fixable |
```