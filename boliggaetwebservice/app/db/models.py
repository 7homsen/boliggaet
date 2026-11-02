import uuid
from datetime import date, datetime
from enum import StrEnum

from geoalchemy2 import Geography, WKBElement
from sqlalchemy import (
    ARRAY,
    BigInteger,
    Date,
    DateTime,
    Enum,
    Index,
    MetaData,
    SmallInteger,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class ListingType(StrEnum):
    APARTMENT = "apartment"
    HOUSE = "house"


class ListingStatus(StrEnum):
    ACTIVE = "active"
    CONTRACT_SIGNED = "contract_signed"
    SOLD = "sold"
    REMOVED = "removed"


class EnergyRating(StrEnum):
    A2020 = "A2020"
    A2015 = "A2015"
    A2010 = "A2010"
    B = "B"
    C = "C"
    D = "D"
    E = "E"
    F = "F"
    G = "G"


def _string_enum(enum: type[StrEnum], name: str) -> Enum:
    """Store an enum as text with a check constraint, so new values need no ALTER TYPE."""
    return Enum(
        enum,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=20,
        values_callable=lambda members: [member.value for member in members],
    )


class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(table_name)s_%(column_0_name)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s_%(column_1_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


class Listing(Base):
    __tablename__ = "listings"
    __table_args__ = (
        UniqueConstraint("source", "source_listing_id"),
        Index("ix_listings_location", "location", postgresql_using="gist"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source: Mapped[str] = mapped_column(Text)
    source_listing_id: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(Text)

    type: Mapped[ListingType] = mapped_column(_string_enum(ListingType, "listing_type"))
    location: Mapped[WKBElement] = mapped_column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=False)
    )

    images: Mapped[list[str]] = mapped_column(ARRAY(Text))
    floor_plans: Mapped[list[str]] = mapped_column(ARRAY(Text))

    energy_rating: Mapped[EnergyRating | None] = mapped_column(
        _string_enum(EnergyRating, "energy_rating")
    )
    build_year: Mapped[int | None] = mapped_column(SmallInteger)
    renovation_year: Mapped[int | None] = mapped_column(SmallInteger)
    floors: Mapped[int | None] = mapped_column(SmallInteger)
    floor: Mapped[int | None] = mapped_column(SmallInteger)
    rooms: Mapped[int | None] = mapped_column(SmallInteger)
    bathrooms: Mapped[int | None] = mapped_column(SmallInteger)
    toilets: Mapped[int | None] = mapped_column(SmallInteger)
    square_meters: Mapped[int | None] = mapped_column(SmallInteger)
    listed_date: Mapped[date | None] = mapped_column(Date)

    price: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[ListingStatus] = mapped_column(_string_enum(ListingStatus, "listing_status"))
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
