"""ZTTTdrift command-line interface.

Five subcommands:

* ``ztttdrift triage``        — split below-target items into new-drift / lapsed / governed.
* ``ztttdrift drift``         — compare two maturity runs (regressions, progressions, churn).
* ``ztttdrift gate``          — triage (+ optional baseline regressions) and exit non-zero
  if action is required (CI).
* ``ztttdrift conmon-record`` — append a run's triage to the history ledger.
* ``ztttdrift conmon-report`` — periodic report: pillar trend + SLA aging.

``--as-of`` pins the date used for exception-expiry and aging math (default:
today), so CI runs are reproducible and testable. ``--target`` sets the global
default maturity target (default: ``advanced``); per-item ``target_stage`` in
the input overrides it.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from . import __version__
from .conmon import DEFAULT_SLA_WINDOWS, History, SlaStatus, build_report, record_run
from .drift import diff_runs
from .gate import evaluate_gate
from .models import DEFAULT_TARGET, Stage
from .parser import ParseError, load_exceptions, load_run
from .triage import Disposition, triage


def _as_of(value: str | None) -> date:
    if not value:
        # Operator-local "as of" date, tz-aware (DTZ011).
        return datetime.now(timezone.utc).astimezone().date()
    try:
        return date.fromisoformat(value)
    except ValueError:
        print(f"ztttdrift: --as-of must be YYYY-MM-DD, got {value!r}", file=sys.stderr)
        raise SystemExit(2)


def _target(value: str) -> Stage:
    try:
        return Stage.parse(value)
    except ValueError as exc:
        print(f"ztttdrift: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


def _emit(obj: dict, as_json: bool, text: str) -> None:
    if as_json:
        print(json.dumps(obj, indent=2, sort_keys=True))
    else:
        print(text)


_ICON = {
    Disposition.ACTIONABLE_NEW_DRIFT: "!",
    Disposition.LAPSED_ACCEPTANCE: "*",
    Disposition.GOVERNED_EXCEPTION: "~",
}


def _triage_text(report) -> str:
    s = report.summary()
    lines = [
        f"ZTTTdrift triage (as of {report.as_of.isoformat()}, target {report.target.value})",
        (
            f"  below target: {s['failing_total']}  |  actionable: {s['actionable_total']}  "
            f"(new drift {s['actionable_new_drift']}, lapsed {s['lapsed_acceptance']})  |  "
            f"governed: {s['governed_exception']}"
        ),
    ]
    for t in report.actionable:
        lines.append(f"  {_ICON[t.disposition]} {t.item.item_id:<12} {t.disposition.value:<22} {t.reason}")
    for t in report.governed:
        lines.append(f"  {_ICON[t.disposition]} {t.item.item_id:<12} {t.disposition.value:<22} {t.reason}")
    if report.retirable:
        ids = ", ".join(a.item_id for a in report.retirable)
        lines.append(f"  retirable acceptances (item now meets target): {ids}")
    return "\n".join(lines)


def _cmd_triage(args: argparse.Namespace) -> int:
    run = load_run(args.results)
    acc = load_exceptions(args.exceptions) if args.exceptions else []
    report = triage(run, acc, as_of=_as_of(args.as_of), target=_target(args.target))
    _emit(report.to_dict(), args.json, _triage_text(report))
    return 0


def _cmd_drift(args: argparse.Namespace) -> int:
    base = load_run(args.baseline)
    curr = load_run(args.current)
    report = diff_runs(base, curr, target=_target(args.target))
    s = report.summary()
    text = [
        "ZTTTdrift run-to-run diff",
        (
            f"  regressions: {s['regression']} ({s['regressions_below_target']} below target)  |  "
            f"progressions: {s['progression']}  |  target changes: {s['target_change']}"
        ),
        f"  scope churn: +{s['new_item']} new / -{s['removed_item']} removed",
    ]
    for i in report.regressions:
        flag = "below target" if i.below_target else "still meets target"
        text.append(f"  ! {i.item_id:<12} {i.baseline_stage} -> {i.current_stage}  ({flag})")
    _emit(report.to_dict(), args.json, "\n".join(text))
    return 0


def _cmd_gate(args: argparse.Namespace) -> int:
    run = load_run(args.results)
    acc = load_exceptions(args.exceptions) if args.exceptions else []
    baseline = load_run(args.baseline) if args.baseline else None
    result = evaluate_gate(run, acc, as_of=_as_of(args.as_of), target=_target(args.target), baseline=baseline)
    if args.json:
        payload = {
            "passed": result.passed,
            "regressions_below_target": [i.to_dict() for i in result.regressions_below_target],
            **result.report.to_dict(),
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(result.headline())
        for t in result.report.actionable:
            print(f"  {_ICON[t.disposition]} {t.item.item_id:<12} {t.reason}")
        for i in result.regressions_below_target:
            print(f"  v {i.item_id:<12} regressed {i.baseline_stage} -> {i.current_stage} (below target)")
    return result.exit_code


def _load_windows(path: str | None) -> dict:
    if not path:
        return dict(DEFAULT_SLA_WINDOWS)
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ztttdrift: cannot read --sla-windows {path!r}: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    return {str(k).lower(): int(v) for k, v in data.items()}


def _cmd_conmon_record(args: argparse.Namespace) -> int:
    run = load_run(args.results)
    acc = load_exceptions(args.exceptions) if args.exceptions else []
    history = History.load(args.history)
    entry = record_run(run, acc, as_of=_as_of(args.as_of), target=_target(args.target))
    history.append(entry)
    history.save(args.history)
    s = entry.counts
    print(
        f"recorded {entry.as_of.isoformat()} ({entry.source or 'run'}) -> {args.history}  "
        f"[{len(history.entries)} entr{'y' if len(history.entries) == 1 else 'ies'}]"
    )
    print(
        f"  below target {s['failing_total']} | actionable {s['actionable_total']} | governed {s['governed_exception']}"
    )
    return 0


_SLA_ICON = {SlaStatus.OVERDUE: "!", SlaStatus.DUE_SOON: "*", SlaStatus.ON_TRACK: "-"}


def _cmd_conmon_report(args: argparse.Namespace) -> int:
    history = History.load(args.history)
    if not history.entries:
        print(f"ztttdrift: history {args.history!r} is empty — record a run first", file=sys.stderr)
        return 2
    report = build_report(history, as_of=_as_of(args.as_of), windows=_load_windows(args.sla_windows))
    if args.json:
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    else:
        start = report.period_start.isoformat() if report.period_start else "(first period)"
        p = report.posture
        print(f"ZTTTdrift continuous-monitoring report  {start} -> {report.period_end.isoformat()}")
        print(
            f"  posture: below target {p['failing_total']} | actionable {p['actionable_total']} | "
            f"governed {p['governed_exception']}"
        )
        print("  pillar maturity (0=traditional .. 3=optimal):")
        for pillar, t in report.pillar_trend.items():
            delta = f"{t['delta']:+.2f}" if t["delta"] is not None else "n/a"
            print(f"    {pillar:<28} {t['score']:.2f}  (delta {delta})")
        print(f"  trend: +{len(report.new_actionable)} new actionable / -{len(report.resolved_actionable)} resolved")
        print(f"  SLA: {len(report.overdue)} overdue, {len(report.due_soon)} due soon")
        for s in report.sla:
            print(
                f"    {_SLA_ICON[s.status]} {s.item_id:<12} {s.tier:<9} age {s.age_days}d / {s.window_days}d  "
                f"{s.status.value}"
            )
    if args.fail_on_breach and report.overdue:
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ztttdrift",
        description="Drift, exception-lifecycle, and conmon gating on top of Zero Trust maturity assessments.",
    )
    p.add_argument("--version", action="version", version=f"ztttdrift {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    def add_common(sp: argparse.ArgumentParser) -> None:
        sp.add_argument(
            "--target",
            default=DEFAULT_TARGET.value,
            help="global default target stage (traditional|initial|advanced|optimal; default advanced); "
            "per-item target_stage overrides it",
        )
        sp.add_argument("--json", action="store_true", help="emit machine-readable JSON")

    t = sub.add_parser("triage", help="split below-target items into new-drift / lapsed / governed")
    t.add_argument("--results", required=True, help="ztttdrift-input/1.0 assessment JSON")
    t.add_argument("--exceptions", help="risk-acceptance register (JSON/YAML)")
    t.add_argument("--as-of", help="date for expiry math (YYYY-MM-DD; default today)")
    add_common(t)
    t.set_defaults(func=_cmd_triage)

    d = sub.add_parser("drift", help="compare two maturity runs")
    d.add_argument("--baseline", required=True, help="earlier ztttdrift-input/1.0 assessment JSON")
    d.add_argument("--current", required=True, help="later ztttdrift-input/1.0 assessment JSON")
    add_common(d)
    d.set_defaults(func=_cmd_drift)

    g = sub.add_parser("gate", help="exit non-zero if action is required (for CI)")
    g.add_argument("--results", required=True, help="ztttdrift-input/1.0 assessment JSON")
    g.add_argument("--exceptions", help="risk-acceptance register (JSON/YAML)")
    g.add_argument("--baseline", help="optional earlier run; regressions below target also fail the gate")
    g.add_argument("--as-of", help="date for expiry math (YYYY-MM-DD; default today)")
    add_common(g)
    g.set_defaults(func=_cmd_gate)

    cr = sub.add_parser("conmon-record", help="append a run's triage to the continuous-monitoring history ledger")
    cr.add_argument("--results", required=True, help="ztttdrift-input/1.0 assessment JSON")
    cr.add_argument("--exceptions", help="risk-acceptance register (JSON/YAML)")
    cr.add_argument("--history", required=True, help="history ledger file (JSON Lines; created if absent)")
    cr.add_argument("--as-of", help="date for expiry math (YYYY-MM-DD; default today)")
    add_common(cr)
    cr.set_defaults(func=_cmd_conmon_record)

    rep = sub.add_parser("conmon-report", help="emit a periodic ConMon report (pillar trend + SLA aging)")
    rep.add_argument("--history", required=True, help="history ledger file (JSON Lines)")
    rep.add_argument("--as-of", help="date for SLA/aging math (YYYY-MM-DD; default today)")
    rep.add_argument(
        "--sla-windows", help="JSON file of {tier: days} SLA windows (default High 30 / Moderate 90 / Low 180)"
    )
    rep.add_argument("--fail-on-breach", action="store_true", help="exit 1 if any gap is past its SLA window")
    rep.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    rep.set_defaults(func=_cmd_conmon_report)
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ParseError as exc:
        print(f"ztttdrift: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
