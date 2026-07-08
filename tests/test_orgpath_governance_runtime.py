"""Behavioral tests for the OrgPath Governance Runtime (UIAO_163 / UIAO_174).

Covers the runnable governance loop in
:mod:`uiao.governance.orgpath_runtime` — snapshot deserialization, the
``govern()`` pass (detection-only and canon-adapter modes), governance
telemetry emission, the halt-on-critical escalation path, and the
``uiao orgtree govern`` CLI surface.

The runtime is transport-free here: every ``apply()`` is write-free, so
``--no-dry-run`` plans operations but dispatches nothing. That keeps these
tests fully offline.
"""

from __future__ import annotations

import itertools
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from uiao.cli.app import app
from uiao.governance.orgpath_runtime import (
    EVENT_DRIFT_DETECTED,
    EVENT_ESCALATION_TRIGGERED,
    EVENT_SNAPSHOT_CREATED,
    GovernanceReport,
    OrgPathGovernanceRuntime,
    SnapshotError,
    snapshot_from_dict,
)

runner = CliRunner()


# A principal whose every enumerated facet is valid, whose required typed
# facet (hire_date) passes its pattern, and whose derived OrgPath (ADR-127)
# equals the recomputation from the hierarchy facets → no P1/P2 findings.
_CLEAN_ATTRS = {
    "extensionAttribute1": "NCR",
    "extensionAttribute2": "IT",
    "extensionAttribute3": "CyberOps",
    "extensionAttribute4": "Analyst",
    "extensionAttribute5": "CC-4100",
    "extensionAttribute6": "Employee",
    "extensionAttribute7": "2020-01-15",  # hire_date (typed, required)
    "extensionAttribute9": "Secret",
    "extensionAttribute10": "Standard",
    "extensionAttribute15": "Region=NCR|Department=IT|Division=CyberOps|",  # derived path, in sync
}


def _attrs(**overrides: str) -> dict[str, str]:
    merged = dict(_CLEAN_ATTRS)
    merged.update(overrides)
    return merged


def _snapshot(principals: list[dict]) -> object:
    return snapshot_from_dict(
        {
            "generated_at": "2026-06-02T00:00:00+00:00",
            "principals": principals,
        }
    )


