from typing import Protocol

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession


class HealthRepository(Protocol):
    async def database_is_reachable(self) -> bool: ...


class SqlHealthRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def database_is_reachable(self) -> bool:
        try:
            await self._session.execute(text("SELECT 1"))
        except (SQLAlchemyError, OSError):
            return False
        return True
