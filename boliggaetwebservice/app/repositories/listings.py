import uuid
from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol

from geoalchemy2 import Geometry, WKTElement
from sqlalchemy import Boolean, cast, func, literal_column, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EnergyRating, Listing, ListingStatus, ListingType


@dataclass(frozen=True)
class ListingStats:
    energy_rating: EnergyRating | None
    build_year: int | None
    renovation_year: int | None
    floors: int | None
    floor: int | None
    rooms: int | None
    bathrooms: int | None
    toilets: int | None
    square_meters: int | None
    listed_date: date | None


@dataclass(frozen=True)
class NormalisedListing:
    """A listing as a scraping source reports it, ready to be stored."""

    source: str
    source_listing_id: str
    source_url: str
    type: ListingType
    lat: float
    lng: float
    images: list[str]
    floor_plans: list[str]
    stats: ListingStats
    price: int
    status: ListingStatus


@dataclass(frozen=True)
class GameListing:
    id: uuid.UUID
    type: ListingType
    lat: float
    lng: float
    images: list[str]
    floor_plans: list[str]
    stats: ListingStats
    price: int


class GameListingRepository(Protocol):
    async def pick_random_active(self, count: int) -> list[GameListing]:
        """Return up to `count` different random active listings that have at least one image."""
        ...


class ScraperListingRepository(Protocol):
    async def upsert(self, listing: NormalisedListing, seen_at: datetime) -> bool:
        """Insert or update a listing on (source, source_listing_id). Return True if it was new."""
        ...

    async def mark_removed_not_seen_since(self, source: str, cutoff: datetime) -> int:
        """Mark the source's listings last seen before `cutoff` as removed, except sold ones.

        Return how many listings changed status.
        """
        ...

    async def commit(self) -> None: ...


class SqlListingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def pick_random_active(self, count: int) -> list[GameListing]:
        point = cast(Listing.location, Geometry)
        statement = (
            select(Listing, func.ST_Y(point), func.ST_X(point))
            .where(Listing.status == ListingStatus.ACTIVE)
            .where(func.cardinality(Listing.images) > 0)
            .order_by(func.random())
            .limit(count)
        )
        rows = (await self._session.execute(statement)).all()
        return [_to_game_listing(listing, lat, lng) for listing, lat, lng in rows]

    async def upsert(self, listing: NormalisedListing, seen_at: datetime) -> bool:
        values = {
            "source": listing.source,
            "source_listing_id": listing.source_listing_id,
            "source_url": listing.source_url,
            "type": listing.type,
            "location": WKTElement(f"POINT({listing.lng} {listing.lat})", srid=4326),
            "images": listing.images,
            "floor_plans": listing.floor_plans,
            "energy_rating": listing.stats.energy_rating,
            "build_year": listing.stats.build_year,
            "renovation_year": listing.stats.renovation_year,
            "floors": listing.stats.floors,
            "floor": listing.stats.floor,
            "rooms": listing.stats.rooms,
            "bathrooms": listing.stats.bathrooms,
            "toilets": listing.stats.toilets,
            "square_meters": listing.stats.square_meters,
            "listed_date": listing.stats.listed_date,
            "price": listing.price,
            "status": listing.status,
            "last_seen_at": seen_at,
        }
        insert_statement = insert(Listing).values(**values)
        statement = insert_statement.on_conflict_do_update(
            index_elements=[Listing.source, Listing.source_listing_id],
            set_={key: insert_statement.excluded[key] for key in values},
        ).returning(
            # xmax is 0 only for a freshly inserted row version.
            literal_column("xmax = 0", Boolean)
        )
        inserted = (await self._session.execute(statement)).scalar_one()
        return bool(inserted)

    async def mark_removed_not_seen_since(self, source: str, cutoff: datetime) -> int:
        statement = (
            update(Listing)
            .where(Listing.source == source)
            .where(Listing.last_seen_at < cutoff)
            .where(Listing.status.not_in([ListingStatus.SOLD, ListingStatus.REMOVED]))
            .values(status=ListingStatus.REMOVED)
            .returning(Listing.id)
        )
        return len((await self._session.execute(statement)).all())

    async def commit(self) -> None:
        await self._session.commit()


def _to_game_listing(listing: Listing, lat: float, lng: float) -> GameListing:
    return GameListing(
        id=listing.id,
        type=listing.type,
        lat=lat,
        lng=lng,
        images=listing.images,
        floor_plans=listing.floor_plans,
        stats=ListingStats(
            energy_rating=listing.energy_rating,
            build_year=listing.build_year,
            renovation_year=listing.renovation_year,
            floors=listing.floors,
            floor=listing.floor,
            rooms=listing.rooms,
            bathrooms=listing.bathrooms,
            toilets=listing.toilets,
            square_meters=listing.square_meters,
            listed_date=listing.listed_date,
        ),
        price=listing.price,
    )
