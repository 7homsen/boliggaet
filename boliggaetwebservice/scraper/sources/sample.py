"""Sample-data source: loads listings from a JSON file in the repository.

For development and tests only; enabled with SAMPLE_SOURCE_ENABLED.
"""

import json
import logging
from datetime import date
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ValidationError

from app.db.models import EnergyRating, ListingStatus, ListingType
from app.repositories.listings import ListingStats, NormalisedListing
from scraper.source import FetchResult, map_property_type

logger = logging.getLogger(__name__)

DEFAULT_PATH = Path(__file__).with_name("sample_listings.json")


class _SampleRecord(BaseModel):
    id: str
    url: str
    property_type: str
    status: Literal["active", "contract_signed", "sold"]
    lat: float
    lng: float
    images: list[str]
    floor_plans: list[str]
    energy_rating: EnergyRating | None = None
    build_year: int | None = None
    renovation_year: int | None = None
    floors: int | None = None
    floor: int | None = None
    rooms: int | None = None
    bathrooms: int | None = None
    toilets: int | None = None
    square_meters: int | None = None
    listed_date: date | None = None
    price: int


class SampleSource:
    name = "sample"

    def __init__(self, path: Path = DEFAULT_PATH) -> None:
        self._path = path

    async def fetch(self) -> FetchResult:
        raw_records: list[Any] = json.loads(self._path.read_text(encoding="utf-8"))
        result = FetchResult()
        for raw in raw_records:
            try:
                record = _SampleRecord.model_validate(raw)
            except ValidationError as error:
                logger.warning("Skipping invalid sample listing: %s", error)
                result.failed += 1
                continue
            listing = _normalise(record)
            if listing is not None:
                result.listings.append(listing)
        return result


def _normalise(record: _SampleRecord) -> NormalisedListing | None:
    listing_type = map_property_type(record.property_type)
    if listing_type is None:
        return None
    return NormalisedListing(
        source=SampleSource.name,
        source_listing_id=record.id,
        source_url=record.url,
        type=listing_type,
        lat=record.lat,
        lng=record.lng,
        images=record.images,
        floor_plans=record.floor_plans,
        stats=ListingStats(
            energy_rating=record.energy_rating,
            build_year=record.build_year,
            renovation_year=record.renovation_year,
            floors=record.floors,
            floor=record.floor if listing_type is ListingType.APARTMENT else None,
            rooms=record.rooms,
            bathrooms=record.bathrooms,
            toilets=record.toilets,
            square_meters=record.square_meters,
            listed_date=record.listed_date,
        ),
        price=record.price,
        status=ListingStatus(record.status),
    )
