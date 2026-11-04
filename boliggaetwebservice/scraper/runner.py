import logging
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.repositories.listings import ListingRejectedError, ScraperListingRepository
from scraper.source import Source
from scraper.validation import listing_problems

logger = logging.getLogger(__name__)

REMOVAL_GRACE_PERIOD = timedelta(days=2)

# A run that stores fewer than this share of the source's listed listings looks partial
# (a broken parser, a missing page), so nothing is marked removed. Without it, a partial
# run more than the grace period after the previous one would remove listings at once.
MIN_SHARE_FOR_REMOVAL = 0.5


@dataclass(frozen=True)
class RunSummary:
    source: str
    new: int
    updated: int
    deactivated: int
    failed: int
    removal_skipped: bool = False


async def run_source(
    source: Source, listings: ScraperListingRepository, now: datetime
) -> RunSummary:
    result = await source.fetch()
    listed_before = await listings.count_listed(source.name)
    new = updated = 0
    failed = result.failed
    for listing in result.listings:
        problems = listing_problems(listing)
        if problems:
            logger.warning(
                "Source %s: skipping listing %s: %s",
                source.name,
                listing.source_listing_id,
                "; ".join(problems),
            )
            failed += 1
            continue
        try:
            is_new = await listings.upsert(listing, seen_at=now)
        except ListingRejectedError as error:
            logger.warning(
                "Source %s: database rejected listing %s: %s",
                source.name,
                listing.source_listing_id,
                error,
            )
            failed += 1
            continue
        if is_new:
            new += 1
        else:
            updated += 1

    deactivated = 0
    removal_skipped = new + updated < listed_before * MIN_SHARE_FOR_REMOVAL
    if removal_skipped:
        logger.warning(
            "Source %s: stored only %d of %d listed listings; not marking any as removed",
            source.name,
            new + updated,
            listed_before,
        )
    else:
        deactivated = await listings.mark_removed_not_seen_since(
            source.name, cutoff=now - REMOVAL_GRACE_PERIOD
        )
    await listings.commit()
    summary = RunSummary(source.name, new, updated, deactivated, failed, removal_skipped)
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
    """Run every source; one failing source doesn't stop the others.

    Return True if every source ran and none looked partial.
    """
    if not sources:
        logger.warning("No scraping sources are enabled")
    all_ok = True
    for source in sources:
        try:
            async with repository_scope() as listings:
                summary = await run_source(source, listings, now())
        except Exception:
            # Leaving the scope without a commit discards the source's partial changes.
            logger.exception("Source %s failed", source.name)
            all_ok = False
            continue
        if summary.removal_skipped:
            all_ok = False
    return all_ok
