"""tests/test_oscal_generate_plane.py — Plane 4: Evidence → OSCAL test suite.

Tests are split into four layers:

1. Unit: _load_bundle / _load_evidence_records / _load_config helpers
2. Unit: _build_poam_items — mutation rules, severity, SLA, ordering
3. Unit: _build_implemented_requirements — status mapping, ordering
4. Integration: generate_oscal() end-to-end (reads a real evidence bundle,
   writes poam.json + ssp.json + artifact-index.json)

The integration tests build a minimal but structurally valid evidence bundle
in a tmp directory so no fixture files are required.

All tests are deterministic, hermetic (no network), and import nothing from
the SCuBA layer (Plane 1), IR layer (Plane 2), or KSI layer (Plane 3 input).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import pytest

# ---------------------------------------------------------------------------
# Module under test
# ---------------------------------------------------------------------------
from uiao.oscal.generator import (
    _build_implemented_requirements,
    _build_poam_items,
    _det_uuid,
    _load_bundle,
    _load_config,
    _load_evidence_records,
    _stable_hash,
    generate_oscal,
)

# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

_RUN_ID = "ev-build-00000000"
_GENERATED_AT = "2026-01-01T00:00:00Z"


def _make_record(
    control_id: str,
    status: str = "satisfied",
    verdict: str = "pass",
    fresh: bool = True,
) -> Dict[str, Any]:
    return {
        "id": f"ev:{control_id}:{_RUN_ID[:8]}",
        "control_id": control_id,
        "verdict": verdict,
        "status": status,
        "fresh": fresh,
        "rationale": f"Test rationale for {control_id}",
        "evidence_count": 1,
        "rule_key": None,
        "generated_at": _GENERATED_AT,
        "run_id": _RUN_ID,
        "provenance": {
            "source": "ksi-to-evidence-builder",
            "generated_at": _GENERATED_AT,
            "version": "1.0",
            "collector_id": "uiao-evidence-builder",
        },
    }


def _make_bundle(total: int = 3) -> Dict[str, Any]:
    return {
        "schema_version": "1.0",
        "plane": "ksi-to-evidence",
        "generated_at": _GENERATED_AT,
        "run_id": "ev-build-abc12345",
        "source_ksi_run_id": "ksi-eval-xyz",
        "hashing_algorithm": "sha256",
        "collector_id": "uiao-evidence-builder",
        "bundle_hash": "deadbeefdeadbeef",
        "manifest": {
            "total_records": total,
            "by_verdict": {"pass": 1, "fail": 1, "inconclusive": 1},
            "by_status": {"satisfied": 1, "not-satisfied": 1, "not-applicable": 1},
            "hash_index": {},
        },
    }


def _write_evidence_bundle(tmp_path: Path, records: List[Dict[str, Any]]) -> Path:
    bundle_dir = tmp_path / "output" / "evidence" / "tenant-a"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    bundle = _make_bundle(len(records))
    (bundle_dir / "bundle.json").write_text(json.dumps(bundle, indent=2), encoding="utf-8")
    with (bundle_dir / "evidence.jsonl").open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, sort_keys=True) + "\n")
    return bundle_dir


def _default_records() -> List[Dict[str, Any]]:
    return [
        _make_record("c1", "satisfied", "pass", True),
        _make_record("c2", "not-satisfied", "fail", True),
        _make_record("c3", "not-applicable", "inconclusive", False),
        _make_record("c4", "not-applicable", "excluded", False),
    ]


# ---------------------------------------------------------------------------
# 1. I/O helpers
# ---------------------------------------------------------------------------


class TestLoadBundle:
    def test_loads_valid_bundle(self, tmp_path: Path) -> None:
        bundle_dir = _write_evidence_bundle(tmp_path, _default_records())
        data = _load_bundle(bundle_dir)
        assert data["plane"] == "ksi-to-evidence"
        assert data["manifest"]["total_records"] == 4

    def test_raises_on_missing_bundle_json(self, tmp_path: Path) -> None:
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        with pytest.raises(FileNotFoundError, match="bundle.json"):
            _load_bundle(empty_dir)

    def test_raises_on_non_dict(self, tmp_path: Path) -> None:
        d = tmp_path / "bad"
        d.mkdir()
        (d / "bundle.json").write_text(json.dumps([1, 2]), encoding="utf-8")
        with pytest.raises(ValueError, match="dict"):
            _load_bundle(d)


class TestLoadEvidenceRecords:
    def test_loads_all_records(self, tmp_path: Path) -> None:
        bundle_dir = _write_evidence_bundle(tmp_path, _default_records())
        records = _load_evidence_records(bundle_dir)
        assert len(records) == 4

    def test_raises_on_missing_jsonl(self, tmp_path: Path) -> None:
        d = tmp_path / "no-jsonl"
        d.mkdir()
        (d / "bundle.json").write_text("{}", encoding="utf-8")
        with pytest.raises(FileNotFoundError, match="evidence.jsonl"):
            _load_evidence_records(d)

    def test_each_record_has_control_id(self, tmp_path: Path) -> None:
        bundle_dir = _write_evidence_bundle(tmp_path, _default_records())
        records = _load_evidence_records(bundle_dir)
        assert all("control_id" in r for r in records)


class TestLoadConfig:
    def test_returns_empty_on_none(self) -> None:
        assert _load_config(None) == {}

    def test_returns_empty_on_missing(self, tmp_path: Path) -> None:
        assert _load_config(str(tmp_path / "nope.json")) == {}

    def test_loads_valid_config(self, tmp_path: Path) -> None:
        cfg = {"system_name": "Test System", "default_severity": "High"}
        p = tmp_path / "cfg.json"
        p.write_text(json.dumps(cfg), encoding="utf-8")
        loaded = _load_config(str(p))
        assert loaded["system_name"] == "Test System"


# ---------------------------------------------------------------------------
# 2. _build_poam_items
# ---------------------------------------------------------------------------


class TestBuildPOAMItems:
    def test_only_not_satisfied_generates_items(self) -> None:
        records = _default_records()
        items = _build_poam_items(records, {})
        assert len(items) == 1
        assert items[0]["control-id"] == "c2"

    def test_poam_item_has_required_fields(self) -> None:
        records = [_make_record("c1", "not-satisfied", "fail")]
        items = _build_poam_items(records, {})
        item = items[0]
        assert "uuid" in item
        assert "title" in item
        assert "status" in item
        assert "risk-status" in item
        assert "sla-days" in item
        assert "control-id" in item
        assert "evidence-hash" in item
        assert "recommended-action" in item

    def test_default_severity_is_medium(self) -> None:
        records = [_make_record("c1", "not-satisfied", "fail")]
        items = _build_poam_items(records, {})
        assert items[0]["risk-status"] == "Medium"
        assert items[0]["sla-days"] == 60

    def test_config_default_severity_applied(self) -> None:
        records = [_make_record("c1", "not-satisfied", "fail")]
        items = _build_poam_items(records, {"default_severity": "High"})
        assert items[0]["risk-status"] == "High"
        assert items[0]["sla-days"] == 30

    def test_severity_override_per_control(self) -> None:
        records = [_make_record("c1", "not-satisfied", "fail")]
        cfg = {"severity_overrides": {"c1": "Critical"}}
        items = _build_poam_items(records, cfg)
        assert items[0]["risk-status"] == "Critical"
        assert items[0]["sla-days"] == 15

    def test_items_sorted_by_severity_then_control_id(self) -> None:
        records = [
            _make_record("c-z", "not-satisfied", "fail"),
            _make_record("c-a", "not-satisfied", "fail"),
        ]
        cfg = {"severity_overrides": {"c-z": "Critical", "c-a": "High"}}
        items = _build_poam_items(records, cfg)
        assert items[0]["control-id"] == "c-z"  # Critical first
        assert items[1]["control-id"] == "c-a"  # High second

    def test_uuid_is_deterministic(self) -> None:
        records = [_make_record("c1", "not-satisfied", "fail")]
        items1 = _build_poam_items(records, {})
        items2 = _build_poam_items(records, {})
        assert items1[0]["uuid"] == items2[0]["uuid"]

    def test_custom_poam_include_statuses(self) -> None:
        records = _default_records()
        cfg = {"poam_include_statuses": ["not-satisfied", "not-applicable"]}
        items = _build_poam_items(records, cfg)
        assert len(items) == 3  # c2 + c3 + c4


# ---------------------------------------------------------------------------
# 3. _build_implemented_requirements
# ---------------------------------------------------------------------------


class TestBuildImplementedRequirements:
    def test_all_records_produce_requirements(self) -> None:
        records = _default_records()
        reqs = _build_implemented_requirements(records, {})
        assert len(reqs) == 4

    def test_status_mapping(self) -> None:
        records = _default_records()
        reqs = {r["control-id"]: r for r in _build_implemented_requirements(records, {})}
        assert reqs["c1"]["implementation-status"] == "implemented"
        assert reqs["c2"]["implementation-status"] == "not-implemented"
        assert reqs["c3"]["implementation-status"] == "not-applicable"
        assert reqs["c4"]["implementation-status"] == "not-applicable"

    def test_sorted_by_control_id(self) -> None:
        records = [
            _make_record("z-ctrl", "satisfied"),
            _make_record("a-ctrl", "satisfied"),
        ]
        reqs = _build_implemented_requirements(records, {})
        assert reqs[0]["control-id"] == "a-ctrl"
        assert reqs[1]["control-id"] == "z-ctrl"

    def test_uuid_is_deterministic(self) -> None:
        records = [_make_record("c1", "satisfied")]
        reqs1 = _build_implemented_requirements(records, {})
        reqs2 = _build_implemented_requirements(records, {})
        assert reqs1[0]["uuid"] == reqs2[0]["uuid"]

    def test_fresh_field_preserved(self) -> None:
        records = [_make_record("c1", "satisfied", "pass", True)]
        reqs = _build_implemented_requirements(records, {})
        assert reqs[0]["fresh"] is True


# ---------------------------------------------------------------------------
# 4. Hashing utilities
# ---------------------------------------------------------------------------


class TestHashing:
    def test_stable_hash_identical_input(self) -> None:
        d = {"b": 2, "a": 1}
        assert _stable_hash(d) == _stable_hash({"a": 1, "b": 2})

    def test_det_uuid_is_deterministic(self) -> None:
        u1 = _det_uuid("poam-item", "ev:c1:abc123")
        u2 = _det_uuid("poam-item", "ev:c1:abc123")
        assert u1 == u2

    def test_det_uuid_different_for_different_names(self) -> None:
        assert _det_uuid("poam-item", "a") != _det_uuid("poam-item", "b")


# ---------------------------------------------------------------------------
# 5. Integration: generate_oscal() end-to-end
# ---------------------------------------------------------------------------


class TestGenerateOSCALIntegration:
    def _setup(self, tmp_path: Path) -> tuple[Path, Path]:
        bundle_dir = _write_evidence_bundle(tmp_path, _default_records())
        out_dir = tmp_path / "output" / "artifacts" / "tenant-a"
        return bundle_dir, out_dir

    def test_creates_output_directory(self, tmp_path: Path) -> None:
        bundle_dir, out_dir = self._setup(tmp_path)
        generate_oscal(str(bundle_dir), str(out_dir))
        assert out_dir.is_dir()

    def test_poam_json_exists(self, tmp_path: Path) -> None:
        bundle_dir, out_dir = self._setup(tmp_path)
        generate_oscal(str(bundle_dir), str(out_dir))
        assert (out_dir / "poam.json").exists()

    def test_ssp_json_exists(self, tmp_path: Path) -> None:
        bundle_dir, out_dir = self._setup(tmp_path)
        generate_oscal(str(bundle_dir), str(out_dir))
        assert (out_dir / "ssp.json").exists()

    def test_artifact_index_exists(self, tmp_path: Path) -> None:
        bundle_dir, out_dir = self._setup(tmp_path)
        generate_oscal(str(bundle_dir), str(out_dir))
        assert (out_dir / "artifact-index.json").exists()

    def test_poam_schema(self, tmp_path: Path) -> None:
        bundle_dir, out_dir = self._setup(tmp_path)
        generate_oscal(str(bundle_dir), str(out_dir))
        poam = json.loads((out_dir / "poam.json").read_text(encoding="utf-8"))
        assert poam["schema_version"] == "1.0"
        assert poam["plane"] == "evidence-to-oscal"
        assert poam["artifact"] == "poam"
        assert "summary" in poam
        assert "poam-items" in poam

    def test_ssp_schema(self, tmp_path: Path) -> None:
        bundle_dir, out_dir = self._setup(tmp_path)
        generate_oscal(str(bundle_dir), str(out_dir))
        ssp = json.loads((out_dir / "ssp.json").read_text(encoding="utf-8"))
        assert ssp["schema_version"] == "1.0"
        assert ssp["plane"] == "evidence-to-oscal"
        assert ssp["artifact"] == "ssp"
        assert "summary" in ssp
        assert "implemented-requirements" in ssp

    def test_poam_has_one_item(self, tmp_path: Path) -> None:
        bundle_dir, out_dir = self._setup(tmp_path)
        generate_oscal(str(bundle_dir), str(out_dir))
        poam = json.loads((out_dir / "poam.json").read_text(encoding="utf-8"))
        assert poam["summary"]["total_items"] == 1
        assert poam["poam-items"][0]["control-id"] == "c2"

    def test_ssp_has_four_requirements(self, tmp_path: Path) -> None:
        bundle_dir, out_dir = self._setup(tmp_path)
        generate_oscal(str(bundle_dir), str(out_dir))
        ssp = json.loads((out_dir / "ssp.json").read_text(encoding="utf-8"))
        assert ssp["summary"]["total_controls"] == 4
        assert ssp["summary"]["implemented"] == 1

    def test_ssp_coverage(self, tmp_path: Path) -> None:
        bundle_dir, out_dir = self._setup(tmp_path)
        generate_oscal(str(bundle_dir), str(out_dir))
        ssp = json.loads((out_dir / "ssp.json").read_text(encoding="utf-8"))
        assert ssp["summary"]["coverage"] == 0.25  # 1/4

    def test_artifact_index_hashes(self, tmp_path: Path) -> None:
        bundle_dir, out_dir = self._setup(tmp_path)
        generate_oscal(str(bundle_dir), str(out_dir))
        index = json.loads((out_dir / "artifact-index.json").read_text(encoding="utf-8"))
        assert "poam" in index["artifacts"]
        assert "ssp" in index["artifacts"]
        assert len(index["artifacts"]["poam"]["hash"]) == 64

    def test_log_file_created(self, tmp_path: Path) -> None:
        bundle_dir, out_dir = self._setup(tmp_path)
        generate_oscal(str(bundle_dir), str(out_dir))
        logs = list((tmp_path / "output" / "logs").glob("*-oscal-generate.log"))
        assert len(logs) == 1

    def test_deterministic_output(self, tmp_path: Path) -> None:
        bundle_dir = _write_evidence_bundle(tmp_path, _default_records())
        out1 = tmp_path / "run1"
        out2 = tmp_path / "run2"
        generate_oscal(str(bundle_dir), str(out1))
        generate_oscal(str(bundle_dir), str(out2))
        p1 = json.loads((out1 / "poam.json").read_text(encoding="utf-8"))
        p2 = json.loads((out2 / "poam.json").read_text(encoding="utf-8"))
        assert p1["poam-items"] == p2["poam-items"]
        s1 = json.loads((out1 / "ssp.json").read_text(encoding="utf-8"))
        s2 = json.loads((out2 / "ssp.json").read_text(encoding="utf-8"))
        assert s1["implemented-requirements"] == s2["implemented-requirements"]

    def test_raises_on_missing_bundle_dir(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            generate_oscal(
                str(tmp_path / "nonexistent"),
                str(tmp_path / "out"),
            )

    def test_system_name_from_config(self, tmp_path: Path) -> None:
        bundle_dir = _write_evidence_bundle(tmp_path, _default_records())
        out_dir = tmp_path / "out"
        cfg = {"system_name": "MyGovSystem"}
        cfg_path = tmp_path / "cfg.json"
        cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
        generate_oscal(str(bundle_dir), str(out_dir), config_path=str(cfg_path))
        ssp = json.loads((out_dir / "ssp.json").read_text(encoding="utf-8"))
        assert ssp["system_name"] == "MyGovSystem"
