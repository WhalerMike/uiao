"""tests/test_ksi_eval_plane.py — Plane 2: IR -> KSI evaluation test suite.

Tests are split into four layers:

1. Unit: _load_ir / _load_rules / _write_ksi helpers
2. Unit: _evaluate_control logic (pass / fail / inconclusive / excluded / override)
3. Unit: _build_summary + _build_evidence_index helpers
4. Integration: evaluate_ksi() end-to-end (reads a real IR file, writes KSI JSON)

The integration test builds a minimal but structurally valid IR envelope in
a tmp directory so no fixture files are required.

All tests are deterministic, hermetic (no network), and import nothing from
the SCuBA layer (Plane 1) or from the Evidence/POA&M layers (Planes 3/4).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import pytest

# ---------------------------------------------------------------------------
# Module under test
# ---------------------------------------------------------------------------
from uiao_impl.ksi.evaluate import (
    _build_evidence_index,
    _build_summary,
    _evaluate_control,
    _load_ir,
    _load_rules,
    _write_ksi,
    evaluate_ksi,
)

# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

def _make_control(cid: str) -> Dict[str, Any]:
    return {
        "id": cid,
        "source": "ksi",
        "description": f"Control {cid}",
        "parameters": {},
        "mappings": {"nist80053": [], "fedramp": []},
        "provenance": {
            "source": "test",
            "timestamp": "2026-01-01T00:00:00Z",
            "version": "1.0",
        },
    }


def _make_evidence(eid: str, control_id: str, result: str) -> Dict[str, Any]:
    return {
        "id": eid,
        "source": "test",
        "control_id": control_id,
        "policy_id": None,
        "timestamp": "2026-01-01T00:00:00Z",
        "data": {"result": result},
        "evaluation": {"result": result},
        "provenance": {
            "source": "test",
            "timestamp": "2026-01-01T00:00:00Z",
            "version": "1.0",
        },
    }


def _make_ir_envelope(
    controls: List[Dict[str, Any]],
    evidence: List[Dict[str, Any]],
) -> Dict[str, Any]:
    return {
        "schema_version": "1.0",
        "plane": "scuba-to-ir",
        "generated_at": "2026-01-01T00:00:00Z",
        "run_id": "test-run-001",
        "summary": {},
        "controls": controls,
        "evidence": evidence,
        "policies": [],
    }


# ---------------------------------------------------------------------------
# 1. _load_ir
# ---------------------------------------------------------------------------

class TestLoadIR:
    def test_loads_valid_json(self, tmp_path: Path) -> None:
        ir = _make_ir_envelope([_make_control("c1")], [])
        p = tmp_path / "source.ir.json"
        p.write_text(json.dumps(ir), encoding="utf-8")
        loaded = _load_ir(p)
        assert loaded["schema_version"] == "1.0"
        assert len(loaded["controls"]) == 1

    def test_raises_on_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            _load_ir(tmp_path / "nonexistent.ir.json")

    def test_raises_on_non_dict_json(self, tmp_path: Path) -> None:
        p = tmp_path / "bad.ir.json"
        p.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
        with pytest.raises(ValueError, match="dict"):
            _load_ir(p)


# ---------------------------------------------------------------------------
# 2. _load_rules
# ---------------------------------------------------------------------------

class TestLoadRules:
    def test_returns_empty_dict_when_none(self) -> None:
        assert _load_rules(None) == {}

    def test_returns_empty_dict_when_file_missing(self, tmp_path: Path) -> None:
        result = _load_rules(str(tmp_path / "nonexistent.json"))
        assert result == {}

    def test_loads_valid_rules(self, tmp_path: Path) -> None:
        rules = {"require_all_evidence_pass": True, "exclude_controls": ["c99"]}
        p = tmp_path / "rules.json"
        p.write_text(json.dumps(rules), encoding="utf-8")
        loaded = _load_rules(str(p))
        assert loaded["require_all_evidence_pass"] is True
        assert "c99" in loaded["exclude_controls"]


# ---------------------------------------------------------------------------
# 3. _write_ksi
# ---------------------------------------------------------------------------

class TestWriteKSI:
    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        dst = tmp_path / "output" / "ksi" / "source.ksi.json"
        _write_ksi(dst, {"schema_version": "1.0", "ksi": []})
        assert dst.exists()

    def test_writes_valid_json(self, tmp_path: Path) -> None:
        dst = tmp_path / "out.ksi.json"
        payload = {"schema_version": "1.0", "ksi": [{"control_id": "c1"}]}
        _write_ksi(dst, payload)
        data = json.loads(dst.read_text(encoding="utf-8"))
        assert data["schema_version"] == "1.0"
        assert len(data["ksi"]) == 1


# ---------------------------------------------------------------------------
# 4. _build_evidence_index
# ---------------------------------------------------------------------------

class TestBuildEvidenceIndex:
    def test_groups_by_control_id(self) -> None:
        ev = [
            _make_evidence("e1", "c1", "pass"),
            _make_evidence("e2", "c1", "fail"),
            _make_evidence("e3", "c2", "pass"),
        ]
        idx = _build_evidence_index(ev)
        assert len(idx["c1"]) == 2
        assert len(idx["c2"]) == 1

    def test_ignores_evidence_without_control_id(self) -> None:
        ev = [{"id": "e1", "source": "x", "timestamp": "t", "data": {}, "evaluation": {}}]
        idx = _build_evidence_index(ev)
        assert idx == {}

    def test_empty_evidence_returns_empty_index(self) -> None:
        assert _build_evidence_index([]) == {}


# ---------------------------------------------------------------------------
# 5. _evaluate_control — default logic
# ---------------------------------------------------------------------------

class TestEvaluateControlDefault:
    def test_inconclusive_when_no_evidence(self) -> None:
        ctrl = _make_control("c1")
        result = _evaluate_control(ctrl, {}, {})
        assert result["verdict"] == "inconclusive"
        assert result["passed"] is False
        assert result["evidence_count"] == 0

    def test_pass_when_any_evidence_passes(self) -> None:
        ctrl = _make_control("c1")
        idx = {"c1": [_make_evidence("e1", "c1", "pass")]}
        result = _evaluate_control(ctrl, idx, {})
        assert result["verdict"] == "pass"
        assert result["passed"] is True

    def test_fail_when_all_evidence_fails(self) -> None:
        ctrl = _make_control("c1")
        idx = {"c1": [_make_evidence("e1", "c1", "fail")]}
        result = _evaluate_control(ctrl, idx, {})
        assert result["verdict"] == "fail"
        assert result["passed"] is False

    def test_pass_when_mixed_evidence_any_mode(self) -> None:
        """In the default (require_all=False) mode, mixed evidence still passes."""
        ctrl = _make_control("c1")
        idx = {
            "c1": [
                _make_evidence("e1", "c1", "fail"),
                _make_evidence("e2", "c1", "pass"),
            ]
        }
        result = _evaluate_control(ctrl, idx, {})
        assert result["verdict"] == "pass"

    def test_fail_when_mixed_evidence_all_mode(self) -> None:
        """With require_all=True, mixed evidence must fail."""
        ctrl = _make_control("c1")
        idx = {
            "c1": [
                _make_evidence("e1", "c1", "fail"),
                _make_evidence("e2", "c1", "pass"),
            ]
        }
        rules = {"require_all_evidence_pass": True}
        result = _evaluate_control(ctrl, idx, rules)
        assert result["verdict"] == "fail"
        assert result["rule_key"] is None

    def test_pass_when_all_evidence_passes_in_all_mode(self) -> None:
        ctrl = _make_control("c1")
        idx = {
            "c1": [
                _make_evidence("e1", "c1", "pass"),
                _make_evidence("e2", "c1", "pass"),
            ]
        }
        rules = {"require_all_evidence_pass": True}
        result = _evaluate_control(ctrl, idx, rules)
        assert result["verdict"] == "pass"


# ---------------------------------------------------------------------------
# 6. _evaluate_control — exclusions
# ---------------------------------------------------------------------------

class TestEvaluateControlExclusions:
    def test_excluded_control(self) -> None:
        ctrl = _make_control("c1")
        rules = {"exclude_controls": ["c1"]}
        result = _evaluate_control(ctrl, {}, rules)
        assert result["verdict"] == "excluded"
        assert result["passed"] is False
        assert result["rule_key"] == "exclude_controls"

    def test_non_excluded_control_proceeds_normally(self) -> None:
        ctrl = _make_control("c2")
        rules = {"exclude_controls": ["c1"]}
        idx = {"c2": [_make_evidence("e1", "c2", "pass")]}
        result = _evaluate_control(ctrl, idx, rules)
        assert result["verdict"] == "pass"


# ---------------------------------------------------------------------------
# 7. _evaluate_control — per-control overrides
# ---------------------------------------------------------------------------

class TestEvaluateControlOverrides:
    def test_override_pass_when_matching_evidence(self) -> None:
        ctrl = _make_control("c1")
        idx = {"c1": [_make_evidence("e1", "c1", "pass")]}
        rules = {"control_overrides": {"c1": {"expected_result": "pass"}}}
        result = _evaluate_control(ctrl, idx, rules)
        assert result["verdict"] == "pass"
        assert result["rule_key"] == "control_overrides.c1"

    def test_override_fail_when_no_matching_evidence(self) -> None:
        ctrl = _make_control("c1")
        idx = {"c1": [_make_evidence("e1", "c1", "fail")]}
        rules = {"control_overrides": {"c1": {"expected_result": "pass"}}}
        result = _evaluate_control(ctrl, idx, rules)
        assert result["verdict"] == "fail"

    def test_override_not_applied_to_other_controls(self) -> None:
        ctrl = _make_control("c2")
        idx = {"c2": [_make_evidence("e1", "c2", "pass")]}
        rules = {"control_overrides": {"c1": {"expected_result": "fail"}}}
        result = _evaluate_control(ctrl, idx, rules)
        # c2 not in overrides -> default logic -> pass
        assert result["verdict"] == "pass"
        assert result["rule_key"] is None


# ---------------------------------------------------------------------------
# 8. _build_summary
# ---------------------------------------------------------------------------

class TestBuildSummary:
    def _make_result(self, verdict: str) -> Dict[str, Any]:
        return {"verdict": verdict, "passed": verdict == "pass", "evidence_count": 0}

    def test_all_pass(self) -> None:
        results = [self._make_result("pass")] * 3
        s = _build_summary(results)
        assert s["passing"] == 3
        assert s["failing"] == 0
        assert s["pass_rate"] == 1.0

    def test_mixed_verdicts(self) -> None:
        results = [
            self._make_result("pass"),
            self._make_result("fail"),
            self._make_result("inconclusive"),
            self._make_result("excluded"),
        ]
        s = _build_summary(results)
        assert s["total_controls"] == 4
        assert s["passing"] == 1
        assert s["failing"] == 1
        assert s["inconclusive"] == 1
        assert s["excluded"] == 1
        assert s["pass_rate"] == 0.25

    def test_empty_results(self) -> None:
        s = _build_summary([])
        assert s["total_controls"] == 0
        assert s["pass_rate"] == 0.0


# ---------------------------------------------------------------------------
# 9. Integration: evaluate_ksi() end-to-end
# ---------------------------------------------------------------------------

class TestEvaluateKSIIntegration:
    """Full round-trip test through evaluate_ksi()."""

    def _build_ir_file(self, tmp_path: Path) -> Path:
        controls = [_make_control("c1"), _make_control("c2"), _make_control("c3")]
        evidence = [
            _make_evidence("e1", "c1", "pass"),   # c1 -> pass
            _make_evidence("e2", "c2", "fail"),   # c2 -> fail
            # c3 has no evidence -> inconclusive
        ]
        ir = _make_ir_envelope(controls, evidence)
        ir_path = tmp_path / "output" / "ir" / "tenant-a.ir.json"
        ir_path.parent.mkdir(parents=True, exist_ok=True)
        ir_path.write_text(json.dumps(ir, indent=2), encoding="utf-8")
        return ir_path

    def test_produces_ksi_output_file(self, tmp_path: Path) -> None:
        ir_path = self._build_ir_file(tmp_path)
        out_path = tmp_path / "output" / "ksi" / "tenant-a.ksi.json"
        evaluate_ksi(str(ir_path), str(out_path))
        assert out_path.exists()

    def test_output_has_correct_schema(self, tmp_path: Path) -> None:
        ir_path = self._build_ir_file(tmp_path)
        out_path = tmp_path / "output" / "ksi" / "tenant-a.ksi.json"
        evaluate_ksi(str(ir_path), str(out_path))
        data = json.loads(out_path.read_text(encoding="utf-8"))
        assert data["schema_version"] == "1.0"
        assert data["plane"] == "ir-to-ksi"
        assert "run_id" in data
        assert "generated_at" in data
        assert "source_ir" in data
        assert "summary" in data
        assert "results_hash" in data
        assert "ksi" in data

    def test_output_has_three_results(self, tmp_path: Path) -> None:
        ir_path = self._build_ir_file(tmp_path)
        out_path = tmp_path / "output" / "ksi" / "tenant-a.ksi.json"
        evaluate_ksi(str(ir_path), str(out_path))
        data = json.loads(out_path.read_text(encoding="utf-8"))
        assert len(data["ksi"]) == 3

    def test_verdicts_are_correct(self, tmp_path: Path) -> None:
        ir_path = self._build_ir_file(tmp_path)
        out_path = tmp_path / "output" / "ksi" / "tenant-a.ksi.json"
        evaluate_ksi(str(ir_path), str(out_path))
        data = json.loads(out_path.read_text(encoding="utf-8"))
        by_id = {r["control_id"]: r for r in data["ksi"]}
        assert by_id["c1"]["verdict"] == "pass"
        assert by_id["c2"]["verdict"] == "fail"
        assert by_id["c3"]["verdict"] == "inconclusive"

    def test_summary_counts_are_correct(self, tmp_path: Path) -> None:
        ir_path = self._build_ir_file(tmp_path)
        out_path = tmp_path / "output" / "ksi" / "tenant-a.ksi.json"
        evaluate_ksi(str(ir_path), str(out_path))
        data = json.loads(out_path.read_text(encoding="utf-8"))
        s = data["summary"]
        assert s["total_controls"] == 3
        assert s["passing"] == 1
        assert s["failing"] == 1
        assert s["inconclusive"] == 1
        assert s["excluded"] == 0

    def test_log_file_is_created(self, tmp_path: Path) -> None:
        ir_path = self._build_ir_file(tmp_path)
        out_path = tmp_path / "output" / "ksi" / "tenant-a.ksi.json"
        evaluate_ksi(str(ir_path), str(out_path))
        log_dir = tmp_path / "output" / "logs"
        logs = list(log_dir.glob("*-ksi-eval.log"))
        assert len(logs) == 1

    def test_with_exclusion_config(self, tmp_path: Path) -> None:
        ir_path = self._build_ir_file(tmp_path)
        out_path = tmp_path / "output" / "ksi" / "tenant-a.ksi.json"
        rules = {"exclude_controls": ["c2"]}
        cfg_path = tmp_path / "config" / "ksi-rules.json"
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        cfg_path.write_text(json.dumps(rules), encoding="utf-8")
        evaluate_ksi(str(ir_path), str(out_path), config_path=str(cfg_path))
        data = json.loads(out_path.read_text(encoding="utf-8"))
        by_id = {r["control_id"]: r for r in data["ksi"]}
        assert by_id["c2"]["verdict"] == "excluded"

    def test_deterministic_output(self, tmp_path: Path) -> None:
        """Running evaluate_ksi twice on identical inputs must produce identical hashes."""
        ir_path = self._build_ir_file(tmp_path)
        out1 = tmp_path / "run1.ksi.json"
        out2 = tmp_path / "run2.ksi.json"
        evaluate_ksi(str(ir_path), str(out1))
        evaluate_ksi(str(ir_path), str(out2))
        d1 = json.loads(out1.read_text(encoding="utf-8"))
        d2 = json.loads(out2.read_text(encoding="utf-8"))
        assert d1["results_hash"] == d2["results_hash"]
        assert d1["ksi"] == d2["ksi"]

    def test_raises_on_missing_ir_file(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            evaluate_ksi(
                str(tmp_path / "nonexistent.ir.json"),
                str(tmp_path / "out.ksi.json"),
            )

