"""Database operations for videos and their generated content."""

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError
from app.database import session_scope
from app.models import QAPair, QuizQuestion, StudyMaterial, Video, VideoStatus
from app.schemas.video import LANGUAGES, Language, LanguageContent, VideoDetail
from app.utils.youtube import canonical_url, extract_video_id


def _user_video_query(user_id: str):
    return select(Video).where(Video.user_id == user_id)


def start_analysis(db: Session, user_id: str, url: str, quiz_count: int) -> tuple[Video, bool]:
    """Return the video record and whether a new generation job must start.

    A video the user already processed or is processing is returned as is, so
    the same video is never stored or generated twice for one user.
    """
    youtube_id = extract_video_id(url)
    existing_query = _user_video_query(user_id).where(Video.youtube_id == youtube_id)
    video = db.scalar(existing_query)

    if video is not None:
        if video.status != VideoStatus.FAILED:
            return video, False
        # Retry a previous failure using the same record.
        video.status = VideoStatus.PROCESSING
        video.progress = 0
        video.progress_message = "Queued"
        video.error_message = None
        video.quiz_count = quiz_count
        db.commit()
        return video, True

    video = Video(user_id=user_id, youtube_id=youtube_id, url=canonical_url(youtube_id), quiz_count=quiz_count)
    db.add(video)
    try:
        db.commit()
    except IntegrityError:
        # Another request created the same video at the same moment.
        db.rollback()
        return db.scalar(existing_query), False
    return video, True


def list_videos(db: Session, user_id: str, search: str | None) -> list[Video]:
    query = _user_video_query(user_id).order_by(Video.created_at.desc())
    if search:
        query = query.where(Video.title.icontains(search.strip(), autoescape=True))
    return list(db.scalars(query))


_CONTENT_OPTIONS = (
    selectinload(Video.materials),
    selectinload(Video.quiz_questions),
    selectinload(Video.qa_pairs),
)


def get_video(db: Session, user_id: str, video_pk: int) -> Video:
    """The user's video with its content; another user's video is 'not found'."""
    video = db.scalar(_user_video_query(user_id).where(Video.id == video_pk).options(*_CONTENT_OPTIONS))
    if video is None:
        raise AppError("Saved notes not found. They may have been deleted.", 404)
    return video


def delete_video(db: Session, user_id: str, video_pk: int) -> None:
    video = get_video(db, user_id, video_pk)
    if video.status == VideoStatus.PROCESSING:
        raise AppError("This video is still being processed. Delete it after it finishes.", 409)
    db.delete(video)
    db.commit()


def build_detail(video: Video) -> VideoDetail:
    detail = VideoDetail.model_validate(video, from_attributes=True)
    if video.status != VideoStatus.COMPLETED:
        return detail

    for language in LANGUAGES:
        material = next((m for m in video.materials if m.language == language), None)
        if material is None:
            continue
        detail.content[language] = LanguageContent(
            summary=material.summary,
            notes=material.notes,
            timestamps=material.timestamps,
            quiz=[
                {
                    "question": q.question,
                    "options": q.options,
                    "correct_index": q.correct_index,
                    "explanation": q.explanation,
                }
                for q in video.quiz_questions
                if q.language == language
            ],
            qa=[{"question": p.question, "answer": p.answer} for p in video.qa_pairs if p.language == language],
        )
    return detail


def update_progress(video_pk: int, progress: int, message: str, **fields) -> None:
    with session_scope() as db:
        db.execute(
            update(Video)
            .where(Video.id == video_pk)
            .values(progress=progress, progress_message=message, **fields)
        )


def mark_failed(video_pk: int, error_message: str) -> None:
    with session_scope() as db:
        db.execute(
            update(Video)
            .where(Video.id == video_pk)
            .values(status=VideoStatus.FAILED, progress_message="Failed", error_message=error_message)
        )


def save_results(video_pk: int, content: dict[Language, LanguageContent]) -> None:
    """Store all generated content in a single transaction."""
    with session_scope() as db:
        video = db.get(Video, video_pk, options=_CONTENT_OPTIONS)
        # Replace any content from an earlier attempt.
        video.materials.clear()
        video.quiz_questions.clear()
        video.qa_pairs.clear()
        db.flush()

        for language, item in content.items():
            video.materials.append(
                StudyMaterial(
                    user_id=video.user_id,
                    language=language,
                    summary=item.summary.model_dump(),
                    notes=item.notes.model_dump(),
                    timestamps=[stamp.model_dump() for stamp in item.timestamps],
                )
            )
            video.quiz_questions.extend(
                QuizQuestion(user_id=video.user_id, language=language, position=index, **question.model_dump())
                for index, question in enumerate(item.quiz)
            )
            video.qa_pairs.extend(
                QAPair(user_id=video.user_id, language=language, position=index, **pair.model_dump())
                for index, pair in enumerate(item.qa)
            )

        video.status = VideoStatus.COMPLETED
        video.progress = 100
        video.progress_message = "Ready"
        video.error_message = None


def fail_interrupted_jobs() -> None:
    """Jobs cannot survive a server restart, so mark them as failed (not deleted)."""
    with session_scope() as db:
        db.execute(
            update(Video)
            .where(Video.status == VideoStatus.PROCESSING)
            .values(
                status=VideoStatus.FAILED,
                progress_message="Failed",
                error_message=(
                    "Processing was interrupted because the server restarted. Please analyze the video again."
                ),
            )
        )
