"""CLI tests for ``uiao directory`` (ADR-100)."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from uiao.cli.app import app

runner = CliRunner()

SNAPSHOT = {
    "principals": [
        {"principal_id": "alice@uiao.gov", "principal_type": "user", "attributes": {"extensionAttribute1": "NCR"}},
    ]
}


def _write_snapshot(tmp_path: Path) -> Path:
    path = tmp_path / "snapshot.json"
    path.write_text(json.dumps(SNAPSHOT), encoding="utf-8")
    return path


def test_tree_emits_ldif(tmp_path: Path) -> None:
    result = runner.invoke(app, ["directory", "tree", "--snapshot", str(_write_snapshot(tmp_path))])
    assert result.exit_code == 0, result.output
    assert "dn: cn=alice-uiao.gov,ou=people,dc=agd,dc=uiao,dc=gov" in result.output
    assert "uiaoOrgPathRegion: NCR" in result.output


def test_tree_empty_snapshot_still_projects_containers() -> None:
    result = runner.invoke(app, ["directory", "tree"])
    assert result.exit_code == 0, result.output
    assert "dn: dc=agd,dc=uiao,dc=gov" in result.output


def test_tree_missing_snapshot_fails(tmp_path: Path) -> None:
    result = runner.invoke(app, ["directory", "tree", "--snapshot", str(tmp_path / "nope.json")])
    assert result.exit_code == 1
    assert "not found" in result.output.lower()


def test_tree_invalid_json_fails(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    result = runner.invoke(app, ["directory", "tree", "--snapshot", str(bad)])
    assert result.exit_code == 1
    assert "invalid json" in result.output.lower()


def test_serve_check_does_not_bind(tmp_path: Path) -> None:
    result = runner.invoke(app, ["directory", "serve", "--check", "--snapshot", str(_write_snapshot(tmp_path))])
    assert result.exit_code == 0, result.output
    assert "would serve" in result.output.lower()
    assert "read-only" in result.output.lower()
    assert "ldap://127.0.0.1:1389" in result.output


def test_serve_check_with_tls_uses_ldaps_default_port(tmp_path: Path) -> None:
    cert = tmp_path / "c.pem"
    key = tmp_path / "k.pem"
    cert.write_text("x", encoding="utf-8")
    key.write_text("x", encoding="utf-8")
    result = runner.invoke(
        app,
        ["directory", "serve", "--check", "--tls-cert", str(cert), "--tls-key", str(key)],
    )
    assert result.exit_code == 0, result.output
    assert "ldaps://127.0.0.1:636" in result.output


def test_serve_tls_cert_without_key_fails(tmp_path: Path) -> None:
    cert = tmp_path / "c.pem"
    cert.write_text("x", encoding="utf-8")
    result = runner.invoke(app, ["directory", "serve", "--check", "--tls-cert", str(cert)])
    assert result.exit_code == 1
    assert "together" in result.output.lower()


def test_serve_check_starttls_mode(tmp_path: Path) -> None:
    cert = tmp_path / "c.pem"
    key = tmp_path / "k.pem"
    cert.write_text("x", encoding="utf-8")
    key.write_text("x", encoding="utf-8")
    result = runner.invoke(
        app,
        ["directory", "serve", "--check", "--starttls", "--tls-cert", str(cert), "--tls-key", str(key)],
    )
    assert result.exit_code == 0, result.output
    # StartTLS serves on the plaintext port (1389), not LDAPS 636.
    assert "ldap+starttls://127.0.0.1:1389" in result.output


def test_serve_starttls_without_cert_fails() -> None:
    result = runner.invoke(app, ["directory", "serve", "--check", "--starttls"])
    assert result.exit_code == 1
    assert "requires --tls-cert" in result.output.lower()


def test_serve_check_enable_writes_noted() -> None:
    result = runner.invoke(app, ["directory", "serve", "--check", "--enable-writes"])
    assert result.exit_code == 0, result.output
    assert "writes(dry-run)" in result.output.lower()


def test_tree_ad_veneer_emits_ad_attributes(tmp_path: Path) -> None:
    result = runner.invoke(app, ["directory", "tree", "--ad-veneer", "--snapshot", str(_write_snapshot(tmp_path))])
    assert result.exit_code == 0, result.output
    assert "sAMAccountName: alice" in result.output
    assert "uiaoSyntheticSid: TRUE" in result.output  # advertised non-authoritative
    assert "objectSid: S-1-5-21-" in result.output


def test_tree_without_veneer_has_no_ad_attributes(tmp_path: Path) -> None:
    result = runner.invoke(app, ["directory", "tree", "--snapshot", str(_write_snapshot(tmp_path))])
    assert result.exit_code == 0, result.output
    assert "sAMAccountName" not in result.output


def test_serve_check_sasl_gssapi_noted() -> None:
    result = runner.invoke(app, ["directory", "serve", "--check", "--sasl-gssapi"])
    assert result.exit_code == 0, result.output
    assert "sasl/gssapi" in result.output.lower()


# ---------------------------------------------------------------------------
# Assessment feed (--from-assessment)
# ---------------------------------------------------------------------------

ASSESSMENT = [
    {"target_id": "alice@uiao.gov", "target_type": "user", "facet_values": {"region": "NCR"}, "findings": []},
]


def _write_assessment(tmp_path: Path) -> Path:
    path = tmp_path / "assessment.json"
    path.write_text(json.dumps(ASSESSMENT), encoding="utf-8")
    return path


def test_tree_from_assessment_projects(tmp_path: Path) -> None:
    result = runner.invoke(app, ["directory", "tree", "--from-assessment", str(_write_assessment(tmp_path))])
    assert result.exit_code == 0, result.output
    assert "uiaoOrgPathRegion: NCR" in result.output


def test_serve_check_from_assessment(tmp_path: Path) -> None:
    result = runner.invoke(
        app, ["directory", "serve", "--check", "--from-assessment", str(_write_assessment(tmp_path))]
    )
    assert result.exit_code == 0, result.output
    assert "would serve 3 entries" in result.output.lower()  # base + ou + alice


def test_snapshot_and_assessment_are_mutually_exclusive(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "directory",
            "tree",
            "--snapshot",
            str(_write_snapshot(tmp_path)),
            "--from-assessment",
            str(_write_assessment(tmp_path)),
        ],
    )
    assert result.exit_code == 1
    assert "not both" in result.output.lower()


def test_invalid_assessment_feed_fails(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"results": "not-a-list"}), encoding="utf-8")
    result = runner.invoke(app, ["directory", "tree", "--from-assessment", str(bad)])
    assert result.exit_code == 1
    assert "invalid assessment feed" in result.output.lower()


# ---------------------------------------------------------------------------
# Simple-bind credential config (--bind)
# ---------------------------------------------------------------------------


def test_serve_check_accepts_bind_pairs() -> None:
    result = runner.invoke(app, ["directory", "serve", "--check", "--bind", "svc=secret"])
    assert result.exit_code == 0, result.output


def test_serve_malformed_bind_fails() -> None:
    result = runner.invoke(app, ["directory", "serve", "--check", "--bind", "no-equals"])
    assert result.exit_code == 1
    assert "name=password" in result.output.lower()


# ---------------------------------------------------------------------------
# Write actuation (--apply) — gates and plan note
# ---------------------------------------------------------------------------


def test_apply_requires_enable_writes() -> None:
    result = runner.invoke(app, ["directory", "serve", "--check", "--apply", "--provider-host", "dc01"])
    assert result.exit_code == 1
    assert "--enable-writes" in result.output


def test_apply_requires_provider_host() -> None:
    result = runner.invoke(app, ["directory", "serve", "--check", "--enable-writes", "--apply"])
    assert result.exit_code == 1
    assert "--provider-host" in result.output


def test_apply_check_reports_l3_actuation() -> None:
    result = runner.invoke(
        app,
        ["directory", "serve", "--check", "--enable-writes", "--apply", "--provider-host", "dc01.contoso.com"],
    )
    assert result.exit_code == 0, result.output
    assert "apply→provider" in result.output.lower() or "apply" in result.output.lower()
    assert "l3" in result.output.lower()
    # --check must not open a connection or claim read-only when applying.
    assert "(read-only)" not in result.output
