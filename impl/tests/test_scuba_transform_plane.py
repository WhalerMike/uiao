"""Tests for Plane 1: SCuBA -> IR transformation.

These tests exercise uiao.adapters.scuba.transform.transform_scuba_to_ir
against the canonical fixture already used by test_scuba_transformer_determinism.py,
verifying the *new* file-in / file-out contract (paths, schema envelope, logging).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from uiao.adapters.scuba.transform import (
    _apply_config_overrides,
    _ir_result_to_dict,
    _load_config,
    _load_scuba,
    _resolve_log_path,
    transform_scuba_to_ir,
)

FIXTURE = Path(__file__).parent / "fixtures" / "scuba_normalized_sample.json"


# ---------------------------------------------------------------------------
# _load_scuba
# ---------------------------------------------------------------------------

def test_load_scuba_json(tmp_path):
    src = tmp_path / "sample.json"
    src.write_text('{"ksi_results": []}', encoding="utf-8")
    data = _load_scuba(src)
    assert data == {"ksi_results": []}


def test_load_scuba_yaml(tmp_path):
    src = tmp_path / "sample.yaml"
    src.write_text("ksi_results: []\n", encoding="utf-8")
    data = _load_scuba(src)
    assert data == {"ksi_results": []}


def test_load_scuba_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        _load_scuba(tmp_path / "ghost.json")


def test_load_scuba_bad_type(tmp_path):
    src = tmp_path / "bad.json"
    src.write_text("[1, 2, 3]", encoding="utf-8")
    with pytest.raises(ValueError, match="dict"):
        _load_scuba(src)


# ---------------------------------------------------------------------------
# _load_config
# ---------------------------------------------------------------------------

def test_load_config_none_returns_empty():
    assert _load_config(None) == {}


def test_load_config_missing_path_returns_empty(tmp_path):
    result = _load_config(str(tmp_path / "nonexistent.json"))
    assert result == {}


def test_load_config_json(tmp_path):
    cfg = tmp_path / "cfg.json"
    cfg.write_text('{"tenant_boundary_id": "bnd:test"}', encoding="utf-8")
    result = _load_config(str(cfg))
    assert result["tenant_boundary_id"] == "bnd:test"


def test_load_config_yaml(tmp_path):
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text("tenant_boundary_id: bnd:yaml-test\n", encoding="utf-8")
    result = _load_config(str(cfg))
    assert result["tenant_boundary_id"] == "bnd:yaml-test"


# ---------------------------------------------------------------------------
# _apply_config_overrides
# ---------------------------------------------------------------------------

def test_apply_config_overrides_empty_cfg():
    scuba = {"ksi_results": [{"status": "FAIL"}]}
    result = _apply_config_overrides({}, scuba)
    assert result is scuba  # fast-path: no copy when cfg is empty


def test_apply_config_overrides_drop_statuses():
    scuba = {
        "ksi_results": [
            {"ksi_id": "KSI-A", "status": "PASS"},
            {"ksi_id": "KSI-B", "status": "INFO"},
            {"ksi_id": "KSI-C", "status": "FAIL"},
        ]
    }
    cfg = {"drop_statuses": ["INFO"]}
    result = _apply_config_overrides(cfg, scuba)
    ids = [r["ksi_id"] for r in result["ksi_results"]]
    assert "KSI-B" not in ids
    assert "KSI-A" in ids
    assert "KSI-C" in ids


def test_apply_config_overrides_does_not_mutate_original():
    scuba = {"ksi_results": [{"status": "INFO"}]}
    cfg = {"drop_statuses": ["INFO"]}
    _apply_config_overrides(cfg, scuba)
    assert len(scuba["ksi_results"]) == 1  # original unchanged


# ---------------------------------------------------------------------------
# _resolve_log_path
# ---------------------------------------------------------------------------

def test_resolve_log_path_format(tmp_path):
    output = tmp_path / "ir" / "tenant.ir.json"
    log = _resolve_log_path(output)
    assert log.parent == tmp_path / "logs"
    assert log.name.endswith("-scuba-transform.log")
    # Timestamp pattern: 20260101T000000Z-scuba-transform.log
    assert re.match(r"\d{8}T\d{6}Z-scuba-transform\.log", log.name)


# ---------------------------------------------------------------------------
# _ir_result_to_dict
# ---------------------------------------------------------------------------

def test_ir_result_to_dict_schema():
    from uiao.adapters.scuba.ir.transformer import transform_scuba_to_ir as _core
    result = _core(FIXTURE)
    d = _ir_result_to_dict(result)
    assert d["schema_version"] == "1.0"
    assert d["plane"] == "scuba-to-ir"
    assert "generated_at" in d
    assert "run_id" in d
    assert "summary" in d
    assert "evidence" in d
    assert "controls" in d
    assert "policies" in d


def test_ir_result_to_dict_summary_counts():
    from uiao.adapters.scuba.ir.transformer import transform_scuba_to_ir as _core
    result = _core(FIXTURE)
    d = _ir_result_to_dict(result)
    s = d["summary"]
    assert s["pass"] == result.pass_count
    assert s["warn"] == result.warn_count
    assert s["fail"] == result.fail_count
    assert s["total"] == len(result.evidence)


# ---------------------------------------------------------------------------
# transform_scuba_to_ir (full pipeline)
# ---------------------------------------------------------------------------

def test_full_pipeline_creates_output_file(tmp_path):
    out = tmp_path / "ir" / "tenant.ir.json"
    transform_scuba_to_ir(str(FIXTURE), str(out))
    assert out.exists(), "IR output file not created"


def test_full_pipeline_output_is_valid_json(tmp_path):
    out = tmp_path / "ir" / "tenant.ir.json"
    transform_scuba_to_ir(str(FIXTURE), str(out))
    data = json.loads(out.read_text(encoding="utf-8"))
    assert isinstance(data, dict)


def test_full_pipeline_output_schema_version(tmp_path):
    out = tmp_path / "ir" / "tenant.ir.json"
    transform_scuba_to_ir(str(FIXTURE), str(out))
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["schema_version"] == "1.0"
    assert data["plane"] == "scuba-to-ir"


def test_full_pipeline_creates_log_file(tmp_path):
    out = tmp_path / "ir" / "tenant.ir.json"
    transform_scuba_to_ir(str(FIXTURE), str(out))
    logs = list((tmp_path / "logs").glob("*-scuba-transform.log"))
    assert len(logs) == 1, f"Expected 1 log file, found {len(logs)}: {logs}"


def test_full_pipeline_log_contains_summary(tmp_path):
    out = tmp_path / "ir" / "tenant.ir.json"
    transform_scuba_to_ir(str(FIXTURE), str(out))
    log = next((tmp_path / "logs").glob("*-scuba-transform.log"))
    text = log.read_text(encoding="utf-8")
    assert "Transform complete" in text
    assert "PASS=" in text


def test_full_pipeline_missing_input_raises(tmp_path):
    out = tmp_path / "ir" / "tenant.ir.json"
    with pytest.raises(FileNotFoundError):
        transform_scuba_to_ir(str(tmp_path / "ghost.json"), str(out))


def test_full_pipeline_is_deterministic(tmp_path):
    out_a = tmp_path / "a.ir.json"
    out_b = tmp_path / "b.ir.json"
    transform_scuba_to_ir(str(FIXTURE), str(out_a))
    transform_scuba_to_ir(str(FIXTURE), str(out_b))
    data_a = json.loads(out_a.read_text(encoding="utf-8"))
    data_b = json.loads(out_b.read_text(encoding="utf-8"))
    # Evidence hashes must be identical across runs
    hashes_a = sorted(e["evaluation"]["canonical_hash"] for e in data_a["evidence"])
    hashes_b = sorted(e["evaluation"]["canonical_hash"] for e in data_b["evidence"])
    assert hashes_a == hashes_b


def test_full_pipeline_with_config_drop_statuses(tmp_path):
    """Verify that drop_statuses config filters ksi_results before transform."""
    fixture_data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    # How many PASS items are in the fixture?
    pass_count = sum(1 for r in fixture_data["ksi_results"] if r["status"] == "PASS")

    # Write config that drops PASS items
    cfg = tmp_path / "cfg.json"
    cfg.write_text('{"drop_statuses": ["PASS"]}', encoding="utf-8")

    out = tmp_path / "dropped.ir.json"
    transform_scuba_to_ir(str(FIXTURE), str(out), str(cfg))
    data = json.loads(out.read_text(encoding="utf-8"))

    # Total evidence should be less (no PASS items)
    full_total = len(fixture_data["ksi_results"])
    assert data["summary"]["total"] == full_total - pass_count


def test_full_pipeline_creates_parent_directories(tmp_path):
    out = tmp_path / "deep" / "nested" / "output" / "tenant.ir.json"
    transform_scuba_to_ir(str(FIXTURE), str(out))
    assert out.exists()

