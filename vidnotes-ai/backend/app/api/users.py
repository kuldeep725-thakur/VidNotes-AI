from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.auth import CurrentUser, get_current_user
from app.schemas.user import PreferencesOut, PreferencesUpdate, ProfileOut, ProfileUpdate
from app.services import user_service

router = APIRouter(prefix="/api/me", tags=["account"])


def _profile_out(db: Session, user: CurrentUser, profile) -> ProfileOut:
    return ProfileOut(
        id=profile.id,
        email=profile.email,
        full_name=profile.full_name,
        avatar_url=profile.avatar_url,
        provider=user.provider,
        created_at=profile.created_at,
        stats=user_service.profile_stats(db, user.id),
    )


@router.get("", response_model=ProfileOut)
def get_profile(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return _profile_out(db, user, user_service.sync_profile(db, user))


@router.patch("", response_model=ProfileOut)
def update_profile(
    payload: ProfileUpdate, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)
):
    return _profile_out(db, user, user_service.update_profile_name(db, user, payload.full_name))


@router.get("/preferences", response_model=PreferencesOut)
def get_preferences(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return user_service.get_preferences(db, user.id)


@router.patch("/preferences", response_model=PreferencesOut)
def update_preferences(
    payload: PreferencesUpdate, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)
):
    return user_service.update_preferences(db, user.id, payload)
