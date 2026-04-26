---
adr: ADR-046
title: "CLI Surface Convention: Sub-App-per-Domain"
status: Accepted
date: 2026-04-23
author: WhalerMike
supersedes: []
superseded_by: null
related:
  - ADR-032  # single-package consolidation
  - ADR-044  # substrate governance realignment
---

# ADR-046: CLI Surface Convention — Sub-App-per-Domain

## Context

The v0.4.0 cycle completed substrate governance realignment
([ADR-044](adr-044-substrate-governance-realignment.md)) and restored
every blocking CI gate. With the repair cycle closed, Phase 1 (adoption
readiness, tracked in issue #183) begins. M1 of that phase is a CLI
surface audit; the audit (2026-04-23, commit `1896d890`) found:

- **48 commands**, 40 of them flat at the top level in `cli/app.py`
  (1,375 lines)
- **6 already-modularized sub-apps** (`evidence`, `ksi`, `orchestrator`,
  `oscal`, `scuba`, `substrate`) showing the target pattern
- **36 flat commands** grouped only by hyphen-prefix naming convention:
  13× `ir-*`, 11× `generate-*`, 3× `conmon-*`, 2× `adapter-run*`, plus
  strays (`canon-check`, `validate`, `validate-ssp`)
- **Half-migration wart:** `generate-all` exists as a flat command but
  there is no `generate` group — `uiao generate --help` returns
  "No such command"
- **Only 8% of commands** (4/48) have a runnable example in their
  docstring
- **No smoke test** exercises `--help` across the surface — import
  regressions in any of the 48 commands ship silently until a user
  hits them (PR #158 was one such latent bug)

The current state is a half-migration. Leaving it alone guarantees the
first external adopter (target exit criterion of Phase 1) will hit the
inconsistency on their first `uiao --help`.

## Decision

Adopt **sub-app-per-domain** as the canonical CLI surface convention:

1. **Top-level commands are sub-app names, not verbs.** The top level
   enumerates domains (`adapter`, `canon`, `conmon`, `evidence`,
   `generate`, `ir`, `ksi`, `orchestrator`, `oscal`, `scuba`,
   `substrate`), not individual actions.

2. **Each sub-app lives in its own module** under `src/uiao/cli/`.
   The module exports `<name>_app: typer.Typer`; `cli/app.py` imports
   and registers it via `app.add_typer(<name>_app, name="<name>")`.

3. **Commands under a sub-app are verb-objects** (`ir scuba-transform`,
   `generate ssp`, `oscal validate`). Hyphens are allowed inside a
   sub-command name when the verb or object is compound.

4. **New commands MUST live under a sub-app.** The only exception is
   the `--version` / `--help` callback on the root `app`. Any PR adding
   a flat top-level command will be rejected at review unless the PR
   also introduces the sub-app that hosts it.

5. **Every command MUST have a runnable example in its help text.**
   The example must use only paths + arguments a reader can
   substitute; no private fixtures, no out-of-band setup. The smoke
   test in `tests/test_cli_help_smoke.py` enforces that `--help`
   returns exit 0 for every registered command, but does not
   currently enforce the example-present rule — that stays as a
   review-time check pending a lint rule.

## Consequences

### Immediate (v0.5.0, shipped in this PR)

All 36 flat commands are renamed under their sub-app:

| Old name | New name |
|---|---|
| `adapter-run` | `adapter run` |
| `adapter-run-scuba` | `adapter run-scuba` |
| `canon-check` | `canon check` |
| `conmon-dashboard` | `conmon dashboard` |
| `conmon-export-oa` | `conmon export-oa` |
| `conmon-process` | `conmon process` |
| `generate-all` | `generate all` |
| `generate-artifacts` | `generate artifacts` |
| `generate-briefing` | `generate briefing` |
| `generate-diagrams` | `generate diagrams` |
| `generate-docs` | `generate docs` |
| `generate-docx` | `generate docx` |
| `generate-gemini` | `generate gemini` |
| `generate-pptx` | `generate pptx` |
| `generate-sbom` | `generate sbom` |
| `generate-ssp` | `generate ssp` |
| `generate-visuals` | `generate visuals` |
| `ir-auditor-bundle` | `ir auditor-bundle` |
| `ir-dashboard` | `ir dashboard` |
| `ir-diff` | `ir diff` |
| `ir-drift-detect` | `ir drift-detect` |
| `ir-evidence-bundle` | `ir evidence-bundle` |
| `ir-freshness` | `ir freshness` |
| `ir-freshness-schedule` | `ir freshness-schedule` |
| `ir-generate-sar` | `ir generate-sar` |
| `ir-governance-report` | `ir governance-report` |
| `ir-poam-export` | `ir poam-export` |
| `ir-scuba-transform` | `ir scuba-transform` |
| `ir-ssp-inject` | `ir ssp-inject` |
| `ir-ssp-report` | `ir ssp-report` |
| `ir-validate` | `ir validate` |
| `validate` | `oscal validate` |
| `validate-ssp` | `oscal validate-ssp` |

`cli/app.py` shrinks from 1,375 to ~80 lines (just the root app,
version callback, and sub-app registrations).

### Breaking change policy

This is a **hard-break rename without deprecation shims.** Rationale:

- Repo has zero known external users at v0.4.0 — the cheapest moment
  to break names
- Deprecation shims carry weight (≥1 minor release of dual-name
  registration, accompanying DeprecationWarning plumbing, tests that
  assert the warnings fire)
- Post-v0.5.0 the convention is enforced; future renames MUST go
  through deprecation per the semver contract Phase 2 will establish

Adopters upgrading past v0.4.0 must update their invocations. The
v0.5.0 CHANGELOG includes the full mapping table above.

### Tooling consequences

- **Smoke test** (`tests/test_cli_help_smoke.py`) iterates the Typer
  command tree and asserts `--help` exits 0 for every command. New
  commands get coverage automatically.
- **Makefile / docs / CI workflows** referencing old command names
  are updated in the same PR. The substrate walker will flag any
  missed references at the next walk.
- **AGENTS.md** invariant list gains I6: "CLI commands live under
  sub-apps; new flat top-level commands are disallowed."

### Rejected alternatives

- **Additive with deprecation window (Option B from audit report):**
  Rejected because zero external users makes the deprecation plumbing
  pure overhead.
- **Keep flat names (Option C):** Rejected because the inconsistency
  surfaces on `uiao --help` to every first-time user.
- **Rename via multiple PRs, one per sub-app family:** Rejected
  because cross-cutting concerns (tests, Makefile, docs) update
  atomically; splitting them causes bisect pain during review.

## Verification

- [ ] `uiao --help` shows 11 sub-apps + version flag at the top level
- [ ] Every pre-rename invocation in `tests/` updated
- [ ] Every pre-rename invocation in `Makefile` updated
- [ ] Every pre-rename invocation in `.github/workflows/*.yml` updated
- [ ] Every pre-rename reference in `docs/` updated
- [ ] `tests/test_cli_help_smoke.py` exists and passes
- [ ] `substrate walk` reports zero findings
- [ ] All existing CI gates (ruff, mypy, pytest, substrate-drift,
  metadata-validator) green
