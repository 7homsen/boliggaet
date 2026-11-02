from app.repositories.health import HealthRepository


class HealthService:
    def __init__(self, health: HealthRepository) -> None:
        self._health = health

    async def is_healthy(self) -> bool:
        return await self._health.database_is_reachable()
