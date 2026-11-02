from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_game_service
from app.schemas.game import ErrorResponse, GameListingResponse, GameResponse
from app.services.game import GameService, NotEnoughListingsError

router = APIRouter()

NOT_ENOUGH_LISTINGS_MESSAGE = "Der er ikke nok boliger til et spil lige nu. Prøv igen senere."


@router.get(
    "/game",
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ErrorResponse}},
)
async def get_game(service: Annotated[GameService, Depends(get_game_service)]) -> GameResponse:
    try:
        listings = await service.new_game()
    except NotEnoughListingsError:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, detail=NOT_ENOUGH_LISTINGS_MESSAGE
        ) from None
    return GameResponse(listings=[GameListingResponse.from_listing(item) for item in listings])
