from datetime import date
from pathlib import Path

from app.db.models import EnergyRating, ListingStatus, ListingType
from app.repositories.listings import ListingStats, NormalisedListing
from scraper.sources.sample import SampleSource

FIXTURE = Path(__file__).parent / "fixtures" / "sample_listings.json"


async def test_parses_listings_and_skips_unused_types_and_invalid_records() -> None:
    result = await SampleSource(FIXTURE).fetch()

    assert result.failed == 2
    assert [listing.source_listing_id for listing in result.listings] == ["apartment-1", "house-1"]
    assert result.listings[0] == NormalisedListing(
        source="sample",
        source_listing_id="apartment-1",
        source_url="https://example.com/sample/apartment-1",
        type=ListingType.APARTMENT,
        lat=55.6867,
        lng=12.5701,
        images=["https://example.com/a1.jpg", "https://example.com/a2.jpg"],
        floor_plans=["https://example.com/plan.jpg"],
        stats=ListingStats(
            energy_rating=EnergyRating.A2020,
            build_year=2021,
            renovation_year=None,
            floors=6,
            floor=-1,
            rooms=2,
            bathrooms=1,
            toilets=1,
            square_meters=61,
            listed_date=date(2026, 10, 1),
        ),
        price=2_995_000,
        status=ListingStatus.ACTIVE,
    )


async def test_house_has_no_floor_and_missing_stats_are_none() -> None:
    house = (await SampleSource(FIXTURE).fetch()).listings[1]

    assert house.type is ListingType.HOUSE
    assert house.status is ListingStatus.CONTRACT_SIGNED
    assert house.stats == ListingStats(None, None, None, None, None, None, None, None, None, None)


async def test_bundled_sample_file_has_enough_varied_listings() -> None:
    result = await SampleSource().fetch()

    assert result.failed == 0
    assert len(result.listings) >= 15
    assert {listing.type for listing in result.listings} == set(ListingType)
    active_with_images = [
        listing
        for listing in result.listings
        if listing.status is ListingStatus.ACTIVE and listing.images
    ]
    assert len(active_with_images) >= 5
    assert len({listing.source_listing_id for listing in result.listings}) == len(result.listings)