def _deterministic_runtime(**kwargs: object) -> OrgPathGovernanceRuntime:
    counter = itertools.count()
    return OrgPathGovernanceRuntime(
        id_factory=lambda: f"ev-{next(counter)}",
        clock=lambda: "2026-06-02T00:00:00+00:00",
        **kwargs,  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# snapshot_from_dict
# ---------------------------------------------------------------------------


def test_snapshot_from_dict_parses_all_collections() -> None:
    snap = snapshot_from_dict(
        {
            "generated_at": "2026-06-02T00:00:00+00:00",
            "principals": [{"principal_id": "u1", "attributes": _CLEAN_ATTRS}],
            "groups": [{"name": "OrgTree-IT", "membership_rule": "x"}],
            "admin_units": [{"name": "AU-IT", "membership_rule": "y"}],
            "policy_targets": [{"assignment_id": "a1", "policy_definition_id": "p1"}],
        }
    )
    assert snap.generated_at == "2026-06-02T00:00:00+00:00"
    assert len(snap.principals) == 1
    assert snap.principals[0].principal_type == "user"  # defaulted
    assert len(snap.groups) == 1
    assert len(snap.admin_units) == 1
    assert len(snap.policy_targets) == 1


def test_snapshot_from_dict_defaults_generated_at() -> None:
    snap = snapshot_from_dict({"principals": []})
    assert snap.generated_at  # non-empty ISO timestamp


def test_snapshot_from_dict_rejects_non_mapping() -> None:
    with pytest.raises(SnapshotError):
        snapshot_from_dict([])  # type: ignore[arg-type]


def test_snapshot_from_dict_rejects_malformed_principal() -> None:
    # Missing the required principal_id key.
    with pytest.raises(SnapshotError):
        snapshot_from_dict({"principals": [{"attributes": {}}]})


# ---------------------------------------------------------------------------
# govern() — detection-only mode
# ---------------------------------------------------------------------------


def test_govern_emits_snapshot_created_event() -> None:
    snap = _snapshot([{"principal_id": "u1", "attributes": _CLEAN_ATTRS}])
    report = _deterministic_runtime().govern(snap)
    created = report.events_of_type(EVENT_SNAPSHOT_CREATED)
    assert len(created) == 1
    assert created[0].payload["principals"] == 1
    assert created[0].snapshot_id == report.snapshot_id


def test_govern_clean_principal_has_no_p1_or_p2_for_that_principal() -> None:
    # Orphan (P3) findings are expected for unused enumeration values, but a
    # fully-valid principal must not contribute any P1/P2 facet finding.
    snap = _snapshot([{"principal_id": "u1", "attributes": _CLEAN_ATTRS}])
    report = _deterministic_runtime().govern(snap)
    principal_findings = [f for f in report.scan.findings if f.target.endswith("u1")]
    assert principal_findings == []
    assert not report.halted


def test_govern_classifies_value_drift_as_drift_detected_event() -> None:
    snap = _snapshot([{"principal_id": "u1", "attributes": _attrs(extensionAttribute2="Marketing")}])
    report = _deterministic_runtime().govern(snap)
    value_events = [
        e
        for e in report.events_of_type(EVENT_DRIFT_DETECTED)
        if e.payload["facet"] == "department" and e.payload["drift_category"] == "Value"
    ]
    assert len(value_events) == 1
    assert value_events[0].payload["severity"] == "P2"
    assert "Marketing" in value_events[0].payload["reason"]


def test_govern_emits_one_drift_detected_event_per_finding() -> None:
    snap = _snapshot([{"principal_id": "u1", "attributes": _CLEAN_ATTRS}])
    report = _deterministic_runtime().govern(snap)
    assert len(report.events_of_type(EVENT_DRIFT_DETECTED)) == report.drift_count


def test_govern_event_ids_are_deterministic_under_injected_factory() -> None:
    snap = _snapshot([{"principal_id": "u1", "attributes": _CLEAN_ATTRS}])
    report = _deterministic_runtime().govern(snap)
    ids = [e.event_id for e in report.events]
    assert ids == [f"ev-{i}" for i in range(len(ids))]


# ---------------------------------------------------------------------------
# govern() — halt-on-critical escalation
# ---------------------------------------------------------------------------


def test_govern_halts_and_escalates_on_p1_finding() -> None:
    # A typed-facet (hire_date) pattern violation is Format drift → P1.
    snap = _snapshot([{"principal_id": "u1", "attributes": _attrs(extensionAttribute7="not-a-date")}])
    report = OrgPathGovernanceRuntime.with_canon_adapters().govern(snap, dry_run=False)
    assert report.halted
    assert report.severity_counts.get("P1", 0) >= 1
    escalations = report.events_of_type(EVENT_ESCALATION_TRIGGERED)
    assert len(escalations) == 1
    # Halt suppresses every write even with dry_run=False.
    assert report.remediated_count == 0


# ---------------------------------------------------------------------------
# govern() — canon adapter mode
# ---------------------------------------------------------------------------


def test_with_canon_adapters_plans_but_does_not_write_in_dry_run() -> None:
    snap = _snapshot([{"principal_id": "u1", "attributes": _CLEAN_ATTRS}])
    report = OrgPathGovernanceRuntime.with_canon_adapters().govern(snap)
    assert set(report.scan.apply_results) == {"dynamic_groups", "admin_units", "policy_targeting"}
    assert report.planned_count > 0
    assert report.remediated_count == 0  # transport-free + dry-run


def test_detection_only_runtime_plans_nothing() -> None:
    snap = _snapshot([{"principal_id": "u1", "attributes": _CLEAN_ATTRS}])
    report = OrgPathGovernanceRuntime().govern(snap)
    assert report.planned_count == 0
    assert report.scan.apply_results == {}


# ---------------------------------------------------------------------------
# GovernanceReport.to_dict
# ---------------------------------------------------------------------------


def test_report_to_dict_is_json_serializable_and_structured() -> None:
    snap = _snapshot([{"principal_id": "u1", "attributes": _attrs(extensionAttribute2="Marketing")}])
    report = OrgPathGovernanceRuntime.with_canon_adapters().govern(snap)
    blob = json.dumps(report.to_dict())  # must not raise
    data = json.loads(blob)
    assert data["snapshot_id"] == report.snapshot_id
    assert data["drift_count"] == report.drift_count
    assert "events" in data and len(data["events"]) == len(report.events)
    assert "apply_results" in data
    assert isinstance(report, GovernanceReport)


# ---------------------------------------------------------------------------
# CLI — uiao orgtree govern
# ---------------------------------------------------------------------------


def _write_snapshot(tmp_path: Path, principals: list[dict]) -> Path:
    path = tmp_path / "snapshot.json"
    path.write_text(
        json.dumps({"generated_at": "2026-06-02T00:00:00+00:00", "principals": principals}),
        encoding="utf-8",
    )
    return path


def test_cli_govern_happy_path_writes_report(tmp_path: Path) -> None:
    snap_path = _write_snapshot(tmp_path, [{"principal_id": "u1", "attributes": _CLEAN_ATTRS}])
    out_path = tmp_path / "report.json"
    result = runner.invoke(
        app,
        ["orgtree", "govern", str(snap_path), "--out", str(out_path)],
    )
    assert result.exit_code == 0, f"stdout={result.stdout}"
    assert "OrgPath governance pass" in result.stdout
    assert out_path.exists()
    report = json.loads(out_path.read_text(encoding="utf-8"))
    assert "drift_count" in report and "events" in report


def test_cli_govern_detection_only_flag(tmp_path: Path) -> None:
    snap_path = _write_snapshot(tmp_path, [{"principal_id": "u1", "attributes": _CLEAN_ATTRS}])
    result = runner.invoke(app, ["orgtree", "govern", str(snap_path), "--detection-only"])
    assert result.exit_code == 0, f"stdout={result.stdout}"
    assert "detection-only" in result.stdout


def test_cli_govern_missing_file_exits_1() -> None:
    result = runner.invoke(app, ["orgtree", "govern", "/nonexistent/snapshot.json"])
    assert result.exit_code == 1
    assert "not found" in result.stdout


def test_cli_govern_invalid_json_exits_1(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid json", encoding="utf-8")
    result = runner.invoke(app, ["orgtree", "govern", str(bad)])
    assert result.exit_code == 1
    assert "Invalid snapshot" in result.stdout
