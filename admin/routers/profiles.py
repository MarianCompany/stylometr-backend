from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from admin.schemas.moderation import (
    AdminProfilesPage,
    AdminProfileRead, AdminProfileTextsPage,
)
from admin.services import moderation as moderation_service
from db.session import get_db

router = APIRouter(prefix="/profiles", tags=["admin-profiles"])

@router.get("/", response_model=AdminProfilesPage)
def list_profiles(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return moderation_service.list_profiles(db, page, per_page)


@router.get("/{profile_id}", response_model=AdminProfileRead)
def get_profile(
    profile_id: int,
    db: Session = Depends(get_db),
):
    return moderation_service.get_profile(db, profile_id)

@router.get("/{profile_id}/texts", response_model=AdminProfileTextsPage)
def list_profile_texts(
    profile_id: int,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return moderation_service.list_profile_texts(db, profile_id, page, per_page)