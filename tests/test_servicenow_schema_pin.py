"""Tests for the ServiceNow deployment contract pin checker (UIAO_211).

Covers the three checks in scripts/check_servicenow_schema_pin.py:
structure coherence, code agreement, and instance agreement — including the
negative cases, because a gate that has never been shown to fail is not a
gate.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import sys

import pytest
import yaml

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "check_servicenow_schema_pin.py"
EXPECTED_PATH = REPO_ROOT / "src" / "uiao" / "canon" / "data" / "servicenow" / "expected-schema.yaml"


def _load_module():
    spec = importlib.util.spec_from_file_location("check_servicenow_schema_pin", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def mod():
    return _load_module()


@pytest.fixture(scope="module")
def doc() -> dict:
    return yaml.safe_load(EXPECTED_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# The committed assertion file
# ---------------------------------------------------------------------------


class TestCommittedFile:
    def test_assertion_file_exists(self) -> None:
        assert EXPECTED_PATH.exists()

    def test_structure_is_coherent(self, mod, doc) -> None:
        assert mod.check_structure(doc) == []

    def test_code_agreement_holds(self, mod, doc) -> None:
        """Every asserted column appears in the source file it cites."""
        assert mod.check_code_agreement(doc) == []

    def test_gcc_domain_is_recorded(self, doc) -> None:
        assert doc["instance"]["domain"] == "servicenowservices.com"

    def test_every_conflict_resolves(self, doc) -> None:
        unresolved = {u["id"] for u in doc["unresolved"]}
        for table in doc["tables"]:
            for col in table.get("custom-columns") or []:
                if col.get("conflict"):
                    assert col["conflict"] in unresolved

    def test_control_id_conflict_is_recorded(self, doc) -> None:
        """The two spellings of the control-id column are both asserted."""
        incident = next(t for t in doc["tables"] if t["name"] == "incident")
        names = {c["name"] for c in incident["custom-columns"]}
        assert {"u_uiao_control_id", "uiao_control_id"} <= names
        conflict = next(u for u in doc["unresolved"] if u["id"] == "control-id-prefix")
        assert conflict["severity"] == "high"

    def test_sc_request_registry_gap_is_flagged(self, doc) -> None:
        """The JML write path posts to a table the registry scope omits."""
        sc = next(t for t in doc["tables"] if t["name"] == "sc_request")
        assert sc.get("registry-gap") is True


# ---------------------------------------------------------------------------
# Structure check — negative cases
# ---------------------------------------------------------------------------


class TestStructureFailures:
    def test_missing_top_level_key_fails(self, mod, doc) -> None:
        broken = {k: v for k, v in doc.items() if k != "instance"}
        failures = mod.check_structure(broken)
        assert any("missing top-level keys" in f for f in failures)

    def test_dangling_conflict_id_fails(self, mod) -> None:
        broken = {
            "schema-version": "1.0.0",
            "registry-class": "servicenow-expected-schema",
            "updated": "2026-08-20",
            "instance": {},
            "tables": [
                {
                    "name": "incident",
                    "kind": "out-of-box",
                    "access": "read",
                    "used-by": [],
                    "custom-columns": [
                        {"name": "u_x", "code-ref": "scripts/check_servicenow_schema_pin.py", "conflict": "nope"}
                    ],
                }
            ],
            "unresolved": [],
        }
        failures = mod.check_structure(broken)
        assert any("has no entry under unresolved" in f for f in failures)

    def test_duplicate_column_fails(self, mod) -> None:
        broken = {
            "schema-version": "1.0.0",
            "registry-class": "servicenow-expected-schema",
            "updated": "2026-08-20",
            "instance": {},
            "tables": [
                {
                    "name": "incident",
                    "kind": "out-of-box",
                    "access": "read",
                    "used-by": [],
                    "custom-columns": [
                        {"name": "u_dup", "code-ref": "a"},
                        {"name": "u_dup", "code-ref": "b"},
                    ],
                }
            ],
            "unresolved": [],
        }
        assert any("duplicate column" in f for f in mod.check_structure(broken))


# ---------------------------------------------------------------------------
# Code agreement — negative cases
# ---------------------------------------------------------------------------


class TestCodeAgreementFailures:
    def test_column_absent_from_cited_file_fails(self, mod) -> None:
        broken = {
            "tables": [
                {
                    "name": "incident",
                    "used-by": [],
                    "custom-columns": [
                        {
                            "name": "u_uiao_not_a_real_column",
                            "code-ref": "src/uiao/adapters/servicenow_adapter.py",
                        }
                    ],
                }
            ]
        }
        failures = mod.check_code_agreement(broken)
        assert any("drifted from the code it cites" in f for f in failures)

    def test_missing_code_ref_file_fails(self, mod) -> None:
        broken = {
            "tables": [
                {
                    "name": "incident",
                    "used-by": [],
                    "custom-columns": [{"name": "u_x", "code-ref": "src/uiao/nope.py:1"}],
                }
            ]
        }
        assert any("does not exist" in f for f in mod.check_code_agreement(broken))

    def test_missing_used_by_path_fails(self, mod) -> None:
        broken = {"tables": [{"name": "incident", "used-by": ["src/uiao/gone.py"], "custom-columns": []}]}
        assert any("used-by path does not exist" in f for f in mod.check_code_agreement(broken))


# ---------------------------------------------------------------------------
# Instance agreement
# ---------------------------------------------------------------------------


class TestInstanceAgreement:
    @staticmethod
    def _doc() -> dict:
        return {
            "tables": [
                {
                    "name": "incident",
                    "custom-columns": [{"name": "u_uiao_control_id"}],
                }
            ]
        }

    def test_matching_export_passes(self, mod, tmp_path) -> None:
        export = tmp_path / "sys-dictionary.json"
        export.write_text(
            json.dumps({"result": [{"name": "incident", "element": "u_uiao_control_id"}]}),
            encoding="utf-8",
        )
        assert mod.check_instance_agreement(self._doc(), export) == []

    def test_missing_column_on_instance_fails(self, mod, tmp_path) -> None:
        export = tmp_path / "sys-dictionary.json"
        export.write_text(json.dumps({"result": []}), encoding="utf-8")
        failures = mod.check_instance_agreement(self._doc(), export)
        assert any("absent from the instance export" in f for f in failures)

    def test_unasserted_uiao_column_on_instance_fails(self, mod, tmp_path) -> None:
        """A UIAO-looking column nobody claims is as much a finding as a missing one."""
        export = tmp_path / "sys-dictionary.json"
        export.write_text(
            json.dumps(
                {
                    "result": [
                        {"name": "incident", "element": "u_uiao_control_id"},
                        {"name": "incident", "element": "u_uiao_orphaned"},
                    ]
                }
            ),
            encoding="utf-8",
        )
        failures = mod.check_instance_agreement(self._doc(), export)
        assert any("not asserted by any UIAO code path" in f for f in failures)

    def test_bare_list_export_is_accepted(self, mod, tmp_path) -> None:
        export = tmp_path / "sys-dictionary.json"
        export.write_text(json.dumps([{"name": "incident", "element": "u_uiao_control_id"}]), encoding="utf-8")
        assert mod.check_instance_agreement(self._doc(), export) == []

    def test_invalid_json_fails(self, mod, tmp_path) -> None:
        export = tmp_path / "sys-dictionary.json"
        export.write_text("{not json", encoding="utf-8")
        assert any("not valid JSON" in f for f in mod.check_instance_agreement(self._doc(), export))
