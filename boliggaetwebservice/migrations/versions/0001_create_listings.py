"""Create listings table

Revision ID: 0001
Revises:
Create Date: 2026-11-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geography
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _string_enum(name: str, *values: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=20)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.create_table(
        "listings",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("source_listing_id", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("type", _string_enum("listing_type", "apartment", "house"), nullable=False),
        sa.Column(
            "location",
            Geography(geometry_type="POINT", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.Column("images", sa.ARRAY(sa.Text()), nullable=False),
        sa.Column("floor_plans", sa.ARRAY(sa.Text()), nullable=False),
        sa.Column(
            "energy_rating",
            _string_enum("energy_rating", "A2020", "A2015", "A2010", "B", "C", "D", "E", "F", "G"),
            nullable=True,
        ),
        sa.Column("build_year", sa.SmallInteger(), nullable=True),
        sa.Column("renovation_year", sa.SmallInteger(), nullable=True),
        sa.Column("floors", sa.SmallInteger(), nullable=True),
        sa.Column("floor", sa.SmallInteger(), nullable=True),
        sa.Column("rooms", sa.SmallInteger(), nullable=True),
        sa.Column("bathrooms", sa.SmallInteger(), nullable=True),
        sa.Column("toilets", sa.SmallInteger(), nullable=True),
        sa.Column("square_meters", sa.SmallInteger(), nullable=True),
        sa.Column("listed_date", sa.Date(), nullable=True),
        sa.Column("price", sa.BigInteger(), nullable=False),
        sa.Column(
            "status",
            _string_enum("listing_status", "active", "contract_signed", "sold", "removed"),
            nullable=False,
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_listings"),
        sa.UniqueConstraint(
            "source", "source_listing_id", name="uq_listings_source_source_listing_id"
        ),
    )
    op.create_index("ix_listings_location", "listings", ["location"], postgresql_using="gist")


def downgrade() -> None:
    op.drop_index("ix_listings_location", table_name="listings", postgresql_using="gist")
    op.drop_table("listings")
