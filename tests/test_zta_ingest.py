"""Tests for uiao.adapters.zta.ingest — JSON / HTML loading and reportData extraction."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from uiao.adapters.zta.ingest import ZtIngestError, extract_report_data, load_report

FIXTURES = Path(__file__).parent / "fixtures" / "zta"
MINI_JSON = FIXTURES / "sample-mini.json"
MINI_HTML = FIXTURES / "sample-mini.html"


def test_load_json_fixture():
    report = load_report(MINI_JSON)
    assert report.tenant_name == "Fixture Corp"
    assert report.is_demo is True
    assert len(report.tests) == 7


def test_html_and_json_are_equivalent():
    from_json = load_report(MINI_JSON)
    from_html = load_report(MINI_HTML)
    assert len(from_json.tests) == len(from_html.tests)
    assert [t.test_id for t in from_json.tests] == [t.test_id for t in from_html.tests]
    assert from_json.tenant_name == from_html.tenant_name


def test_int_test_id_is_coerced_to_str():
    report = load_report(MINI_JSON)
    planned = [t for t in report.tests if t.test_status == "Planned"][0]
    assert planned.test_id == "23004"
    assert isinstance(planned.test_id, str)


def test_string_license_is_coerced_to_list():
    report = load_report(MINI_JSON)
    passed = [t for t in report.tests if t.test_status == "Passed"][0]
    assert passed.test_minimum_license == ["AAD_PREMIUM_P2"]


def test_extract_report_data_anchors_on_assignment():
    html = MINI_HTML.read_text(encoding="utf-8")
    obj = extract_report_data(html)
    assert obj["TenantName"] == "Fixture Corp"
    assert len(obj["Tests"]) == 7


def test_extract_report_data_fallback_anchor():
    # No `reportData =` assignment; only the bare object beginning with ExecutedAt.
    data = json.loads(MINI_JSON.read_text(encoding="utf-8"))
    blob = json.dumps(data, separators=(",", ":"))
    html = f"<html><body><script>{blob}</script></body></html>"
    obj = extract_report_data(html)
    assert len(obj["Tests"]) == 7


def test_unknown_extension_sniffs_json(tmp_path: Path):
    target = tmp_path / "report.txt"
    target.write_text(MINI_JSON.read_text(encoding="utf-8"), encoding="utf-8")
    report = load_report(target)
    assert len(report.tests) == 7


def test_missing_file_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_report(tmp_path / "nope.json")


def test_non_report_html_raises():
    with pytest.raises(ZtIngestError):
        extract_report_data("<html><body>no data here</body></html>")
