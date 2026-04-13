# Command: /drift
## Description
Scan for cross-repository drift against uiao-core canon and internal documentation drift.
## Usage
```
/drift [--path <target>] [--mode <full|targeted|diff|format>] [--cross-repo <path>]
```
## Parameters
| Parameter | Default | Description |
|-----------|---------|-------------|
| `--path` | `.` | Target directory or file to scan |
| `--mode` | `full` | Scan mode: full, targeted, diff, or format |
| `--cross-repo` | `../uiao-core` | Path to uiao-core repository for cross-repo checks |
## Behavior
1. Determine scan scope based on `--mode`
2. For cross-repo mode:
a. Resolve each document's provenance.source to uiao-core
b. Compare derived version vs canonical current version
c. Flag divergences as CROSS_REPO_DRIFT (BLOCKING)
3. For format mode:
a. Validate articles against Article 1 template
b. Check header styling, body text color, structure, pseudonym
4. For internal mode:
a. Schema compliance, naming conventions, boundary checks
5. Generate structured drift report with remediation priorities
## Agent
Delegates to `docs-drift-detector`
> **SSOT Reference:** See /ssot/UIAO-SSOT.md
