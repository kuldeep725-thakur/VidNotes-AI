"""Column types and mixins shared by all models.

They work on both databases: the local SQLite file and Supabase Postgres.
"""

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, String, TypeDecorator
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

# The single user who owns all data in local mode (no Supabase configured).
LOCAL_USER_ID = "00000000-0000-0000-0000-000000000000"

# jsonb on Postgres, plain JSON text on SQLite.
JSONData = JSON().with_variant(JSONB(), "postgresql")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class UTCDateTime(TypeDecorator):
    """Stores UTC datetimes and always returns them timezone-aware.

    SQLite has no timezone support, so values are stored as naive UTC there;
    Postgres uses timestamptz. Either way the API returns aware UTC values.
    """

    impl = DateTime
    cache_ok = True

    def load_dialect_impl(self, dialect):
        return dialect.type_descriptor(DateTime(timezone=dialect.name == "postgresql"))

    def process_bind_param(self, value, dialect):
        if value is not None and value.tzinfo is not None and dialect.name == "sqlite":
            value = value.astimezone(timezone.utc).replace(tzinfo=None)
        return value

    def process_result_value(self, value, dialect):
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value


class UserId(TypeDecorator):
    """A Supabase Auth user ID: native uuid on Postgres, text on SQLite."""

    impl = String(36)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(UUID(as_uuid=False))
        return dialect.type_descriptor(String(36))

    def process_result_value(self, value, dialect):
        return str(value) if value is not None else None


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, onupdate=utc_now)


class OwnedMixin:
    """Marks a row as belonging to one user. Row Level Security matches on it."""

    user_id: Mapped[str] = mapped_column(UserId, index=True)
