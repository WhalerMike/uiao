"""The IIS uvicorn entrypoint's port-fallback chain (deploy/windows-server/run.py).

Round-3 review: zero coverage existed for the UIAO_API_PORT /
HTTP_PLATFORM_PORT fallback that binds the process behind
HttpPlatformHandler. The module is imported by path (it is a deploy
script, not a package member); importing it must not start uvicorn.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

pytest.importorskip("uvicorn")

_RUN_PY = Path(__file__).resolve().parents[1] / "deploy" / "windows-server" / "run.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("uiao_deploy_run", _RUN_PY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_import_does_not_launch_server() -> None:
    module = _load_module()
    assert hasattr(module, "resolve_port")


def test_uiao_api_port_wins() -> None:
    module = _load_module()
    assert module.resolve_port({"UIAO_API_PORT": "9001", "HTTP_PLATFORM_PORT": "5000"}) == 9001


def test_http_platform_port_is_the_iis_fallback() -> None:
    module = _load_module()
    assert module.resolve_port({"HTTP_PLATFORM_PORT": "5000"}) == 5000


def test_default_is_8000() -> None:
    module = _load_module()
    assert module.resolve_port({}) == 8000
