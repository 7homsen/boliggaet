import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict

from app.db.models import EnergyRating, ListingType
from app.repositories.listings import GameListing

# Product rule: apart from `price`, nothing in these models may give the price away
# (price per m², down payment, price history, text that mentions the price).


class Location(BaseModel):
    lat: float
    lng: float


class HouseStats(BaseModel):
    # Forbidding extra fields makes `ApartmentStats | HouseStats` resolve unambiguously:
    # only apartment stats have `floor`.
    model_config = ConfigDict(extra="forbid")

    energy_rating: EnergyRating | None
    build_year: int | None
    renovation_year: int | None
    floors: int | None
    rooms: int | None
    bathrooms: int | None
    toilets: int | None
    square_meters: int | None
    listed_date: date | None


class ApartmentStats(HouseStats):
    floor: int | None


class GameListingResponse(BaseModel):
    id: uuid.UUID
    type: ListingType
    location: Location
    images: list[str]
    floor_plans: list[str]
    stats: ApartmentStats | HouseStats
    price: int

    @classmethod
    def from_listing(cls, listing: GameListing) -> "GameListingResponse":
        house_stats = HouseStats(
            energy_rating=listing.stats.energy_rating,
            build_year=listing.stats.build_year,
            renovation_year=listing.stats.renovation_year,
            floors=listing.stats.floors,
            rooms=listing.stats.rooms,
            bathrooms=listing.stats.bathrooms,
            toilets=listing.stats.toilets,
            square_meters=listing.stats.square_meters,
            listed_date=listing.stats.listed_date,
        )
        stats: ApartmentStats | HouseStats = (
            ApartmentStats(**house_stats.model_dump(), floor=listing.stats.floor)
            if listing.type is ListingType.APARTMENT
            else house_stats
        )
        return cls(
            id=listing.id,
            type=listing.type,
            location=Location(lat=listing.lat, lng=listing.lng),
            images=listing.images,
            floor_plans=listing.floor_plans,
            stats=stats,
            price=listing.price,
        )


class GameResponse(BaseModel):
    listings: list[GameListingResponse]


class ErrorResponse(BaseModel):
    detail: str
