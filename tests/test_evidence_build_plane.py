"""tests/test_evidence_build_plane.py — Plane 3: KSI → Evidence build test suite.

Tests are split into four layers:

1. Unit: _load_ksi / _load_config helpers
2. Unit: _ksi_result_to_evidence_record — mutation rules + field mapping
3. Unit: _build_manifest / _stable_hash / _write_* helpers
4. Integration: build_evidence() end-to-end round-trip

The integration tests build a minimal but structurally valid KSI envelope in
a tmp directory so no fixture files are required.

All tests are deterministic, hermetic (no network), and import nothing from
the SCuBA layer (Plane 1), the IR layer, or the POA&M/SSP layer (Plane 4).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import pytest

# ---------------------------------------------------------------------------
# Module under test
# ---------------------------------------------------------------------------
from uiao_core.evidence.builder import (
    _build_manifest,
    _canonical_json,
    _ksi_result_to_evidence_record,
    _load_config,
    _load_ksi,
    _stable_hash,
    _write_bundle_json,
    _write_evidence_jsonl,
    _write_hash_sidecars,
    _write_provenance_files,
    build_evidence,
)

# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

_RUN_ID = "test-run-00000000"
_GENERATED_AT = "2026-01-01T00:00:00Z"


def _make_ksi_result(
    control_id: str,
    verdict: str = "pass",
    evidence_count: int = 1,
    rule_key: str | None = None,
) -> Dict[str, Any]:
    return {
        "control_id": control_id,
        "verdict": verdict,
        "passed": verdict == "pass",
        "rule_key": rule_key,
        "rationale": f"Test rationale for {control_id}",
        "evidence_count": evidence_count,
    }


def _make_ksi_envelope(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(results)
    passing = sum(1 for r in results if r["verdict"] == "pass")
    return {
        "schema_version": "1.0",
        "plane": "ir-to-ksi",
        "generated_at": _GENERATED_AT,
        "run_id": "ksi-eval-abc12345",
        "source_ir": "output/ir/tenant-a.ir.json",
        "summary": {
            "total_controls": total,
            "passing": passing,
            "failing": total - passing,
            "inconclusive": 0,
            "excluded": 0,
            "pass_rate": passing / total if total else 0.0,
        },
        "results_hash": "deadbeef",
        "ksi": results,
    }


def _write_ksi_file(tmp_path: Path, results: List[Dict[str, Any]]) -> Path:
    envelope = _make_ksi_envelope(results)
    p = tmp_path / "output" / "ksi" / "tenant-a.ksi.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(envelope, indent=2), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# 1. _load_ksi
# ---------------------------------------------------------------------------

class TestLoadKSI:
    def test_loads_valid_envelope(self, tmp_path: Path) -> None:
        results = [_make_ksi_result("c1", "pass")]
        p = _write_ksi_file(tmp_path, results)
        data = _load_ksi(p)
        assert data["plane"] == "ir-to-ksi"
        assert len(data["ksi"]) == 1

    def test_raises_on_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            _load_ksi(tmp_path / "nonexistent.ksi.json")

    def test_raises_on_non_dict(self, tmp_path: Path) -> None:
        p = tmp_path / "bad.ksi.json"
        p.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
        with pytest.raises(ValueError, match="dict"):
            _load_ksi(p)

    def test_raises_on_missing_ksi_key(self, tmp_path: Path) -> None:
        p = tmp_path / "bad2.ksi.json"
        p.write_text(json.dumps({"plane": "ir-to-ksi"}), encoding="utf-8")
        with pytest.raises(ValueError, match="ksi"):
            _load_ksi(p)


# ---------------------------------------------------------------------------
# 2. _load_config
# ---------------------------------------------------------------------------

class TestLoadConfig:
    def test_returns_empty_on_none(self) -> None:
        assert _load_config(None) == {}

    def test_returns_empty_on_missing_file(self, tmp_path: Path) -> None:
        assert _load_config(str(tmp_path / "nope.json")) == {}

    def test_loads_valid_config(self, tmp_path: Path) -> None:
        cfg = {"collector_id": "test-collector", "version": "2.0"}
        p = tmp_path / "cfg.json"
        p.write_text(json.dumps(cfg), encoding="utf-8")
        loaded = _load_config(str(p))
        assert loaded["collector_id"] == "test-collector"


# ---------------------------------------------------------------------------
# 3. _ksi_result_to_evidence_record — mutation rules
# ---------------------------------------------------------------------------

class TestKSIResultToEvidenceRecord:
    def _build(self, verdict: str, cfg: Dict[str, Any] | None = None) -> Dict[str, Any]:
        result = _make_ksi_result("ctrl-1", verdict)
        return _ksi_result_to_evidence_record(result, _RUN_ID, _GENERATED_AT, cfg or {})

    def test_pass_maps_to_satisfied(self) -> None:
        rec = self._build("pass")
        assert rec["status"] == "satisfied"
        assert rec["fresh"] is True

    def test_fail_maps_to_not_satisfied(self) -> None:
        rec = self._build("fail")
        assert rec["status"] == "not-satisfied"
        assert rec["fresh"] is True

    def test_inconclusive_maps_to_not_applicable(self) -> None:
        rec = self._build("inconclusive")
        assert rec["status"] == "not-applicable"
        assert rec["fresh"] is False

    def test_excluded_maps_to_not_applicable(self) -> None:
        rec = self._build("excluded")
        assert rec["status"] == "not-applicable"
        assert rec["fresh"] is False

    def test_id_is_deterministic(self) -> None:
        result = _make_ksi_result("ctrl-42", "pass")
        rec = _ksi_result_to_evidence_record(result, _RUN_ID, _GENERATED_AT, {})
        assert rec["id"] == f"ev:ctrl-42:{_RUN_ID[:8]}"

    def test_provenance_uses_collector_id_from_config(self) -> None:
        rec = self._build("pass", {"collector_id": "my-collector"})
        assert rec["provenance"]["collector_id"] == "my-collector"

    def test_provenance_defaults_when_no_config(self) -> None:
        rec = self._build("pass")
        assert rec["provenance"]["collector_id"] == "uiao-evidence-builder"

    def test_control_id_preserved(self) -> None:
        rec = self._build("pass")
        assert rec["control_id"] == "ctrl-1"

    def test_run_id_preserved(self) -> None:
        rec = self._build("pass")
        assert rec["run_id"] == _RUN_ID


# ---------------------------------------------------------------------------
# 4. _stable_hash + _canonical_json
# ---------------------------------------------------------------------------

class TestHashing:
    def test_identical_dicts_produce_identical_hashes(self) -> None:
        data = {"b": 2, "a": 1}
        h1 = _stable_hash(data)
        h2 = _stable_hash({"a": 1, "b": 2})
        assert h1 == h2

    def test_different_dicts_produce_different_hashes(self) -> None:
        assert _stable_hash({"a": 1}) != _stable_hash({"a": 2})

    def test_canonical_json_sorts_keys(self) -> None:
        assert _canonical_json({"b": 2, "a": 1}) == '{"a":1,"b":2}'

    def test_hash_is_64_char_hex(self) -> None:
        h = _stable_hash({"x": "y"})
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)


# ---------------------------------------------------------------------------
# 5. _build_manifest
# ---------------------------------------------------------------------------

class TestBuildManifest:
    def _make_records(self) -> List[Dict[str, Any]]:
        return [
            _ksi_result_to_evidence_record(
                _make_ksi_result("c1", "pass"), _RUN_ID, _GENERATED_AT, {}
            ),
            _ksi_result_to_evidence_record(
                _make_ksi_result("c2", "fail"), _RUN_ID, _GENERATED_AT, {}
            ),
            _ksi_result_to_evidence_record(
                _make_ksi_result("c3", "inconclusive"), _RUN_ID, _GENERATED_AT, {}
            ),
        ]

    def test_total_records(self) -> None:
        m = _build_manifest(self._make_records())
        assert m["total_records"] == 3

    def test_by_verdict_counts(self) -> None:
        m = _build_manifest(self._make_records())
        assert m["by_verdict"]["pass"] == 1
        assert m["by_verdict"]["fail"] == 1
        assert m["by_verdict"]["inconclusive"] == 1

    def test_by_status_counts(self) -> None:
        m = _build_manifest(self._make_records())
        assert m["by_status"]["satisfied"] == 1
        assert m["by_status"]["not-satisfied"] == 1
        assert m["by_status"]["not-applicable"] == 1

    def test_hash_index_has_all_ids(self) -> None:
        records = self._make_records()
        m = _build_manifest(records)
        for rec in records:
            assert rec["id"] in m["hash_index"]

    def test_hash_index_values_are_hex(self) -> None:
        m = _build_manifest(self._make_records())
        for h in m["hash_index"].values():
            assert len(h) == 64


# ---------------------------------------------------------------------------
# 6. File I/O helpers
# ---------------------------------------------------------------------------

class TestFileHelpers:
    def _records(self) -> List[Dict[str, Any]]:
        return [
            _ksi_result_to_evidence_record(
                _make_ksi_result("c1", "pass"), _RUN_ID, _GENERATED_AT, {}
            )
        ]

    def test_write_evidence_jsonl(self, tmp_path: Path) -> None:
        dst = tmp_path / "evidence.jsonl"
        _write_evidence_jsonl(self._records(), dst)
        lines = dst.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed["control_id"] == "c1"

    def test_write_hash_sidecars(self, tmp_path: Path) -> None:
        hashes_dir = tmp_path / "hashes"
        _write_hash_sidecars(self._records(), hashes_dir)
        files = list(hashes_dir.glob("*.sha256"))
        assert len(files) == 1
        content = files[0].read_text(encoding="utf-8").strip()
        assert len(content) == 64

    def test_write_provenance_files(self, tmp_path: Path) -> None:
        prov_dir = tmp_path / "provenance"
        _write_provenance_files(self._records(), prov_dir)
        files = list(prov_dir.glob("*.provenance.json"))
        assert len(files) == 1
        prov = json.loads(files[0].read_text(encoding="utf-8"))
        assert prov["source"] == "ksi-to-evidence-builder"


# ---------------------------------------------------------------------------
# 7. Integration: build_evidence() end-to-end
# ---------------------------------------------------------------------------

class TestBuildEvidenceIntegration:
    def _write_ksi(self, tmp_path: Path) -> Path:
        results = [
            _make_ksi_result("c1", "pass"),
            _make_ksi_result("c2", "fail"),
            _make_ksi_result("c3", "inconclusive"),
            _make_ksi_result("c4", "excluded"),
        ]
        return _write_ksi_file(tmp_path, results)

    def test_creates_bundle_directory(self, tmp_path: Path) -> None:
        ksi_path = self._write_ksi(tmp_path)
        out_dir = tmp_path / "output" / "evidence" / "tenant-a"
        build_evidence(str(ksi_path), str(out_dir))
        assert out_dir.is_dir()

    def test_bundle_json_exists(self, tmp_path: Path) -> None:
        ksi_path = self._write_ksi(tmp_path)
        out_dir = tmp_path / "output" / "evidence" / "tenant-a"
        build_evidence(str(ksi_path), str(out_dir))
        assert (out_dir / "bundle.json").exists()

    def test_evidence_jsonl_exists(self, tmp_path: Path) -> None:
        ksi_path = self._write_ksi(tmp_path)
        out_dir = tmp_path / "output" / "evidence" / "tenant-a"
        build_evidence(str(ksi_path), str(out_dir))
        assert (out_dir / "evidence.jsonl").exists()

    def test_hashes_dir_exists(self, tmp_path: Path) -> None:
        ksi_path = self._write_ksi(tmp_path)
        out_dir = tmp_path / "output" / "evidence" / "tenant-a"
        build_evidence(str(ksi_path), str(out_dir))
        assert (out_dir / "hashes").is_dir()

    def test_provenance_dir_exists(self, tmp_path: Path) -> None:
        ksi_path = self._write_ksi(tmp_path)
        out_dir = tmp_path / "output" / "evidence" / "tenant-a"
        build_evidence(str(ksi_path), str(out_dir))
        assert (out_dir / "provenance").is_dir()

    def test_bundle_has_correct_schema(self, tmp_path: Path) -> None:
        ksi_path = self._write_ksi(tmp_path)
        out_dir = tmp_path / "output" / "evidence" / "tenant-a"
        build_evidence(str(ksi_path), str(out_dir))
        bundle = json.loads((out_dir / "bundle.json").read_text(encoding="utf-8"))
        assert bundle["schema_version"] == "1.0"
        assert bundle["plane"] == "ksi-to-evidence"
        assert "bundle_hash" in bundle
        assert "manifest" in bundle
        assert "run_id" in bundle

    def test_evidence_jsonl_has_four_records(self, tmp_path: Path) -> None:
        ksi_path = self._write_ksi(tmp_path)
        out_dir = tmp_path / "output" / "evidence" / "tenant-a"
        build_evidence(str(ksi_path), str(out_dir))
        lines = (out_dir / "evidence.jsonl").read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 4

    def test_mutation_rules_applied(self, tmp_path: Path) -> None:
        ksi_path = self._write_ksi(tmp_path)
        out_dir = tmp_path / "output" / "evidence" / "tenant-a"
        build_evidence(str(ksi_path), str(out_dir))
        lines = (out_dir / "evidence.jsonl").read_text(encoding="utf-8").strip().splitlines()
        records = {json.loads(l)["control_id"]: json.loads(l) for l in lines}
        assert records["c1"]["status"] == "satisfied"
        assert records["c1"]["fresh"] is True
        assert records["c2"]["status"] == "not-satisfied"
        assert records["c2"]["fresh"] is True
        assert records["c3"]["status"] == "not-applicable"
        assert records["c3"]["fresh"] is False
        assert records["c4"]["status"] == "not-applicable"
        assert records["c4"]["fresh"] is False

    def test_log_file_created(self, tmp_path: Path) -> None:
        ksi_path = self._write_ksi(tmp_path)
        out_dir = tmp_path / "output" / "evidence" / "tenant-a"
        build_evidence(str(ksi_path), str(out_dir))
        logs = list((tmp_path / "output" / "logs").glob("*-evidence-build.log"))
        assert len(logs) == 1

    def test_deterministic_bundle_hash(self, tmp_path: Path) -> None:
        ksi_path = self._write_ksi(tmp_path)
        out1 = tmp_path / "run1"
        out2 = tmp_path / "run2"
        build_evidence(str(ksi_path), str(out1))
        build_evidence(str(ksi_path), str(out2))
        b1 = json.loads((out1 / "bundle.json").read_text(encoding="utf-8"))
        b2 = json.loads((out2 / "bundle.json").read_text(encoding="utf-8"))
        assert b1["bundle_hash"] == b2["bundle_hash"]

    def test_raises_on_missing_ksi_file(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            build_evidence(
                str(tmp_path / "nonexistent.ksi.json"),
                str(tmp_path / "evidence"),
            )

    def test_with_custom_collector_id(self, tmp_path: Path) -> None:
        ksi_path = self._write_ksi(tmp_path)
        out_dir = tmp_path / "output" / "evidence" / "tenant-a"
        cfg = {"collector_id": "custom-collector"}
        cfg_path = tmp_path / "cfg.json"
        cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
        build_evidence(str(ksi_path), str(out_dir), config_path=str(cfg_path))
        lines = (out_dir / "evidence.jsonl").read_text(encoding="utf-8").strip().splitlines()
        rec = json.loads(lines[0])
        assert rec["provenance"]["collector_id"] == "custom-collector"
