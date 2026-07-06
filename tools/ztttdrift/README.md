# ZTTTdrift

**Drift, exception-lifecycle, and conmon gating on top of Zero Trust maturity-stage assessments (Microsoft ZTTT / CISA ZTMM-style self-assessments).**

A Zero Trust maturity self-assessment — the Microsoft Zero Trust assessment
tooling (ZTTT), a [CISA Zero Trust Maturity Model v2.0](https://www.cisa.gov/zero-trust-maturity-model)
self-assessment worksheet, or similar — is the assessment: it emits a
point-in-time **maturity stage** for every assessed item. That's assessment.
The assessment deliberately stops there — it does **not** track how your
maturity changes run-to-run, whether a given below-target item is already
governed by a documented risk-acceptance, or when that acceptance quietly
lapses, and it does not gate a pipeline.

ZTTTdrift is a small, tested Python layer that adds exactly those three things
— and nothing else. It **stands on** the assessment tool rather than
reimplementing any part of it. It never talks to your tenant; it consumes the
assessment's output, normalized to a versioned input contract (below). It is
the Zero Trust maturity counterpart to [ScubaDrift](../scubadrift/), which does
the same for ScubaGear's pass/fail policy verdicts.

> Design stance: ZTTTdrift adds *operational lifecycle* to an *authoritative
> assessment*. It is intentionally not a competing framework, not an assessor,
> and not a maturity model. If your assessment says an item is at `advanced`,
> ZTTTdrift agrees — its only job is to tell you which of the *below-target*
> items you actually have to act on.

## What it does

Given a maturity run and a risk-acceptance register, ZTTTdrift splits every
**failing** item — one whose assessed stage is *below its target stage* — into
three dispositions:

| Disposition | Meaning | Gate |
|---|---|---|
| `actionable_new_drift` | Below target, **no** risk-acceptance on file | **Act** |
| `lapsed_acceptance` | Below target, an acceptance exists but its expiry has **passed** | **Act** |
| `governed_exception` | Below target, covered by an **in-date** acceptance | Already governed |

It also:

- flags **retirable** acceptances — exceptions whose item now meets target,
  i.e. dead weight to remove from the register;
- computes **run-to-run drift** between two runs on the ordinal stage scale
  (**regressions** with from/to stages, **progressions**, new/removed items,
  and **target changes**);
- provides a **conmon gate**: exit non-zero only on `actionable_new_drift`,
  `lapsed_acceptance`, or (given a baseline) any **regression below target** —
  governed exceptions never break the build, and a regression that still meets
  target is reported but is not by itself gate-failing;
- adds **continuous monitoring** — a run history ledger, a **per-pillar average
  maturity trend**, and remediation **SLA aging** of open gaps, mapped to CISA
  BOD 25-01, NIST SP 800-137 (ISCM), NIST 800-53 CA-7, and FedRAMP ConMon.

All expiry and aging math is `--as-of`-injected, so runs are deterministic and
never drift with the wall clock.

## The stage scale

Stages are the CISA ZTMM v2.0 four-stage scale, and they are **ordered**:

```
traditional (0)  <  initial (1)  <  advanced (2)  <  optimal (3)
```

An item **fails** when `stage < target_stage`. Each item may declare its own
`target_stage`; otherwise the global `--target` option applies (default:
`advanced`). The parenthesized rank doubles as the numeric score used for
per-pillar trend averaging in the conmon report (documented mapping:
traditional=0, initial=1, advanced=2, optimal=3).

## Input contract: `ztttdrift-input/1.0`

**Honesty note — read this first.** There is **no verified sample of Microsoft
ZTTT's export format** available to this project, and ZTTTdrift does not
pretend otherwise by guessing at vendor field names. Instead, ZTTTdrift defines
its own small, versioned input contract, `ztttdrift-input/1.0`, as the
integration point. Any assessment export — ZTTT, a CISA ZTMM self-assessment
worksheet, a home-grown spreadsheet — is mapped onto this contract by a thin
converter. **Writing such a converter is out of scope pending a verified sample
of the source format.** What ships here is the contract, validated strictly:
unknown schema versions, stages, and pillars are rejected, never coerced.

```json
{
  "schema": "ztttdrift-input/1.0",
  "assessed_at": "2026-07-01",
  "source": "ZTMM-self-assessment",
  "items": [
    {
      "item_id": "ZT.ID.01",
      "pillar": "Identity",
      "title": "Phishing-resistant MFA coverage",
      "stage": "initial",
      "target_stage": "advanced"
    }
  ]
}
```

- `schema` — must be exactly `"ztttdrift-input/1.0"`.
- `assessed_at` — `YYYY-MM-DD`.
- `source` — free text describing where the run came from (e.g. `ZTTT` or
  `ZTMM-self-assessment`).
- `items[].item_id` — a stable identifier; duplicates are rejected.
- `items[].pillar` — one of the six ZTMM v2.0 pillars: `Identity`, `Devices`,
  `Networks`, `Applications and Workloads`, `Data`, `Cross-Cutting`
  (case-insensitive; normalized to this spelling).
- `items[].stage` — one of `traditional | initial | advanced | optimal`.
- `items[].target_stage` — optional, same enum; overrides the global
  `--target` for that item.
- `items[].title` — optional, human-readable.

## Install

```bash
pip install ./ztttdrift          # from this package
# optional YAML register support:
pip install './ztttdrift[yaml]'
```

Zero runtime dependencies (stdlib only). Python 3.10+.

## Usage

```bash
# 1) Which maturity gaps must I act on right now?
ztttdrift triage \
  --results assessment.json \
  --exceptions exceptions.yaml \
  --target advanced \
  --as-of 2026-07-01

# 2) What changed since the last assessment?
ztttdrift drift --baseline last_quarter.json --current assessment.json

# 3) Gate a pipeline (exit 1 if action is required; the optional
#    baseline also fails the gate on any regression below target):
ztttdrift gate --results assessment.json --exceptions exceptions.yaml \
  --baseline last_quarter.json

# 4) Record a run into the conmon ledger, then report the trend:
ztttdrift conmon-record --results assessment.json --exceptions exceptions.yaml \
  --history ledger.jsonl --as-of 2026-07-01
ztttdrift conmon-report --history ledger.jsonl --as-of 2026-07-01 --fail-on-breach
```

Example `triage` output (matches the fixtures under `tests/fixtures/`):

```
ZTTTdrift triage (as of 2026-07-01, target advanced)
  below target: 4  |  actionable: 3  (new drift 2, lapsed 1)  |  governed: 1
  ! ZT.ID.01     actionable_new_drift   stage initial below target advanced; no risk-acceptance on file
  * ZT.DV.01     lapsed_acceptance      stage initial below target advanced; risk-acceptance expired 2026-01-15 (POAM-0911)
  ! ZT.CC.01     actionable_new_drift   stage initial below target advanced; no risk-acceptance on file
  ~ ZT.NW.01     governed_exception     stage traditional below target advanced; accepted until 2026-12-31 (POAM-1042)
  retirable acceptances (item now meets target): ZT.AP.01
```

Add `--json` to any command for machine-readable output (for dashboards / SIEM).

## Inputs

**Assessment runs** — `ztttdrift-input/1.0` JSON as documented above. See
[`tests/fixtures/run_baseline.json`](tests/fixtures/run_baseline.json) and
[`tests/fixtures/run_current.json`](tests/fixtures/run_current.json) for
clearly-synthetic examples.

**Risk-acceptance register** — JSON (always) or YAML (`[yaml]` extra). Each
entry: `item_id`, `justification`, `approved_by`, `approved_date`,
`expiry_date`, optional `ticket`. Duplicate `item_id`s are rejected so a
register can never carry two conflicting acceptances. See
[`examples/exceptions.yaml`](examples/exceptions.yaml).

## Continuous monitoring

`ztttdrift gate` returns `0` when every gap is a governed, in-date exception
(and, if a baseline is given, nothing regressed below target) and `1` the
moment there is new drift, a lapsed acceptance, or such a regression — the
exit code a CI/conmon job keys on. See
[`examples/conmon-gate.yml`](examples/conmon-gate.yml).

`ztttdrift conmon-record` appends each run's triage to a JSON Lines ledger;
`ztttdrift conmon-report` turns the ledger into a periodic report: posture
counts, **per-pillar average stage** (0–3 scale, with delta vs. the previous
period), newly-actionable / resolved items, and **SLA aging** of every open
actionable gap. SLA tiers come from the stage gap — two or more stages below
target is *high* (30-day window), one stage below is *moderate* (90 days),
*low* is 180 days — mirroring common FedRAMP ConMon figures. These windows are
**defaults you must confirm** against your authorizing official's
requirements, and are overridable via `--sla-windows`.

Federal context this **supports** (it does not, by itself, certify
compliance):

- **CISA BOD 25-01** — recurring automated assessment recorded to a durable
  history ledger;
- **NIST SP 800-137 (ISCM)** — ongoing assessment with trend and a defined
  monitoring frequency;
- **NIST 800-53 CA-7** — continuous monitoring: maturity status over time, not
  a point-in-time check;
- **FedRAMP ConMon** — open gaps aged against remediation SLA windows.

## Library API

```python
from datetime import date
from ztttdrift import Stage, load_run, load_exceptions, triage, evaluate_gate, diff_runs

run = load_run("assessment.json")
acc = load_exceptions("exceptions.yaml")

report = triage(run, acc, as_of=date.today(), target=Stage.ADVANCED)
for t in report.actionable:
    print(t.item.item_id, t.disposition.value, t.reason)

gate = evaluate_gate(run, acc, as_of=date.today(), baseline=load_run("previous.json"))
raise SystemExit(gate.exit_code)
```

## Develop / test

```bash
pip install './ztttdrift[dev]'
pytest -q          # 60 tests, offline, deterministic
ruff check src tests
```

## Scope & non-goals

- **Not** an assessor — it reads assessment output, it does not assess a tenant.
- **Not** a maturity model — the stages and pillars are CISA's; ZTTTdrift adds
  no capabilities and re-scores nothing.
- **Not** a converter (yet) — mapping a real ZTTT/ZTMM export onto
  `ztttdrift-input/1.0` is a thin, separate step, out of scope pending a
  verified sample of the source format.
- **Not** a remediator — it tells you what to act on; your Zero Trust roadmap
  says how.

## License

MIT — same terms as ScubaDrift (see [`../scubadrift/LICENSE`](../scubadrift/LICENSE)).
