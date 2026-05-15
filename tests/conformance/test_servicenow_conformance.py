"""ServiceNow Adapter Conformance Tests (WS-A5).

Pairs the adapter against tier-2 fixtures from WS-A4 (skip-if-missing
pattern) and exercises end-to-end behaviours: normalize, drift, and
write-side round-trips.

Skip policy
-----------
- Fixture files: skipped with reason when the tier-2 fixture file is absent
  (WS-A4 not yet merged to this branch).
- WS-A1 write methods: skipped with reason when methods are not yet on the
  adapter (WS-A1 not yet merged).
- WS-A2 OSCAL emitter: skipped with reason when the emitter module is absent.

References
----------
- inbox/v0.6.1-servicenow/00-phase0-plan.md §WS-A5
- src/uiao/adapters/servicenow_adapter.py
- tests/fixtures/tier-2/servicenow/
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from uiao.adapters.servicenow_adapter import ServiceNowAdapter

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_TIER2_ROOT = Path(__file__).parent.parent / "fixtures" / "tier-2" / "servicenow"

_F_INCIDENT_CREATE = _TIER2_ROOT / "incident-create.json"
_F_INCIDENT_UPDATE = _TIER2_ROOT / "incident-update.json"
_F_CHANGE_REQUEST = _TIER2_ROOT / "change-request-create.json"
_F_QUERY_EMPTY = _TIER2_ROOT / "query-result-empty.json"
_F_QUERY_3_RECORDS = _TIER2_ROOT / "query-result-3-records.json"

# Fallback: canonical 4-record fixture present on main branch
_F_QUERY_FALLBACK = Path(__file__).parent.parent / "fixtures" / "servicenow-incidents.json"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_fixture(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _adapter() -> ServiceNowAdapter:
    return ServiceNowAdapter({"instance": "uiao-dev", "token": ""})


# ---------------------------------------------------------------------------
# Write-method availability guard
# ---------------------------------------------------------------------------

_HAS_WRITE_METHODS = all(
    hasattr(ServiceNowAdapter, m) for m in ("create_incident", "update_incident", "create_change_request")
)


# ---------------------------------------------------------------------------
# OSCAL emitter availability guard
# ---------------------------------------------------------------------------


def _oscal_emitter_available() -> bool:
    try:
        mod = importlib.import_module("uiao.oscal.servicenow_evidence")
        return hasattr(mod, "emit_servicenow_component_definition")
    except ImportError:
        return False


# ---------------------------------------------------------------------------
# 1. incident-create.json fixture → create_incident() returns matching evidence
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not _F_INCIDENT_CREATE.exists(),
    reason="WS-A4 fixture incident-create.json not yet merged — skipping",
)
@pytest.mark.skipif(
    not _HAS_WRITE_METHODS,
    reason="WS-A1 write methods not yet merged — skipping",
)
def test_incident_create_fixture_matches_evidence() -> None:
    """incident-create.json fixture → create_incident() returns matching evidence."""
    fixture = _load_fixture(_F_INCIDENT_CREATE)
    req_body = fixture["request"]["body"]
    resp_body = fixture["response"]["body"]["result"]
    mock_response = {"result": resp_body}

    adapter = _adapter()
    with patch.object(adapter.collector, "post_record", return_value=mock_response):
        result = adapter.create_incident(
            short_description=req_body.get("short_description", ""),
            uiao_control_id=req_body.get("uiao_control_id", "AC-2"),
        )

    assert result["ok"] is True
    assert result["sys_id"] == resp_body.get("sys_id", "")
    assert result["evidence"]["source"] == "servicenow"


# ---------------------------------------------------------------------------
# 2. incident-update.json fixture → update_incident() round-trips
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not _F_INCIDENT_UPDATE.exists(),
    reason="WS-A4 fixture incident-update.json not present — skipping",
)
@pytest.mark.skipif(
    not _HAS_WRITE_METHODS,
    reason="WS-A1 write methods not yet merged — skipping",
)
def test_incident_update_fixture_round_trips() -> None:
    """incident-update.json fixture → update_incident() round-trips."""
    fixture = _load_fixture(_F_INCIDENT_UPDATE)
    req_body = fixture["request"]["body"]
    resp_result = fixture["response"]["body"]["result"]
    sys_id: str = resp_result["sys_id"]
    mock_response = {"result": resp_result}

    adapter = _adapter()
    with patch.object(adapter.collector, "patch_record", return_value=mock_response):
        result = adapter.update_incident(sys_id, **req_body)

    assert result["ok"] is True
    # sys_id MUST be preserved across the PATCH
    assert result["sys_id"] == sys_id
    assert result["error"] is None


# ---------------------------------------------------------------------------
# 3. query-result-3-records.json fixture → normalize() produces 3 claims
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not _F_QUERY_3_RECORDS.exists() and not _F_QUERY_FALLBACK.exists(),
    reason="No query-result fixture available — skipping",
)
def test_query_result_three_records_produces_three_claims() -> None:
    """normalize() MUST produce exactly 3 claims from a 3-record query result."""
    if _F_QUERY_3_RECORDS.exists():
        raw = _load_fixture(_F_QUERY_3_RECORDS)
        records = raw.get("response", {}).get("body", {}).get("result", raw.get("result", []))
    else:
        # Fallback: first 3 records from the canonical 4-record fixture
        raw = _load_fixture(_F_QUERY_FALLBACK)
        records = raw.get("result", [])[:3]

    adapter = _adapter()
    claim_set = adapter.normalize(records)

    assert len(claim_set.claims) == 3


# ---------------------------------------------------------------------------
# 4. query-result-empty.json fixture → normalize() produces 0 claims
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not _F_QUERY_EMPTY.exists() and not _F_QUERY_FALLBACK.exists(),
    reason="No query-result fixture available — skipping",
)
def test_query_result_empty_produces_zero_claims() -> None:
    """normalize() MUST produce 0 claims from an empty result list."""
    if _F_QUERY_EMPTY.exists():
        fixture = _load_fixture(_F_QUERY_EMPTY)
        records = fixture.get("response", {}).get("body", {}).get("result", [])
    else:
        # Fallback: synthesize an empty result set
        records = []

    adapter = _adapter()
    claim_set = adapter.normalize(records)

    assert len(claim_set.claims) == 0


# ---------------------------------------------------------------------------
# 5. End-to-end: collector → normalize → emit-oscal
#    (skip if WS-A2 emitter not merged)
# ---------------------------------------------------------------------------


def test_collect_normalize_oscal_end_to_end() -> None:
    """End-to-end: collector → normalize → OSCAL emission (skip if WS-A2 absent)."""
    if not _oscal_emitter_available():
        pytest.skip("WS-A2 OSCAL emitter (uiao.oscal.servicenow_evidence) not yet merged — skipping")

    from uiao.oscal.servicenow_evidence import emit_servicenow_component_definition  # noqa: PLC0415

    adapter = _adapter()
    # collector returns empty scaffold (no token) — safe for CI
    result = adapter.collect_and_align()
    claims = result.get("claims", {}).get("claims", [])

    # WS-A2 signature: (claims, tenant_id, signer, signing_key)
    component_def = emit_servicenow_component_definition(
        claims,
        tenant_id="test-tenant-conformance",
        signer="conformance-test",
        signing_key=b"conformance-test-key-do-not-use-in-prod",
    )
    assert component_def is not None
    assert isinstance(component_def, dict)


# ---------------------------------------------------------------------------
# 6. End-to-end drift: synthesize divergence, detect_drift() flags it
# ---------------------------------------------------------------------------


def test_end_to_end_drift_detection_flags_divergence() -> None:
    """Synthesise a drifted record set and verify detect_drift() returns high severity."""
    adapter = _adapter()

    synthetic_records = [
        {"sys_id": "INC-SYNTH-001", "short_description": "unauthorized ticket outside canon scope"},
        {"sys_id": "INC-SYNTH-002", "short_description": "another undocumented change"},
    ]
    drifted = [{**r, "_drift": "new_record"} for r in synthetic_records]

    with (
        patch.object(
            adapter.collector,
            "fetch_relevant_records",
            return_value={"result": synthetic_records},
        ),
        patch.object(
            adapter.collector,
            "compare_for_drift",
            return_value=drifted,
        ),
    ):
        report = adapter.detect_drift()

    assert report.severity == "high"
    assert report.drift_type == "servicenow-record-divergence"
    assert report.details["drifted_count"] == 2
    assert "INC-SYNTH-001" in report.details["new_records"]
    assert "INC-SYNTH-002" in report.details["new_records"]
    assert report.remediation is not None and len(report.remediation) > 0
