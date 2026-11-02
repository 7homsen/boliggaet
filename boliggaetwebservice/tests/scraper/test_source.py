import pytest

from app.db.models import ListingType
from scraper.source import map_property_type


@pytest.mark.parametrize(
    ("property_type", "expected"),
    [
        ("villa", ListingType.HOUSE),
        ("Rækkehus", ListingType.HOUSE),
        ("landejendom", ListingType.HOUSE),
        ("fritidshus", ListingType.HOUSE),
        ("ejerlejlighed", ListingType.APARTMENT),
        (" andelsbolig ", ListingType.APARTMENT),
        ("grund", None),
        ("projekt", None),
        ("", None),
    ],
)
def test_map_property_type(property_type: str, expected: ListingType | None) -> None:
    assert map_property_type(property_type) == expected
