"""Tests for the concrete ARM transport (``uiao.adapters.arm_transport``).

The live ARM dispatch is not exercised against a real tenant (no creds);
tests verify the URL/auth wiring with a stubbed token + httpx
MockTransport, mirroring the GraphTransport coverage in
``test_orgpath_assess_cli.py``. The decisive assertions are that an
ARM-relative resource path joins onto ``management.azure.com`` (and the
Government host for sovereign clouds) — *not* onto a Graph host.
"""

from __future__ import annotations

import httpx

from uiao.adapters.arm_transport import ArmTransport

_ARC_MACHINE = (
    "/subscriptions/00000000-0000-0000-0000-000000000000"
    "/resourceGroups/rg-arc/providers/Microsoft.HybridCompute/machines/srv-01"
    "?api-version=2023-03-15-preview"
)


class _StubTokens:
    def get_auth_headers(self) -> dict[str, str]:
        return {"Authorization": "Bearer stub-arm-token"}


def test_arm_transport_resolves_commercial_base() -> None:
    t = ArmTransport(_StubTokens(), cloud="commercial")  # type: ignore[arg-type]
    assert t._url(_ARC_MACHINE) == f"https://management.azure.com{_ARC_MACHINE}"


def test_arm_transport_resolves_government_base() -> None:
    t = ArmTransport(_StubTokens(), cloud="gcc-high")  # type: ignore[arg-type]
    assert t._url("/subscriptions/x").startswith("https://management.usgovcloudapi.net/")
    # And crucially it is NOT a Graph host.
    assert "graph.microsoft" not in t._url("/subscriptions/x")


def test_arm_transport_passes_absolute_url_through() -> None:
    t = ArmTransport(_StubTokens(), cloud="commercial")  # type: ignore[arg-type]
    absolute = "https://management.azure.com/subscriptions/x?api-version=2023-03-15-preview"
    assert t._url(absolute) == absolute


def test_arm_transport_dispatches_via_httpx(monkeypatch) -> None:
    captured: dict[str, str | None] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("authorization")
        return httpx.Response(200, json={"id": "srv-01", "tags": {"Region": "EASTUS"}})

    real_client = httpx.Client

    def fake_client(*args, **kwargs):  # noqa: ANN002, ANN003
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "Client", fake_client)

    t = ArmTransport(_StubTokens(), cloud="commercial")  # type: ignore[arg-type]
    resp = t("PATCH", _ARC_MACHINE, {"tags": {"Region": "EASTUS"}})
    assert resp == {"id": "srv-01", "tags": {"Region": "EASTUS"}}
    assert captured["method"] == "PATCH"
    assert captured["url"] == f"https://management.azure.com{_ARC_MACHINE}"
    assert captured["auth"] == "Bearer stub-arm-token"


def test_arm_transport_returns_empty_dict_on_204(monkeypatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(204)

    real_client = httpx.Client

    def fake_client(*args, **kwargs):  # noqa: ANN002, ANN003
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "Client", fake_client)

    t = ArmTransport(_StubTokens(), cloud="commercial")  # type: ignore[arg-type]
    assert t("PATCH", _ARC_MACHINE, {"tags": {}}) == {}
