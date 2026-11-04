from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Listing, ListingStatus, ListingType
from app.repositories.listings import ListingRejectedError, SqlListingRepository
from tests.fakes import make_listing

NOW = datetime(2026, 11, 2, 12, tzinfo=UTC)


@pytest.fixture
def repository(db_session: AsyncSession) -> SqlListingRepository:
    return SqlListingRepository(db_session)


async def _status(session: AsyncSession, source_listing_id: str) -> ListingStatus:
    statement = select(Listing.status).where(Listing.source_listing_id == source_listing_id)
    return (await session.execute(statement)).scalar_one()


async def test_upsert_inserts_then_updates_without_duplicates(
    repository: SqlListingRepository, db_session: AsyncSession
) -> None:
    assert await repository.upsert(make_listing("1"), seen_at=NOW) is True
    changed = make_listing("1", status=ListingStatus.SOLD)
    assert await repository.upsert(changed, seen_at=NOW + timedelta(hours=1)) is False

    rows = (await db_session.execute(select(Listing))).scalars().all()
    assert len(rows) == 1
    assert rows[0].status is ListingStatus.SOLD
    assert rows[0].last_seen_at == NOW + timedelta(hours=1)


async def test_rejected_upsert_keeps_earlier_listings_in_the_transaction(
    repository: SqlListingRepository, db_session: AsyncSession
) -> None:
    await repository.upsert(make_listing("kept"), seen_at=NOW)
    too_big = make_listing("too-big")
    too_big = replace(too_big, stats=replace(too_big.stats, square_meters=40_000))

    with pytest.raises(ListingRejectedError):
        await repository.upsert(too_big, seen_at=NOW)
    await repository.upsert(make_listing("after"), seen_at=NOW)
    await repository.commit()

    ids = set((await db_session.execute(select(Listing.source_listing_id))).scalars())
    assert ids == {"kept", "after"}


async def test_count_listed_counts_the_sources_unsold_listings(
    repository: SqlListingRepository,
) -> None:
    for status in ListingStatus:
        await repository.upsert(make_listing(status.value, status=status), seen_at=NOW)
    await repository.upsert(make_listing("other", source="other"), seen_at=NOW)

    assert await repository.count_listed("test") == 2


async def test_same_listing_id_from_different_sources_are_separate(
    repository: SqlListingRepository, db_session: AsyncSession
) -> None:
    await repository.upsert(make_listing("1", source="a"), seen_at=NOW)
    await repository.upsert(make_listing("1", source="b"), seen_at=NOW)

    assert await db_session.scalar(select(func.count()).select_from(Listing)) == 2


async def test_mark_removed_only_touches_old_unsold_listings_of_the_source(
    repository: SqlListingRepository, db_session: AsyncSession
) -> None:
    old = NOW - timedelta(days=3)
    await repository.upsert(make_listing("old"), seen_at=old)
    await repository.upsert(make_listing("old-signed", status=ListingStatus.CONTRACT_SIGNED), old)
    await repository.upsert(make_listing("old-sold", status=ListingStatus.SOLD), seen_at=old)
    await repository.upsert(make_listing("recent"), seen_at=NOW - timedelta(days=1))
    await repository.upsert(make_listing("other-source", source="other"), seen_at=old)

    changed = await repository.mark_removed_not_seen_since("test", cutoff=NOW - timedelta(days=2))

    assert changed == 2
    assert await _status(db_session, "old") is ListingStatus.REMOVED
    assert await _status(db_session, "old-signed") is ListingStatus.REMOVED
    assert await _status(db_session, "old-sold") is ListingStatus.SOLD
    assert await _status(db_session, "recent") is ListingStatus.ACTIVE
    assert await _status(db_session, "other-source") is ListingStatus.ACTIVE
    assert await repository.mark_removed_not_seen_since("test", NOW - timedelta(days=2)) == 0


async def test_pick_random_active_only_returns_active_listings_with_images(
    repository: SqlListingRepository,
) -> None:
    await repository.upsert(make_listing("apartment"), seen_at=NOW)
    await repository.upsert(make_listing("house", listing_type=ListingType.HOUSE), seen_at=NOW)
    await repository.upsert(make_listing("no-images", images=[]), seen_at=NOW)
    for status in (ListingStatus.CONTRACT_SIGNED, ListingStatus.SOLD, ListingStatus.REMOVED):
        await repository.upsert(make_listing(status.value, status=status), seen_at=NOW)

    picked = await repository.pick_random_active(5)

    assert sorted(listing.type for listing in picked) == [ListingType.APARTMENT, ListingType.HOUSE]
    apartment = next(listing for listing in picked if listing.type is ListingType.APARTMENT)
    assert apartment.lat == pytest.approx(55.6761)
    assert apartment.lng == pytest.approx(12.5683)
    assert apartment.stats == make_listing().stats
    assert apartment.price == 3_495_000


async def test_pick_random_active_returns_different_listings(
    repository: SqlListingRepository,
) -> None:
    for number in range(8):
        await repository.upsert(make_listing(str(number)), seen_at=NOW)

    picked = await repository.pick_random_active(5)

    assert len({listing.id for listing in picked}) == 5
