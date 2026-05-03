"""Tier-1 (live-tenant) test fixtures.

Per UIAO_131 §3.1, tier-1 tests run against a real vendor tenant. Every
test in this package depends on credentials. When credentials are absent
(developer machine without secrets, CI without provisioned secrets), tests
skip cleanly so the suite is always green.

This conftest provides:
  - ``tier1_creds`` factory — returns a dict of resolved env vars OR calls
    ``pytest.skip`` if any required var is missing.
  - The ``tier1`` pytest marker — registered here so ``-m tier1`` works.

Do NOT add helpers that hit vendor APIs here. Per-adapter HTTP clients live
next to their tests so each can evolve independently.
"""

from __future__ import annotations

import os
from typing import Iterable

import pytest


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "tier1: live-tenant test, requires vendor credentials in environment.",
    )


@pytest.fixture
def tier1_creds():
    """Returns a callable ``(adapter, required_vars) -> dict``.

    The callable resolves each var in ``required_vars`` from the
    environment and returns a dict mapping var-name -> value. If any var is
    missing or empty, it raises ``pytest.skip`` with a precise message
    naming the adapter and the missing vars. This is the canonical way for a
    tier-1 test to declare its credential dependency.

    Usage::

        def test_something(tier1_creds):
            creds = tier1_creds(
                "service-now",
                ["SERVICENOW_PDI_INSTANCE", "SERVICENOW_PDI_USER", "SERVICENOW_PDI_PASSWORD"],
            )
            ...
    """

    def _resolve(adapter: str, required_vars: Iterable[str]) -> dict[str, str]:
        missing: list[str] = []
        resolved: dict[str, str] = {}
        for var in required_vars:
            value = os.environ.get(var, "")
            if not value:
                missing.append(var)
            else:
                resolved[var] = value
        if missing:
            pytest.skip(
                f"tier-1 {adapter}: required environment variable(s) not set: "
                + ", ".join(missing)
                + ". See tests/integration/README.md for sandbox setup."
            )
        return resolved

    return _resolve
