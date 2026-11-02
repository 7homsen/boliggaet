from dataclasses import dataclass, field
from typing import Protocol

from app.db.models import ListingType
from app.repositories.listings import NormalisedListing

_PROPERTY_TYPES = {
    "villa": ListingType.HOUSE,
    "rækkehus": ListingType.HOUSE,
    "landejendom": ListingType.HOUSE,
    "fritidshus": ListingType.HOUSE,
    "ejerlejlighed": ListingType.APARTMENT,
    "andelsbolig": ListingType.APARTMENT,
}


def map_property_type(property_type: str) -> ListingType | None:
    """Map a Danish property type to a listing type, or None if the game skips it."""
    return _PROPERTY_TYPES.get(property_type.strip().lower())


@dataclass
class FetchResult:
    listings: list[NormalisedListing] = field(default_factory=list)
    failed: int = 0
    """Listings the source found but couldn't parse."""


class Source(Protocol):
    @property
    def name(self) -> str: ...

    async def fetch(self) -> FetchResult:
        """Return every listing currently on the source.

        Only `active`, `contract_signed` and `sold` are valid statuses here; `removed` is
        decided by the runner. Property types the game doesn't use are left out.
        """
        ...
