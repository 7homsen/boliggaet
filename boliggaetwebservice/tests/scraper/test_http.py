from collections.abc import Callable

import httpx
import pytest

from scraper.http import USER_AGENT, RateLimitedClient


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.now

    async def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def _client(
    handler: Callable[[httpx.Request], httpx.Response], clock: FakeClock
) -> RateLimitedClient:
    return RateLimitedClient(transport=httpx.MockTransport(handler), sleep=clock.sleep, clock=clock)


async def test_sends_user_agent() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.headers["User-Agent"])
        return httpx.Response(200)

    async with _client(handler, FakeClock()) as client:
        await client.get("https://example.com/")

    assert seen == [USER_AGENT]


async def test_waits_between_requests_to_stay_at_one_per_second() -> None:
    clock = FakeClock()
    async with _client(lambda request: httpx.Response(200), clock) as client:
        await client.get("https://example.com/1")
        clock.now += 0.25
        await client.get("https://example.com/2")

    assert clock.sleeps == [0.75]


async def test_retries_server_errors_with_backoff() -> None:
    responses = iter([httpx.Response(503), httpx.Response(429), httpx.Response(200)])
    clock = FakeClock()

    async with _client(lambda request: next(responses), clock) as client:
        response = await client.get("https://example.com/")

    assert response.status_code == 200
    assert clock.sleeps == [2.0, 4.0]


async def test_retries_transport_errors() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise httpx.ConnectError("refused")
        return httpx.Response(200)

    async with _client(handler, FakeClock()) as client:
        assert (await client.get("https://example.com/")).status_code == 200


async def test_gives_up_after_max_retries() -> None:
    clock = FakeClock()
    async with _client(lambda request: httpx.Response(500), clock) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await client.get("https://example.com/")

    assert clock.sleeps == [2.0, 4.0, 8.0]


async def test_does_not_retry_client_errors() -> None:
    clock = FakeClock()
    async with _client(lambda request: httpx.Response(404), clock) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await client.get("https://example.com/")

    assert clock.sleeps == []
