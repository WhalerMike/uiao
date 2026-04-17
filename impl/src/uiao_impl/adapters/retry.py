"""
retry.py — Shared retry/throttle utilities for UIAO adapters.

Provides exponential-backoff retry logic and rate-limit handling
for adapters that interact with rate-limited vendor APIs
(Graph API, ServiceNow, CyberArk, Infoblox, etc.).

Usage in adapters:
    from .retry import with_retry, RateLimitError

    result = with_retry(lambda: api_call(), max_retries=3)
"""

from __future__ import annotations

import logging
import time
from typing import Callable, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RateLimitError(Exception):
    """Raised when a vendor API returns a rate-limit response (429, 503, etc.)."""

    def __init__(self, message: str = "", retry_after: Optional[float] = None):
        super().__init__(message)
        self.retry_after = retry_after


class TransientError(Exception):
    """Raised on transient failures (network timeout, 500, connection reset)."""
    pass


def with_retry(
    fn: Callable[[], T],
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    backoff_factor: float = 2.0,
    retryable_exceptions: tuple = (RateLimitError, TransientError, ConnectionError, TimeoutError),
) -> T:
    """Execute fn() with exponential-backoff retry on transient failures.

    Args:
        fn: Zero-arg callable to execute.
        max_retries: Maximum number of retry attempts (0 = no retry).
        base_delay: Initial delay in seconds before first retry.
        max_delay: Maximum delay between retries.
        backoff_factor: Multiplier applied to delay on each retry.
        retryable_exceptions: Tuple of exception types that trigger retry.

    Returns:
        The result of fn() on success.

    Raises:
        The last exception if all retries are exhausted.
    """
    last_exception: Optional[Exception] = None
    delay = base_delay

    for attempt in range(max_retries + 1):
        try:
            return fn()
        except retryable_exceptions as exc:
            last_exception = exc
            if attempt == max_retries:
                logger.warning(
                    "Retry exhausted after %d attempts: %s",
                    max_retries + 1, exc,
                )
                raise

            # Respect Retry-After header if available
            if isinstance(exc, RateLimitError) and exc.retry_after:
                actual_delay = min(exc.retry_after, max_delay)
            else:
                actual_delay = min(delay, max_delay)

            logger.info(
                "Attempt %d/%d failed (%s), retrying in %.1fs",
                attempt + 1, max_retries + 1, type(exc).__name__, actual_delay,
            )
            time.sleep(actual_delay)
            delay *= backoff_factor

    # Should never reach here, but satisfy type checker
    raise last_exception  # type: ignore[misc]


def parse_retry_after(header_value: str) -> Optional[float]:
    """Parse a Retry-After header value (seconds or HTTP-date).

    Args:
        header_value: Raw header value string.

    Returns:
        Delay in seconds, or None if unparseable.
    """
    try:
        return float(header_value)
    except (ValueError, TypeError):
        return None
