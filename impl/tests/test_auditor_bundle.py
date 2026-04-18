import json
import pathlib

import pytest

from uiao.impl.auditor.bundle import build_auditor_bundle

FAKE = {
    "assessment_metadata": {
        "run_id": "audit-001",
        "assessment_date": "2025-01-01T00:00:00Z",
        "tool_version": "1.0",
        "collector_user": "ci",
    },
    "tenant": {"tenant_id": "test-tenant"},
    "ksi_results": [
        {"ksi_id": "KSI-IAM-01", "status": "PASS", "severity": "Low", "details": "ok"},
        {"ksi_id": "KSI-IAM-02", "status": "FAIL", "severity": "High", "details": "gap"},
    ],
}
EXPECTED = {
    "governance-report.md",
    "ssp-narrative.md",
    "lineage.json",
    "evidence-bundle.json",
    "poam.json",
    "manifest.json",
}


@pytest.fixture()
def scuba_file(tmp_path):
    f = tmp_path / "scuba.json"
    f.write_text(json.dumps(FAKE))
    return str(f)


def test_creates_all_files(tmp_path, scuba_file):
    build_auditor_bundle(scuba_file, str(tmp_path / "out"))
    created = {p.name for p in pathlib.Path(tmp_path / "out").iterdir()}
    assert EXPECTED.issubset(created)


def test_manifest_run_id(tmp_path, scuba_file):
    manifest = build_auditor_bundle(scuba_file, str(tmp_path / "out"))
    assert manifest["run_id"] == "audit-001"


def test_manifest_hashes_are_sha256(tmp_path, scuba_file):
    manifest = build_auditor_bundle(scuba_file, str(tmp_path / "out"))
    for fname in EXPECTED - {"manifest.json"}:
        assert len(manifest["artifacts"][fname]) == 64


def test_summary_counts(tmp_path, scuba_file):
    manifest = build_auditor_bundle(scuba_file, str(tmp_path / "out"))
    assert manifest["summary"]["evidence_total"] == 2
    assert manifest["summary"]["pass"] == 1
    assert manifest["summary"]["fail"] == 1


def test_lineage_parseable(tmp_path, scuba_file):
    build_auditor_bundle(scuba_file, str(tmp_path / "out"))
    assert isinstance(json.loads((tmp_path / "out" / "lineage.json").read_text()), dict)


def test_poam_contains_fail_only(tmp_path, scuba_file):
    build_auditor_bundle(scuba_file, str(tmp_path / "out"))
    rows = json.loads((tmp_path / "out" / "poam.json").read_text())
    assert len(rows) == 1
    assert rows[0]["ksi_id"] == "KSI-IAM-02"

