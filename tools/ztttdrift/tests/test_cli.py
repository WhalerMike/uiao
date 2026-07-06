"""CLI: exit codes, JSON output, and the --as-of / --target contracts."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ztttdrift.cli import main

FIXTURES = Path(__file__).parent / "fixtures"
RESULTS = str(FIXTURES / "run_current.json")
BASELINE = str(FIXTURES / "run_baseline.json")
EXC = str(FIXTURES / "exceptions.json")


def test_gate_exit_code_nonzero(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["gate", "--results", RESULTS, "--exceptions", EXC, "--as-of", "2026-07-01"])
    assert rc == 1
    assert "FAIL" in capsys.readouterr().out


def test_gate_json_output(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["gate", "--results", RESULTS, "--exceptions", EXC, "--as-of", "2026-07-01", "--json"])
    assert rc == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["passed"] is False
    assert payload["summary"]["actionable_total"] == 3


def test_gate_with_baseline_reports_regressions(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(
        ["gate", "--results", RESULTS, "--exceptions", EXC, "--baseline", BASELINE, "--as-of", "2026-07-01", "--json"]
    )
    assert rc == 1
    payload = json.loads(capsys.readouterr().out)
    assert [i["item_id"] for i in payload["regressions_below_target"]] == ["ZT.ID.01"]


def test_triage_always_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["triage", "--results", RESULTS, "--exceptions", EXC, "--as-of", "2026-07-01"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "governed" in out
    assert "target advanced" in out


def test_triage_target_option(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["triage", "--results", RESULTS, "--as-of", "2026-07-01", "--target", "optimal", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["target"] == "optimal"
    assert payload["summary"]["failing_total"] == 7  # everything except the optimal items


def test_bad_target_is_a_usage_error() -> None:
    with pytest.raises(SystemExit) as exc:
        main(["triage", "--results", RESULTS, "--target", "platinum"])
    assert exc.value.code == 2


def test_drift_subcommand(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["drift", "--baseline", BASELINE, "--current", RESULTS, "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["summary"]["regression"] == 2
    assert payload["summary"]["regressions_below_target"] == 1
    assert payload["summary"]["target_change"] == 1


def test_bad_as_of_is_a_usage_error() -> None:
    with pytest.raises(SystemExit):
        main(["gate", "--results", RESULTS, "--as-of", "07/01/2026"])


def test_parse_error_returns_code_2(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    rc = main(["gate", "--results", str(bad)])
    assert rc == 2
    assert "ztttdrift:" in capsys.readouterr().err


def _seed_ledger(tmp_path: Path) -> str:
    ledger = str(tmp_path / "ledger.jsonl")
    assert (
        main(
            ["conmon-record", "--results", BASELINE, "--exceptions", EXC, "--history", ledger, "--as-of", "2026-04-01"]
        )
        == 0
    )
    assert (
        main(["conmon-record", "--results", RESULTS, "--exceptions", EXC, "--history", ledger, "--as-of", "2026-07-01"])
        == 0
    )
    return ledger


def test_conmon_record_and_report(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    ledger = _seed_ledger(tmp_path)
    capsys.readouterr()
    rc = main(["conmon-report", "--history", ledger, "--as-of", "2026-07-01", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["period_start"] == "2026-04-01"
    assert payload["period_end"] == "2026-07-01"
    assert any(s["item_id"] == "ZT.DV.01" for s in payload["sla"]["overdue"])
    assert payload["pillar_trend"]["Applications and Workloads"]["delta"] == 1.0
    assert "NIST 800-53 CA-7" in payload["framework_alignment"]


def test_conmon_report_fail_on_breach(tmp_path: Path) -> None:
    ledger = _seed_ledger(tmp_path)
    assert main(["conmon-report", "--history", ledger, "--as-of", "2026-07-01", "--fail-on-breach"]) == 1


def test_conmon_report_empty_history_is_error(tmp_path: Path) -> None:
    empty = str(tmp_path / "none.jsonl")
    assert main(["conmon-report", "--history", empty]) == 2


def test_conmon_custom_sla_windows_file(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    ledger = _seed_ledger(tmp_path)
    windows = tmp_path / "windows.json"
    windows.write_text('{"high": 365, "moderate": 365, "low": 365}')
    capsys.readouterr()
    # With a generous window nothing is overdue -> --fail-on-breach still passes.
    rc = main(
        [
            "conmon-report",
            "--history",
            ledger,
            "--as-of",
            "2026-07-01",
            "--sla-windows",
            str(windows),
            "--fail-on-breach",
            "--json",
        ]
    )
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["sla"]["overdue"] == []


def test_conmon_bad_sla_windows_file_is_error(tmp_path: Path) -> None:
    ledger = _seed_ledger(tmp_path)
    bad = tmp_path / "w.json"
    bad.write_text("{nope")
    with pytest.raises(SystemExit) as exc:
        main(["conmon-report", "--history", ledger, "--sla-windows", str(bad)])
    assert exc.value.code == 2
