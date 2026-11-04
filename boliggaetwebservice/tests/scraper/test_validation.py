from dataclasses import replace

import pytest

from app.db.models import ListingType
from scraper.validation import listing_problems
from tests.fakes import make_listing


def test_valid_listing_has_no_problems() -> None:
    assert listing_problems(make_listing()) == []


def test_bornholm_is_inside_denmark() -> None:
    assert listing_problems(replace(make_listing(), lat=55.1, lng=14.9)) == []


@pytest.mark.parametrize(
    ("lat", "lng"),
    [
        (95.0, 12.5),  # PostGIS would silently store this as 85
        (12.5683, 55.6761),  # lat and lng swapped
        (52.52, 13.40),  # Berlin
    ],
)
def test_location_outside_denmark_is_a_problem(lat: float, lng: float) -> None:
    assert listing_problems(replace(make_listing(), lat=lat, lng=lng))


@pytest.mark.parametrize("price", [0, -1])
def test_price_must_be_positive(price: int) -> None:
    assert listing_problems(replace(make_listing(), price=price)) == [
        f"price {price} is not positive"
    ]


def test_stats_out_of_column_range_are_problems() -> None:
    listing = make_listing()
    stats = replace(listing.stats, square_meters=40_000, rooms=-1)

    assert listing_problems(replace(listing, stats=stats)) == [
        "rooms -1 is out of range",
        "square_meters 40000 is out of range",
    ]


def test_basement_floor_is_allowed() -> None:
    listing = make_listing(listing_type=ListingType.APARTMENT)

    assert listing_problems(replace(listing, stats=replace(listing.stats, floor=-1))) == []
