"""Unit tests for passwordless (AWS RDS IAM) Postgres auth token caching.

Pure stdlib — the token generator and clock are injected, so neither ``boto3``
nor ``sqlalchemy`` (the ``[aws]`` extra) is needed. Mirrors the Entra provider
tests (test_saas_pg_auth) and the dependency-isolation doctrine.
"""

from __future__ import annotations

import pytest

from uiao.saas.aws_pg_auth import RDS_IAM_TOKEN_TTL_SECONDS, RdsIamTokenProvider


class _FakeClock:
    def __init__(self, t: float = 1000.0) -> None:
        self.t = t

    def __call__(self) -> float:
        return self.t


class _Generator:
    """Records calls + the arguments it was signed with."""

    def __init__(self) -> None:
        self.calls = 0
        self.last_args: tuple | None = None

    def __call__(self, host: str, port: int, user: str, region: str) -> str:
        self.calls += 1
        self.last_args = (host, port, user, region)
        return f"iam-tok-{self.calls}"


def _provider(gen, clock, **kw) -> RdsIamTokenProvider:
    return RdsIamTokenProvider(
        hostname="db.example.rds.amazonaws.com",
        username="uiao_app",
        region="us-east-1",
        generate=gen,
        clock=clock,
        **kw,
    )


# --------------------------------------------------------------------------
# construction validation
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    "kw",
    [
        {"hostname": "", "username": "u", "region": "r"},
        {"hostname": "h", "username": "", "region": "r"},
        {"hostname": "h", "username": "u", "region": ""},
    ],
)
def test_missing_required_fields_rejected(kw):
    with pytest.raises(ValueError):
        RdsIamTokenProvider(**kw)


def test_refresh_margin_must_be_smaller_than_ttl():
    with pytest.raises(ValueError):
        RdsIamTokenProvider(hostname="h", username="u", region="r", ttl=900, refresh_margin=900)


# --------------------------------------------------------------------------
# signing arguments
# --------------------------------------------------------------------------
def test_token_signed_with_connection_coordinates():
    gen = _Generator()
    provider = _provider(gen, _FakeClock(), port=5432)
    provider.token()
    assert gen.last_args == ("db.example.rds.amazonaws.com", 5432, "uiao_app", "us-east-1")


# --------------------------------------------------------------------------
# caching + refresh
# --------------------------------------------------------------------------
def test_token_cached_between_calls():
    gen = _Generator()
    clock = _FakeClock()
    provider = _provider(gen, clock)
    assert provider.token() == provider.token() == "iam-tok-1"
    assert gen.calls == 1


def test_token_regenerates_within_margin():
    gen = _Generator()
    clock = _FakeClock()
    provider = _provider(gen, clock, ttl=900, refresh_margin=120)
    assert provider.token() == "iam-tok-1"
    clock.t += 900 - 119  # inside the refresh margin
    assert provider.token() == "iam-tok-2"
    assert gen.calls == 2


def test_token_not_regenerated_before_margin():
    gen = _Generator()
    clock = _FakeClock()
    provider = _provider(gen, clock, ttl=900, refresh_margin=120)
    provider.token()
    clock.t += 900 - 300  # comfortably before the margin
    provider.token()
    assert gen.calls == 1


def test_invalidate_forces_regenerate():
    gen = _Generator()
    provider = _provider(gen, _FakeClock())
    provider.token()
    provider.invalidate()
    provider.token()
    assert gen.calls == 2


def test_default_ttl_constant():
    assert RDS_IAM_TOKEN_TTL_SECONDS == 900.0
