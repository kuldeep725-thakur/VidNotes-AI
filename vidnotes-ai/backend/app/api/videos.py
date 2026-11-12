import re

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.auth import CurrentUser, get_current_user
from app.core.errors import AppError
from app.models import VideoStatus
from app.schemas.user import QuizResultCreate, QuizResultOut
from app.schemas.video import AnalyzeRequest, Language, VideoDetail, VideoListItem, VideoStatusOut
from app.services import pdf_service, user_service, video_service
from app.services.video_processor import process_video

router = APIRouter(prefix="/api/videos", tags=["videos"])


@router.post("", response_model=VideoStatusOut, status_code=status.HTTP_202_ACCEPTED)
def analyze_video(
    payload: AnalyzeRequest,
    background_tasks: BackgroundTasks,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    video, should_process = video_service.start_analysis(db, user.id, payload.url, payload.quiz_count)
    if should_process:
        background_tasks.add_task(process_video, video.id)
    return video


@router.get("", response_model=list[VideoListItem])
def list_videos(
    search: str | None = Query(default=None, max_length=100),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return video_service.list_videos(db, user.id, search)


@router.get("/{video_id}", response_model=VideoDetail)
def get_video(video_id: int, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return video_service.build_detail(video_service.get_video(db, user.id, video_id))


@router.get("/{video_id}/status", response_model=VideoStatusOut)
def get_status(video_id: int, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return video_service.get_video(db, user.id, video_id)


@router.delete("/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_video(video_id: int, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    video_service.delete_video(db, user.id, video_id)


@router.get("/{video_id}/pdf")
def download_pdf(
    video_id: int,
    language: Language = "en",
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    detail = video_service.build_detail(video_service.get_video(db, user.id, video_id))
    if detail.status != VideoStatus.COMPLETED or language not in detail.content:
        raise AppError("Notes for this video are not ready yet.", 409)

    pdf_bytes = pdf_service.build_pdf(detail, language)
    safe_title = re.sub(r"[^A-Za-z0-9]+", "-", detail.title).strip("-")[:60] or "notes"
    filename = f"{safe_title}-{language}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{video_id}/quiz-results", response_model=QuizResultOut, status_code=status.HTTP_201_CREATED)
def save_quiz_result(
    video_id: int,
    payload: QuizResultCreate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return user_service.save_quiz_result(db, user.id, video_id, payload)


@router.get("/{video_id}/quiz-results", response_model=list[QuizResultOut])
def list_quiz_results(video_id: int, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return user_service.list_quiz_results(db, user.id, video_id)
