from app.config import Settings
from scraper.source import Source
from scraper.sources.sample import SampleSource


def enabled_sources(settings: Settings) -> list[Source]:
    sources: list[Source] = []
    if settings.sample_source_enabled:
        sources.append(SampleSource())
    return sources
