"""Profiles, preferences and quiz results of the signed-in user."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser
from app.core.errors import AppError
from app.models import Profile, QuizResult, Todo, UserPreferences, Video, VideoStatus
from app.schemas.user import PreferencesUpdate, ProfileStats, QuizResultCreate
from app.services import video_service

MAX_RESULTS_PER_VIDEO = 10


def sync_profile(db: Session, user: CurrentUser) -> Profile:
    """Create or refresh the profile from the sign-in details.

    Email and picture follow the account; a name the user edited is kept.
    """
    profile = db.get(Profile, user.id)
    if profile is None:
        profile = Profile(id=user.id, email=user.email, full_name=user.full_name, avatar_url=user.avatar_url)
        db.add(profile)
    else:
        profile.email = user.email or profile.email
        profile.avatar_url = user.avatar_url or profile.avatar_url
        profile.full_name = profile.full_name or user.full_name
    db.commit()
    return profile


def update_profile_name(db: Session, user: CurrentUser, full_name: str) -> Profile:
    profile = sync_profile(db, user)
    profile.full_name = full_name
    db.commit()
    return profile


def profile_stats(db: Session, user_id: str) -> ProfileStats:
    def count(query) -> int:
        return db.scalar(query) or 0

    def tasks(done: bool):
        return select(func.count()).select_from(Todo).where(Todo.user_id == user_id, Todo.is_done.is_(done))

    return ProfileStats(
        videos=count(select(func.count()).select_from(Video).where(Video.user_id == user_id)),
        quizzes_taken=count(select(func.count()).select_from(QuizResult).where(QuizResult.user_id == user_id)),
        open_tasks=count(tasks(False)),
        done_tasks=count(tasks(True)),
    )


def get_preferences(db: Session, user_id: str) -> UserPreferences:
    """Saved preferences, or the defaults if the user never changed them."""
    preferences = db.get(UserPreferences, user_id)
    if preferences is None:
        preferences = UserPreferences(user_id=user_id, theme="dark", default_language="en", default_quiz_count=10)
    return preferences


def update_preferences(db: Session, user_id: str, data: PreferencesUpdate) -> UserPreferences:
    preferences = get_preferences(db, user_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        if value is None:
            raise AppError(f"{field} cannot be empty.", 422)
        setattr(preferences, field, value)
    db.add(preferences)
    db.commit()
    return preferences


def save_quiz_result(db: Session, user_id: str, video_pk: int, data: QuizResultCreate) -> QuizResult:
    """Score the answers against the stored quiz and keep the attempt."""
    video = video_service.get_video(db, user_id, video_pk)
    if video.status != VideoStatus.COMPLETED:
        raise AppError("The quiz for this video is not ready yet.", 409)
    questions = [q for q in video.quiz_questions if q.language == data.language]
    if len(data.answers) != len(questions):
        raise AppError("The answers do not match this quiz. Reload the page and try again.", 422)

    score = sum(answer == question.correct_index for answer, question in zip(data.answers, questions))
    result = QuizResult(
        user_id=user_id,
        video_id=video.id,
        language=data.language,
        score=score,
        total=len(questions),
        answers=data.answers,
    )
    db.add(result)
    db.commit()
    return result


def list_quiz_results(db: Session, user_id: str, video_pk: int) -> list[QuizResult]:
    video_service.get_video(db, user_id, video_pk)
    query = (
        select(QuizResult)
        .where(QuizResult.user_id == user_id, QuizResult.video_id == video_pk)
        .order_by(QuizResult.created_at.desc(), QuizResult.id.desc())
        .limit(MAX_RESULTS_PER_VIDEO)
    )
    return list(db.scalars(query))
