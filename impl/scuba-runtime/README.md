# impl/scuba-runtime/

Non-Python runtime artifacts for the SCuBA / ScubaGear adapter. Moved here from the (now-removed) `impl/adapters/scuba/` as part of dissolving the deprecated flat-tree `impl/adapters/` directory (replaced by the src-layout at `impl/src/uiao/impl/adapters/`).

## Layout

| Path | Purpose |
|---|---|
| `run/adapter-run-scuba.ps1` | PowerShell entry point: runs SCuBA/ScubaGear, normalizes, evaluates KSI rules. |
| `transforms/normalize.ps1` | Maps raw ScubaGear output to the canonical normalized schema. |
| `schemas/scuba-normalized.schema.json` | JSON Schema for the normalized output. |

## Relationship to the Python adapter

The Python SCuBA adapter lives at `impl/src/uiao/impl/adapters/scuba_adapter.py` and is the canonical integration point. This directory hosts **operator-run scripts** for cases where the PowerShell path is preferred (Windows operator workstations, environments where `pwsh` is the scripting norm). Both paths feed the same canonical schema under `schemas/`.

## Known tech debt (tracked for a follow-on PR)

The PowerShell scripts in `run/` and `transforms/` carry hardcoded paths from the pre-consolidation era, e.g.:

```powershell
pwsh ./uiao-core/adapters/scuba/transforms/normalize.ps1
pwsh ./uiao-core/ksi/evaluations/evaluate-ksi.ps1
```

`uiao-core/` was the archived predecessor repository; those paths no longer resolve in the monorepo. The scripts are therefore non-operational as-is and require path rewrites before they can be invoked. This is recorded as a follow-on cleanup; the move in this PR preserves history without touching script internals so the debt is visible as drift the next CI pass will flag.
