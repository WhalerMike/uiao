"""Tests for `uiao orgtree assess` and the concrete GraphTransport.

The live LDAP read and live Graph dispatch are not exercised (no server/creds);
tests drive the offline --from-export path and the dry-run device-write path,
and verify GraphTransport's URL/auth wiring with a stubbed token + httpx.
"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from uiao.cli.app import app

runner = CliRunner()

_DEVICE = {
    "id": "dev-1",
    "disposition": "ENTRA-DEVICE",
    "department": "Finance",
    "title": "Staff Engineer",
    "physicalDeliveryOfficeName": "Chicago IL",
    "employeeType": "Employee",
    "whenCreated": "2021-06-01T00:00:00Z",
}


def _write(tmp_path: Path, records: list[dict]) -> Path:
    p = tmp_path / "ad.json"
    p.write_text(json.dumps(records), encoding="utf-8")
    return p


def test_assess_from_export_writes_assignments(tmp_path: Path) -> None:
    src = _write(tmp_path, [_DEVICE])
    out = tmp_path / "assignments.json"
    result = runner.invoke(app, ["orgtree", "assess", "--from-export", str(src), "--out", str(out)])
    assert result.exit_code == 0, result.stdout
    assert "OrgPath assessment" in result.stdout
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data[0]["target_id"] == "dev-1"
    assert data[0]["facet_values"]["department"] == "Finance"
    assert data[0]["facet_values"]["region"] == "CENTRAL"  # Chicago


def test_assess_missing_export_exits_1() -> None:
    result = runner.invoke(app, ["orgtree", "assess", "--from-export", "/no/such.json"])
    assert result.exit_code == 1
    assert "not found" in result.stdout


def test_assess_no_source_exits_1() -> None:
    result = runner.invoke(app, ["orgtree", "assess"])
    assert result.exit_code == 1
    assert "--from-export" in result.stdout


def test_assess_bad_target_type_exits_1(tmp_path: Path) -> None:
    src = _write(tmp_path, [_DEVICE])
    result = runner.invoke(app, ["orgtree", "assess", "--from-export", str(src), "--target-type", "group"])
    assert result.exit_code == 1


def test_assess_write_dry_run_plans_device_facets(tmp_path: Path) -> None:
    src = _write(tmp_path, [_DEVICE])
    result = runner.invoke(
        app,
        ["orgtree", "assess", "--from-export", str(src), "--target-type", "device", "--write"],
    )
    assert result.exit_code == 0, result.stdout
    assert "Device writes" in result.stdout
    assert "dry_run=True" in result.stdout
    assert "Sent    : 0" in result.stdout  # dry-run dispatches nothing


def test_assess_write_rejects_user_target(tmp_path: Path) -> None:
    src = _write(tmp_path, [_DEVICE])
    result = runner.invoke(app, ["orgtree", "assess", "--from-export", str(src), "--target-type", "user", "--write"])
    assert result.exit_code == 1


def test_assess_bad_mapping_exits_1(tmp_path: Path) -> None:
    src = _write(tmp_path, [_DEVICE])
    bad = tmp_path / "m.yaml"
    bad.write_text("facets: []\n", encoding="utf-8")
    result = runner.invoke(app, ["orgtree", "assess", "--from-export", str(src), "--mapping", str(bad)])
    assert result.exit_code == 1
    assert "Invalid mapping" in result.stdout


# ---------------------------------------------------------------------------
# GraphTransport
# ---------------------------------------------------------------------------


class _StubTokens:
    def get_auth_headers(self) -> dict[str, str]:
        return {"Authorization": "Bearer stub-token"}


def test_graph_transport_resolves_cloud_base() -> None:
    from uiao.adapters.graph_transport import GraphTransport

    t = GraphTransport(_StubTokens(), cloud="gcc-high", graph_api_version="v1.0")  # type: ignore[arg-type]
    assert t._url("/devices/1") == "https://graph.microsoft.us/v1.0/devices/1"
    # Absolute URLs (e.g. @odata.nextLink) pass through unchanged.
    assert t._url("https://graph.microsoft.us/v1.0/users?$skiptoken=x").startswith("https://")


def test_graph_transport_dispatches_via_httpx(monkeypatch) -> None:
    import httpx

    from uiao.adapters.graph_transport import GraphTransport

    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("authorization")
        return httpx.Response(200, json={"id": "dev-1", "ok": True})

    real_client = httpx.Client

    def fake_client(*args, **kwargs):  # noqa: ANN002, ANN003
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "Client", fake_client)

    t = GraphTransport(_StubTokens(), cloud="commercial")  # type: ignore[arg-type]
    resp = t("PATCH", "/devices/dev-1", {"onPremisesExtensionAttributes": {"extensionAttribute1": "NCR"}})
    assert resp == {"id": "dev-1", "ok": True}
    assert captured["method"] == "PATCH"
    assert captured["url"] == "https://graph.microsoft.com/v1.0/devices/dev-1"
    assert captured["auth"] == "Bearer stub-token"
