"""Run every enabled scraping source once: `uv run python -m scraper`."""

import asyncio
import logging
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from app.config import get_settings
from app.db.session import get_engine, get_sessionmaker
from app.repositories.listings import ScraperListingRepository, SqlListingRepository
from scraper.runner import run_all
from scraper.sources import enabled_sources


@asynccontextmanager
async def repository_scope() -> AsyncIterator[ScraperListingRepository]:
    async with get_sessionmaker()() as session:
        yield SqlListingRepository(session)


async def main() -> int:
    try:
        all_ok = await run_all(
            enabled_sources(get_settings()), repository_scope, now=lambda: datetime.now(UTC)
        )
    finally:
        await get_engine().dispose()
    return 0 if all_ok else 1


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    sys.exit(asyncio.run(main()))
