from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.content import QAItem, QuizItem, StudyNotes, Summary, VideoTimestamp

Language = Literal["en", "hinglish"]
LANGUAGES: tuple[Language, ...] = ("en", "hinglish")


class AnalyzeRequest(BaseModel):
    url: str = Field(min_length=10, max_length=300)
    quiz_count: int = Field(default=10, ge=5, le=20)


class VideoStatusOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    youtube_id: str
    status: str
    progress: int
    progress_message: str
    error_message: str | None


class VideoListItem(VideoStatusOut):
    url: str
    title: str
    channel_name: str | None
    thumbnail_url: str | None
    duration_seconds: int | None
    created_at: datetime
    updated_at: datetime


class LanguageContent(BaseModel):
    summary: Summary
    notes: StudyNotes
    timestamps: list[VideoTimestamp]
    quiz: list[QuizItem]
    qa: list[QAItem]


class VideoDetail(VideoListItem):
    transcript_language: str | None
    content: dict[Language, LanguageContent] = {}
