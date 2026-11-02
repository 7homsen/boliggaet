import logging
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.repositories.listings import ScraperListingRepository
from scraper.source import Source

logger = logging.getLogger(__name__)

REMOVAL_GRACE_PERIOD = timedelta(days=2)


@dataclass(frozen=True)
class RunSummary:
    source: str
    new: int
    updated: int
    deactivated: int
    failed: int


async def run_source(
    source: Source, listings: ScraperListingRepository, now: datetime
) -> RunSummary:
    result = await source.fetch()
    new = updated = 0
    for listing in result.listings:
        if await listings.upsert(listing, seen_at=now):
            new += 1
        else:
            updated += 1
    deactivated = await listings.mark_removed_not_seen_since(
        source.name, cutoff=now - REMOVAL_GRACE_PERIOD
    )
    await listings.commit()
    summary = RunSummary(source.name, new, updated, deactivated, result.failed)
    logger.info(
        "Source %s: %d new, %d updated, %d deactivated, %d failed",
        summary.source,
        summary.new,
        summary.updated,
        summary.deactivated,
        summary.failed,
    )
    return summary


async def run_all(
    sources: list[Source],
    repository_scope: Callable[[], AbstractAsyncContextManager[ScraperListingRepository]],
    now: Callable[[], datetime],
) -> bool:
    """Run every source; one failing source doesn't stop the others. Return True if all ran."""
    if not sources:
        logger.warning("No scraping sources are enabled")
    all_ok = True
    for source in sources:
        try:
            async with repository_scope() as listings:
                await run_source(source, listings, now())
        except Exception:
            # Leaving the scope without a commit discards the source's partial changes.
            logger.exception("Source %s failed", source.name)
            all_ok = False
    return all_ok
