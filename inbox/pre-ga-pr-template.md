# PR Template — pre-GA v0.6.0 cleanups

**Branch**: `claude/v0.6.0-pre-ga-cleanups`
**Base**: `main`
**Title**: `pre-ga: A1 FILETIME audit + A3 distro robustness + A6 mypy + A6 golden canonicalization`

## Body

Post-rc1, pre-GA hardening for v0.6.0. Parent: #246 (Phase 2 integration).

- **A1 FILETIME audit**: Fixed `_FILETIME_2024_01_01` test constant (`133_156_608_000_000_000` mapped to 2022-12-16, not 2024-01-01; correct value is `133_485_408_000_000_000`). Days bounds made dynamic so the test stays green as wall-clock advances. Production `is_stale_account()` conversion was already correct. Added module-level comment citing MS-ADTS 2.2.18.

- **A3 Linux distro robustness**: Extended `_is_linux_server_os()` to handle `"Ubuntu 22.04 LTS Server"` (and similar variants where `"server"` trails the version number) via a co-presence check for `ubuntu` + `server` in the normalized string. All 46 parametrized distro-variant test cases pass.

- **A6 mypy override scope**: Removed module-wide `[[tool.mypy.overrides]]` for `uiao.oscal.orgtree_evidence` that disabled `call-arg`/`arg-type` across the entire file. The 3 trestle constructor sites already carry inline `# type: ignore[call-arg/arg-type]` comments; `mypy src/uiao/oscal/orgtree_evidence.py` returns zero errors. Keeps mypy strict on all non-trestle code in the module.

- **A6 golden canonicalization**: Replaced `_normalise_for_golden()` with `_canonicalize()` in the OSCAL golden test. New function recursively sorts dict keys, normalizes timestamp sentinels, and drops `metadata.version` (changes per release but not evidence content). Returns a stable `json.dumps` string for human-readable failure diffs. Golden file regenerated.

## Test plan

- [x] `ruff check . && ruff format --check .` — passes (412 files)
- [x] `mypy src/uiao/oscal/orgtree_evidence.py` — zero errors
- [x] `pytest tests/test_active_directory_survey_enrichment.py tests/test_arc_readiness.py tests/test_orgtree_evidence_oscal.py -v` — 202 passed

https://claude.ai/code/session_0148BFawa7sNAR2ZrRFByFrp
