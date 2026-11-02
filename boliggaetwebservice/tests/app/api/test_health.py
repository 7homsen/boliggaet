import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_health_repository
from app.main import app


class FakeHealthRepository:
    def __init__(self, reachable: bool) -> None:
        self.reachable = reachable

    async def database_is_reachable(self) -> bool:
        return self.reachable


@pytest.mark.parametrize(
    ("reachable", "status_code", "body"),
    [(True, 200, {"status": "ok"}), (False, 503, {"status": "unavailable"})],
)
def test_health_reports_database_status(
    reachable: bool, status_code: int, body: dict[str, str]
) -> None:
    app.dependency_overrides[get_health_repository] = lambda: FakeHealthRepository(reachable)
    try:
        response = TestClient(app).get("/health")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == status_code
    assert response.json() == body
