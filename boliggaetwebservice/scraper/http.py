import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any

import httpx

USER_AGENT = "BoliggaetScraper/0.1 (property price guessing game; respects robots.txt)"

_RETRY_STATUS_CODES = {429, 500, 502, 503, 504}


class RateLimitedClient:
    """HTTP client for one source: identifies itself, rate-limits and retries with backoff."""

    def __init__(
        self,
        requests_per_second: float = 1.0,
        max_retries: int = 3,
        backoff_seconds: float = 2.0,
        transport: httpx.AsyncBaseTransport | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._min_interval = 1.0 / requests_per_second
        self._max_retries = max_retries
        self._backoff_seconds = backoff_seconds
        self._sleep = sleep
        self._clock = clock
        self._lock = asyncio.Lock()
        self._last_request_at: float | None = None
        self._client = httpx.AsyncClient(
            headers={"User-Agent": USER_AGENT},
            transport=transport,
            timeout=30.0,
            follow_redirects=True,
        )

    async def get(self, url: str, **kwargs: Any) -> httpx.Response:
        """GET a URL. Raises httpx.HTTPError once the retries are used up."""
        attempt = 0
        while True:
            await self._wait_for_turn()
            try:
                response = await self._client.get(url, **kwargs)
                if response.status_code not in _RETRY_STATUS_CODES:
                    return response.raise_for_status()
                if attempt >= self._max_retries:
                    return response.raise_for_status()
            except httpx.TransportError:
                if attempt >= self._max_retries:
                    raise
            await self._sleep(self._backoff_seconds * 2**attempt)
            attempt += 1

    async def _wait_for_turn(self) -> None:
        async with self._lock:
            if self._last_request_at is not None:
                wait = self._last_request_at + self._min_interval - self._clock()
                if wait > 0:
                    await self._sleep(wait)
            self._last_request_at = self._clock()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "RateLimitedClient":
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()
