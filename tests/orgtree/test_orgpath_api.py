"""Tests for the per-facet OrgPath FastAPI route (ADR-084 §C7)."""

from __future__ import annotations


import pytest
from fastapi.testclient import TestClient

from uiao.api.routes import orgpath as orgpath_route
from uiao.governance.drift_engine import DriftEngine
from uiao.modernization.orgtree.types import PrincipalSnapshot, Snapshot


@pytest.fixture
def api_client(codebook_model_c):
    """Build a TestClient with the orgpath route + injected suppliers."""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(orgpath_route.router, prefix="/api/v1/orgpath")

    # Inject the fixture Codebook so the route doesn't try to load YAML.
    orgpath_route.set_codebook_supplier(lambda: codebook_model_c)

    # Clear suppliers between tests.
    orgpath_route.set_principal_supplier(None)
    orgpath_route.set_report_supplier(None)
    yield TestClient(app)
    # Reset to default after test
    from uiao.modernization.orgtree.codebook import default_codebook

    orgpath_route.set_codebook_supplier(default_codebook)
    orgpath_route.set_principal_supplier(None)
    orgpath_route.set_report_supplier(None)


# ---------------------------------------------------------------------------
# GET /codebook
# ---------------------------------------------------------------------------


def test_get_codebook_returns_all_facets(api_client):
    resp = api_client.get("/api/v1/orgpath/codebook")
    assert resp.status_code == 200
    data = resp.json()
    assert data["schema_version"] == "2.0.0"
    assert data["model"] == "C"
    facet_names = {f["name"] for f in data["facets"]}
    assert "region" in facet_names
    assert "department" in facet_names
    assert "reserved_11" in facet_names


def test_get_codebook_serializes_enumeration(api_client):
    resp = api_client.get("/api/v1/orgpath/codebook")
    data = resp.json()
    region = next(f for f in data["facets"] if f["name"] == "region")
    region_values = {v["value"] for v in region["enumeration"]}
    assert "NCR" in region_values
    assert "EASTUS" in region_values


def test_get_codebook_serializes_deprecated(api_client):
    resp = api_client.get("/api/v1/orgpath/codebook")
    data = resp.json()
    division = next(f for f in data["facets"] if f["name"] == "division")
    deprecated = {d["value"]: d["replaced_by"] for d in division["deprecated"]}
    assert deprecated == {"OldCyber": "CyberOps"}


def test_get_codebook_serializes_typed_facet(api_client):
    resp = api_client.get("/api/v1/orgpath/codebook")
    data = resp.json()
    hire_date = next(f for f in data["facets"] if f["name"] == "hire_date")
    assert hire_date["kind"] == "typed"
    assert hire_date["value_type"] == "date"
    assert hire_date["value_pattern"] == r"^\d{4}-\d{2}-\d{2}$"


def test_get_codebook_serializes_reserved_facet(api_client):
    resp = api_client.get("/api/v1/orgpath/codebook")
    data = resp.json()
    reserved = next(f for f in data["facets"] if f["name"] == "reserved_11")
    assert reserved["kind"] == "reserved"
    assert reserved["enumeration"] == []


# ---------------------------------------------------------------------------
# GET /principals/{id}/facets
# ---------------------------------------------------------------------------


def test_get_principal_facets_returns_503_without_supplier(api_client):
    resp = api_client.get("/api/v1/orgpath/principals/alice/facets")
    assert resp.status_code == 503
    assert "principal supplier" in resp.json()["detail"]


def test_get_principal_facets_returns_404_when_missing(api_client):
    orgpath_route.set_principal_supplier(lambda pid: None)
    resp = api_client.get("/api/v1/orgpath/principals/alice/facets")
    assert resp.status_code == 404


def test_get_principal_facets_returns_10_facet_values(api_client):
    snap = PrincipalSnapshot(
        principal_id="alice",
        principal_type="user",
        attributes={
            "extensionAttribute1": "EASTUS",
            "extensionAttribute2": "IT",
            "extensionAttribute3": "InfraOps",
            "extensionAttribute4": "Engineer",
            "extensionAttribute5": "CC-BAL",
            "extensionAttribute6": "Employee",
            "extensionAttribute7": "2024-01-15",
            "extensionAttribute8": "",
            "extensionAttribute9": "Secret",
            "extensionAttribute10": "Standard",
        },
    )
    orgpath_route.set_principal_supplier(lambda pid: snap if pid == "alice" else None)
    resp = api_client.get("/api/v1/orgpath/principals/alice/facets")
    assert resp.status_code == 200
    data = resp.json()
    assert data["principal_id"] == "alice"
    assert data["principal_type"] == "user"
    assert data["facets"]["extensionAttribute1"] == "EASTUS"
    assert data["facets"]["extensionAttribute2"] == "IT"


# ---------------------------------------------------------------------------
# GET /drift
# ---------------------------------------------------------------------------


def test_get_drift_returns_503_without_supplier(api_client):
    resp = api_client.get("/api/v1/orgpath/drift")
    assert resp.status_code == 503


def test_get_drift_returns_404_when_no_report(api_client):
    orgpath_route.set_report_supplier(lambda: None)
    resp = api_client.get("/api/v1/orgpath/drift")
    assert resp.status_code == 404


def test_get_drift_returns_findings(api_client, codebook_model_c):
    p = PrincipalSnapshot(
        principal_id="u1",
        principal_type="user",
        attributes={"extensionAttribute2": "BogusDept"},
    )
    engine = DriftEngine(codebook_model_c, {})
    snap = Snapshot.now(principals=(p,))
    report = engine.run(snap)
    orgpath_route.set_report_supplier(lambda: report)

    resp = api_client.get("/api/v1/orgpath/drift")
    assert resp.status_code == 200
    data = resp.json()
    assert data["finding_count"] >= 1
    value_findings = [f for f in data["findings"] if f["drift_category"] == "Value"]
    assert any(f["facet"] == "department" for f in value_findings)


# ---------------------------------------------------------------------------
# POST /validate
# ---------------------------------------------------------------------------


def test_validate_active_value(api_client):
    resp = api_client.post("/api/v1/orgpath/validate", json={"facet": "region", "value": "NCR"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_active"] is True
    assert data["is_deprecated"] is False
    assert data["replacement_for"] is None


def test_validate_unknown_value(api_client):
    resp = api_client.post("/api/v1/orgpath/validate", json={"facet": "region", "value": "MARS"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_active"] is False
    assert data["is_deprecated"] is False


def test_validate_deprecated_value_returns_replacement(api_client):
    resp = api_client.post("/api/v1/orgpath/validate", json={"facet": "division", "value": "OldCyber"})
    data = resp.json()
    assert data["is_active"] is False
    assert data["is_deprecated"] is True
    assert data["replacement_for"] == "CyberOps"


def test_validate_typed_facet_iso_date(api_client):
    resp = api_client.post("/api/v1/orgpath/validate", json={"facet": "hire_date", "value": "2024-01-15"})
    assert resp.json()["is_active"] is True


def test_validate_typed_facet_bad_format(api_client):
    resp = api_client.post("/api/v1/orgpath/validate", json={"facet": "hire_date", "value": "01/15/2024"})
    assert resp.json()["is_active"] is False


def test_validate_unknown_facet_returns_404(api_client):
    resp = api_client.post("/api/v1/orgpath/validate", json={"facet": "nonexistent", "value": "x"})
    assert resp.status_code == 404
