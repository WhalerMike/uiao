"""Tests for the OrgPath web console (uiao.api.web.console).

The console is the Azure-Portal-style, read-only governance UI over the
OrgPath Governance Runtime. These tests build a standalone FastAPI app with
the console mounted (avoiding the main app's Entra lifespan) and exercise
each view plus the JSON govern action via TestClient.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from uiao.api.web import console


@pytest.fixture
def client():
    """A TestClient over a standalone app with the console mounted.

    Resets the process-local console state before and after each test so the
    default sample snapshot is always the starting point.
    """
    console.set_state(None)
    app = FastAPI()
    console.mount(app, prefix="/orgpath")
    yield TestClient(app)
    console.set_state(None)


# A minimal valid snapshot with one clean principal and one drifting one.
_SNAPSHOT = {
    "generated_at": "2026-06-02T00:00:00+00:00",
    "principals": [
        {
            "principal_id": "p-clean",
            "principal_type": "user",
            "attributes": {
                "extensionAttribute1": "NCR",
                "extensionAttribute2": "IT",
                "extensionAttribute3": "CyberOps",
                "extensionAttribute4": "Analyst",
                "extensionAttribute5": "CC-4100",
                "extensionAttribute6": "Employee",
                "extensionAttribute7": "2020-01-15",
                "extensionAttribute9": "Secret",
                "extensionAttribute10": "Standard",
            },
        },
        {
            "principal_id": "p-drift",
            "principal_type": "user",
            "attributes": {
                "extensionAttribute1": "NCR",
                "extensionAttribute2": "Marketing",  # unknown department → Value drift
                "extensionAttribute3": "CyberOps",
                "extensionAttribute4": "Analyst",
                "extensionAttribute5": "CC-4100",
                "extensionAttribute6": "Employee",
                "extensionAttribute7": "2020-01-15",
                "extensionAttribute9": "Secret",
                "extensionAttribute10": "Standard",
            },
        },
    ],
}


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------


def test_dashboard_renders(client: TestClient) -> None:
    resp = client.get("/orgpath/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    body = resp.text
    assert "OrgPath Governance — Overview" in body
    assert "Drift findings" in body
    assert "Telemetry feed" in body


def test_codebook_explorer_lists_facets(client: TestClient) -> None:
    resp = client.get("/orgpath/codebook")
    assert resp.status_code == 200
    body = resp.text
    assert "Codebook explorer" in body
    assert "region" in body
    assert "department" in body
    assert "extensionAttribute1" in body


def test_principals_page_without_id_prompts_selection(client: TestClient) -> None:
    resp = client.get("/orgpath/principals")
    assert resp.status_code == 200
    body = resp.text
    # Sample snapshot ids are listed as quick links.
    assert "u-1001" in body
    assert "Select a principal" in body


def test_principal_lookup_shows_facet_rows(client: TestClient) -> None:
    resp = client.get("/orgpath/principals", params={"id": "u-1001"})
    assert resp.status_code == 200
    body = resp.text
    assert "u-1001" in body
    # A clean principal has no drifted facet status.
    assert "status-drift" not in body
    assert "region" in body and "department" in body


def test_principal_lookup_flags_drift(client: TestClient) -> None:
    # u-1004 in the sample carries an unknown clearance → drift status.
    resp = client.get("/orgpath/principals", params={"id": "u-1004"})
    assert resp.status_code == 200
    assert "status-drift" in resp.text


def test_principal_lookup_unknown_id(client: TestClient) -> None:
    resp = client.get("/orgpath/principals", params={"id": "does-not-exist"})
    assert resp.status_code == 200
    assert "No principal" in resp.text


def test_govern_page_renders(client: TestClient) -> None:
    resp = client.get("/orgpath/govern")
    assert resp.status_code == 200
    assert "Run a governance pass" in resp.text
    assert "/orgpath/static/app.js" in resp.text


# ---------------------------------------------------------------------------
# JSON action — POST /orgpath/api/govern
# ---------------------------------------------------------------------------


def test_run_governance_returns_report(client: TestClient) -> None:
    resp = client.post("/orgpath/api/govern", json=_SNAPSHOT)
    assert resp.status_code == 200
    data = resp.json()
    assert data["snapshot_id"] == "snap-2026-06-02T00:00:00+00:00"
    assert data["drift_count"] >= 1  # the Marketing department row, at least
    assert "events" in data and "severity_counts" in data


def test_run_governance_sets_active_snapshot(client: TestClient) -> None:
    client.post("/orgpath/api/govern", json=_SNAPSHOT)
    # The principal page now reflects the posted snapshot, not the sample.
    resp = client.get("/orgpath/principals", params={"id": "p-drift"})
    assert resp.status_code == 200
    assert "p-drift" in resp.text


def test_run_governance_rejects_malformed_snapshot(client: TestClient) -> None:
    resp = client.post("/orgpath/api/govern", json={"principals": [{"attributes": {}}]})
    assert resp.status_code == 400
    assert resp.json()["error"] == "invalid_snapshot"


# ---------------------------------------------------------------------------
# Static assets
# ---------------------------------------------------------------------------


def test_static_css_served(client: TestClient) -> None:
    resp = client.get("/orgpath/static/app.css")
    assert resp.status_code == 200
    assert "--accent" in resp.text


def test_static_js_served(client: TestClient) -> None:
    resp = client.get("/orgpath/static/app.js")
    assert resp.status_code == 200
    assert "api/govern" in resp.text
