"""Tests for the retry/throttle utility."""

from __future__ import annotations

import pytest

from uiao_impl.adapters.retry import (
    RateLimitError,
    TransientError,
    with_retry,
    parse_retry_after,
)


class TestWithRetry:
    def test_success_no_retry(self) -> None:
        result = with_retry(lambda: 42)
        assert result == 42

    def test_retries_on_transient(self) -> None:
        attempts = {"count": 0}

        def flaky():
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise TransientError("flake")
            return "ok"

        result = with_retry(flaky, max_retries=3, base_delay=0.01)
        assert result == "ok"
        assert attempts["count"] == 3

    def test_exhausts_retries(self) -> None:
        def always_fail():
            raise TransientError("permanent")

        with pytest.raises(TransientError, match="permanent"):
            with_retry(always_fail, max_retries=2, base_delay=0.01)

    def test_rate_limit_respected(self) -> None:
        attempts = {"count": 0}

        def rate_limited():
            attempts["count"] += 1
            if attempts["count"] == 1:
                raise RateLimitError("429", retry_after=0.01)
            return "ok"

        result = with_retry(rate_limited, max_retries=2, base_delay=0.01)
        assert result == "ok"

    def test_non_retryable_raises_immediately(self) -> None:
        def type_error():
            raise TypeError("not retryable")

        with pytest.raises(TypeError):
            with_retry(type_error, max_retries=3, base_delay=0.01)

    def test_zero_retries(self) -> None:
        def fail():
            raise TransientError("no retry")

        with pytest.raises(TransientError):
            with_retry(fail, max_retries=0)


class TestParseRetryAfter:
    def test_numeric(self) -> None:
        assert parse_retry_after("30") == 30.0

    def test_float(self) -> None:
        assert parse_retry_after("1.5") == 1.5

    def test_invalid(self) -> None:
        assert parse_retry_after("not-a-number") is None

    def test_empty(self) -> None:
        assert parse_retry_after("") is None
