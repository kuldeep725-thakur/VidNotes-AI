"""Shapes of AI-generated study content.

These models are passed to Gemini as response schemas, so the model returns
JSON that is validated before anything is saved.
"""

from pydantic import BaseModel, Field


class SummaryTopic(BaseModel):
    title: str
    explanation: str


class KeyConcept(BaseModel):
    term: str
    explanation: str


class Summary(BaseModel):
    overview: str
    topics: list[SummaryTopic]
    key_concepts: list[KeyConcept]
    key_takeaways: list[str]


class NoteSubsection(BaseModel):
    heading: str
    definition: str = Field(description="Empty string when the video gives no definition.")
    points: list[str]
    example: str = Field(description="Empty string when the video gives no example.")


class NoteSection(BaseModel):
    heading: str
    start_seconds: int = Field(description="Where this topic starts in the video, in seconds.")
    introduction: str
    subsections: list[NoteSubsection]


class StudyNotes(BaseModel):
    sections: list[NoteSection]


class VideoTimestamp(BaseModel):
    seconds: int
    title: str
    description: str


class QuizItem(BaseModel):
    question: str
    options: list[str] = Field(description="Exactly four answer options.")
    correct_index: int = Field(description="Zero-based index of the correct option.")
    explanation: str


class QAItem(BaseModel):
    question: str
    answer: str


class StudyPack(BaseModel):
    """Everything except the notes, generated in one request to save API quota."""

    summary: Summary
    timestamps: list[VideoTimestamp]
    quiz: list[QuizItem]
    qa: list[QAItem]
