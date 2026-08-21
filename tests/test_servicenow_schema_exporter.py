"""Tests for the ServiceNow deployment exporter (UIAO_211 §4).

The exporter reaches a live federal instance, so the behaviour worth testing
is everything it does *before* and *around* the network call: where it gets
its table list, the queries it builds, and — most importantly — that it fails
closed rather than dialling a placeholder host or writing an export that
would misreport the instance.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "export_servicenow_schema.py"

ENV_VARS = ("SERVICENOW_INSTANCE", "SERVICENOW_BASE_URL", "SERVICENOW_TOKEN", "SERVICENOW_DOMAIN")


def _load_module():
    spec = importlib.util.spec_from_file_location("export_servicenow_schema", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def mod():
    return _load_module()


@pytest.fixture
def clean_env(monkeypatch):
    for name in ENV_VARS:
        monkeypatch.delenv(name, raising=False)


# ---------------------------------------------------------------------------
# Query construction
# ---------------------------------------------------------------------------


class TestQueryConstruction:
    def test_table_list_comes_from_the_assertion_file(self, mod) -> None:
        """The exporter must not carry its own copy of the table list."""
        tables = mod.tables_from_expected()
        assert "incident" in tables
        assert "sc_request" in tables
        assert len(tables) == 6

    def test_two_jobs_are_built(self, mod) -> None:
        jobs = mod.build_jobs(["incident"])
        assert [j["table"] for j in jobs] == ["sys_dictionary", "sys_db_object"]

    def test_dictionary_query_excludes_empty_elements(self, mod) -> None:
        jobs = mod.build_jobs(["incident", "problem"])
        dictionary = jobs[0]
        assert dictionary["query"] == "nameINincident,problem^elementISNOTEMPTY"

    def test_fields_carry_no_record_data(self, mod) -> None:
        """The field lists are fixed, so record data cannot be pulled by accident."""
        for job in mod.build_jobs(["incident"]):
            fields = set(job["fields"].split(","))
            assert "sys_id" not in fields
            assert not {"short_description", "description", "opened_at"} & fields

    def test_scope_is_requested(self, mod) -> None:
        """scoped-app-unknown is one of the findings the export must settle."""
        for job in mod.build_jobs(["incident"]):
            assert "sys_scope.scope" in job["fields"]


# ---------------------------------------------------------------------------
# Fail-closed behaviour
# ---------------------------------------------------------------------------


class TestFailsClosed:
    def test_no_instance_configured_exits_nonzero(self, mod, clean_env, monkeypatch) -> None:
        monkeypatch.setattr(sys, "argv", ["export_servicenow_schema.py"])
        assert mod.main() == 1

    def test_no_token_exits_nonzero(self, mod, clean_env, monkeypatch) -> None:
        monkeypatch.setenv("SERVICENOW_INSTANCE", "agency-prod")
        monkeypatch.setattr(sys, "argv", ["export_servicenow_schema.py"])
        assert mod.main() == 1

    def test_placeholder_host_is_never_printed(self, mod, clean_env, monkeypatch, capsys) -> None:
        """The collector's 'your-instance' fallback must not surface as a URL."""
        monkeypatch.setattr(sys, "argv", ["export_servicenow_schema.py", "--dry-run"])
        assert mod.main() == 0
        out = capsys.readouterr().out
        assert "your-instance" not in out
        assert "NOT CONFIGURED" in out

    def test_dry_run_writes_nothing(self, mod, clean_env, monkeypatch, capsys) -> None:
        before = set(mod.DEPLOYMENT_DIR.glob("*.json"))
        monkeypatch.setattr(sys, "argv", ["export_servicenow_schema.py", "--dry-run"])
        assert mod.main() == 0
        assert set(mod.DEPLOYMENT_DIR.glob("*.json")) == before

    def test_empty_result_is_not_written(self, mod, clean_env, monkeypatch, tmp_path) -> None:
        """A zero-record response would make the gate report every column missing."""

        class _EmptyCollector:
            base_url = "https://agency-prod.servicenowservices.com"

            def fetch_relevant_records(self, **_: object) -> dict:
                return {"result": []}

        monkeypatch.setenv("SERVICENOW_INSTANCE", "agency-prod")
        monkeypatch.setenv("SERVICENOW_TOKEN", "not-a-real-token")
        monkeypatch.setattr(mod, "ServiceNowCollector", lambda *a, **k: _EmptyCollector())
        monkeypatch.setattr(mod, "DEPLOYMENT_DIR", tmp_path)
        monkeypatch.setattr(sys, "argv", ["export_servicenow_schema.py"])

        assert mod.main() == 1
        assert list(tmp_path.glob("*.json")) == []


# ---------------------------------------------------------------------------
# Successful export
# ---------------------------------------------------------------------------


class TestExport:
    def test_writes_both_artifacts_and_hashes(self, mod, clean_env, monkeypatch, tmp_path, capsys) -> None:
        class _Collector:
            base_url = "https://agency-prod.servicenowservices.com"

            def fetch_relevant_records(self, **_: object) -> dict:
                return {"result": [{"name": "incident", "element": "u_uiao_control_id"}]}

        monkeypatch.setenv("SERVICENOW_INSTANCE", "agency-prod")
        monkeypatch.setenv("SERVICENOW_TOKEN", "not-a-real-token")
        monkeypatch.setattr(mod, "ServiceNowCollector", lambda *a, **k: _Collector())
        monkeypatch.setattr(mod, "DEPLOYMENT_DIR", tmp_path)
        monkeypatch.setattr(sys, "argv", ["export_servicenow_schema.py", "--env", "test"])

        assert mod.main() == 0

        written = sorted(p.name for p in tmp_path.glob("*.json"))
        assert written == ["sys-db-object.test.json", "sys-dictionary.test.json"]

        payload = json.loads((tmp_path / "sys-dictionary.test.json").read_text(encoding="utf-8"))
        assert payload["result"][0]["element"] == "u_uiao_control_id"
        assert "sha256" in capsys.readouterr().out

    def test_export_log_placeholder_is_replaced(self, mod, tmp_path, monkeypatch) -> None:
        readme = tmp_path / "README.md"
        readme.write_text(f"{mod.LOG_HEADER}\n|---|---|---|---|---|\n{mod.LOG_PLACEHOLDER}\n", encoding="utf-8")
        monkeypatch.setattr(mod, "DEPLOYMENT_DIR", tmp_path)

        mod.update_export_log([("sys-dictionary.prod.json", "abc123")], "prod", "2026-08-20", "ops")

        text = readme.read_text(encoding="utf-8")
        assert mod.LOG_PLACEHOLDER not in text
        assert "abc123" in text
        assert "sys-dictionary.prod.json" in text
