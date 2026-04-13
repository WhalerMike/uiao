# Command: /validate
## Description
Run the full metadata and formatting validation suite against documentation artifacts.
## Usage
```
/validate [--path <target>] [--fix] [--report] [--format-check]
```
## Parameters
| Parameter | Default | Description |
|-----------|---------|-------------|
| `--path` | `.` | Target directory or file to validate |
| `--fix` | `false` | Auto-fix INFO-level issues (never auto-fixes BLOCKING) |
| `--report` | `false` | Generate a standalone validation report file |
| `--format-check` | `false` | Include Article 1 formatting template validation |
## Behavior
1. Load the docs metadata schema from `schemas/docs-metadata-schema.json`
2. Walk the target path recursively
3. For each `.md` file, parse YAML frontmatter and validate against schema
4. Verify provenance blocks reference valid `uiao-core` canon
5. If `--format-check`, validate articles against Article 1 template
6. Verify placeholder standards (unique IDs, detailed descriptions)
7. Verify image standards (title, dimensions, alt text)
8. Verify diagram renderer (PlantUML only, no Mermaid)
9. Classify findings as BLOCKING, WARNING, or INFO
10. If `--fix` is set, apply deterministic fixes for INFO-level issues
11. Output structured findings table
12. If `--report` is set, write report to `reports/validation-<timestamp>.md`
## Agent
Delegates to `docs-governance-agent`
> **SSOT Reference:** See /ssot/UIAO-SSOT.md
