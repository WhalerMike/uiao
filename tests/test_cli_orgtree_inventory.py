"""CLI tests for `uiao orgtree inventory` — happy path + failure modes.

The live Graph/ARM reads are not exercised (no creds); tests drive the offline
--devices-export / --machines-export path and the source-map resolution.
"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from uiao.cli.app import app

runner = CliRunner()


def _write(p: Path, obj) -> Path:  # noqa: ANN001
    p.write_text(json.dumps(obj), encoding="utf-8")
    return p


def test_inventory_offline_classifies_and_writes_outputs(tmp_path: Path) -> None:
    devices = _write(
        tmp_path / "devices.json",
        [
            {"id": "dev-absent", "displayName": "WS-1", "onPremisesExtensionAttributes": {}},
            {
                "id": "dev-complete",
                "displayName": "WS-2",
                "onPremisesExtensionAttributes": {f"extensionAttribute{i}": "x" for i in range(1, 11)},
            },
        ],
    )
    machines = _write(
        tmp_path / "machines.json",
        [{"id": "/subs/s/providers/Microsoft.HybridCompute/machines/srv1", "name": "srv1", "tags": {"Region": "NCR"}}],
    )
    snap = tmp_path / "snap.json"
    wl = tmp_path / "wl.json"

    result = runner.invoke(
        app,
        [
            "orgtree",
            "inventory",
            "--devices-export",
            str(devices),
            "--machines-export",
            str(machines),
            "--snapshot-out",
            str(snap),
            "--worklist-out",
            str(wl),
        ],
    )
    assert result.exit_code == 0, result.stdout
    assert "OrgPath inventory" in result.stdout
    assert "Absent (no OrgPath)" in result.stdout

    snapshot = json.loads(snap.read_text(encoding="utf-8"))
    assert len(snapshot["principals"]) == 3
    worklist = json.loads(wl.read_text(encoding="utf-8"))
    assert worklist["summary"]["total"] == 3
    assert worklist["summary"]["absent"] == 1
    assert worklist["summary"]["complete"] == 1
    assert worklist["summary"]["partial"] == 1  # the Arc machine has only Region


def test_inventory_owner_map_resolves_proposal(tmp_path: Path) -> None:
    devices = _write(
        tmp_path / "d.json",
        [
            {
                "id": "dev-1",
                "displayName": "WS-1",
                "onPremisesExtensionAttributes": {f"extensionAttribute{i}": "x" for i in range(2, 11)},
                "registeredOwners": [{"id": "user-9"}],
            }
        ],
    )
    owners = _write(tmp_path / "owners.json", {"user-9": {"region": "NCR"}})
    wl = tmp_path / "wl.json"

    result = runner.invoke(
        app,
        [
            "orgtree",
            "inventory",
            "--devices-export",
            str(devices),
            "--owner-map",
            str(owners),
            "--worklist-out",
            str(wl),
        ],
    )
    assert result.exit_code == 0, result.stdout
    device = json.loads(wl.read_text(encoding="utf-8"))["devices"][0]
    assert device["status"] == "partial"
    assert device["proposed_facets"] == {"region": "NCR"}
    assert device["source"] == "owner-map"


def test_inventory_requires_a_source() -> None:
    result = runner.invoke(app, ["orgtree", "inventory"])
    assert result.exit_code == 1
    assert "at least one source" in result.stdout


def test_inventory_from_arm_requires_subscription() -> None:
    result = runner.invoke(app, ["orgtree", "inventory", "--from-arm"])
    assert result.exit_code == 1
    assert "--subscription" in result.stdout


def test_inventory_missing_export_exits_1(tmp_path: Path) -> None:
    result = runner.invoke(app, ["orgtree", "inventory", "--devices-export", str(tmp_path / "nope.json")])
    assert result.exit_code == 1
    assert "not found" in result.stdout
