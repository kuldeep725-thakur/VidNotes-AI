"""Background pipeline: transcript -> notes per chunk -> summary and quiz -> Hinglish -> database."""

import logging

from app.core.config import get_settings
from app.core.errors import AppError
from app.database import session_scope
from app.models import Video
from app.schemas.content import StudyNotes
from app.schemas.video import LanguageContent
from app.services import content_generator, video_service
from app.services.ai_client import AIClient
from app.services.supadata_client import SupadataClient
from app.services.transcript_chunker import build_timed_lines, split_into_chunks

logger = logging.getLogger(__name__)


def process_video(video_pk: int) -> None:
    """Run the full generation pipeline. Errors are stored on the video record."""
    try:
        _run_pipeline(video_pk)
    except AppError as exc:
        logger.warning("Video %s failed: %s", video_pk, exc.message)
        video_service.mark_failed(video_pk, exc.message)
    except Exception:
        logger.exception("Unexpected error while processing video %s", video_pk)
        video_service.mark_failed(video_pk, "Something went wrong while generating notes. Please try again.")


def _run_pipeline(video_pk: int) -> None:
    settings = get_settings()
    with session_scope() as db:
        video = db.get(Video, video_pk)
        youtube_id, quiz_count = video.youtube_id, video.quiz_count

    ai = AIClient()
    with SupadataClient() as supadata:
        video_service.update_progress(video_pk, 5, "Fetching video details")
        metadata = supadata.get_metadata(youtube_id)
        video_service.update_progress(
            video_pk,
            10,
            "Fetching transcript",
            title=metadata.title,
            channel_name=metadata.channel_name,
            thumbnail_url=metadata.thumbnail_url,
            duration_seconds=metadata.duration_seconds,
        )
        transcript = supadata.get_transcript(youtube_id)

    lines = build_timed_lines(transcript.segments)
    total_chars = sum(len(line) for line in lines)
    if total_chars > settings.max_transcript_chars:
        raise AppError(
            f"This transcript is too long to process ({total_chars:,} characters; the limit is "
            f"{settings.max_transcript_chars:,}, roughly 10 hours of speech). Try a shorter video.",
            422,
        )
    video_service.update_progress(video_pk, 20, "Reading transcript", transcript_language=transcript.language)

    chunks = split_into_chunks(lines, settings.chunk_max_chars)
    english_parts = []
    for index, chunk in enumerate(chunks, start=1):
        label = f"part {index} of {len(chunks)}" if len(chunks) > 1 else "the video"
        progress = 20 + 30 * (index - 1) // len(chunks)
        video_service.update_progress(video_pk, progress, f"Writing study notes for {label}")
        english_parts.append(content_generator.build_notes(ai, metadata.title, chunk, index, len(chunks)))
    english_notes = StudyNotes(sections=[section for part in english_parts for section in part.sections])

    # Short videos use the full transcript. For long ones the per-part notes
    # stand in for it, so every part of the video is covered without
    # exceeding the model's token limits.
    if len(chunks) == 1:
        source, source_kind = chunks[0], "full transcript"
    else:
        source = content_generator.notes_as_source(english_notes.sections)
        source_kind = "detailed study notes covering every part of the video, in order"

    video_service.update_progress(video_pk, 55, "Writing summary, quiz and exam questions")
    english_pack = content_generator.build_study_pack(
        ai, metadata.title, source, source_kind, metadata.duration_seconds, quiz_count
    )

    hinglish_parts = []
    for index, part in enumerate(english_parts, start=1):
        progress = 70 + 15 * (index - 1) // len(english_parts)
        video_service.update_progress(video_pk, progress, "Writing Hinglish study notes")
        hinglish_parts.append(content_generator.translate_notes(ai, part))
    hinglish_notes = StudyNotes(sections=[section for part in hinglish_parts for section in part.sections])
    video_service.update_progress(video_pk, 88, "Writing Hinglish summary and quiz")
    hinglish_pack = content_generator.translate_study_pack(ai, english_pack)

    video_service.save_results(
        video_pk,
        {
            "en": LanguageContent(notes=english_notes, **english_pack.model_dump()),
            "hinglish": LanguageContent(notes=hinglish_notes, **hinglish_pack.model_dump()),
        },
    )
