from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.repositories.health import HealthRepository, SqlHealthRepository
from app.repositories.listings import GameListingRepository, SqlListingRepository
from app.services.game import GameService
from app.services.health import HealthService

Session = Annotated[AsyncSession, Depends(get_session)]


def get_game_listing_repository(session: Session) -> GameListingRepository:
    return SqlListingRepository(session)


def get_health_repository(session: Session) -> HealthRepository:
    return SqlHealthRepository(session)


def get_game_service(
    listings: Annotated[GameListingRepository, Depends(get_game_listing_repository)],
) -> GameService:
    return GameService(listings)


def get_health_service(
    health: Annotated[HealthRepository, Depends(get_health_repository)],
) -> HealthService:
    return HealthService(health)
