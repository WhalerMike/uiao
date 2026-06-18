"""SASL mechanism state-machine tests (ADR-101).

The multi-step machinery is exercised with a fake mechanism — no Kerberos
stack needed. The GSSAPI adapter is covered only for its missing-dependency
guard (gssapi is an optional [kerberos] extra).
"""

from __future__ import annotations

import pytest

from uiao.directory.sasl import GssapiMechanism, SaslError, SaslMechanism, SaslResult


class _FakeMechanism(SaslMechanism):
    """A scripted mechanism: N challenges, then succeed (or fail)."""

    name = "FAKE"

    def __init__(self, *, challenges: int = 0, succeed: bool = True, principal: str = "alice@REALM") -> None:
        self._remaining = challenges
        self._succeed = succeed
        self._principal = principal

    def step(self, token: bytes | None) -> SaslResult:
        if self._remaining > 0:
            self._remaining -= 1
            return SaslResult.challenge(b"server-token")
        if self._succeed:
            return SaslResult.ok(self._principal)
        return SaslResult.fail("nope")


def test_single_step_success() -> None:
    result = _FakeMechanism().step(b"client-token")
    assert result.done and result.success
    assert result.principal == "alice@REALM"


def test_multi_step_challenge_then_success() -> None:
    mech = _FakeMechanism(challenges=2)
    first = mech.step(b"t1")
    assert not first.done and first.response_token == b"server-token"
    second = mech.step(b"t2")
    assert not second.done
    third = mech.step(b"t3")
    assert third.done and third.success


def test_failure_result() -> None:
    result = _FakeMechanism(succeed=False).step(b"t")
    assert result.done and not result.success
    assert result.message == "nope"


def test_sasl_result_factories() -> None:
    assert SaslResult.challenge(b"x").response_token == b"x"
    assert SaslResult.ok("p@R").principal == "p@R"
    assert SaslResult.fail("bad").message == "bad"


def test_gssapi_without_extra_raises_sasl_error() -> None:
    # gssapi is the optional [kerberos] extra; absent it, construction must
    # fail loudly with SaslError (never silently degrade).
    try:
        import gssapi  # noqa: F401
    except ImportError:
        with pytest.raises(SaslError):
            GssapiMechanism()
    else:  # pragma: no cover - only when [kerberos] is installed
        pytest.skip("gssapi installed; missing-dependency path not exercised")
