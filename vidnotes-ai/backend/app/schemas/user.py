from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.video import Language


class PublicConfig(BaseModel):
    """Settings the browser needs. Contains no secrets."""

    auth_enabled: bool
    cloud_sync: bool
    supabase_url: str | None
    supabase_publishable_key: str | None


class ProfileStats(BaseModel):
    videos: int
    quizzes_taken: int
    open_tasks: int
    done_tasks: int


class ProfileOut(BaseModel):
    id: str
    email: str | None
    full_name: str | None
    avatar_url: str | None
    provider: str | None
    created_at: datetime
    stats: ProfileStats


class ProfileUpdate(BaseModel):
    full_name: str = Field(max_length=200)

    @field_validator("full_name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Name cannot be empty")
        return value


class PreferencesOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    theme: Literal["dark", "light"]
    default_language: Language
    default_quiz_count: int


class PreferencesUpdate(BaseModel):
    """Only the fields that are sent are changed."""

    theme: Literal["dark", "light"] | None = None
    default_language: Language | None = None
    default_quiz_count: int | None = Field(default=None, ge=5, le=20)


class QuizResultCreate(BaseModel):
    language: Language
    # The chosen option for each question in order; null when skipped.
    answers: list[int | None] = Field(min_length=1, max_length=20)

    @field_validator("answers")
    @classmethod
    def check_options(cls, answers: list[int | None]) -> list[int | None]:
        if any(answer is not None and not 0 <= answer <= 3 for answer in answers):
            raise ValueError("Each answer must be an option index from 0 to 3")
        return answers


class QuizResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    language: str
    score: int
    total: int
    created_at: datetime
