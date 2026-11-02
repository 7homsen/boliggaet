import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import pytest
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Listing, ListingStatus
from app.db.session import get_session
from app.main import app
from app.repositories.listings import ScraperListingRepository, SqlListingRepository
from scraper.runner import run_all, run_source
from scraper.source import FetchResult, Source
from scraper.sources.sample import DEFAULT_PATH, SampleSource
from tests.fakes import FakeScraperListingRepository, make_listing

NOW = datetime(2026, 11, 2, 12, tzinfo=UTC)


class StaticSource:
    def __init__(self, result: FetchResult, name: str = "test") -> None:
        self.name = name
        self._result = result

    async def fetch(self) -> FetchResult:
        return self._result


class BrokenSource:
    name = "broken"

    async def fetch(self) -> FetchResult:
        raise RuntimeError("source is down")


async def test_run_source_counts_new_updated_deactivated_and_failed() -> None:
    repository = FakeScraperListingRepository()
    await repository.upsert(make_listing("existing"), seen_at=NOW - timedelta(days=1))
    await repository.upsert(make_listing("gone"), seen_at=NOW - timedelta(days=3))
    source = StaticSource(FetchResult([make_listing("existing"), make_listing("new")], failed=1))

    summary = await run_source(source, repository, NOW)

    assert (summary.new, summary.updated, summary.deactivated, summary.failed) == (1, 1, 1, 1)
    assert repository.stored[("test", "gone")].status is ListingStatus.REMOVED
    assert repository.commits == 1


async def test_run_all_continues_after_a_failing_source() -> None:
    repository = FakeScraperListingRepository()

    @asynccontextmanager
    async def scope() -> AsyncIterator[ScraperListingRepository]:
        yield repository

    sources: list[Source] = [BrokenSource(), StaticSource(FetchResult([make_listing("1")]))]
    all_ok = await run_all(sources, scope, now=lambda: NOW)

    assert all_ok is False
    assert ("test", "1") in repository.stored


# Acceptance scenario from docs/specs/backend-foundation/spec.md, against the test database.


def _sample_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = json.loads(DEFAULT_PATH.read_text(encoding="utf-8"))
    return records


def _write_records(path: Path, records: list[dict[str, Any]]) -> None:
    path.write_text(json.dumps(records), encoding="utf-8")


async def _run_sample(session: AsyncSession, path: Path, now: datetime) -> None:
    await run_source(SampleSource(path), SqlListingRepository(session), now)


async def _game_ids(session: AsyncSession) -> set[str]:
    async def override() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_session] = override
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            ids: set[str] = set()
            # Enough random draws that a listing that can be picked shows up.
            for _ in range(20):
                response = await client.get("/game")
                assert response.status_code == 200
                ids |= {listing["id"] for listing in response.json()["listings"]}
            return ids
    finally:
        app.dependency_overrides.clear()


async def _listing(session: AsyncSession, source_listing_id: str) -> Listing:
    statement = select(Listing).where(Listing.source_listing_id == source_listing_id)
    listing = (await session.execute(statement)).scalar_one()
    await session.refresh(listing)
    return listing


@pytest.fixture
def sample_file(tmp_path: Path) -> Path:
    path = tmp_path / "sample_listings.json"
    path.write_text(json.dumps(_sample_records()), encoding="utf-8")
    return path


async def test_repeated_runs_create_no_duplicates(
    db_session: AsyncSession, sample_file: Path
) -> None:
    await _run_sample(db_session, sample_file, NOW)
    await _run_sample(db_session, sample_file, NOW + timedelta(hours=1))

    count = await db_session.scalar(select(func.count()).select_from(Listing))
    assert count == len((await SampleSource(sample_file).fetch()).listings)


async def test_missing_listing_is_removed_after_grace_period_and_returns_when_back(
    db_session: AsyncSession, sample_file: Path
) -> None:
    records = _sample_records()
    missing = next(record for record in records if record["status"] == "active")
    await _run_sample(db_session, sample_file, NOW)
    missing_id = str((await _listing(db_session, missing["id"])).id)

    _write_records(sample_file, [record for record in records if record is not missing])
    await _run_sample(db_session, sample_file, NOW + timedelta(days=1))
    assert (await _listing(db_session, missing["id"])).status is ListingStatus.ACTIVE

    await db_session.execute(
        update(Listing)
        .where(Listing.source_listing_id == missing["id"])
        .values(last_seen_at=NOW - timedelta(days=3))
    )
    await _run_sample(db_session, sample_file, NOW + timedelta(days=1))
    assert (await _listing(db_session, missing["id"])).status is ListingStatus.REMOVED
    assert missing_id not in await _game_ids(db_session)

    _write_records(sample_file, records)
    await _run_sample(db_session, sample_file, NOW + timedelta(days=2))
    assert (await _listing(db_session, missing["id"])).status is ListingStatus.ACTIVE


async def test_game_never_returns_signed_or_sold_listings(
    db_session: AsyncSession, sample_file: Path
) -> None:
    await _run_sample(db_session, sample_file, NOW)
    excluded = {
        str((await _listing(db_session, record["id"])).id)
        for record in _sample_records()
        if record["status"] in ("contract_signed", "sold")
    }

    assert excluded
    assert excluded.isdisjoint(await _game_ids(db_session))


async def test_game_returns_503_with_too_few_active_listings(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    path = tmp_path / "few.json"
    active = [record for record in _sample_records() if record["status"] == "active"]
    path.write_text(json.dumps(active[:4]), encoding="utf-8")
    await _run_sample(db_session, path, NOW)

    async def override() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_session] = override
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/game")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
