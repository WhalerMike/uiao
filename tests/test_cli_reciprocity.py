"""Tests for ``uiao reciprocity`` CLI sub-app (WS-A4).

Covers:
- --help exits 0 for all three commands
- onboard-agency without WS-A2 merged returns exit code 3
- onboard-agency --dry-run with all required args returns exit 0 (mocked emitter)
- list-records against empty dir returns exit 0 with "no records found"
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any
from unittest import mock

import pytest
from typer.testing import CliRunner

from uiao.cli.app import app

runner = CliRunner()

# ---------------------------------------------------------------------------
# --help smoke tests
# ---------------------------------------------------------------------------


def test_reciprocity_help_exits_zero() -> None:
    result = runner.invoke(app, ["reciprocity", "--help"])
    assert result.exit_code == 0, result.stdout


def test_onboard_agency_help_exits_zero() -> None:
    result = runner.invoke(app, ["reciprocity", "onboard-agency", "--help"])
    assert result.exit_code == 0, result.stdout
    # Verify the runnable example block is present
    assert "OPM-HRIT-2026-001" in result.stdout
    assert "--controlling-ato" in result.stdout


def test_list_records_help_exits_zero() -> None:
    result = runner.invoke(app, ["reciprocity", "list-records", "--help"])
    assert result.exit_code == 0, result.stdout
    assert "--records-dir" in result.stdout


def test_verify_help_exits_zero() -> None:
    result = runner.invoke(app, ["reciprocity", "verify", "--help"])
    assert result.exit_code == 0, result.stdout
    assert "--record" in result.stdout


# ---------------------------------------------------------------------------
# onboard-agency without WS-A2 → exit code 3
# ---------------------------------------------------------------------------

_REQUIRED_ONBOARD_ARGS = [
    "reciprocity",
    "onboard-agency",
    "--controlling-ato",
    "OPM-HRIT-2026-001",
    "--consuming-agency",
    "TREAS",
    "--legal-basis",
    "interagency-mou",
    "--configuration-latitude-ref",
    "ssp-2026-latitude-baseline-v1",
]


def test_onboard_agency_missing_ws_a2_returns_exit_3() -> None:
    """When uiao.oscal.reciprocity_record is not importable, exit code must be 3."""
    with mock.patch.dict(sys.modules, {"uiao.oscal.reciprocity_record": None}):
        result = runner.invoke(app, _REQUIRED_ONBOARD_ARGS)
    assert result.exit_code == 3, result.stdout
    assert "WS-A2" in result.stdout or "Phase 2" in result.stdout


# ---------------------------------------------------------------------------
# onboard-agency --dry-run with mocked emitter → exit 0 + JSON output
# ---------------------------------------------------------------------------


def _make_fake_emitter_module() -> ModuleType:
    """Return a fake uiao.oscal.reciprocity_record module with emit stub."""

    def emit_reciprocity_record(**kwargs: Any) -> dict:
        return {"_mock": True, **kwargs}

    mod = ModuleType("uiao.oscal.reciprocity_record")
    mod.emit_reciprocity_record = emit_reciprocity_record  # type: ignore[attr-defined]
    return mod


def test_onboard_agency_dry_run_exits_zero_with_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    """--dry-run prints a JSON-shaped record and exits 0 when emitter is mocked."""
    fake_mod = _make_fake_emitter_module()
    monkeypatch.setitem(sys.modules, "uiao.oscal.reciprocity_record", fake_mod)

    result = runner.invoke(app, [*_REQUIRED_ONBOARD_ARGS, "--dry-run"])
    assert result.exit_code == 0, result.stdout
    # The output must contain something that looks like JSON
    assert "{" in result.stdout
    assert "controlling_ato" in result.stdout or "OPM-HRIT-2026-001" in result.stdout


def test_onboard_agency_dry_run_prints_valid_json(monkeypatch: pytest.MonkeyPatch) -> None:
    """--dry-run output contains parseable JSON with expected fields."""
    fake_mod = _make_fake_emitter_module()
    monkeypatch.setitem(sys.modules, "uiao.oscal.reciprocity_record", fake_mod)

    result = runner.invoke(app, [*_REQUIRED_ONBOARD_ARGS, "--dry-run"])
    assert result.exit_code == 0, result.stdout

    # Extract the JSON portion from output (everything from the first '{')
    json_start = result.stdout.find("{")
    assert json_start != -1, "No JSON object found in output"
    payload = json.loads(result.stdout[json_start:])
    assert payload["controlling_ato_id"] == "OPM-HRIT-2026-001"
    assert payload["consuming_agency_code"] == "TREAS"
    assert payload["legal_basis"] == "interagency-mou"


# ---------------------------------------------------------------------------
# list-records against empty / non-existent dir → exit 0 + "no records found"
# ---------------------------------------------------------------------------


def test_list_records_empty_dir_exits_zero(tmp_path: Path) -> None:
    result = runner.invoke(app, ["reciprocity", "list-records", "--records-dir", str(tmp_path)])
    assert result.exit_code == 0, result.stdout
    assert "no records found" in result.stdout


def test_list_records_nonexistent_dir_exits_zero(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"
    result = runner.invoke(app, ["reciprocity", "list-records", "--records-dir", str(missing)])
    assert result.exit_code == 0, result.stdout
    assert "no records found" in result.stdout


# ---------------------------------------------------------------------------
# list-records with real records on disk
# ---------------------------------------------------------------------------


def test_list_records_shows_records(tmp_path: Path) -> None:
    from datetime import datetime, timedelta, timezone

    now = datetime.now(tz=timezone.utc)
    record = {
        "controlling_ato_id": "OPM-HRIT-2026-001",
        "consuming_agency_code": "TREAS",
        "effective_at": now.isoformat(),
        "expires_at": (now + timedelta(days=365)).isoformat(),
    }
    agency_dir = tmp_path / "TREAS"
    agency_dir.mkdir()
    (agency_dir / "reciprocity-record.json").write_text(json.dumps(record), encoding="utf-8")

    # Use --json to get machine-readable output (avoids rich table column truncation)
    result = runner.invoke(app, ["reciprocity", "list-records", "--records-dir", str(tmp_path), "--json"])
    assert result.exit_code == 0, result.stdout
    rows = json.loads(result.stdout)
    assert len(rows) == 1
    assert rows[0]["controlling_ato_id"] == "OPM-HRIT-2026-001"
    assert rows[0]["consuming_agency_code"] == "TREAS"
    assert rows[0]["status"] == "Active"


def test_list_records_json_flag(tmp_path: Path) -> None:
    from datetime import datetime, timedelta, timezone

    now = datetime.now(tz=timezone.utc)
    record = {
        "controlling_ato_id": "OPM-HRIT-2026-001",
        "consuming_agency_code": "IRS",
        "effective_at": now.isoformat(),
        "expires_at": (now - timedelta(days=1)).isoformat(),  # expired
    }
    agency_dir = tmp_path / "IRS"
    agency_dir.mkdir()
    (agency_dir / "reciprocity-record.json").write_text(json.dumps(record), encoding="utf-8")

    result = runner.invoke(app, ["reciprocity", "list-records", "--records-dir", str(tmp_path), "--json"])
    assert result.exit_code == 0, result.stdout
    rows = json.loads(result.stdout)
    assert len(rows) == 1
    assert rows[0]["status"] == "Expired"
    assert rows[0]["consuming_agency_code"] == "IRS"


# ---------------------------------------------------------------------------
# verify without WS-A2 → exit code 3
# ---------------------------------------------------------------------------


def test_verify_missing_ws_a2_returns_exit_3(tmp_path: Path) -> None:
    record_file = tmp_path / "reciprocity-record.json"
    record_file.write_text(json.dumps({"foo": "bar"}), encoding="utf-8")

    with mock.patch.dict(sys.modules, {"uiao.oscal.reciprocity_record": None}):
        result = runner.invoke(app, ["reciprocity", "verify", "--record", str(record_file)])
    assert result.exit_code == 3, result.stdout
    assert "WS-A2" in result.stdout or "Phase 2" in result.stdout
