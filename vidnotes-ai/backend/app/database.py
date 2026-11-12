import json
import logging
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings
from app.utils.sqlite_backup import backup_sqlite_database

logger = logging.getLogger(__name__)
settings = get_settings()

# Tables that hold per-user data. On Postgres they are protected by Row Level
# Security (see supabase/migrations); on SQLite the services filter by user.
OWNED_TABLES = ("videos", "study_materials", "quiz_questions", "qa_pairs", "todos")
CLOUD_SCHEMA_FILE = "supabase/migrations/20261108000000_vidnotes_schema.sql"


def _create_engine():
    if settings.uses_postgres:
        return create_engine(
            settings.sqlalchemy_url,
            pool_pre_ping=True,
            # The Supabase pooler does not support prepared statements in
            # transaction mode, so they are switched off.
            connect_args={"prepare_threshold": None},
        )
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    # Background generation jobs run in worker threads.
    return create_engine(settings.sqlalchemy_url, connect_args={"check_same_thread": False})


engine = _create_engine()


@event.listens_for(engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, _record):
    if engine.dialect.name == "sqlite":
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@event.listens_for(SessionLocal, "after_begin")
def _apply_row_level_security(session, _transaction, connection):
    """Run every transaction of a user's request as that user (Postgres only).

    This is how Supabase itself applies RLS: the transaction switches to the
    `authenticated` role and auth.uid() returns the user ID from the claims,
    so the database refuses access to other users' rows even if a query
    forgets to filter by user.
    """
    user_id = session.info.get("user_id")
    if user_id and connection.dialect.name == "postgresql":
        claims = json.dumps({"sub": user_id, "role": "authenticated"})
        connection.execute(text("select set_config('request.jwt.claims', :claims, true)"), {"claims": claims})
        connection.exec_driver_sql("set local role authenticated")


class Base(DeclarativeBase):
    pass


def user_session(user_id: str) -> Iterator[Session]:
    """Yield a session whose queries run as the given user."""
    db = SessionLocal(info={"user_id": user_id})
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    """Session for trusted background work: commits on success, rolls back on error."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    # Importing the models registers them on Base.metadata.
    from app import models  # noqa: F401

    if engine.dialect.name == "postgresql":
        _check_cloud_schema()
        return
    _upgrade_sqlite_for_accounts()
    # create_all only creates missing tables; existing data is never touched.
    Base.metadata.create_all(bind=engine)


def _check_cloud_schema() -> None:
    """The cloud schema (with RLS policies) is created by the SQL migration."""
    present = set(inspect(engine).get_table_names(schema="public"))
    missing = sorted(set(Base.metadata.tables) - present)
    if missing:
        raise RuntimeError(
            f"The Supabase database is missing tables: {', '.join(missing)}. "
            f"Run {CLOUD_SCHEMA_FILE} in the Supabase SQL Editor first (see README)."
        )


def _upgrade_sqlite_for_accounts() -> None:
    """Add the user_id column to databases created before accounts existed.

    Existing rows are assigned to the local user. A backup copy is made first,
    so the previous database can always be restored.
    """
    from app.models import LOCAL_USER_ID

    inspector = inspect(engine)
    existing = set(inspector.get_table_names())
    outdated = [
        table
        for table in OWNED_TABLES
        if table in existing and "user_id" not in {column["name"] for column in inspector.get_columns(table)}
    ]
    if not outdated:
        return

    backup = backup_sqlite_database(settings.database_path, "before-accounts-upgrade")
    logger.info("Backed up the database to %s before upgrading it", backup)
    with engine.begin() as connection:
        for table in outdated:
            connection.exec_driver_sql(
                f"ALTER TABLE {table} ADD COLUMN user_id VARCHAR(36) NOT NULL DEFAULT '{LOCAL_USER_ID}'"
            )
            connection.exec_driver_sql(f"CREATE INDEX IF NOT EXISTS ix_{table}_user_id ON {table} (user_id)")
    logger.info("Upgraded tables for accounts: %s", ", ".join(outdated))
