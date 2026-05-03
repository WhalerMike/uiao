"""Tier-1 plumbing stubs for the ``service-now`` adapter.

Roadmap §2.1. Operations exercised (per roadmap):
  1. Incident creation
  2. Change-request creation
  3. Status read

Each test below resolves credentials via the ``tier1_creds`` fixture, which
skips with a clear message when sandbox env vars are absent. The actual API
calls are deliberately not implemented yet — the body is a TODO marker plus
the exact endpoint and assertion contract so the implementing PR is a
fill-in-the-blanks exercise.

When sandbox access lands:
  1. Replace each ``_NOT_IMPLEMENTED`` block with the live HTTP call.
  2. Run ``UIAO_TIER1_RECORD=1 pytest tests/integration/tier1/test_service_now_tier1.py``
     to capture responses.
  3. Sanitize captures and promote to ``tests/fixtures/contract/service-now/``
     per the contract README.
"""

from __future__ import annotations

import pytest

REQUIRED_VARS = [
    "SERVICENOW_PDI_INSTANCE",   # e.g. dev123456.service-now.com
    "SERVICENOW_PDI_USER",
    "SERVICENOW_PDI_PASSWORD",
]

_NOT_IMPLEMENTED_MSG = (
    "tier-1 plumbing-only stub: ServiceNow PDI access pending per roadmap §2.1. "
    "Replace with live HTTP call + assertions when sandbox credentials are wired."
)


@pytest.mark.tier1
def test_create_incident(tier1_creds, record_response):
    """POST /api/now/table/incident with a minimal incident record.

    Endpoint: ``https://<INSTANCE>/api/now/table/incident``
    Auth: HTTP Basic (PDI_USER / PDI_PASSWORD)
    Expected: 201 + JSON body with ``result.sys_id`` and ``result.number``
    Cleanup: DELETE /api/now/table/incident/{sys_id}
    """
    creds = tier1_creds("service-now", REQUIRED_VARS)
    assert creds  # ensures the fixture's contract is honored even in stubs
    pytest.skip(_NOT_IMPLEMENTED_MSG)


@pytest.mark.tier1
def test_create_change_request(tier1_creds, record_response):
    """POST /api/now/table/change_request with a Standard change.

    Endpoint: ``https://<INSTANCE>/api/now/table/change_request``
    Body MUST set ``type=standard`` to avoid CAB-approval blocking.
    Expected: 201 + JSON body with ``result.sys_id`` and ``result.number``
    Cleanup: DELETE /api/now/table/change_request/{sys_id}
    """
    creds = tier1_creds("service-now", REQUIRED_VARS)
    assert creds
    pytest.skip(_NOT_IMPLEMENTED_MSG)


@pytest.mark.tier1
def test_status_read(tier1_creds, record_response):
    """GET /api/now/table/sys_user?sysparm_limit=1 — cheapest non-mutating call.

    Used as a freshness/health probe. Expected: 200 + non-empty result array.
    A failure here is a hard FAIL of the entire tier-1 suite for service-now.
    """
    creds = tier1_creds("service-now", REQUIRED_VARS)
    assert creds
    pytest.skip(_NOT_IMPLEMENTED_MSG)
