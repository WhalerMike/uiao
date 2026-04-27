# Phase 2 Integration Report — UIAO v0.6.0 OrgTree Readiness

Generated: 2026-04-27
Branch: `claude/v0.6.0-integration-zpRap`

---

## Milestone 0: Branch Setup

**Path taken: REUSE** — `claude/v0.6.0-integration-zpRap` already existed pointing to the same
HEAD as `origin/claude/v0.6.0-batch-a-integration`. The branch was already tracking origin and
up-to-date.

All 10 WS branches confirmed as ancestors:
- A4 (1722ba4d), A1 (faa2c529), A2 (e9e9153), A3 (a8981eb9), A5 (851b78ea)
- A6 (c68fbfee), A7 (5445f8c6), A9 (6adc9f8e), A8 (8e4a54e4), A10 (98042f2e)

---

## Milestone 1: Full CI Baseline (Pre-Phase-2 fixes)

Commit: `119ba228` (inherited from Phase 1.5)

| Gate | Status | Notes |
|------|--------|-------|
| ruff check src/ tests/ | **PASS** | `All checks passed!` |
| mypy src/uiao/ | **PASS** | 39 pre-existing `import-untyped` stub warnings (yaml/requests); 0 new errors |
| pytest tests/ -q --tb=short | **PASS** | `2484 passed, 171 skipped, 4 warnings in 41.34s` |
| Schema validation (jsonschema) | **PASS** | `orgtree-readiness.schema.json` validates against well-formed bundle |
| Substrate drift walker | **PASS** | No P1 blockers; 8 P2 warnings are all pre-existing (unrelated to orgtree) |
| Adapter conformance | **SKIP** | No `uiao adapter conformance` subcommand; adapter CLI only has `run`/`run-scuba` |
| Metadata validator | **SKIP** | No dedicated metadata validator CLI; validated implicitly via pytest |
| Quarto | **SKIP** | `quarto` binary not installed in CI environment |

---

## Milestone 2: Wire WS-A6 OSCAL Emitter into WS-A5 CLI

Commit: `8f530afb`

**Change:** Added `--oscal-out <dir>` flag to `uiao ir orgtree-readiness-bundle` command in
`src/uiao/cli/ir.py`. When set, after writing the three bundle artifacts (bundle.json, bundle.hash,
bundle.sig), the command calls:

```python
from uiao.oscal.orgtree_evidence import emit_orgtree_evidence
emit_orgtree_evidence(bundle, oscal_out)
```

**Test added:** `test_cli_orgtree_readiness_bundle_oscal_out_wires_a6_emitter` in
`tests/test_orgtree_readiness_bundle.py` — verifies:
- Exit code 0 with `--oscal-out` flag
- `orgtree-evidence.json` written to specified dir
- `assessment-results` top-level key present in output
- At least one `result` in assessment-results

---

## Milestone 3: Unmock WS-A9 Smoke Test

Commit: `26022c16`

**KSI YAML fixes:** KSI-001 through KSI-007 had broken indentation — nested fields
(`Data_Type`, `Evaluation`, `Severity`, `Mappings`, `Provenance`) were wrongly indented
under `Source/SCuBA_Field` instead of at the top level. All 7 files rewritten to match
the correct structure (matching KSI-008 through KSI-010).

**Result:** 14 previously-skipped KSI parse/field-presence tests promoted to PASS.

**New tests added to `tests/test_orgtree_readiness_smoke.py`:**
- `test_ksi_rules_reference_real_nist_controls[KSI-001..010]` — asserts each rule references a real NIST 800-53 control family
- `test_phase2_end_to_end_pipeline` — real WS-A5/A6 integration:
  - Runs `uiao ir orgtree-readiness-bundle` on `synthetic-forest-export.json` via CLI
  - Validates bundle signature (64-char hex hash + HMAC)
  - Invokes `emit_orgtree_evidence` via `--oscal-out` flag
  - Validates OSCAL structural output (assessment-results + results)
  - Asserts end-to-end runtime <60s (actual: ~0.4s)

**Additional fix:** Added `distinguishedName → dn` normalization in the bundle CLI so the
AD raw field name from the synthetic forest fixture passes schema validation.

**Smoke test before/after:**
- Before: 29 passed, 14 skipped, 0 failed
- After: 40 passed, 0 skipped, 0 failed

---

## Milestone 4: Substrate Walker

Run after Milestone 3 changes. No new findings introduced.

| Finding type | Count | Orgtree-related? |
|---|---|---|
| P1 blockers (DRIFT-PROVENANCE) | 0 | N/A |
| P2 warnings (DRIFT-PROVENANCE) | 8 | No — all pre-existing |

All 8 P2 findings are stale doc references to non-existent tool stubs
(`sync_canonical`, `impl/adapters/`, `demo_adapter`, `agency-config.yaml`,
`tenants.yaml`, `policies.yaml`, `specs/data-catalog`) — unchanged since Phase 1.5.
None reference orgtree, KSI, OSCAL, or any of the 10 WS branches' new files.

**Acceptance criteria met:** No DRIFT-PROVENANCE findings on new orgtree files.

---

## Milestone 5: Re-run All 8 Gates (Post-fixes)

Run after all Phase 2 changes committed.

| Gate | Status | Notes |
|------|--------|-------|
| ruff check src/ tests/ | **PASS** | `All checks passed!` |
| mypy src/uiao/ | **PASS** | Still 39 pre-existing stubs; 0 new errors |
| pytest tests/ -q --tb=short | **PASS** | `2510 passed, 157 skipped, 4 warnings in 39.70s` |
| Schema validation (jsonschema) | **PASS** | Bundle schema validates; smoke test exercises schema roundtrip |
| Substrate drift walker | **PASS** | No P1 blockers; 8 P2 pre-existing warnings (no change) |
| Adapter conformance | **SKIP** | No subcommand (unchanged) |
| Metadata validator | **SKIP** | No subcommand (unchanged) |
| Quarto | **SKIP** | Binary absent (unchanged) |

Net test change from Phase 1.5 baseline: +26 tests (14 KSI skips promoted + 12 new Phase 2 tests);
14 fewer skips.

---

## Milestone 6: Release Candidate Tag

**Tag `v0.6.0-rc1` CUT** — all 5 required gates green, smoke test passes.

```
git tag -a v0.6.0-rc1 -m "v0.6.0-rc1 — OrgTree readiness Phase 2 integration
...
```

See M6 commit for tag details.

---

## Deferred Items

- **Adapter conformance gate:** No `uiao adapter conformance` CLI subcommand exists;
  adapter conformance is validated implicitly through pytest test coverage.
  Recommend adding a formal subcommand in a future sprint.
- **Metadata validator gate:** Same — no dedicated CLI; validated via pytest.
- **Quarto gate:** `quarto` binary not installed in CI; the `.qmd` file exists and
  was registered in substrate manifest (Phase 1.5 M8). Recommend adding quarto to CI
  Docker image.
- **8 P2 substrate findings:** All pre-existing stale doc references; not introduced
  by Phase 2 work. Deferred to a docs cleanup sprint.
