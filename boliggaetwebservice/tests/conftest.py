"""Shared fixtures. Database fixtures use the PostGIS container from docker-compose.yml.

Database tests run against their own database: DATABASE_URL with "_test" appended to the name.
"""

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import make_url, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.config import get_settings

ALEMBIC_INI = Path(__file__).parents[1] / "alembic.ini"


def alembic_config(database_url: str) -> Config:
    config = Config(ALEMBIC_INI)
    config.attributes["database_url"] = database_url
    config.attributes["configure_logger"] = False
    return config


async def _create_database_if_missing(database_url: str) -> None:
    url = make_url(database_url)
    admin = create_async_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        async with admin.connect() as connection:
            exists = await connection.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": url.database}
            )
            if not exists:
                await connection.execute(text(f'CREATE DATABASE "{url.database}"'))
    finally:
        await admin.dispose()


@pytest.fixture(scope="session")
def test_database_url() -> str:
    url = make_url(get_settings().database_url)
    test_url = url.set(database=f"{url.database}_test").render_as_string(hide_password=False)
    asyncio.run(_create_database_if_missing(test_url))
    config = alembic_config(test_url)
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    return test_url


@pytest.fixture
async def db_session(test_database_url: str) -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(test_database_url)
    async with engine.begin() as connection:
        await connection.execute(text("TRUNCATE listings"))
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session
    await engine.dispose()
