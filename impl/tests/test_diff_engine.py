import json
from uiao.impl.diff.engine import diff_runs, format_diff_markdown, format_diff_json
from uiao.adapters.scuba.ir.transformer import transform_scuba_to_ir


def _run(tmp_path, name, ksi_results):
    data = {
        "assessment_metadata": {
            "run_id": name,
            "assessment_date": "2025-01-01T00:00:00Z",
            "tool_version": "1.0",
            "collector_user": "ci",
        },
        "tenant": {"tenant_id": "t1"},
        "ksi_results": ksi_results,
    }
    p = tmp_path / (name + ".json")
    p.write_text(json.dumps(data))
    return transform_scuba_to_ir(str(p))


def test_identical_runs_no_diff(tmp_path):
    ksis = [{"ksi_id": "KSI-IAM-01", "status": "PASS", "severity": "Low", "details": "ok"}]
    diff = diff_runs(_run(tmp_path, "same-run", ksis), _run(tmp_path, "same-run", ksis))
    assert not diff.ksi_diff.added and not diff.ksi_diff.removed
    assert not any(d.changed for d in diff.evidence_diffs)


def test_added_ksi(tmp_path):
    ra = _run(tmp_path, "a", [{"ksi_id": "KSI-IAM-01", "status": "PASS", "severity": "Low", "details": ""}])
    rb = _run(
        tmp_path,
        "b",
        [
            {"ksi_id": "KSI-IAM-01", "status": "PASS", "severity": "Low", "details": ""},
            {"ksi_id": "KSI-IAM-02", "status": "FAIL", "severity": "High", "details": ""},
        ],
    )
    diff = diff_runs(ra, rb)
    assert "KSI-IAM-02" in diff.ksi_diff.added


def test_removed_ksi(tmp_path):
    ra = _run(
        tmp_path,
        "a",
        [
            {"ksi_id": "KSI-IAM-01", "status": "PASS", "severity": "Low", "details": ""},
            {"ksi_id": "KSI-IAM-02", "status": "FAIL", "severity": "High", "details": ""},
        ],
    )
    rb = _run(tmp_path, "b", [{"ksi_id": "KSI-IAM-01", "status": "PASS", "severity": "Low", "details": ""}])
    diff = diff_runs(ra, rb)
    assert "KSI-IAM-02" in diff.ksi_diff.removed


def test_status_change(tmp_path):
    ra = _run(tmp_path, "a", [{"ksi_id": "KSI-IAM-01", "status": "PASS", "severity": "Low", "details": ""}])
    rb = _run(tmp_path, "b", [{"ksi_id": "KSI-IAM-01", "status": "FAIL", "severity": "Low", "details": ""}])
    diff = diff_runs(ra, rb)
    assert diff.status_changes[0] == {"ksi_id": "KSI-IAM-01", "from": "PASS", "to": "FAIL"}


def test_format_markdown(tmp_path):
    ra = _run(tmp_path, "run-a", [{"ksi_id": "KSI-IAM-01", "status": "PASS", "severity": "Low", "details": ""}])
    rb = _run(tmp_path, "run-b", [{"ksi_id": "KSI-IAM-01", "status": "FAIL", "severity": "Low", "details": ""}])
    md = format_diff_markdown(diff_runs(ra, rb))
    assert "run-a" in md and "run-b" in md


def test_format_json_structure(tmp_path):
    ra = _run(tmp_path, "a", [{"ksi_id": "KSI-IAM-01", "status": "PASS", "severity": "Low", "details": ""}])
    rb = _run(tmp_path, "b", [{"ksi_id": "KSI-IAM-02", "status": "FAIL", "severity": "High", "details": ""}])
    data = json.loads(format_diff_json(diff_runs(ra, rb)))
    assert data["ksi_diff"]["added"] == ["KSI-IAM-02"]
    assert data["ksi_diff"]["removed"] == ["KSI-IAM-01"]

