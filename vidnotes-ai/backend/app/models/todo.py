from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.types import OwnedMixin, TimestampMixin
from app.models.video import Video


class Todo(OwnedMixin, TimestampMixin, Base):
    """A study task, optionally linked to a saved video."""

    __tablename__ = "todos"
    __table_args__ = {"sqlite_autoincrement": True}

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    is_done: Mapped[bool] = mapped_column(Boolean, default=False)
    due_date: Mapped[date | None] = mapped_column(Date)
    # Deleting a video keeps its tasks and just removes the link.
    video_id: Mapped[int | None] = mapped_column(ForeignKey("videos.id", ondelete="SET NULL"), index=True)

    video: Mapped[Video | None] = relationship()
