from collections.abc import Iterator
from dataclasses import fields, replace

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_game_listing_repository
from app.db.models import ListingType
from app.main import app
from app.repositories.listings import ListingStats
from tests.fakes import FakeGameListingRepository, make_game_listing

LISTING_KEYS = {"id", "type", "location", "images", "floor_plans", "stats", "price"}
HOUSE_STATS_KEYS = {
    "energy_rating",
    "build_year",
    "renovation_year",
    "floors",
    "rooms",
    "bathrooms",
    "toilets",
    "square_meters",
    "listed_date",
}
APARTMENT_STATS_KEYS = HOUSE_STATS_KEYS | {"floor"}


@pytest.fixture
def repository() -> Iterator[FakeGameListingRepository]:
    fake = FakeGameListingRepository([])
    app.dependency_overrides[get_game_listing_repository] = lambda: fake
    yield fake
    app.dependency_overrides.clear()


def test_game_response_has_exact_shape(repository: FakeGameListingRepository) -> None:
    apartment = make_game_listing(ListingType.APARTMENT)
    house = make_game_listing(ListingType.HOUSE)
    repository.listings = [apartment, house, *(make_game_listing() for _ in range(3))]

    response = TestClient(app).get("/game")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"listings"}
    assert len(body["listings"]) == 5
    for listing in body["listings"]:
        assert set(listing) == LISTING_KEYS
        assert set(listing["location"]) == {"lat", "lng"}
    assert body["listings"][0] == {
        "id": str(apartment.id),
        "type": "apartment",
        "location": {"lat": 55.6761, "lng": 12.5683},
        "images": ["https://example.com/image.jpg"],
        "floor_plans": ["https://example.com/plan.jpg"],
        "stats": {
            "energy_rating": "C",
            "build_year": 1932,
            "renovation_year": 2015,
            "floors": 5,
            "floor": 3,
            "rooms": 3,
            "bathrooms": 1,
            "toilets": 1,
            "square_meters": 82,
            "listed_date": "2026-08-14",
        },
        "price": 3_495_000,
    }
    assert set(body["listings"][0]["stats"]) == APARTMENT_STATS_KEYS
    assert set(body["listings"][1]["stats"]) == HOUSE_STATS_KEYS


def test_game_returns_null_for_missing_stats(repository: FakeGameListingRepository) -> None:
    empty_stats = ListingStats(**dict.fromkeys(f.name for f in fields(ListingStats)))
    listing = replace(make_game_listing(ListingType.APARTMENT), stats=empty_stats)
    repository.listings = [listing, *(make_game_listing() for _ in range(4))]

    stats = TestClient(app).get("/game").json()["listings"][0]["stats"]

    assert stats == dict.fromkeys(APARTMENT_STATS_KEYS)


def test_game_returns_503_with_danish_message_when_too_few_listings(
    repository: FakeGameListingRepository,
) -> None:
    repository.listings = [make_game_listing() for _ in range(4)]

    response = TestClient(app).get("/game")

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Der er ikke nok boliger til et spil lige nu. Prøv igen senere."
    }
