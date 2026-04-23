"""tests/test_cql_engine.py — UIAO_108 CQL engine tests."""

from __future__ import annotations
import pytest
from uiao.cql import parse, CQLEngine, CQLParseError

CONTROLS = [
    {"id": "AC-2", "status": "FAIL", "severity": "High", "last_assessed": "2026-04-20T00:00:00Z"},
    {"id": "IA-2", "status": "PASS", "severity": "Low", "last_assessed": "2026-04-20T00:00:00Z"},
    {"id": "AC-21", "status": "FAIL", "severity": "Medium", "last_assessed": "2026-04-20T00:00:00Z"},
]
EVIDENCE = [
    {
        "id": "EV-001",
        "control_id": "AC-2",
        "verdict": "fail",
        "status": "not-satisfied",
        "generated_at": "2026-04-20T00:00:00Z",
    },
    {
        "id": "EV-002",
        "control_id": "IA-2",
        "verdict": "pass",
        "status": "satisfied",
        "generated_at": "2026-04-20T00:00:00Z",
    },
    {
        "id": "EV-003",
        "control_id": "AC-21",
        "verdict": "fail",
        "status": "not-satisfied",
        "generated_at": "2025-01-01T00:00:00Z",
    },
]
DRIFT = [
    {"id": "D-001", "tenant": "contoso", "control": "IA-2", "drift_class": "DRIFT-SEMANTIC"},
]
POAM = [
    {"id": "POAM-001", "status": "Open", "severity": "High", "control_id": "AC-2"},
    {"id": "POAM-002", "status": "Closed", "severity": "Medium", "control_id": "IA-2"},
    {"id": "POAM-003", "status": "Open", "severity": "Critical", "control_id": "AC-21"},
]


def engine():
    return CQLEngine(controls=CONTROLS, evidence=EVIDENCE, drift=DRIFT, poam=POAM)


class TestParser:
    def test_parse_controls_where(self):
        q = parse("SHOW CONTROLS WHERE status = 'FAIL'")
        assert q.query_type == "CONTROLS"
        assert q.filters == [("status", "=", "FAIL")]

    def test_parse_evidence_for_control_since(self):
        q = parse("SHOW EVIDENCE FOR CONTROL 'AC-21' SINCE '2026-04-01'")
        assert q.query_type == "EVIDENCE"
        assert q.for_control == "AC-21"
        assert q.since == "2026-04-01"

    def test_parse_drift_where(self):
        q = parse("SHOW DRIFT WHERE tenant = 'contoso' AND control = 'IA-2'")
        assert q.query_type == "DRIFT"
        assert len(q.filters) == 2

    def test_parse_poam_order_by(self):
        q = parse("SHOW POAM WHERE status = 'Open' ORDER BY severity DESC")
        assert q.query_type == "POAM"
        assert q.order_by == "severity"
        assert q.order_dir == "DESC"

    def test_parse_strips_semicolon(self):
        q = parse("SHOW CONTROLS WHERE status = 'FAIL';")
        assert q.query_type == "CONTROLS"

    def test_parse_invalid_raises(self):
        with pytest.raises(CQLParseError):
            parse("SELECT * FROM controls")


class TestControlsQuery:
    def test_filter_by_status_fail(self):
        r = engine().execute("SHOW CONTROLS WHERE status = 'FAIL'")
        assert r.total == 2
        assert all(c["status"] == "FAIL" for c in r.records)

    def test_filter_by_status_pass(self):
        r = engine().execute("SHOW CONTROLS WHERE status = 'PASS'")
        assert r.total == 1
        assert r.records[0]["id"] == "IA-2"

    def test_no_filter_returns_all(self):
        r = engine().execute("SHOW CONTROLS")
        assert r.total == 3

    def test_severity_gte_medium(self):
        r = engine().execute("SHOW CONTROLS WHERE severity >= 'Medium'")
        ids = [c["id"] for c in r.records]
        assert "AC-2" in ids
        assert "AC-21" in ids
        assert "IA-2" not in ids


class TestEvidenceQuery:
    def test_for_control_filter(self):
        r = engine().execute("SHOW EVIDENCE FOR CONTROL 'AC-2'")
        assert r.total == 1
        assert r.records[0]["id"] == "EV-001"

    def test_since_filter(self):
        r = engine().execute("SHOW EVIDENCE FOR CONTROL 'AC-21' SINCE '2026-01-01'")
        assert r.total == 0

    def test_verdict_filter(self):
        r = engine().execute("SHOW EVIDENCE WHERE verdict = 'fail'")
        assert r.total == 2


class TestDriftQuery:
    def test_filter_by_tenant(self):
        r = engine().execute("SHOW DRIFT WHERE tenant = 'contoso'")
        assert r.total == 1

    def test_filter_no_match(self):
        r = engine().execute("SHOW DRIFT WHERE tenant = 'agency'")
        assert r.total == 0


class TestPOAMQuery:
    def test_open_poam(self):
        r = engine().execute("SHOW POAM WHERE status = 'Open'")
        assert r.total == 2

    def test_order_by_severity_desc(self):
        r = engine().execute("SHOW POAM WHERE status = 'Open' ORDER BY severity DESC")
        assert r.records[0]["severity"] == "Critical"

    def test_closed_poam(self):
        r = engine().execute("SHOW POAM WHERE status = 'Closed'")
        assert r.total == 1


class TestCQLResult:
    def test_to_dict_has_required_keys(self):
        r = engine().execute("SHOW CONTROLS WHERE status = 'FAIL'")
        d = r.to_dict()
        assert all(k in d for k in ("query_type", "total", "records", "cql", "executed_at"))
