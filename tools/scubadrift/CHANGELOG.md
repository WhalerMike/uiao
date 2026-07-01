# Changelog

All notable changes to ScubaDrift are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project aims
to follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] — 2026-07-01

Initial release.

### Added
- **Exception-lifecycle triage** (`scubadrift triage`): splits every failing
  ScubaGear policy into `actionable_new_drift`, `lapsed_acceptance`, or
  `governed_exception`, and flags **retirable** acceptances whose policy now
  passes.
- **Run-to-run drift** (`scubadrift drift`): classifies changes between two
  ScubaGear runs as `new_failure` (regression), `resolved`, `persistent_failure`,
  `new_policy`, or `removed_policy`.
- **Conmon gate** (`scubadrift gate`): exit `0` when every failure is a governed,
  in-date exception; exit `1` on new drift or a lapsed acceptance; exit `2` on
  input error.
- **Continuous monitoring** (`scubadrift conmon-record` / `conmon-report`): an
  append-only history ledger, posture trend across runs, and remediation **SLA
  aging** of open findings (default windows High 30 / Moderate 90 / Low 180,
  overridable). `--fail-on-breach` gates on overdue findings. Reports carry a
  framework-alignment map (CISA BOD 25-01, NIST SP 800-137 ISCM, NIST 800-53
  CA-7, FedRAMP ConMon) — support, not certification.
- **Tolerant ScubaGear parser**: accepts the flat `{metadata, results:[…]}` shape
  and the full `{MetaData, Results:{PRODUCT:[…]}}` shape, with field-name aliases
  (`PolicyId`/`Control ID`, `PolicyDescription`/`Requirement`, …). Policy version
  suffixes are preserved.
- **Risk-acceptance register**: JSON always, YAML via the `[yaml]` extra.
  Duplicate `policy_id`s and malformed dates are rejected.
- **Deterministic expiry**: all time-dependent logic takes an explicit
  `as_of: date`; the wall clock is read only at the CLI default.
- **Library API**: frozen dataclasses with `to_dict()`; `--json` output mirrors
  the API shape.
- 34-test offline suite, `ruff`-clean, zero runtime dependencies.
- Full documentation set under `docs/`, plus example register and CI workflow.

[0.1.0]: https://example.invalid/scubadrift/releases/0.1.0
