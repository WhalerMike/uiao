"""Tier-1 plumbing stubs for the ``palo-alto`` adapter.

Roadmap §2.2. Operations exercised (per roadmap):
  1. Security policy read
  2. Rule audit

Target: PAN-OS XML API on a vendor eval VM or XSOAR developer instance.
XML API root: ``https://<HOST>/api/?type=...&key=<API_KEY>``.
"""

from __future__ import annotations

import pytest

REQUIRED_VARS = [
    "PANOS_HOST",  # full URL of the eval VM, RFC1918 inside the dev VPC
    "PANOS_API_KEY",
]

_NOT_IMPLEMENTED_MSG = (
    "tier-1 plumbing-only stub: PAN-OS sandbox access pending per roadmap §2.2. "
    "Replace with live HTTP call + assertions when sandbox credentials are wired."
)


@pytest.mark.tier1
def test_security_policy_read(tier1_creds, record_response):
    """GET <HOST>/api/?type=op&cmd=<show><running><security-policy></security-policy></running></show>&key=<API_KEY>.

    Expected: 200 + XML body containing one or more ``<entry>`` elements,
    each with ``name``, ``from``, ``to``, ``source``, ``destination``,
    ``application``, ``action``.
    """
    creds = tier1_creds("palo-alto", REQUIRED_VARS)
    assert creds
    pytest.skip(_NOT_IMPLEMENTED_MSG)


@pytest.mark.tier1
def test_rule_audit(tier1_creds, record_response):
    """GET <HOST>/api/?type=op&cmd=<show><rule-hit-count><...></...></rule-hit-count></show>&key=<API_KEY>.

    Audit perspective: each security policy rule should have an
    accompanying hit-count. Expected: 200 + XML body where every rule from
    test_security_policy_read has a ``hit-count`` element (zero is allowed;
    missing is a fail).
    """
    creds = tier1_creds("palo-alto", REQUIRED_VARS)
    assert creds
    pytest.skip(_NOT_IMPLEMENTED_MSG)
