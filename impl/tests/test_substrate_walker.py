"""Tests for the substrate repo-walker (impl/src/uiao_impl/substrate/walker.py)
and the `uiao substrate walk` / `uiao substrate drift` CLI commands.

Happy paths and failure modes per the test-coverage rule
(impl/.claude/rules/test-coverage.md).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from uiao_impl.cli.substrate import substrate_app as app
from uiao_impl.substrate.walker import walk_substrate

runner = CliRunner()


MANIFEST_BODY = {
    "metadata": {
        "document_id": "UIAO_200",
        "title": "UIAO Substrate Manifest",
        "version": "1.0",
        "status": "Current",
        "classification": "OPERATIONAL",
        "owner": "test",
        "created_at": "2026-04-17",
        "updated_at": "2026-04-17",
        "boundary": "GCC-Moderate",
    },
    "workspace": {"root_env": "UIAO_WORKSPACE_ROOT"},
    "github": {"root": "https://example.com/test/uiao", "default_branch": "main"},
    "modules": [
        {"name": "core", "path": "core", "role": "authority", "canon_consumer": False},
        {"name": "docs", "path": "docs", "role": "consumer", "canon_consumer": True},
        {"name": "impl", "path": "impl", "role": "consumer", "canon_consumer": True},
    ],
    "drift_scan": {"classes": ["DRIFT-SCHEMA", "DRIFT-PROVENANCE"], "roots": ["core", "docs", "impl"]},
    "registry_refs": {"document_registry": "core/canon/document-registry.yaml"},
}

CONTRACT_BODY = {
    "metadata": {
        "document_id": "UIAO_201",
        "title": "UIAO Workspace Contract",
        "version": "1.0",
        "status": "Current",
        "classification": "OPERATIONAL",
        "owner": "test",
        "created_at": "2026-04-17",
        "updated_at": "2026-04-17",
        "boundary": "GCC-Moderate",
    },
    "local": {"root_env": "UIAO_WORKSPACE_ROOT"},
    "remote": {"root": "https://example.com/test/uiao", "default_branch": "main"},
    "module_paths": {"core": "core", "docs": "docs", "impl": "impl"},
    "drift_scan_roots": ["core", "docs", "impl"],
    "build_outputs": {},
}


def _write_yaml(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False))


def _make_workspace(tmp_path: Path, *, with_contract: bool = True, doc_exists: bool = True) -> Path:
    """Synthesize a minimal valid substrate workspace on disk."""
    for mod in ("core", "docs", "impl"):
        (tmp_path / mod).mkdir()
    _write_yaml(tmp_path / "core/canon/substrate-manifest.yaml", MANIFEST_BODY)
    if with_contract:
        _write_yaml(tmp_path / "core/canon/workspace-contract.yaml", CONTRACT_BODY)
    registry = {
        "schema-version": "1.0.0",
        "updated": "2026-04-17",
        "documents": [
            {
                "id": "UIAO_200",
                "path": "canon/substrate-manifest.yaml",
                "title": "UIAO Substrate Manifest",
                "status": "Current",
                "classification": "OPERATIONAL",
            }
        ],
    }
    if not doc_exists:
        registry["documents"].append(
            {
                "id": "UIAO_999",
                "path": "canon/does-not-exist.md",
                "title": "Intentionally missing",
                "status": "Current",
                "classification": "OPERATIONAL",
            }
        )
    _write_yaml(tmp_path / "core/canon/document-registry.yaml", registry)
    return tmp_path


def test_walker_happy_path(tmp_path: Path) -> None:
    root = _make_workspace(tmp_path)
    report = walk_substrate(workspace_root=root)
    assert report.ok, report.findings
    assert report.manifest_present
    assert report.contract_present
    assert report.modules_checked == 3
    assert report.documents_checked == 1


def test_walker_detects_missing_module(tmp_path: Path) -> None:
    root = _make_workspace(tmp_path)
    # Remove a declared module path
    (root / "docs").rmdir()
    report = walk_substrate(workspace_root=root)
    assert not report.ok
    schema_findings = [f for f in report.findings if f.drift_class == "DRIFT-SCHEMA"]
    assert schema_findings, report.findings
    assert any("docs" in f.path for f in schema_findings)


def test_walker_detects_missing_canon_document(tmp_path: Path) -> None:
    root = _make_workspace(tmp_path, doc_exists=False)
    report = walk_substrate(workspace_root=root)
    assert not report.ok
    provenance = [f for f in report.findings if f.drift_class == "DRIFT-PROVENANCE"]
    assert provenance
    assert any("does-not-exist" in f.path for f in provenance)


def test_walker_missing_manifest_yields_p1(tmp_path: Path) -> None:
    root = tmp_path
    report = walk_substrate(workspace_root=root)
    assert not report.manifest_present
    assert any(f.drift_class == "DRIFT-SCHEMA" and f.severity == "P1" for f in report.findings)


def test_walker_optional_contract(tmp_path: Path) -> None:
    root = _make_workspace(tmp_path, with_contract=False)
    report = walk_substrate(workspace_root=root)
    assert report.ok, report.findings
    assert report.contract_present is False


def test_cli_substrate_walk_happy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _make_workspace(tmp_path)
    monkeypatch.setenv("UIAO_WORKSPACE_ROOT", str(root))
    result = runner.invoke(app, ["walk"])
    assert result.exit_code == 0, result.stdout
    assert "PASS" in result.stdout


def test_cli_substrate_walk_fail(tmp_path: Path) -> None:
    root = _make_workspace(tmp_path)
    (root / "impl").rmdir()
    result = runner.invoke(app, ["walk", "--workspace-root", str(root)])
    assert result.exit_code == 1
    assert "FAIL" in result.stdout
    assert "DRIFT-SCHEMA" in result.stdout


def test_cli_substrate_walk_json(tmp_path: Path) -> None:
    root = _make_workspace(tmp_path)
    result = runner.invoke(
        app, ["walk", "--workspace-root", str(root), "--json"]
    )
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["modules_checked"] == 3


def test_cli_substrate_drift_passes(tmp_path: Path) -> None:
    root = _make_workspace(tmp_path)
    result = runner.invoke(app, ["drift", "--workspace-root", str(root)])
    assert result.exit_code == 0
    assert "PASS" in result.stdout


def test_cli_substrate_drift_fails(tmp_path: Path) -> None:
    root = _make_workspace(tmp_path, doc_exists=False)
    result = runner.invoke(app, ["drift", "--workspace-root", str(root)])
    assert result.exit_code == 1
    assert "FAIL" in result.stdout
