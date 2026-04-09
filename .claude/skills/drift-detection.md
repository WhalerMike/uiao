# Skill: Drift Detection

## Purpose
Detect and classify metadata drift between canonical sources and derived artifacts.

## When to Use
- Before merging any PR that touches `canon/` or `appendices/`
- During scheduled drift audits
- As part of the `/drift` or `/canon` command pipeline

## Drift Categories

| Category | Pattern | Severity |
|---|---|---|
| SCHEMA_DRIFT | Frontmatter doesn't match schema | BLOCKING |
| PROVENANCE_DRIFT | Derived diverges from canonical source | BLOCKING |
| BOUNDARY_DRIFT | Cloud boundary violation | BLOCKING |
| VERSION_DRIFT | Reference to deprecated version | WARNING |
| OWNER_DRIFT | Owner missing or stale | WARNING |
| NAMING_DRIFT | Filename convention mismatch | WARNING |
| COSMETIC_DRIFT | Formatting inconsistency | INFO |

## Detection Modes

### Full Scan
Walk entire repository, compare every artifact against schema and canon.
```bash
python tools/drift_detector.py --path . --mode full
```

### Targeted Scan
Scan specific directory or artifact by path.
```bash
python tools/drift_detector.py --path canon/UIAO_001.md --mode targeted
```

### Diff Scan
Compare two branches or commits for drift introduction.
```bash
python tools/drift_detector.py --base main --head feature/update --mode diff
```

## Output Format

Drift reports use the standard finding table:
```
| File | Drift Type | Severity | Details | Suggested Fix |
```

## Remediation

- BLOCKING findings must be resolved before merge
- WARNING findings should be resolved in the same PR cycle
- INFO findings are advisory and may be batched
