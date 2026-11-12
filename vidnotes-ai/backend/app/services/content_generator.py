"""Prompts and AI calls that turn a transcript into study material."""

import json
from collections.abc import Callable
from typing import TypeVar

from pydantic import BaseModel

from app.core.errors import ExternalServiceError
from app.schemas.content import NoteSection, StudyNotes, StudyPack, VideoTimestamp
from app.services.ai_client import AIClient
from app.utils.time_format import format_timestamp

GROUNDING_RULES = """You are an expert teacher who turns YouTube video transcripts into study material.
Rules:
- Use only information that is present in the provided transcript or notes.
- Never invent facts, examples, names, numbers or timestamps.
- If the video does not cover something, leave it out instead of guessing.
- Write clearly so a student can revise from your output without watching the video.
- In JSON output, write plain text: no Markdown symbols such as #, * or backticks."""

HINGLISH_RULES = """You translate English study material into natural Hinglish.
Rules:
- Hinglish means Hindi written in Roman (English) letters, mixed with English, the way Indian students and teachers speak.
- Never use Devanagari script.
- Keep technical terms, formulas, code, proper names and standard terminology in English.
- Keep exactly the same meaning, facts and level of detail. Do not add or remove information.
- Keep the same JSON structure, the same number of items in every list, and the same order.
Example: "A neural network learns patterns from data." -> "Neural network ek aisa model hai jo data se patterns seekhta hai." """

TIMESTAMP_RULE = "Seconds must be converted from a [m:ss] or [h:mm:ss] marker in the source (for example [12:05] is 725)."

ContentT = TypeVar("ContentT", bound=BaseModel)


def build_notes(ai: AIClient, title: str, transcript_part: str, part: int, total: int) -> StudyNotes:
    """Detailed notes for one transcript chunk (the "map" step for long videos)."""
    scope = f"This is part {part} of {total} of the transcript." if total > 1 else "This is the full transcript."
    prompt = f"""Video title: {title}
{scope} Each line starts with a [m:ss] timestamp.

Write detailed topic-wise study notes in English for this transcript, in the order the topics appear.
Create one section for every distinct topic (usually 3-8 sections for this text) with a heading, the
start_seconds where the topic begins, a short introduction and 2-5 subsections. {TIMESTAMP_RULE}
Each subsection has a heading, a definition (empty string if the video gives none), 3-7 bullet points that
capture the explanations, reasoning, numbers, code and steps from the video, and an example (empty string if
the video has none). A student should be able to revise this part of the video from these notes alone.

TRANSCRIPT:
{transcript_part}"""
    return ai.generate_structured(prompt, GROUNDING_RULES, StudyNotes)


def notes_as_source(sections: list[NoteSection]) -> str:
    """Render notes as compact text, used as the source for long videos."""
    lines = []
    for section in sections:
        lines.append(f"[{format_timestamp(section.start_seconds)}] {section.heading}: {section.introduction}")
        for sub in section.subsections:
            lines.append(f"  {sub.heading}. {sub.definition}".rstrip())
            lines.extend(f"  - {point}" for point in sub.points)
            if sub.example:
                lines.append(f"  Example: {sub.example}")
    return "\n".join(lines)


def build_study_pack(
    ai: AIClient,
    title: str,
    source: str,
    source_kind: str,
    duration_seconds: int | None,
    quiz_count: int,
) -> StudyPack:
    duration_hint = f"The video is {duration_seconds} seconds long. " if duration_seconds else ""
    prompt = f"""Video title: {title}
{duration_hint}Below is the {source_kind}. It carries [m:ss] timestamps.

Create, in English:

summary.overview: 2-4 paragraphs explaining what the video teaches and why it matters.
summary.topics: every main topic in the order it appears, each with a clear explanation (3-6 sentences).
summary.key_concepts: the important terms or ideas with precise explanations.
summary.key_takeaways: 5-10 short, memorable points a student should remember.

timestamps: 6-15 important moments spread across the whole video, each with a short title and a
one-sentence description. {TIMESTAMP_RULE}

quiz: exactly {quiz_count} multiple-choice questions that test understanding, not trivia. Each has exactly four
options, one correct answer (correct_index is 0-3), plausible wrong options, and an explanation of why the
correct answer is right. Spread the questions across the whole video and vary the position of the correct option.

qa: 6-10 important questions a teacher might ask in an exam or viva, each with a clear, accurate answer of
2-5 sentences.

SOURCE:
{source}"""
    pack = ai.generate_structured(prompt, GROUNDING_RULES, StudyPack)
    pack.timestamps = _clean_timestamps(pack.timestamps, duration_seconds)
    pack.quiz = [item for item in pack.quiz if len(item.options) == 4 and 0 <= item.correct_index < 4]
    if not pack.quiz or not pack.qa:
        raise ExternalServiceError("The AI did not return a usable quiz. Please try again.")
    return pack


def translate_notes(ai: AIClient, english: StudyNotes) -> StudyNotes:
    def matches(hinglish: StudyNotes) -> bool:
        return len(hinglish.sections) == len(english.sections)

    hinglish = _translate(ai, english, StudyNotes, matches)
    for translated, original in zip(hinglish.sections, english.sections):
        translated.start_seconds = original.start_seconds
    return hinglish


def translate_study_pack(ai: AIClient, english: StudyPack) -> StudyPack:
    def matches(hinglish: StudyPack) -> bool:
        return (
            len(hinglish.timestamps) == len(english.timestamps)
            and len(hinglish.quiz) == len(english.quiz)
            and len(hinglish.qa) == len(english.qa)
            and all(len(item.options) == 4 for item in hinglish.quiz)
        )

    hinglish = _translate(ai, english, StudyPack, matches)
    # Video positions and correct answers must be identical in both languages.
    for translated, original in zip(hinglish.timestamps, english.timestamps):
        translated.seconds = original.seconds
    for translated, original in zip(hinglish.quiz, english.quiz):
        translated.correct_index = original.correct_index
    return hinglish


def _translate(
    ai: AIClient, english: ContentT, schema: type[ContentT], is_complete: Callable[[ContentT], bool]
) -> ContentT:
    prompt = (
        "Translate every text value in this JSON into Hinglish. Keep all numbers unchanged.\n\n"
        + json.dumps(english.model_dump(), ensure_ascii=False)
    )
    for _attempt in range(2):
        translated = ai.generate_structured(prompt, HINGLISH_RULES, schema)
        if is_complete(translated):
            return translated
    raise ExternalServiceError("The Hinglish version came back incomplete. Please try again.")


def _clean_timestamps(stamps: list[VideoTimestamp], duration_seconds: int | None) -> list[VideoTimestamp]:
    """Drop impossible timestamps, remove duplicates and sort by time."""
    seen: set[int] = set()
    cleaned = []
    for stamp in sorted(stamps, key=lambda item: item.seconds):
        in_range = stamp.seconds >= 0 and (duration_seconds is None or stamp.seconds <= duration_seconds)
        if in_range and stamp.seconds not in seen:
            seen.add(stamp.seconds)
            cleaned.append(stamp)
    return cleaned
