"""tests/test_auditor_api.py — UIAO_105 Auditor API tests."""
from __future__ import annotations
import pytest
from fastapi.testclient import TestClient

def _make_client():
    from uiao.api.routes.auditor import router
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router, prefix="/api/auditor")
    return TestClient(app)

CLIENT = _make_client()
HEADERS = {"Authorization": "Bearer test-token"}

class TestEvidenceEndpoints:
    def test_list_evidence_no_auth_returns_401(self):
        r = CLIENT.get("/api/auditor/evidence")
        assert r.status_code == 401

    def test_list_evidence_with_token_returns_200(self):
        r = CLIENT.get("/api/auditor/evidence", headers=HEADERS)
        assert r.status_code == 200
        data = r.json()
        assert "evidence" in data
        assert "total" in data
        assert "generated_at" in data

    def test_list_evidence_filters_accepted(self):
        r = CLIENT.get("/api/auditor/evidence?control_id=IA-2&status=satisfied", headers=HEADERS)
        assert r.status_code == 200
        data = r.json()
        assert data["filters"]["control_id"] == "IA-2"

    def test_get_evidence_by_id_not_found(self):
        r = CLIENT.get("/api/auditor/evidence/EV-NONEXISTENT", headers=HEADERS)
        assert r.status_code == 404

class TestFindingsEndpoints:
    def test_list_findings_requires_auth(self):
        r = CLIENT.get("/api/auditor/findings")
        assert r.status_code == 401

    def test_list_findings_returns_200(self):
        r = CLIENT.get("/api/auditor/findings", headers=HEADERS)
        assert r.status_code == 200
        data = r.json()
        assert "findings" in data
        assert "total" in data

    def test_list_findings_severity_filter(self):
        r = CLIENT.get("/api/auditor/findings?severity=P1", headers=HEADERS)
        assert r.status_code == 200

class TestPOAMEndpoints:
    def test_poam_requires_auth(self):
        r = CLIENT.get("/api/auditor/poam")
        assert r.status_code == 401

    def test_poam_returns_200(self):
        r = CLIENT.get("/api/auditor/poam", headers=HEADERS)
        assert r.status_code == 200
        data = r.json()
        assert "poam_entries" in data

class TestOSCALEndpoints:
    def test_sar_requires_auth(self):
        r = CLIENT.get("/api/auditor/oscal/sar")
        assert r.status_code == 401

    def test_sar_returns_200(self):
        r = CLIENT.get("/api/auditor/oscal/sar", headers=HEADERS)
        assert r.status_code == 200

    def test_ssp_returns_200(self):
        r = CLIENT.get("/api/auditor/oscal/ssp", headers=HEADERS)
        assert r.status_code == 200

    def test_poam_oscal_returns_200(self):
        r = CLIENT.get("/api/auditor/oscal/poam", headers=HEADERS)
        assert r.status_code == 200

    def test_sap_returns_200(self):
        r = CLIENT.get("/api/auditor/oscal/sap", headers=HEADERS)
        assert r.status_code == 200

class TestGraphEndpoint:
    def test_graph_requires_auth(self):
        r = CLIENT.get("/api/auditor/graph/AC-2")
        assert r.status_code == 401

    def test_graph_returns_200(self):
        r = CLIENT.get("/api/auditor/graph/AC-2", headers=HEADERS)
        assert r.status_code == 200
        data = r.json()
        assert "control_id" in data
        assert data["control_id"] == "AC-2"
        assert "evidence_count" in data
        assert "findings_count" in data
