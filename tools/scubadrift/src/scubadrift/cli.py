"""ScubaDrift command-line interface.

Three subcommands:

* ``scubadrift triage``  — split failures into new-drift / lapsed / governed.
* ``scubadrift drift``   — compare two ScubaGear runs (regressions, fixes).
* ``scubadrift gate``    — triage + exit non-zero if action is required (CI).

``--as-of`` pins the date used for exception-expiry math (default: today), so
CI runs are reproducible and testable.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from . import __version__
from .conmon import DEFAULT_SLA_WINDOWS, History, SlaStatus, build_report, record_run
from .drift import diff_runs
from .gate import evaluate_gate
from .parser import ParseError, load_exceptions, load_run
from .triage import Disposition, triage


def _as_of(value: str | None) -> date:
    if not value:
        return date.today()
    try:
        return date.fromisoformat(value)
    except ValueError:
        print(f"scubadrift: --as-of must be YYYY-MM-DD, got {value!r}", file=sys.stderr)
        raise SystemExit(2)


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


def _triage_text(report) -> str:  # noqa: ANN001 - internal formatter
    s = report.summary()
    lines = [
        f"ScubaDrift triage (as of {report.as_of.isoformat()})",
        f"  failing: {s['failing_total']}  |  actionable: {s['actionable_total']}  "
        f"(new drift {s['actionable_new_drift']}, lapsed {s['lapsed_acceptance']})  |  "
        f"governed: {s['governed_exception']}",
    ]
    for t in report.actionable:
        lines.append(f"  {_ICON[t.disposition]} {t.policy.policy_id:<16} {t.disposition.value:<22} {t.reason}")
    for t in report.governed:
        lines.append(f"  {_ICON[t.disposition]} {t.policy.policy_id:<16} {t.disposition.value:<22} {t.reason}")
    if report.retirable:
        ids = ", ".join(a.policy_id for a in report.retirable)
        lines.append(f"  retirable acceptances (policy now passing): {ids}")
    return "\n".join(lines)


def _cmd_triage(args: argparse.Namespace) -> int:
    run = load_run(args.results)
    acc = load_exceptions(args.exceptions) if args.exceptions else []
    report = triage(run, acc, as_of=_as_of(args.as_of), include_warnings=args.include_warnings)
    _emit(report.to_dict(), args.json, _triage_text(report))
    return 0


def _cmd_drift(args: argparse.Namespace) -> int:
    base = load_run(args.baseline)
    curr = load_run(args.current)
    report = diff_runs(base, curr, include_warnings=args.include_warnings)
    s = report.summary()
    text = [
        "ScubaDrift run-to-run diff",
        f"  regressions (new failures): {s['new_failure']}  |  resolved: {s['resolved']}  |  "
        f"persistent: {s['persistent_failure']}",
        f"  baseline churn: +{s['new_policy']} new / -{s['removed_policy']} removed",
    ]
    for i in report.regressions:
        text.append(f"  ! {i.policy_id:<16} {i.baseline_result} -> {i.current_result}")
    _emit(report.to_dict(), args.json, "\n".join(text))
    return 0


def _cmd_gate(args: argparse.Namespace) -> int:
    run = load_run(args.results)
    acc = load_exceptions(args.exceptions) if args.exceptions else []
    result = evaluate_gate(run, acc, as_of=_as_of(args.as_of), include_warnings=args.include_warnings)
    if args.json:
        print(json.dumps({"passed": result.passed, **result.report.to_dict()}, indent=2, sort_keys=True))
    else:
        print(result.headline())
        for t in result.report.actionable:
            print(f"  {_ICON[t.disposition]} {t.policy.policy_id:<16} {t.reason}")
    return result.exit_code


def _load_windows(path: str | None) -> dict:
    if not path:
        return dict(DEFAULT_SLA_WINDOWS)
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"scubadrift: cannot read --sla-windows {path!r}: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    return {str(k).lower(): int(v) for k, v in data.items()}


def _cmd_conmon_record(args: argparse.Namespace) -> int:
    run = load_run(args.results)
    acc = load_exceptions(args.exceptions) if args.exceptions else []
    history = History.load(args.history)
    entry = record_run(run, acc, as_of=_as_of(args.as_of), include_warnings=args.include_warnings)
    history.append(entry)
    history.save(args.history)
    s = entry.counts
    print(
        f"recorded {entry.as_of.isoformat()} ({entry.product or 'run'}) -> {args.history}  "
        f"[{len(history.entries)} entr{'y' if len(history.entries) == 1 else 'ies'}]"
    )
    print(f"  failing {s['failing_total']} | actionable {s['actionable_total']} | governed {s['governed_exception']}")
    return 0


_SLA_ICON = {SlaStatus.OVERDUE: "!", SlaStatus.DUE_SOON: "*", SlaStatus.ON_TRACK: "-"}


def _cmd_conmon_report(args: argparse.Namespace) -> int:
    history = History.load(args.history)
    if not history.entries:
        print(f"scubadrift: history {args.history!r} is empty — record a run first", file=sys.stderr)
        return 2
    report = build_report(history, as_of=_as_of(args.as_of), windows=_load_windows(args.sla_windows))
    if args.json:
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    else:
        start = report.period_start.isoformat() if report.period_start else "(first period)"
        p = report.posture
        print(f"ScubaDrift continuous-monitoring report  {start} -> {report.period_end.isoformat()}")
        print(
            f"  posture: failing {p['failing_total']} | actionable {p['actionable_total']} | governed {p['governed_exception']}"
        )
        print(f"  trend: +{len(report.new_actionable)} new actionable / -{len(report.resolved_actionable)} resolved")
        print(f"  SLA: {len(report.overdue)} overdue, {len(report.due_soon)} due soon")
        for s in report.sla:
            print(
                f"    {_SLA_ICON[s.status]} {s.policy_id:<16} {s.tier:<9} age {s.age_days}d / {s.window_days}d  {s.status.value}"
            )
    if args.fail_on_breach and report.overdue:
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="scubadrift",
        description="Drift, exception-lifecycle, and conmon gating on top of CISA ScubaGear output.",
    )
    p.add_argument("--version", action="version", version=f"scubadrift {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    def add_common(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--include-warnings", action="store_true", help="treat Warning verdicts as failures")
        sp.add_argument("--json", action="store_true", help="emit machine-readable JSON")

    t = sub.add_parser("triage", help="split failures into new-drift / lapsed / governed")
    t.add_argument("--results", required=True, help="ScubaGear results JSON")
    t.add_argument("--exceptions", help="risk-acceptance register (JSON/YAML)")
    t.add_argument("--as-of", help="date for expiry math (YYYY-MM-DD; default today)")
    add_common(t)
    t.set_defaults(func=_cmd_triage)

    d = sub.add_parser("drift", help="compare two ScubaGear runs")
    d.add_argument("--baseline", required=True, help="earlier ScubaGear results JSON")
    d.add_argument("--current", required=True, help="later ScubaGear results JSON")
    add_common(d)
    d.set_defaults(func=_cmd_drift)

    g = sub.add_parser("gate", help="exit non-zero if action is required (for CI)")
    g.add_argument("--results", required=True, help="ScubaGear results JSON")
    g.add_argument("--exceptions", help="risk-acceptance register (JSON/YAML)")
    g.add_argument("--as-of", help="date for expiry math (YYYY-MM-DD; default today)")
    add_common(g)
    g.set_defaults(func=_cmd_gate)

    cr = sub.add_parser("conmon-record", help="append a run's triage to the continuous-monitoring history ledger")
    cr.add_argument("--results", required=True, help="ScubaGear results JSON")
    cr.add_argument("--exceptions", help="risk-acceptance register (JSON/YAML)")
    cr.add_argument("--history", required=True, help="history ledger file (JSON Lines; created if absent)")
    cr.add_argument("--as-of", help="date for expiry math (YYYY-MM-DD; default today)")
    add_common(cr)
    cr.set_defaults(func=_cmd_conmon_record)

    rep = sub.add_parser("conmon-report", help="emit a periodic ConMon report (trend + SLA aging) from the ledger")
    rep.add_argument("--history", required=True, help="history ledger file (JSON Lines)")
    rep.add_argument("--as-of", help="date for SLA/aging math (YYYY-MM-DD; default today)")
    rep.add_argument(
        "--sla-windows", help="JSON file of {tier: days} SLA windows (default High 30 / Moderate 90 / Low 180)"
    )
    rep.add_argument("--fail-on-breach", action="store_true", help="exit 1 if any finding is past its SLA window")
    rep.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    rep.set_defaults(func=_cmd_conmon_report)
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ParseError as exc:
        print(f"scubadrift: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
