"""Tests for the reporting-egress actuator (ADR-128).

Covers the ADR-128 invariants: dry-run default, the L3 approval gate, the
"unconfigured endpoint is blocked" rule, malformed-artifact refusal, and the
single transmitting path. Includes happy-path and failure-mode cases per the
repo's CLI/feature test discipline.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from uiao.cli.report import report_app
from uiao.reporting_egress import (
    Approval,
    Destination,
    Disposition,
    Submission,
    submit,
)
from uiao.reporting_egress.drivers import EgressDriver

runner = CliRunner()


@pytest.fixture()
def artifact(tmp_path: Path) -> Path:
    p = tmp_path / "sbom.json"
    p.write_text('{"bomFormat": "CycloneDX"}', encoding="utf-8")
    return p


def _submission(artifact: Path, artifact_type: str = "cyclonedx-sbom") -> Submission:
    return Submission(
        destination=Destination.CISA_SBOM,
        artifact_path=artifact,
        artifact_type=artifact_type,
    )


def _approval() -> Approval:
    return Approval(approver="jane.isso", approved_at="2026-07-09T10:48:00+00:00", operation="submit:cisa-sbom")


class _ConfiguredFakeDriver(EgressDriver):
    """A driver with a wired endpoint — used only to exercise the send path."""

    destination = Destination.CISA_SBOM
    label = "Fake configured"
    accepts = ("cyclonedx-sbom", "openvex")
    configured = True

    def __init__(self) -> None:
        self.calls = 0

    def transmit(self, submission: Submission) -> dict:
        self.calls += 1
        return {"status": "accepted", "id": "RCPT-0001"}


# --- Dry-run (default) -------------------------------------------------------


def test_dry_run_is_default_and_plans_only(artifact: Path) -> None:
    result = submit(_submission(artifact))
    assert result.disposition is Disposition.PLANNED
    assert not result.transmitted
    assert result.problems == ()


def test_dry_run_surfaces_validation_problems(artifact: Path) -> None:
    result = submit(_submission(artifact, artifact_type="wrong-type"))
    assert result.disposition is Disposition.PLANNED  # still a dry-run
    assert any("not accepted" in p for p in result.problems)


# --- L3 gate -----------------------------------------------------------------


def test_live_without_approval_is_blocked(artifact: Path) -> None:
    result = submit(_submission(artifact), live=True, approval=None)
    assert result.disposition is Disposition.BLOCKED
    assert "approval required" in result.reason.lower()
    assert not result.transmitted


def test_live_with_invalid_approval_is_blocked(artifact: Path) -> None:
    bad = Approval(approver="", approved_at="", operation="submit:cisa-sbom")
    result = submit(_submission(artifact), live=True, approval=bad)
    assert result.disposition is Disposition.BLOCKED


# --- Unconfigured endpoint ---------------------------------------------------


def test_live_approved_but_unconfigured_is_blocked(artifact: Path) -> None:
    # Default registered driver is unconfigured -> must not transmit.
    result = submit(_submission(artifact), live=True, approval=_approval())
    assert result.disposition is Disposition.BLOCKED
    assert "not configured" in result.reason.lower()
    assert not result.transmitted


# --- Malformed artifact ------------------------------------------------------


def test_live_approved_missing_artifact_is_blocked(tmp_path: Path) -> None:
    missing = Submission(
        destination=Destination.CISA_SBOM,
        artifact_path=tmp_path / "does-not-exist.json",
        artifact_type="cyclonedx-sbom",
    )
    result = submit(missing, live=True, approval=_approval(), driver=_ConfiguredFakeDriver())
    assert result.disposition is Disposition.BLOCKED
    assert any("not found" in p for p in result.problems)


# --- The single transmitting path -------------------------------------------


def test_live_approved_configured_transmits(artifact: Path) -> None:
    drv = _ConfiguredFakeDriver()
    result = submit(_submission(artifact), live=True, approval=_approval(), driver=drv)
    assert result.disposition is Disposition.SUBMITTED
    assert result.transmitted
    assert result.receipt == {"status": "accepted", "id": "RCPT-0001"}
    assert result.approver == "jane.isso"
    assert drv.calls == 1


def test_no_transmit_without_live_even_with_approval(artifact: Path) -> None:
    drv = _ConfiguredFakeDriver()
    # live defaults to False: approval alone must never transmit.
    result = submit(_submission(artifact), approval=_approval(), driver=drv)
    assert result.disposition is Disposition.PLANNED
    assert drv.calls == 0


# --- CLI ---------------------------------------------------------------------


def test_cli_list_destinations() -> None:
    res = runner.invoke(report_app, ["list-destinations"])
    assert res.exit_code == 0
    assert "cisa-sbom" in res.stdout
    assert "cyberscope" in res.stdout


def test_cli_submit_dry_run_ok(artifact: Path) -> None:
    res = runner.invoke(
        report_app,
        ["submit", "-d", "cisa-sbom", "-a", str(artifact), "-t", "cyclonedx-sbom"],
    )
    assert res.exit_code == 0
    assert "planned" in res.stdout


def test_cli_submit_live_without_approver_exits_nonzero(artifact: Path) -> None:
    res = runner.invoke(
        report_app,
        ["submit", "-d", "cisa-sbom", "-a", str(artifact), "-t", "cyclonedx-sbom", "--live"],
    )
    assert res.exit_code == 1
    assert "blocked" in res.stdout.lower()


def test_cli_submit_unknown_destination_exits_2(artifact: Path) -> None:
    res = runner.invoke(
        report_app,
        ["submit", "-d", "nope", "-a", str(artifact), "-t", "cyclonedx-sbom"],
    )
    assert res.exit_code == 2
