from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.types import JSONData, OwnedMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import QuizResult


class VideoStatus(StrEnum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Video(OwnedMixin, TimestampMixin, Base):
    __tablename__ = "videos"
    __table_args__ = (
        # One record per video per user prevents duplicates.
        UniqueConstraint("user_id", "youtube_id"),
        # AUTOINCREMENT stops SQLite reusing IDs of deleted videos, so an old
        # link can never open a different video's notes.
        {"sqlite_autoincrement": True},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    youtube_id: Mapped[str] = mapped_column(String(11), index=True)
    url: Mapped[str] = mapped_column(String(200))
    title: Mapped[str] = mapped_column(String(300), default="Untitled video")
    channel_name: Mapped[str | None] = mapped_column(String(200))
    thumbnail_url: Mapped[str | None] = mapped_column(String(300))
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    transcript_language: Mapped[str | None] = mapped_column(String(20))
    quiz_count: Mapped[int] = mapped_column(Integer, default=10)

    status: Mapped[str] = mapped_column(String(20), default=VideoStatus.PROCESSING)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    progress_message: Mapped[str] = mapped_column(String(200), default="Queued")
    error_message: Mapped[str | None] = mapped_column(Text)

    materials: Mapped[list["StudyMaterial"]] = relationship(
        back_populates="video", cascade="all, delete-orphan"
    )
    quiz_questions: Mapped[list["QuizQuestion"]] = relationship(
        back_populates="video",
        cascade="all, delete-orphan",
        order_by="QuizQuestion.position",
    )
    qa_pairs: Mapped[list["QAPair"]] = relationship(
        back_populates="video",
        cascade="all, delete-orphan",
        order_by="QAPair.position",
    )
    quiz_results: Mapped[list["QuizResult"]] = relationship(
        back_populates="video", cascade="all, delete-orphan"
    )


class StudyMaterial(OwnedMixin, TimestampMixin, Base):
    """Summary, study notes and timestamps for one video in one language."""

    __tablename__ = "study_materials"
    __table_args__ = (UniqueConstraint("video_id", "language"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"), index=True)
    language: Mapped[str] = mapped_column(String(20))
    summary: Mapped[dict] = mapped_column(JSONData)
    notes: Mapped[dict] = mapped_column(JSONData)
    timestamps: Mapped[list] = mapped_column(JSONData)

    video: Mapped[Video] = relationship(back_populates="materials")


class QuizQuestion(OwnedMixin, Base):
    __tablename__ = "quiz_questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"), index=True)
    language: Mapped[str] = mapped_column(String(20))
    position: Mapped[int] = mapped_column(Integer)
    question: Mapped[str] = mapped_column(Text)
    options: Mapped[list] = mapped_column(JSONData)
    correct_index: Mapped[int] = mapped_column(Integer)
    explanation: Mapped[str] = mapped_column(Text)

    video: Mapped[Video] = relationship(back_populates="quiz_questions")


class QAPair(OwnedMixin, Base):
    __tablename__ = "qa_pairs"

    id: Mapped[int] = mapped_column(primary_key=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"), index=True)
    language: Mapped[str] = mapped_column(String(20))
    position: Mapped[int] = mapped_column(Integer)
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)

    video: Mapped[Video] = relationship(back_populates="qa_pairs")
