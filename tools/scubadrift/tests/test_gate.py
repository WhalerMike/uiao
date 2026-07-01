"""Gate: pass/fail + exit code for a conmon pipeline."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from scubadrift import evaluate_gate, load_exceptions, load_run

FIXTURES = Path(__file__).parent / "fixtures"
AS_OF = date(2026, 7, 1)


def test_gate_fails_on_actionable_drift() -> None:
    run = load_run(FIXTURES / "run_current.json")
    acc = load_exceptions(FIXTURES / "exceptions.json")
    result = evaluate_gate(run, acc, as_of=AS_OF)
    assert result.passed is False
    assert result.exit_code == 1
    assert "FAIL" in result.headline()


def test_gate_passes_when_only_governed_exceptions_remain() -> None:
    from scubadrift import RiskAcceptance

    run = load_run(FIXTURES / "run_current.json")
    # In-date acceptances for every current failure => nothing actionable.
    acc = [
        RiskAcceptance(pid, "j", "isso", date(2026, 6, 1), date(2026, 12, 31), f"T-{pid}")
        for pid in ("MS.AAD.1.1v1", "MS.AAD.3.1v1", "MS.AAD.5.4v1", "MS.EXO.1.1v1")
    ]
    result = evaluate_gate(run, acc, as_of=AS_OF)
    assert result.passed is True
    assert result.exit_code == 0
    assert "PASS" in result.headline()


def test_gate_with_no_exceptions_fails_on_any_failure() -> None:
    run = load_run(FIXTURES / "run_current.json")
    result = evaluate_gate(run, [], as_of=AS_OF)
    assert result.passed is False
    # All four failures are now actionable new drift.
    assert result.report.summary()["actionable_new_drift"] == 4
