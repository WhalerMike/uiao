# Phase 1.5 Integration Baseline — UIAO v0.6.0 OrgTree Readiness Batch A

Generated: 2026-04-27

---

## Milestone 1: Branch Merge Status

All 10 WS branches merged successfully in prescribed order:

| Branch | Merge Status |
|--------|-------------|
| A4 — OrgPath foundation | Clean merge |
| A1 — Survey enrichment | Clean merge |
| A2 — Intune readiness | Clean merge |
| A3 — Arc readiness | Clean merge |
| A5 — Bundle schema + CLI | Clean merge |
| A6 — OSCAL emitter | Clean merge |
| A7 — KSI rules | Clean merge |
| A9 — CI smoke test | Clean merge |
| A10 — Docs | Clean merge |
| A8 — Quickstart + fixture | Clean merge |

No conflict resolution was required. All merges applied cleanly.

---

## Milestone 2: Baseline Test Run

### ruff check src/ tests/

```
All checks passed!
```

### mypy src/uiao/ (last 10 lines)

```
src/uiao/dashboard/export.py:15: error: Library stubs not installed for "yaml"  [import-untyped]
src/uiao/adapters/scuba/transform.py:29: error: Library stubs not installed for "yaml"  [import-untyped]
src/uiao/generators/diagrams.py:17: error: Library stubs not installed for "yaml"  [import-untyped]
src/uiao/generators/docs.py:20: error: Library stubs not installed for "yaml"  [import-untyped]
src/uiao/adapters/modernization/gcc_boundary_probe/probe.py:42: error: Library stubs not installed for "yaml"  [import-untyped]
src/uiao/adapters/modernization/gcc_boundary_probe/probe.py:42: note: Hint: "python3 -m pip install types-PyYAML"
src/uiao/adapters/modernization/gcc_boundary_probe/probe.py:42: note: (or run "mypy --install-types" to install all missing stub packages)
src/uiao/adapters/modernization/gcc_boundary_probe/probe.py:42: note: See https://mypy.readthedocs.io/en/stable/running_mypy.html#missing-imports
src/uiao/api/routes/boundary.py:84: error: Library stubs not installed for "yaml"  [import-untyped]
Found 39 errors in 39 files (checked 202 source files)
```

All 39 errors are pre-existing `import-untyped` stub warnings for `yaml` and `requests` — none are new from the WS branches.

### pytest tests/ -q --tb=short (baseline, before fixes)

Note: pytest requires `uv run python -m pytest` — the system `pytest` binary uses an isolated uv tools env that lacks `yaml`. `fastapi`/`httpx` installed into project venv.

```
2482 passed, 171 skipped, 4 warnings in 44.01s
```

**Baseline: CLEAN. No failures.**

---

## Fixes Applied

_(Updated as milestones complete)_

### Fix #1 — M3: A1↔A4 OrgPath duplicate (PENDING)
### Fix #2 — M4: A6 missing RID 544 (PENDING)
### Fix #3 — M5: A5 HMAC fail-open default (PENDING)
### Fix #4 — M6: A2 TPM/HVCI graceful degradation (PENDING)
### Fix #5 — M7: A8 KAT actually-measured verdicts (PENDING)
### Fix #6 — M8: Register orgtree-readiness schema in substrate manifest (PENDING)

---

## Final State

_(Updated after M9)_
