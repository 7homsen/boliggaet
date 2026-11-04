from app.repositories.listings import NormalisedListing

# Bounding box around Denmark, including Bornholm and Christiansø.
DENMARK_LAT = (54.4, 57.9)
DENMARK_LNG = (7.9, 15.3)

# The stats are stored as SMALLINT.
_SMALLINT_MAX = 32767


def listing_problems(listing: NormalisedListing) -> list[str]:
    """Return why a listing can't be stored, or an empty list if it can."""
    problems = []
    if not DENMARK_LAT[0] <= listing.lat <= DENMARK_LAT[1]:
        problems.append(f"lat {listing.lat} is outside Denmark")
    if not DENMARK_LNG[0] <= listing.lng <= DENMARK_LNG[1]:
        problems.append(f"lng {listing.lng} is outside Denmark")
    if listing.price <= 0:
        problems.append(f"price {listing.price} is not positive")
    stats = listing.stats
    if stats.floor is not None and abs(stats.floor) > _SMALLINT_MAX:
        problems.append(f"floor {stats.floor} is out of range")
    counts = {
        "build_year": stats.build_year,
        "renovation_year": stats.renovation_year,
        "floors": stats.floors,
        "rooms": stats.rooms,
        "bathrooms": stats.bathrooms,
        "toilets": stats.toilets,
        "square_meters": stats.square_meters,
    }
    for name, value in counts.items():
        if value is not None and not 0 <= value <= _SMALLINT_MAX:
            problems.append(f"{name} {value} is out of range")
    return problems
