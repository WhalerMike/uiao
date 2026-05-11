# WS-B3 — Public Surface Audit Report (v0.6.0)

**Date:** 2026-05-11
**Branch:** `claude/v0.6.0-ws-b3-surface-audit`
**Auditor:** WS-B3 session (Phase 3 — Validation)

---

## 1. What's new in the v0.6.0 surface

### New CLI commands (4)

| Command | Sub-app | Module |
|---|---|---|
| `uiao reciprocity onboard-agency` | `reciprocity` | `uiao.cli.reciprocity` |
| `uiao reciprocity list-records` | `reciprocity` | `uiao.cli.reciprocity` |
| `uiao reciprocity verify` | `reciprocity` | `uiao.cli.reciprocity` |
| `uiao conmon ato-cadence-check` | `conmon` | `uiao.monitoring.ato_cadence` |

### New library modules (5, CLI-unreachable)

| Module | Role |
|---|---|
| `uiao.oscal.reciprocity_record` | HMAC-SHA256-signed reciprocity record emitter / verifier (WS-A2) |
| `uiao.oscal.reciprocity_bundle` | Per-agency self-verifying bundle aggregator (WS-A6) |
| `uiao.governance.config_latitude` | Configuration-latitude drift detector, emits DRIFT-SCHEMA (WS-A7) |
| `uiao.evidence.graph` (v1.2) | Evidence graph with ATO-decision + reciprocity-record node types (WS-A3) |
| `uiao.monitoring.ato_cadence` | ATO cadence SLA evaluation engine (backing `ato-cadence-check`) |

### New data artifacts (1 family)

| Artifact | Location | Role |
|---|---|---|
| KSI-RECIP-001..008 | `src/uiao/rules/ksi/KSI-RECIP-*.yaml` | 8 KSIs covering reciprocity-program health (WS-A10) |

---

## 2. Documentation coverage

| Surface item | `--help` example | `cli-reference.md` section | `AGENTS.md` inventory row |
|---|---|---|---|
| `uiao reciprocity onboard-agency` | Yes (source code) | Yes (§3.4, added WS-B3) | Yes (v0.6.0 table) |
| `uiao reciprocity list-records` | Yes (source code) | Yes (§3.4, added WS-B3) | Yes (v0.6.0 table) |
| `uiao reciprocity verify` | Yes (source code) | Yes (§3.4, added WS-B3) | Yes (v0.6.0 table) |
| `uiao conmon ato-cadence-check` | Yes (source code) | Yes (§3.6, added WS-B3) | Yes (v0.6.0 table) |
| `uiao.oscal.reciprocity_record` | N/A (library) | N/A | Yes (v0.6.0 table) |
| `uiao.oscal.reciprocity_bundle` | N/A (library) | N/A | Yes (v0.6.0 table) |
| `uiao.governance.config_latitude` | N/A (library) | N/A | Yes (v0.6.0 table) |
| `uiao.evidence.graph` v1.2 | N/A (library) | Existing §3.11 | Yes (v0.6.0 table) |
| KSI-RECIP family | N/A (data) | N/A | Yes (v0.6.0 table) |

All 4 new CLI commands are fully documented in `cli-reference.md` with synopsis, options table, runnable example block, and expected output shape. All 7 AGENTS.md surface rows added.

**Undocumented:** None for the v0.6.0 scope. Library modules are intentionally CLI-unreachable and documented as such in the AGENTS.md inventory tier column.

---

## 3. Coverage delta from v0.5.0

| Metric | v0.5.0 | v0.6.0 | Delta |
|---|---|---|---|
| CLI leaf commands (smoke-tested) | 44 | 68 | +24 |
| Sub-apps | 11 | 15 | +4 (`reciprocity` + others from Batch A) |
| Library-only modules | 1 | 5+ | +4 |
| `--help` example coverage | 44/44 (100%) | 68/68 (100%) | 0% — maintained |
| `cli-reference.md` sections | 9 (§3.1–3.9) | 11 (§3.1–3.11) | +2 |
| AGENTS.md inventory rows | 15 | 22 | +7 |

The smoke test (`tests/test_cli_help_smoke.py`) confirms all 68 commands return exit 0 on `--help`. No regressions observed.

---

## 4. Recommendations for v0.6.0 release readiness

1. **WS-A2 integration gate:** `uiao reciprocity onboard-agency` and `uiao reciprocity verify` both exit with code 3 when `uiao.oscal.reciprocity_record` is not importable (pre-Phase 2 stub behavior). Confirm Phase 2 merge wires the emitter before cutting v0.6.0; the smoke test will not catch this since `--help` does not exercise the emitter path.

2. **`cli-reference.md` version header:** The document currently reads "Version: Current (April 2026)". Update to "v0.6.0 (May 2026)" at release-cut time (Phase 4).

3. **`evidence graph` section in `cli-reference.md`** (existing §3.11) mentions "UIAO_113" but does not yet reflect the v1.2 node types (`ato-decision`, `reciprocity-record`). Recommend a one-paragraph update in Phase 4.

4. **KSI-RECIP narrative doc** (`docs/docs/22_HRITProductization.qmd`, WS-A10) is not yet reflected in `cli-reference.md` — it is a Quarto doc, not a CLI command. No action needed here; the Quarto site build covers it.

5. **Lab tenant dry-run (WS-B1)** is a human-in-loop step. Surface audit cannot verify end-to-end record emission against a real OPM-style tenant. Recommend treating WS-B1 sign-off as a v0.6.0 release gate before Phase 4.
