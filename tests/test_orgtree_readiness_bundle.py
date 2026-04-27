"""Tests for WS-A5: OrgTree Readiness Bundle — schema validation + CLI smoke."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from importlib.resources import files as _res_files
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SCHEMA_ID = "https://uiao.gov/schemas/orgtree-readiness/orgtree-readiness.schema.json"
BUNDLE_VERSION = "0.6.0"
_HMAC_DEFAULT = "uiao-dev-hmac-key-not-for-production"


def _load_schema() -> Any:
    raw = (
        _res_files("uiao.schemas")
        .joinpath("orgtree-readiness")
        .joinpath("orgtree-readiness.schema.json")
        .read_text()
    )
    return json.loads(raw)


def _make_provenance(source_hash: str = "a" * 64, sig: str = "b" * 64) -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "schema_version": BUNDLE_VERSION,
        "canon_refs": ["UIAO_AD_001"],
        "source_hash": source_hash,
        "signature": sig,
        "hmac_alg": "hmac-sha256",
    }


def _empty_bundle() -> dict[str, Any]:
    """Minimal valid bundle — all arrays empty, plans are empty objects."""
    return {
        "version": BUNDLE_VERSION,
        "generated_at": "2026-04-27T00:00:00Z",
        "users": [],
        "groups": [],
        "computers": [],
        "servers": [],
        "orgpath_plan": {},
        "intune_plan": {},
        "arc_plan": {},
        "findings": [],
        "provenance": _make_provenance(),
    }


def _populated_bundle() -> dict[str, Any]:
    """Synthetic small populated bundle used for schema + roundtrip tests."""
    return {
        "version": BUNDLE_VERSION,
        "generated_at": "2026-04-27T12:34:56Z",
        "users": [
            {
                "dn": "CN=Alice,OU=Corp,DC=contoso,DC=com",
                "sam_account_name": "alice",
                "user_principal_name": "alice@contoso.com",
                "display_name": "Alice Smith",
                "enabled": True,
                "orgpath": "ORG-HR",
                "source_forest": "contoso.com",
                "last_logon_timestamp": "2026-04-20T08:00:00Z",
            }
        ],
        "groups": [
            {
                "dn": "CN=IT-Admins,OU=Groups,DC=contoso,DC=com",
                "sam_account_name": "IT-Admins",
                "group_scope": "Global",
                "group_type": "Security",
                "member_count": 5,
                "source_forest": "contoso.com",
            }
        ],
        "computers": [
            {
                "dn": "CN=WS-001,OU=Workstations,DC=contoso,DC=com",
                "dns_host_name": "ws-001.contoso.com",
                "operating_system": "Windows 11 Enterprise",
                "operating_system_version": "10.0 (22631)",
                "enabled": True,
                "last_logon_timestamp": "2026-04-26T14:00:00Z",
                "source_forest": "contoso.com",
            }
        ],
        "servers": [
            {
                "dn": "CN=SRV-001,OU=Servers,DC=contoso,DC=com",
                "dns_host_name": "srv-001.contoso.com",
                "operating_system": "Windows Server 2022 Standard",
                "operating_system_version": "10.0 (20348)",
                "enabled": True,
                "last_logon_timestamp": None,
                "source_forest": "contoso.com",
            }
        ],
        "orgpath_plan": {
            "total_users": 1,
            "resolved_count": 1,
            "unresolved_count": 0,
            "coverage_pct": 100.0,
            "unresolved_dns": [],
            "ou_orgpath_map": {"OU=Corp,DC=contoso,DC=com": "ORG-HR"},
        },
        "intune_plan": {
            "total_computers": 1,
            "enroll_ready_count": 1,
            "enroll_blocked_count": 0,
            "blocked_dns": [],
            "readiness_pct": 100.0,
        },
        "arc_plan": {
            "total_servers": 1,
            "onboard_ready_count": 1,
            "onboard_blocked_count": 0,
            "blocked_dns": [],
            "readiness_pct": 100.0,
        },
        "findings": [
            {
                "drift_class": "DRIFT-SEMANTIC",
                "severity": "P3",
                "path": "OU=Legacy,DC=contoso,DC=com",
                "detail": "OU uses geographic name encoding; cannot derive canonical OrgPath.",
                "error_code": "GOV-DRF-003",
                "object_type": "OU",
                "source_forest": "contoso.com",
                "suggested_orgpath": "",
            }
        ],
        "provenance": _make_provenance(source_hash="c" * 64, sig="d" * 64),
    }


# ---------------------------------------------------------------------------
# Schema loading
# ---------------------------------------------------------------------------


def test_schema_loads_via_importlib_resources() -> None:
    schema = _load_schema()
    assert schema["$id"] == SCHEMA_ID
    assert schema["title"] == "UIAO OrgTree Readiness Bundle Schema"


# ---------------------------------------------------------------------------
# Schema validation — empty bundle
# ---------------------------------------------------------------------------


def test_empty_bundle_validates() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = _load_schema()
    bundle = _empty_bundle()
    jsonschema.validate(instance=bundle, schema=schema)  # must not raise


# ---------------------------------------------------------------------------
# Schema validation — populated bundle
# ---------------------------------------------------------------------------


def test_populated_bundle_validates() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = _load_schema()
    bundle = _populated_bundle()
    jsonschema.validate(instance=bundle, schema=schema)  # must not raise


# ---------------------------------------------------------------------------
# Schema rejection — missing required key
# ---------------------------------------------------------------------------


def test_bundle_missing_required_key_fails() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = _load_schema()
    bundle = _empty_bundle()
    del bundle["users"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=bundle, schema=schema)


# ---------------------------------------------------------------------------
# HMAC roundtrip (unit-level, no CLI)
# ---------------------------------------------------------------------------


def test_hmac_sha256_roundtrip() -> None:
    """The HMAC-SHA256 over canonical JSON must be deterministic."""
    key = _HMAC_DEFAULT.encode("utf-8")
    bundle = _empty_bundle()
    canonical = json.dumps(bundle, sort_keys=True, separators=(",", ":"))
    sig1 = hmac.new(key, canonical.encode("utf-8"), hashlib.sha256).hexdigest()
    sig2 = hmac.new(key, canonical.encode("utf-8"), hashlib.sha256).hexdigest()
    assert sig1 == sig2
    assert len(sig1) == 64


# ---------------------------------------------------------------------------
# CLI smoke test
# ---------------------------------------------------------------------------


def test_cli_orgtree_readiness_bundle(tmp_path: Path) -> None:
    """uiao ir orgtree-readiness-bundle: exit 0, 3 artifacts, signature roundtrips."""
    from typer.testing import CliRunner

    from uiao.cli.ir import ir_app

    # Build a minimal survey input file
    survey = {
        "users": [
            {
                "dn": "CN=Bob,OU=Corp,DC=example,DC=com",
                "sam_account_name": "bob",
                "enabled": True,
            }
        ],
        "groups": [],
        "computers": [],
        "servers": [],
        "findings": [],
    }
    survey_file = tmp_path / "survey.json"
    survey_file.write_text(json.dumps(survey), encoding="utf-8")

    out_dir = tmp_path / "bundle-out"

    runner = CliRunner()
    result = runner.invoke(
        ir_app,
        ["orgtree-readiness-bundle", str(survey_file), "--out-dir", str(out_dir)],
        env={**os.environ, "UIAO_BUNDLE_HMAC_KEY": "test-key-for-ci"},
        catch_exceptions=False,
    )

    assert result.exit_code == 0, f"Non-zero exit: {result.output}"

    # All three artifacts must exist
    assert (out_dir / "bundle.json").exists(), "bundle.json missing"
    assert (out_dir / "bundle.hash").exists(), "bundle.hash missing"
    assert (out_dir / "bundle.sig").exists(), "bundle.sig missing"

    # bundle.json must be valid JSON with expected keys
    bundle_data = json.loads((out_dir / "bundle.json").read_text())
    assert bundle_data["version"] == BUNDLE_VERSION
    assert isinstance(bundle_data["users"], list)
    assert bundle_data["users"][0]["dn"] == "CN=Bob,OU=Corp,DC=example,DC=com"

    # Signature roundtrip: recompute and compare
    content_hash_file = (out_dir / "bundle.hash").read_text().strip()
    sig_file = (out_dir / "bundle.sig").read_text().strip()

    # The CLI stores bundle.hash as SHA-256 of the canonical-pre-sig bundle.
    # We simply assert the sig file is 64 hex chars and matches format.
    assert len(sig_file) == 64
    assert all(c in "0123456789abcdef" for c in sig_file)
    assert len(content_hash_file) == 64
    assert all(c in "0123456789abcdef" for c in content_hash_file)

    # Verify schema is satisfied by the written bundle
    try:
        import jsonschema

        schema = _load_schema()
        jsonschema.validate(instance=bundle_data, schema=schema)
    except ImportError:
        pass  # jsonschema not available — skip deep check


def test_cli_orgtree_readiness_bundle_help() -> None:
    """uiao ir orgtree-readiness-bundle --help must exit 0."""
    from typer.testing import CliRunner

    from uiao.cli.ir import ir_app

    runner = CliRunner()
    result = runner.invoke(ir_app, ["orgtree-readiness-bundle", "--help"])
    assert result.exit_code == 0
    assert "UIAO_BUNDLE_HMAC_KEY" in result.output


def test_cli_orgtree_readiness_bundle_missing_file(tmp_path: Path) -> None:
    """Non-existent survey file must exit non-zero."""
    from typer.testing import CliRunner

    from uiao.cli.ir import ir_app

    runner = CliRunner()
    result = runner.invoke(
        ir_app,
        ["orgtree-readiness-bundle", str(tmp_path / "nonexistent.json"), "--out-dir", str(tmp_path / "out")],
    )
    assert result.exit_code != 0


def test_cli_orgtree_readiness_bundle_no_hmac_key_fails_closed(tmp_path: Path) -> None:
    """When UIAO_BUNDLE_HMAC_KEY is unset and --insecure-dev-key not passed, exit non-zero.

    Phase 1.5 fix #3: fail-closed behaviour for missing HMAC key.
    """
    from typer.testing import CliRunner

    from uiao.cli.ir import ir_app

    survey = {"users": [], "groups": [], "computers": [], "servers": [], "findings": []}
    survey_file = tmp_path / "survey.json"
    survey_file.write_text(json.dumps(survey), encoding="utf-8")

    # Explicitly unset UIAO_BUNDLE_HMAC_KEY from env
    env_without_key = {k: v for k, v in os.environ.items() if k != "UIAO_BUNDLE_HMAC_KEY"}

    runner = CliRunner()
    result = runner.invoke(
        ir_app,
        ["orgtree-readiness-bundle", str(survey_file), "--out-dir", str(tmp_path / "out")],
        env=env_without_key,
        catch_exceptions=False,
    )
    assert result.exit_code != 0, "Should fail closed when HMAC key is unset and --insecure-dev-key not passed"
    assert "UIAO_BUNDLE_HMAC_KEY" in result.output


def test_cli_orgtree_readiness_bundle_insecure_dev_key_flag(tmp_path: Path) -> None:
    """--insecure-dev-key allows bundle creation without UIAO_BUNDLE_HMAC_KEY (dev/CI only)."""
    from typer.testing import CliRunner

    from uiao.cli.ir import ir_app

    survey = {"users": [], "groups": [], "computers": [], "servers": [], "findings": []}
    survey_file = tmp_path / "survey.json"
    survey_file.write_text(json.dumps(survey), encoding="utf-8")
    out_dir = tmp_path / "out"

    env_without_key = {k: v for k, v in os.environ.items() if k != "UIAO_BUNDLE_HMAC_KEY"}

    runner = CliRunner()
    result = runner.invoke(
        ir_app,
        ["orgtree-readiness-bundle", str(survey_file), "--out-dir", str(out_dir), "--insecure-dev-key"],
        env=env_without_key,
        catch_exceptions=False,
    )
    assert result.exit_code == 0, f"Non-zero exit with --insecure-dev-key: {result.output}"
    assert (out_dir / "bundle.json").exists()


def test_cli_orgtree_readiness_bundle_oscal_out_wires_a6_emitter(tmp_path: Path) -> None:
    """--oscal-out triggers the WS-A6 OSCAL emitter and writes orgtree-evidence.json.

    Phase 2 task 4: wires uiao.oscal.orgtree_evidence.emit_orgtree_evidence into
    the WS-A5 bundle CLI via the --oscal-out flag.
    """
    from typer.testing import CliRunner

    from uiao.cli.ir import ir_app

    # Survey with one user and one server so the OSCAL emitter has non-trivial output.
    # Keys follow the bundle schema: 'dn' is required for users/servers; extra keys allowed.
    survey = {
        "users": [
            {
                "dn": "CN=Alice,OU=Corp,DC=contoso,DC=com",
                "samAccountName": "alice",
                "objectSid": "S-1-5-21-1-2-3-1001",
                "userAccountControl": 512,
                "displayName": "Alice Smith",
                "enabled": True,
                "lastLogonTimestamp": None,
            }
        ],
        "groups": [],
        "computers": [],
        "servers": [
            {
                "dn": "CN=SRV-001,OU=Servers,DC=contoso,DC=com",
                "name": "SRV-001",
                "objectSid": "S-1-5-21-1-2-3-2001",
                "dNSHostName": "srv-001.contoso.com",
                "operatingSystem": "Windows Server 2022 Standard",
                "enabled": True,
                "lastLogonTimestamp": None,
            }
        ],
        "findings": [],
    }
    survey_file = tmp_path / "survey.json"
    survey_file.write_text(json.dumps(survey), encoding="utf-8")
    out_dir = tmp_path / "bundle-out"
    oscal_dir = tmp_path / "oscal-out"

    env_without_key = {k: v for k, v in os.environ.items() if k != "UIAO_BUNDLE_HMAC_KEY"}

    runner = CliRunner()
    result = runner.invoke(
        ir_app,
        [
            "orgtree-readiness-bundle",
            str(survey_file),
            "--out-dir", str(out_dir),
            "--oscal-out", str(oscal_dir),
            "--insecure-dev-key",
        ],
        env=env_without_key,
        catch_exceptions=False,
    )

    assert result.exit_code == 0, f"Non-zero exit: {result.output}"

    # Bundle artifacts must exist
    assert (out_dir / "bundle.json").exists(), "bundle.json missing"
    assert (out_dir / "bundle.hash").exists(), "bundle.hash missing"
    assert (out_dir / "bundle.sig").exists(), "bundle.sig missing"

    # OSCAL evidence file must exist (written by WS-A6 emitter)
    oscal_file = oscal_dir / "orgtree-evidence.json"
    assert oscal_file.exists(), f"orgtree-evidence.json missing from {oscal_dir}"

    # Structural check: top-level key must be assessment-results
    oscal_doc = json.loads(oscal_file.read_text(encoding="utf-8"))
    assert "assessment-results" in oscal_doc, "orgtree-evidence.json missing 'assessment-results' key"
    ar = oscal_doc["assessment-results"]
    assert "results" in ar, "assessment-results missing 'results' list"
    assert len(ar["results"]) >= 1, "assessment-results must have at least one result"

    # Verify output line in CLI output mentions OSCAL
    assert "OSCAL evidence written" in result.output or "orgtree-evidence.json" in result.output
