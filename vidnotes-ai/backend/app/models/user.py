from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.types import JSONData, OwnedMixin, TimestampMixin, UserId
from app.models.video import Video


class Profile(TimestampMixin, Base):
    """Name, email and picture of a signed-in user (id = Supabase Auth user id)."""

    __tablename__ = "profiles"

    id: Mapped[str] = mapped_column(UserId, primary_key=True)
    email: Mapped[str | None] = mapped_column(String(320))
    full_name: Mapped[str | None] = mapped_column(String(200))
    avatar_url: Mapped[str | None] = mapped_column(String(1000))


class UserPreferences(TimestampMixin, Base):
    __tablename__ = "user_preferences"

    user_id: Mapped[str] = mapped_column(UserId, primary_key=True)
    theme: Mapped[str] = mapped_column(String(10), default="dark")
    default_language: Mapped[str] = mapped_column(String(20), default="en")
    default_quiz_count: Mapped[int] = mapped_column(Integer, default=10)


class QuizResult(OwnedMixin, TimestampMixin, Base):
    """One finished quiz attempt, kept so progress syncs across devices."""

    __tablename__ = "quiz_results"
    __table_args__ = {"sqlite_autoincrement": True}

    id: Mapped[int] = mapped_column(primary_key=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"), index=True)
    language: Mapped[str] = mapped_column(String(20))
    score: Mapped[int] = mapped_column(Integer)
    total: Mapped[int] = mapped_column(Integer)
    # The option index chosen for each question (null when skipped).
    answers: Mapped[list] = mapped_column(JSONData)

    video: Mapped[Video] = relationship(back_populates="quiz_results")
