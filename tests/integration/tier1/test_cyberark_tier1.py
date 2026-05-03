"""Tier-1 plumbing stubs for the ``cyberark`` adapter.

Roadmap §2.3. Operations exercised (per roadmap):
  1. Vault account enumeration
  2. Rotation simulation

Target: CyberArk Privilege Cloud trial. Authentication uses OAuth2 client
credentials against the tenant's Identity Service:
  POST https://<TENANT>/oauth2/platformtoken → access_token
  GET  https://<TENANT>/PasswordVault/API/Accounts
"""

from __future__ import annotations

import pytest

REQUIRED_VARS = [
    "CYBERARK_TENANT",  # e.g. abc123.privilegecloud.cyberark.cloud
    "CYBERARK_CLIENT_ID",
    "CYBERARK_CLIENT_SECRET",
]

_NOT_IMPLEMENTED_MSG = (
    "tier-1 plumbing-only stub: CyberArk Privilege Cloud trial pending per roadmap §2.3. "
    "Replace with live HTTP call + assertions when sandbox credentials are wired."
)


@pytest.mark.tier1
def test_vault_account_enumeration(tier1_creds, record_response):
    """GET /PasswordVault/API/Accounts?limit=10.

    Expected: 200 + JSON ``{value: [...], count: N}``. Each element has
    ``id``, ``name``, ``platformId``, ``safeName``, ``userName``. Adapter's
    canonical claim emits one account-record per element.
    """
    creds = tier1_creds("cyberark", REQUIRED_VARS)
    assert creds
    pytest.skip(_NOT_IMPLEMENTED_MSG)


@pytest.mark.tier1
def test_rotation_simulation(tier1_creds, record_response):
    """POST /PasswordVault/API/Accounts/{accountId}/Change with ``ChangeImmediately=true``.

    Simulation, not enforcement: pick a known test account in a dedicated
    rotation-test safe (operator MUST set CYBERARK_TEST_SAFE in env to
    confirm intent). Expected: 200 + verification that the next read
    surfaces a new ``lastModifiedDate``.

    Skip if CYBERARK_TEST_SAFE is unset — we never want to rotate against
    an unspecified safe.
    """
    creds = tier1_creds(
        "cyberark",
        [*REQUIRED_VARS, "CYBERARK_TEST_SAFE"],
    )
    assert creds
    pytest.skip(_NOT_IMPLEMENTED_MSG)
