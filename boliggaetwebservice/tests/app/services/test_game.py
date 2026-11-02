import pytest

from app.services.game import LISTINGS_PER_GAME, GameService, NotEnoughListingsError
from tests.fakes import FakeGameListingRepository, make_game_listing


async def test_new_game_returns_five_listings() -> None:
    listings = [make_game_listing() for _ in range(7)]
    service = GameService(FakeGameListingRepository(listings))

    game = await service.new_game()

    assert game == listings[:LISTINGS_PER_GAME]


async def test_new_game_raises_when_fewer_than_five_listings() -> None:
    service = GameService(FakeGameListingRepository([make_game_listing() for _ in range(4)]))

    with pytest.raises(NotEnoughListingsError):
        await service.new_game()
