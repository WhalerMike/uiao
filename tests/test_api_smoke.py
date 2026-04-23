"""Smoke tests for the FastAPI service entrypoint at `uiao.api.app:app`.

This is the entrypoint IIS uvicorn launches via `deploy/windows-server/run.py`.
A latent deploy-time breakage (the hyphen-named adapter directories
`active-directory/` and `gcc-boundary-probe/` that Python could not import as
packages — see ADR-032 follow-through, PR #155) went undetected for weeks
because no test ever tried to import the app. These tests close that gap:
they fail loudly when an upstream change makes the app unimportable or
silently drops a registered route.

Skipped entirely when the `[api]` optional extra is not installed; CI runs
them because `pytest.yml` installs `pip install -e ".[api]"`.
"""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("msal")
pytest.importorskip("httpx")


def test_api_app_is_importable() -> None:
    """The uvicorn entrypoint module resolves to a FastAPI instance."""
    from fastapi import FastAPI

    from uiao.api.app import app

    assert isinstance(app, FastAPI), f"expected FastAPI, got {type(app)!r}"


def test_api_app_has_expected_route_prefixes() -> None:
    """Every router registered in src/uiao/api/app.py is reachable on the app.

    Prefix expectations come from app.include_router() calls:
      - health:  no prefix
      - survey:  /api/v1/survey
      - orgpath: /api/v1/orgpath
      - auditor: /api/auditor

    Each prefix must match at least one registered route's path.
    """
    from uiao.api.app import app

    registered_paths = [route.path for route in app.routes if hasattr(route, "path")]

    expected_prefixes = ("/api/v1/survey", "/api/v1/orgpath", "/api/auditor")
    for prefix in expected_prefixes:
        assert any(path.startswith(prefix) for path in registered_paths), (
            f"no route registered under {prefix!r}; routes={registered_paths}"
        )

    # Health router has no prefix; presence check is that *some* non-prefixed
    # route ended up on the app (FastAPI auto-adds /openapi.json /docs /redoc
    # too, but those are fine signals that the app was constructed).
    assert registered_paths, "app has no routes at all"


def test_api_app_openapi_schema_builds() -> None:
    """FastAPI can generate an OpenAPI schema from the app. Catches the
    class of bug where a handler's type hints reference a symbol that no
    longer exists — the route imports succeed but schema generation fails."""
    from uiao.api.app import app

    schema = app.openapi()
    assert isinstance(schema, dict)
    assert "paths" in schema
    assert schema["paths"], "OpenAPI schema has zero paths"
