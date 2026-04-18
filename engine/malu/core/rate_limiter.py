from __future__ import annotations

import asyncio
import time

from malu.utils.logger import get_logger

log = get_logger("rate_limiter")


class TokenBucket:
    """Token bucket for a single endpoint."""

    def __init__(self, rate: int, capacity: int | None = None):
        self.rate = rate  # tokens per second
        self.capacity = capacity or rate
        self.tokens = float(self.capacity)
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    def _refill(self):
        now = time.monotonic()
        elapsed = now - self._last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self._last_refill = now

    async def acquire(self):
        while True:
            async with self._lock:
                self._refill()
                if self.tokens >= 1.0:
                    self.tokens -= 1.0
                    return
                wait_time = (1.0 - self.tokens) / self.rate
            await asyncio.sleep(wait_time)

    def update_remaining(self, remaining: int, reset_ms: int | None = None):
        """Self-correct from Bybit response headers."""
        self.tokens = min(self.capacity, float(remaining))
        if reset_ms and remaining == 0:
            log.warning("rate_limit_exhausted", reset_ms=reset_ms)


class APIRateLimiter:
    """Manages rate limiting across all Bybit API endpoints.

    Multiple bots share one API key, so all calls must go through this limiter.
    Bybit V5 limits: 10 req/s for order endpoints, 20 req/s for market data.
    """

    DEFAULT_LIMITS = {
        "order": 10,
        "position": 10,
        "market": 20,
        "account": 10,
    }

    def __init__(self, overrides: dict[str, int] | None = None):
        limits = {**self.DEFAULT_LIMITS, **(overrides or {})}
        self._buckets: dict[str, TokenBucket] = {
            name: TokenBucket(rate=rate) for name, rate in limits.items()
        }
        self._default_bucket = TokenBucket(rate=10)

    async def acquire(self, endpoint: str = "order") -> None:
        bucket = self._buckets.get(endpoint, self._default_bucket)
        await bucket.acquire()

    def update_from_headers(self, endpoint: str, headers: dict) -> None:
        remaining = headers.get("X-Bapi-Limit-Status")
        reset_ms = headers.get("X-Bapi-Limit-Reset-Timestamp")
        if remaining is not None:
            bucket = self._buckets.get(endpoint, self._default_bucket)
            bucket.update_remaining(
                int(remaining),
                int(reset_ms) if reset_ms else None,
            )
