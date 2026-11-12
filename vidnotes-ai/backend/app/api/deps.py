from collections.abc import Iterator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser, get_current_user
from app.database import user_session


def get_db(user: CurrentUser = Depends(get_current_user)) -> Iterator[Session]:
    """A database session for the signed-in user (RLS-scoped on Postgres)."""
    yield from user_session(user.id)
