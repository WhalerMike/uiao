import json
import pytest
from uiao.impl.validators.ir_validator import validate_normalized_json

VALID = {
    "assessment_metadata": {
        "run_id": "x",
        "assessment_date": "2025-01-01T00:00:00Z",
        "tool_version": "1.0",
        "collector_user": "ci",
    },
    "tenant": {"tenant_id": "t1"},
    "ksi_results": [{"ksi_id": "KSI-IAM-01", "status": "PASS", "severity": "Low", "details": "ok"}],
}


@pytest.fixture()
def valid_file(tmp_path):
    p = tmp_path / "v.json"
    p.write_text(json.dumps(VALID))
    return str(p)


def test_valid_passes(valid_file):
    r = validate_normalized_json(valid_file)
    assert r.valid and not r.errors


def test_missing_file():
    r = validate_normalized_json("no.json")
    assert not r.valid and any("not found" in e for e in r.errors)


def test_missing_ksi_results(tmp_path):
    p = tmp_path / "b.json"
    p.write_text(json.dumps({k: v for k, v in VALID.items() if k != "ksi_results"}))
    r = validate_normalized_json(str(p))
    assert not r.valid and any("ksi_results" in e for e in r.errors)


def test_tenant_as_string(tmp_path):
    p = tmp_path / "b.json"
    p.write_text(json.dumps({**VALID, "tenant": "bad"}))
    r = validate_normalized_json(str(p))
    assert not r.valid and any("tenant" in e for e in r.errors)


def test_invalid_status(tmp_path):
    p = tmp_path / "b.json"
    p.write_text(json.dumps({**VALID, "ksi_results": [{"ksi_id": "K1", "status": "BOGUS", "severity": "Low"}]}))
    r = validate_normalized_json(str(p))
    assert not r.valid and any("BOGUS" in e for e in r.errors)


def test_missing_metadata_key(tmp_path):
    p = tmp_path / "b.json"
    p.write_text(
        json.dumps({**VALID, "assessment_metadata": {"run_id": "x", "assessment_date": "2025-01-01T00:00:00Z"}})
    )
    r = validate_normalized_json(str(p))
    assert not r.valid and any("tool_version" in e for e in r.errors)


def test_empty_ksi_warns(tmp_path):
    p = tmp_path / "b.json"
    p.write_text(json.dumps({**VALID, "ksi_results": []}))
    r = validate_normalized_json(str(p))
    assert r.valid and any("empty" in w for w in r.warnings)

