from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

TodoFilter = Literal["all", "active", "done"]


class _TitleMixin(BaseModel):
    @field_validator("title", check_fields=False)
    @classmethod
    def strip_title(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("Title cannot be empty")
        return value


class TodoCreate(_TitleMixin):
    title: str = Field(max_length=200)
    due_date: date | None = None
    video_id: int | None = None


class TodoUpdate(_TitleMixin):
    """Only the fields that are sent are changed; send null to clear a field."""

    title: str | None = Field(default=None, max_length=200)
    is_done: bool | None = None
    due_date: date | None = None
    video_id: int | None = None


class TodoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    is_done: bool
    due_date: date | None
    video_id: int | None
    video_title: str | None
    created_at: datetime
    updated_at: datetime
