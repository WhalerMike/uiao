# Phase 1.5 Integration Report — UIAO v0.6.0 OrgTree Readiness Batch A

Generated: 2026-04-27
Branch: `claude/v0.6.0-batch-a-integration`

---

## Milestone 0: Setup

- pwd verified: `/home/user/uiao/.claude/worktrees/agent-a13741719efc1ce9c` (contains `.claude/worktrees/agent-`)
- Branch `claude/v0.6.0-batch-a-integration` already existed and tracked origin — no new branch creation needed

---

## Milestone 1: Branch Merge Status

All 10 WS branches merged successfully in prescribed order. No conflicts required
manual resolution.

| Branch | Merge Commit | Status |
|--------|-------------|--------|
| A4 — OrgPath foundation | `60889637` | Clean |
| A1 — Survey enrichment | `16d3617d` | Clean |
| A2 — Intune readiness | `547baea4` | Clean |
| A3 — Arc readiness | `5d58226e` | Clean |
| A5 — Bundle schema + CLI | `5cd36f58` | Clean |
| A6 — OSCAL emitter | `05ca492d` | Clean |
| A7 — KSI rules | `e6678377` | Clean |
| A9 — CI smoke test | `15fd9f98` | Clean |
| A10 — Docs | `d457ae99` | Clean |
| A8 — Quickstart + fixture | `423c71eb` | Clean |

---

## Milestone 2: Baseline Test Run

### ruff check src/ tests/

```
All checks passed!
```

### mypy src/uiao/ (error summary)

```
Found 39 errors in 39 files (checked 202 source files)
```

All 39 are pre-existing `import-untyped` stub warnings for `yaml` and `requests`.
Zero new type errors from WS branches.

### pytest tests/ -q --tb=short (baseline)

Note: `pytest` binary is in an isolated uv tools env without `pyyaml`. Tests must
be run via `uv run python -m pytest` using the project venv (after `uv add --dev pytest`
and `uv pip install fastapi httpx`).

```
2482 passed, 171 skipped, 4 warnings in 44.01s
```

**Baseline: CLEAN. No failures.**

---

## Fixes Applied

### Fix #1 — M3: A1↔A4 OrgPath duplicate (DONE — `ec814da8`)

`derive_candidate_orgpath` in `survey.py` now delegates to A4's canonical
`orgpath.derive_orgpath` for codebook-hit lookups. When no codebook hit exists
(empty codebook or unregistered code), falls back to the local
`derive_orgpath_from_dn` to preserve the governance-queue candidate behavior
tested by A1's tests. Late import used to break the `orgpath→survey` circular
dependency (orgpath imports `DriftFinding` and `derive_orgpath_from_dn` from
survey at module level).

### Fix #2 — M4: A6 missing RID 544 (DONE — `ab51a42c`)

Added `544  # BUILTIN\Administrators` to `_PRIVILEGED_RIDS` in
`src/uiao/oscal/orgtree_evidence.py`. Previously any user/computer with
`primaryGroupToken=544` bypassed AC-6 detection.

### Fix #3 — M5: A5 HMAC fail-open default (DONE — `58ee9bb5`)

`ir_orgtree_readiness_bundle` now exits non-zero (code 1) when
`UIAO_BUNDLE_HMAC_KEY` is unset unless `--insecure-dev-key` flag is passed.
Added two tests: `test_cli_orgtree_readiness_bundle_no_hmac_key_fails_closed`
and `test_cli_orgtree_readiness_bundle_insecure_dev_key_flag`.

### Fix #4 — M6: A2 TPM/HVCI graceful degradation (DONE — `4d48a0a9`)

`assess_intune_readiness` now distinguishes absent keys from explicit bad
values. Missing `tpmVersion`/`hvciEnabled` keys emit
`attribute_not_collected` findings in rationale but do not change the verdict.
Explicit `tpmVersion='1.2'` and `hvciEnabled=False` still produce
`NEEDS_TPM`/`NEEDS_HVCI` verdicts.

### Fix #5 — M7: A8 KAT actually-measured verdicts (DONE — `5d67c034`)

- `_parse_os_build` extended to handle AD display form `"10.0 (19045)"` in
  addition to dotted form `"10.0.19045"`. This fixed all 30 computer Intune
  verdicts which were spuriously returning `NEEDS_OS_UPGRADE`.
- Arc fixture KAT updated: Server 2016 is Arc-capable (READY, not
  NEEDS_OS_UPGRADE); Server 2012R2 is ESU-only (NEEDS_OS_UPGRADE, not
  INELIGIBLE); Linux servers without egress get NEEDS_NETWORK_EGRESS (not
  INELIGIBLE).
- `examples/orgtree/synthetic-forest-export.json` `_arc_verdict` annotations
  and `_meta.arc_verdicts_servers` updated.
- Quickstart KAT table rows 7-9 and `arc_verdicts_servers` meta updated.

### Fix #6 — M8: Register orgtree-readiness schema in substrate manifest (DONE — `e613db09`)

Added `orgtree_readiness_schema: src/uiao/schemas/orgtree-readiness/orgtree-readiness.schema.json`
to `registry_refs` in `src/uiao/canon/substrate-manifest.yaml`.

---

## Final Lint / Type / Test State

### ruff check src/ tests/
```
All checks passed!
```

### mypy src/uiao/ (non-stub errors only)
```
0 new errors (39 pre-existing import-untyped stubs, unchanged)
```

### pytest tests/ -q --tb=short
```
2484 passed, 171 skipped, 4 warnings in 40.11s
```

Net change from baseline: +2 tests (new HMAC fail-closed tests in M5).

---

## Deferred Items

None deferred. All 5 required fixes plus M8 schema registration applied.

**Known discovery (not a defect):** The `pytest` binary in this environment
uses an isolated uv tools Python that lacks `pyyaml`, causing collection
failures when using the bare `pytest` command. Workaround documented: always
use `uv run python -m pytest`. This is a CI environment issue, not a code issue;
`pyproject.toml` correctly declares `pyyaml` as a dependency.
