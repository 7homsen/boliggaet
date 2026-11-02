from app.repositories.listings import GameListing, GameListingRepository

LISTINGS_PER_GAME = 5


class NotEnoughListingsError(Exception):
    pass


class GameService:
    def __init__(self, listings: GameListingRepository) -> None:
        self._listings = listings

    async def new_game(self) -> list[GameListing]:
        listings = await self._listings.pick_random_active(LISTINGS_PER_GAME)
        if len(listings) < LISTINGS_PER_GAME:
            raise NotEnoughListingsError
        return listings
