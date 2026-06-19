"""Unit tests for passwordless (Entra) Postgres auth token caching.

Pure stdlib — the token acquirer and clock are injected, so neither
``azure-identity`` nor ``sqlalchemy`` (the ``[saas]`` extra) is needed. This
mirrors the dependency-isolation doctrine: the token-cache logic is covered by
the blocking ``[api]`` CI job.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from uiao.saas.pg_auth import (
    OSSRDBMS_SCOPE_COMMERCIAL,
    OSSRDBMS_SCOPE_USGOV,
    EntraPostgresTokenProvider,
    ossrdbms_scope_for,
)


@dataclass
class _FakeToken:
    token: str
    expires_on: int


class _FakeClock:
    def __init__(self, t: float = 1000.0) -> None:
        self.t = t

    def __call__(self) -> float:
        return self.t


class _Acquirer:
    """Records calls and hands out a sequence of tokens."""

    def __init__(self, *, ttl: int = 3600, clock: _FakeClock) -> None:
        self.calls = 0
        self._ttl = ttl
        self._clock = clock

    def __call__(self, scope: str) -> _FakeToken:
        self.calls += 1
        return _FakeToken(token=f"tok-{self.calls}", expires_on=int(self._clock()) + self._ttl)


# --------------------------------------------------------------------------
# scope selection
# --------------------------------------------------------------------------
def test_scope_for_commercial_and_gcc_moderate():
    assert ossrdbms_scope_for("commercial") == OSSRDBMS_SCOPE_COMMERCIAL


@pytest.mark.parametrize("cloud", ["gcc-high", "dod"])
def test_scope_for_sovereign(cloud):
    assert ossrdbms_scope_for(cloud) == OSSRDBMS_SCOPE_USGOV


def test_provider_uses_requested_scope():
    clock = _FakeClock()
    acq = _Acquirer(clock=clock)
    captured = {}

    def _capture(scope):
        captured["scope"] = scope
        return acq(scope)

    provider = EntraPostgresTokenProvider(acquire=_capture, scope=OSSRDBMS_SCOPE_USGOV, clock=clock)
    provider.token()
    assert captured["scope"] == OSSRDBMS_SCOPE_USGOV


# --------------------------------------------------------------------------
# caching + refresh
# --------------------------------------------------------------------------
def test_token_is_cached_between_calls():
    clock = _FakeClock()
    acq = _Acquirer(clock=clock)
    provider = EntraPostgresTokenProvider(acquire=acq, clock=clock)
    first = provider.token()
    second = provider.token()
    assert first == second == "tok-1"
    assert acq.calls == 1  # only acquired once


def test_token_refreshes_within_margin_of_expiry():
    clock = _FakeClock()
    acq = _Acquirer(ttl=3600, clock=clock)
    provider = EntraPostgresTokenProvider(acquire=acq, refresh_margin=300.0, clock=clock)
    assert provider.token() == "tok-1"
    # Advance to just inside the refresh margin (expiry - 299s) -> re-acquire.
    clock.t += 3600 - 299
    assert provider.token() == "tok-2"
    assert acq.calls == 2


def test_token_not_refreshed_before_margin():
    clock = _FakeClock()
    acq = _Acquirer(ttl=3600, clock=clock)
    provider = EntraPostgresTokenProvider(acquire=acq, refresh_margin=300.0, clock=clock)
    provider.token()
    # Advance to comfortably before the margin (expiry - 600s) -> still cached.
    clock.t += 3600 - 600
    provider.token()
    assert acq.calls == 1


def test_invalidate_forces_reacquire():
    clock = _FakeClock()
    acq = _Acquirer(clock=clock)
    provider = EntraPostgresTokenProvider(acquire=acq, clock=clock)
    provider.token()
    provider.invalidate()
    provider.token()
    assert acq.calls == 2


def test_negative_refresh_margin_rejected():
    with pytest.raises(ValueError):
        EntraPostgresTokenProvider(refresh_margin=-1.0)
