# ScubaDrift

Drift, exception-lifecycle, and continuous-monitoring gating on top of
[CISA ScubaGear](https://github.com/cisagov/ScubaGear).

ScubaGear assesses a Microsoft 365 tenant against the CISA SCuBA Secure
Configuration Baselines and emits a point-in-time verdict per policy. It does
not track run-to-run drift, the lifecycle of documented risk-acceptances, or
gate a pipeline. ScubaDrift is a small, tested layer that adds exactly those
three — standing on the sanctioned tool rather than reimplementing it. It never
talks to a tenant; it consumes ScubaGear's JSON output.

> **Scope stance.** ScubaDrift adds *operational lifecycle* to an *authoritative
> baseline*. It is not a scanner, not a competing baseline, not a remediator,
> and not a policy-inheritance engine. If ScubaGear says a control passes,
> ScubaDrift agrees — its only job is to tell you which of the *failures* you
> actually have to act on.

## Getting started

Requirements: Python 3.10+, a ScubaGear results file (JSON). Zero runtime
dependencies; YAML risk-acceptance registers need the optional `[yaml]` extra.

```bash
pip install ./scubadrift            # or: pip install './scubadrift[yaml]'
scubadrift --version
```

A five-minute tour against the bundled fixtures (fixed `--as-of` so output is
reproducible):

```bash
scubadrift triage --results tests/fixtures/run_current.json \
  --exceptions tests/fixtures/exceptions.json --as-of 2026-07-01
```

```
ScubaDrift triage (as of 2026-07-01)
  failing: 4  |  actionable: 3  (new drift 2, lapsed 1)  |  governed: 1
  ! MS.AAD.1.1v1     actionable_new_drift   no risk-acceptance on file
  * MS.AAD.5.4v1     lapsed_acceptance      risk-acceptance expired 2026-01-15 (POAM-0911)
  ! MS.EXO.1.1v1     actionable_new_drift   no risk-acceptance on file
  ~ MS.AAD.3.1v1     governed_exception     accepted until 2026-12-31 (POAM-1042)
  retirable acceptances (policy now passing): MS.AAD.7.1v1
```

## Architecture

ScubaDrift is six small modules: `models` (the value objects), `parser` (the
only module that touches disk), `triage` (the core decision), `drift` (the
independent run-to-run comparison), `gate` (a thin pass/fail wrapper over
triage), and `cli`. Files go in; a governed decision comes out; the tenant is
never touched.

## Concepts

### The failure model

ScubaGear verdicts normalize to a closed vocabulary. Only **failing** policies
are triaged — by default that is `Fail` alone; `--include-warnings` widens it to
`Fail` + `Warning`. `Manual`, `N/A`, `Omitted`, and `Unknown` are never
auto-actionable: a gate that floods reviewers with items it can never clear
trains them to ignore it.

### The three dispositions

For each failing policy, ScubaDrift asks: *is this already governed?*

- **`actionable_new_drift`** — failing, no risk-acceptance on file. Act now.
- **`lapsed_acceptance`** — failing, an acceptance exists but its `expiry_date`
  has passed. The governance decision expired; re-review, re-approve, or
  remediate.
- **`governed_exception`** — failing, covered by a documented, in-date
  acceptance. Known and owned, so it stays visible but is kept **out of the
  action list** and does **not** fail the gate.

The first two are "actionable"; the third is "governed." The gate keys on this
split.

### Retirable acceptances

A register rots the other way too: when a policy that has an acceptance on file
now **passes** (or is `N/A`), the acceptance is dead weight. ScubaDrift surfaces
these as **retirable** so you can prune the register and keep it honest.

### Run-to-run drift

Triage answers "what must I act on now." Drift answers "what changed." Comparing
two runs classifies each policy as `new_failure` (regression — the
highest-signal event), `resolved` (remediation to credit),
`persistent_failure`, `new_policy` (baseline grew, e.g. a version bump), or
`removed_policy`. Policies that pass in both runs produce no drift item. Drift is
compared by policy id only, so it is fully deterministic given two files.

### Risk-acceptance lifecycle

An acceptance is a documented, time-boxed decision: `policy_id`,
`justification`, `approved_by`, `approved_date`, `expiry_date`, optional
`ticket`. It is in date **through and including** its `expiry_date` and lapses
the day after (`is_expired` is `as_of > expiry_date`). Expiry is the one place
time enters the model, and it is always injected as an explicit `as_of` —
`triage`, `evaluate_gate`, and the ConMon report all take it, and only the CLI
defaults it to today. Same inputs + same `as_of` ⇒ same result, so tests never
drift with the wall clock.

## CLI reference

```
scubadrift [--version] <command> [options]
```

Common to every command: `--include-warnings` (treat `Warning` as failing) and
`--json` (machine-readable output).

**Exit codes.** `0` success (for `gate`: no actionable findings); `1` action
required — `gate` (new drift or lapsed acceptance) or `conmon-report
--fail-on-breach` (an SLA breach); `2` input error (bad file, invalid JSON,
malformed register, bad `--as-of`, empty ledger, or usage error).

### Gating a pipeline

`triage` and `drift` always exit `0` — they report. Only `gate` (and
`conmon-report --fail-on-breach`) return `1` to fail a build.

- **`scubadrift triage --results FILE [--exceptions FILE] [--as-of DATE]`** —
  split failures into new-drift / lapsed / governed, plus retirable acceptances.
- **`scubadrift drift --baseline FILE --current FILE`** — classify every changed
  policy between two runs.
- **`scubadrift gate --results FILE [--exceptions FILE] [--as-of DATE]`** —
  triage, then exit `1` if action is required. This is the CI entry point;
  governed exceptions keep the build green.
- **`scubadrift conmon-record --results FILE [--exceptions FILE] --history FILE
  [--as-of DATE]`** — append a run's triage to the history ledger.
- **`scubadrift conmon-report --history FILE [--as-of DATE] [--sla-windows FILE]
  [--fail-on-breach]`** — emit a periodic report: trend since the prior period
  plus SLA aging of open findings.

Every command accepts `--json`; the JSON mirrors the library `to_dict()` shape.

## Input formats

**ScubaGear results.** ScubaDrift accepts both the flat
`{metadata, results:[…]}` shape and the full `ScubaResults.json`
(`{MetaData, Results:{PRODUCT:[…]}}`), and resolves field-name aliases
(`PolicyId`/`Control ID`, `PolicyDescription`/`Requirement`, …). Policy version
suffixes (`v1`/`v2`) are preserved as part of the key. A row with no resolvable
policy id raises `ParseError`.

**Risk-acceptance register.** JSON always; YAML with the `[yaml]` extra. Either a
bare list or an object with an `acceptances`/`exceptions` key. Each entry needs
`policy_id`, `approved_date`, `expiry_date` (ISO `YYYY-MM-DD`), and should carry
`justification`/`approved_by`. Duplicate `policy_id`s are rejected so a register
can never carry two conflicting acceptances; malformed dates fail loudly. The
parser is tolerant of ScubaGear's variety but strict about the register —
because a governance record that silently accepts ambiguity is worse than none.

## Library API

Everything public is re-exported from the top-level package:

```python
from datetime import date
from scubadrift import load_run, load_exceptions, triage, diff_runs, evaluate_gate

run = load_run("ScubaResults.json")
acc = load_exceptions("exceptions.yaml")
report = triage(run, acc, as_of=date.today())
for t in report.actionable:
    print(t.policy.policy_id, t.disposition.value, t.reason)
raise SystemExit(evaluate_gate(run, acc, as_of=date.today()).exit_code)
```

Value objects are frozen dataclasses with `to_dict()`; every time-dependent
function takes an explicit `as_of: date`. Continuous-monitoring types
(`History`, `HistoryEntry`, `SlaFinding`, `build_report`, `record_run`,
`sla_findings`) are exported alongside the core.

## CI integration

The pattern: ScubaGear runs on a schedule (its own job, with tenant credentials)
and drops `ScubaResults.json`; ScubaDrift gates that artifact against a
version-controlled register. Separating assessment (needs credentials) from
gating (needs only files) keeps the gate credential-free and runnable anywhere.

```yaml
- run: pip install './scubadrift[yaml]'
- name: Gate on actionable drift
  run: scubadrift gate --results ./scuba-out/ScubaResults.json \
                       --exceptions ./governance/exceptions.yaml --json
```

The build fails exactly when `gate` exits `1`. Consume `--json` for a dashboard
or SIEM; the fields most integrations key on are `summary.actionable_total`,
`summary.lapsed_acceptance`, and `summary.retirable_acceptances`.

## Continuous monitoring

ScubaGear is point-in-time; continuous-monitoring programs need the **time
dimension**. ScubaDrift's `conmon` capability adds a durable **history ledger**
(append-only JSON Lines, one entry per run), posture **trend** across runs, and
remediation **SLA aging** of open findings.

Federal context this **supports** (it does not, by itself, certify compliance):

- **CISA BOD 25-01** — recurring automated SCuBA assessment and reporting.
- **NIST SP 800-137 (ISCM)** and **NIST 800-53 CA-7** — ongoing assessment with
  trend and a defined monitoring frequency.
- **FedRAMP ConMon** — POA&M remediation timelines by risk. Default SLA windows
  mirror the common figures (**High 30 / Moderate 90 / Low 180** days, mapped
  from SCuBA `Shall`/`Should`/`May`); they are **defaults you must confirm**
  against your authorizing official's requirements, and are overridable with
  `--sla-windows`.

Only *actionable* findings accrue remediation age (aged from their **first-seen**
date in the ledger); governed exceptions are excluded — their clock is the
acceptance expiry. Workflow:

```bash
# On every ScubaGear run:
scubadrift conmon-record --results ScubaResults.json \
  --exceptions exceptions.yaml --history conmon-ledger.jsonl
# On your reporting cadence (e.g. monthly):
scubadrift conmon-report --history conmon-ledger.jsonl --fail-on-breach --json
```

```
ScubaDrift continuous-monitoring report  2026-04-01 -> 2026-07-01
  posture: failing 4 | actionable 3 | governed 1
  trend: +2 new actionable / -2 resolved
  SLA: 1 overdue, 0 due soon
    ! MS.AAD.5.4v1     high      age 91d / 30d  overdue
```

Each report carries a `framework_alignment` map to the rules above — support,
not certification. Keep the ledger in version control (or an evidence bucket);
the longer it is, the more accurate `first_seen` and therefore aging become.

## Design & scope

The design principle throughout: **stand on the authoritative tool; do not
rebuild any part of it, and do not compete with it.** ScubaDrift never re-decides
whether a control passes, has no second baseline to defend, needs no tenant
access, and is auditable in an afternoon.

Explicit non-goals: it is **not** a scanner/assessor, **not** a baseline or
policy set, **not** a remediator, **not** an OSCAL generator, and **not** a
policy-inheritance/resolution engine. Keeping these out is what keeps the "stand
on the authority" promise honest. Key decisions: deterministic time
(`as_of`-injected everywhere), immutable value objects with `to_dict()` so the
`--json` output and the library shape can't drift, tolerant parsing of ScubaGear
but strict validation of the register, and failure semantics that err toward
*not* manufacturing work.

## FAQ

**Does it run ScubaGear or talk to my tenant?** No — it reads ScubaGear's JSON
output. Run ScubaGear separately.

**A control is `Manual`/`N/A` and I expected it flagged — why isn't it?** Only
`Fail` is actionable by default; `Manual`/`N/A` are not drift a gate can clear.
Use `--include-warnings` to also gate on `Warning`.

**My acceptance is on file but the policy is still actionable.** Either it lapsed
(`expiry_date < as_of` → `lapsed_acceptance`) or the `policy_id` doesn't match
exactly, version suffix included (`MS.AAD.3.1v1` ≠ `MS.AAD.3.1`).

**How do I see what will lapse next month?** Run the gate (or ConMon report)
against a future `--as-of`; expiry is deterministic, so it shows exactly what
will be lapsed then.

**Are the tests time-dependent?** No — every test pins `as_of`, and drift is
compared by policy id only. Nothing reads the wall clock, so the suite will not
rot.
