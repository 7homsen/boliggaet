import uuid
from dataclasses import dataclass, replace
from datetime import date, datetime

from app.db.models import EnergyRating, ListingStatus, ListingType
from app.repositories.listings import GameListing, ListingStats, NormalisedListing


def make_stats(listing_type: ListingType = ListingType.APARTMENT) -> ListingStats:
    return ListingStats(
        energy_rating=EnergyRating.C,
        build_year=1932,
        renovation_year=2015,
        floors=5,
        floor=3 if listing_type is ListingType.APARTMENT else None,
        rooms=3,
        bathrooms=1,
        toilets=1,
        square_meters=82,
        listed_date=date(2026, 8, 14),
    )


def make_listing(
    source_listing_id: str = "1",
    listing_type: ListingType = ListingType.APARTMENT,
    status: ListingStatus = ListingStatus.ACTIVE,
    images: list[str] | None = None,
    source: str = "test",
) -> NormalisedListing:
    return NormalisedListing(
        source=source,
        source_listing_id=source_listing_id,
        source_url=f"https://example.com/{source_listing_id}",
        type=listing_type,
        lat=55.6761,
        lng=12.5683,
        images=["https://example.com/image.jpg"] if images is None else images,
        floor_plans=["https://example.com/plan.jpg"],
        stats=make_stats(listing_type),
        price=3_495_000,
        status=status,
    )


def make_game_listing(listing_type: ListingType = ListingType.APARTMENT) -> GameListing:
    listing = make_listing(listing_type=listing_type)
    return GameListing(
        id=uuid.uuid4(),
        type=listing.type,
        lat=listing.lat,
        lng=listing.lng,
        images=listing.images,
        floor_plans=listing.floor_plans,
        stats=listing.stats,
        price=listing.price,
    )


class FakeGameListingRepository:
    def __init__(self, listings: list[GameListing]) -> None:
        self.listings = listings

    async def pick_random_active(self, count: int) -> list[GameListing]:
        return self.listings[:count]


@dataclass
class StoredListing:
    listing: NormalisedListing
    status: ListingStatus
    last_seen_at: datetime


class FakeScraperListingRepository:
    def __init__(self) -> None:
        self.stored: dict[tuple[str, str], StoredListing] = {}
        self.commits = 0

    async def upsert(self, listing: NormalisedListing, seen_at: datetime) -> bool:
        key = (listing.source, listing.source_listing_id)
        is_new = key not in self.stored
        self.stored[key] = StoredListing(listing, listing.status, seen_at)
        return is_new

    async def mark_removed_not_seen_since(self, source: str, cutoff: datetime) -> int:
        changed = 0
        for key, stored in self.stored.items():
            if (
                key[0] == source
                and stored.last_seen_at < cutoff
                and stored.status not in (ListingStatus.SOLD, ListingStatus.REMOVED)
            ):
                self.stored[key] = replace(stored, status=ListingStatus.REMOVED)
                changed += 1
        return changed

    async def commit(self) -> None:
        self.commits += 1
