# ScubaDrift

**Drift, exception-lifecycle, and conmon gating on top of [CISA ScubaGear](https://github.com/cisagov/ScubaGear).**

ScubaGear is the sanctioned tool: it assesses a Microsoft 365 tenant against the
CISA SCuBA Secure Configuration Baselines and emits a point-in-time verdict for
every policy. That's assessment. ScubaGear deliberately stops there — it does
**not** track how your posture changes run-to-run, whether a given failure is
already governed by a documented risk-acceptance, or when that acceptance
quietly lapses, and it does not gate a pipeline.

ScubaDrift is a small, tested Python layer that adds exactly those three things
— and nothing else. It **stands on** ScubaGear rather than reimplementing any
part of it. It never talks to your tenant; it consumes ScubaGear's JSON output.

> Design stance: ScubaDrift adds *operational lifecycle* to an *authoritative
> baseline*. It is intentionally not a competing framework, not a scanner, and
> not a policy engine. If ScubaGear says a control passes, ScubaDrift agrees —
> its only job is to tell you which of the *failures* you actually have to act on.

## Documentation

Full documentation ships as a single Word document,
**[`ScubaDrift-Documentation.docx`](ScubaDrift-Documentation.docx)**, covering:
Getting started · Concepts · CLI reference · Input formats · Library API · CI
integration · Continuous monitoring · Design & scope · FAQ. It embeds the
architecture, disposition-gate, drift, exception-lifecycle, gate, and
continuous-monitoring figures. The figure sources (SVG) and rendered PNGs are
under [`docs/figures/`](docs/figures/).

Also: [CHANGELOG](CHANGELOG.md) · [CONTRIBUTING](CONTRIBUTING.md).

## What it does

Given a ScubaGear result file and a risk-acceptance register, ScubaDrift splits
every **failing** policy into three dispositions:

| Disposition | Meaning | Gate |
|---|---|---|
| `actionable_new_drift` | Failing, **no** risk-acceptance on file | **Act** |
| `lapsed_acceptance` | Failing, an acceptance exists but its expiry has **passed** | **Act** |
| `governed_exception` | Failing, covered by an **in-date** acceptance | Already governed |

It also:

- flags **retirable** acceptances — exceptions whose policy now passes, i.e.
  dead weight to remove from the register;
- computes **run-to-run drift** between two ScubaGear runs (regressions,
  remediations, baseline churn);
- provides a **conmon gate**: exit non-zero *only* when there is new drift or a
  lapsed acceptance — governed exceptions never break the build;
- adds **continuous monitoring** — a run history ledger, posture trend, and
  remediation **SLA aging** of open findings, mapped to CISA BOD 25-01, NIST
  SP 800-137 (ISCM), NIST 800-53 CA-7, and FedRAMP ConMon. See the Continuous
  monitoring section of `ScubaDrift-Documentation.docx`.

All expiry math is `--as-of`-injected, so runs are deterministic and never drift
with the wall clock.

## Install

```bash
pip install ./scubadrift          # from this package
# optional YAML register support:
pip install './scubadrift[yaml]'
```

Zero runtime dependencies (stdlib only). Python 3.10+.

## Usage

```bash
# 1) Which failures must I act on right now?
scubadrift triage \
  --results ScubaResults.json \
  --exceptions exceptions.yaml \
  --as-of 2026-07-01

# 2) What changed since the last assessment?
scubadrift drift --baseline last_week.json --current ScubaResults.json

# 3) Gate a pipeline (exit 1 if action is required):
scubadrift gate --results ScubaResults.json --exceptions exceptions.yaml
```

Example `triage` output:

```
ScubaDrift triage (as of 2026-07-01)
  failing: 4  |  actionable: 3  (new drift 2, lapsed 1)  |  governed: 1
  ! MS.AAD.1.1v1     actionable_new_drift   no risk-acceptance on file
  ! MS.EXO.1.1v1     actionable_new_drift   no risk-acceptance on file
  * MS.AAD.5.4v1     lapsed_acceptance      risk-acceptance expired 2026-01-15 (POAM-0911)
  ~ MS.AAD.3.1v1     governed_exception     accepted until 2026-12-31 (POAM-1042)
  retirable acceptances (policy now passing): MS.AAD.7.1v1
```

Add `--json` to any command for machine-readable output (for dashboards / SIEM).

## Inputs

**ScubaGear results** — ScubaDrift accepts both the flat
`{metadata, results:[...]}` shape and the full `ScubaResults.json`
(`{MetaData, Results:{PRODUCT:[...]}}`), and resolves common field-name aliases
(`PolicyId`/`Control ID`, `PolicyDescription`/`Requirement`). Policy version
suffixes (`v1`/`v2`) are preserved as part of the key.

**Risk-acceptance register** — JSON (always) or YAML (`[yaml]` extra). Each
entry: `policy_id`, `justification`, `approved_by`, `approved_date`,
`expiry_date`, optional `ticket`. Duplicate `policy_id`s are rejected so a
register can never carry two conflicting acceptances. See
[`examples/exceptions.yaml`](examples/exceptions.yaml).

## Continuous monitoring

`scubadrift gate` returns `0` when every failure is a governed, in-date
exception and `1` the moment there is new drift or a lapsed acceptance — the
exit code a CI/conmon job keys on. See
[`examples/conmon-gate.yml`](examples/conmon-gate.yml).

## Library API

```python
from datetime import date
from scubadrift import load_run, load_exceptions, triage, evaluate_gate, diff_runs

run = load_run("ScubaResults.json")
acc = load_exceptions("exceptions.yaml")

report = triage(run, acc, as_of=date.today())
for t in report.actionable:
    print(t.policy.policy_id, t.disposition.value, t.reason)

gate = evaluate_gate(run, acc, as_of=date.today())
raise SystemExit(gate.exit_code)
```

## Develop / test

```bash
pip install './scubadrift[dev]'
pytest -q          # 30 tests, offline, deterministic
ruff check src tests
```

## Scope & non-goals

- **Not** a scanner — it reads ScubaGear output, it does not assess a tenant.
- **Not** a baseline — the SCuBA baselines are CISA's; ScubaDrift adds no policies.
- **Not** a remediator — it tells you what to act on; you (or ScubaGear's own
  guidance) remediate.

## License

MIT — see [LICENSE](LICENSE).
