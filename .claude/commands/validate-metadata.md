# Command: /validate
## Description
Run the full metadata validation suite against governance artifacts.
## Usage
```
/validate [--path <target>] [--fix] [--report]
```
## Parameters
| Parameter | Default | Description |
|-----------|---------|-------------|
| `--path` | `canon/` | Target directory or file to validate |
| `--fix` | `false` | Auto-fix INFO-level issues (never auto-fixes BLOCKING) |
| `--report` | `false` | Generate a standalone validation report file |
## Behavior
1. Load the metadata schema from `schemas/metadata-schema.json`
2. Walk the target path recursively
3. For each `.md` file, parse YAML frontmatter and validate against schema
4. Classify findings as BLOCKING, WARNING, or INFO
5. If `--fix` is set, apply deterministic fixes for INFO-level issues
6. Output structured findings table
7. If `--report` is set, write report to `reports/validation-<timestamp>.md`
## Agent
Delegates to `governance-agent`
## Example
```
/validate --path canon/ --report
```
Output:
```
Metadata Validation — 2026-04-09T06:59:00
Files scanned: 42
BLOCKING: 2 | WARNING: 5 | INFO: 8
| # | File | Issue | Severity | Suggested Fix |
|---|------|-------|----------|---------------|
| 1 | canon/UIAO_003.md | Missing owner field | BLOCKING | Add owner: <owner-id> |
| 2 | canon/UIAO_017.md | Invalid version format | BLOCKING | Change "1.0a" → "1.0" |
...
```