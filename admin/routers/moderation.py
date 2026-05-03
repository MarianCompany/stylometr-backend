from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from admin.dependencies.auth import get_current_admin_user
from admin.schemas.moderation import (
    AdminModerationDecisionRequest,
    AdminProfilesPage,
    AdminProfileRead,
)
from admin.services import moderation as moderation_service
from db import models
from db.session import get_db

router = APIRouter(prefix="/moderation", tags=["admin-moderation"])


@router.get("/profiles/pending", response_model=AdminProfilesPage)
def list_pending_profiles(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(get_current_admin_user),
):
    return moderation_service.list_pending_profiles(db, page, per_page)


@router.post("/profiles/{profile_id}/approve", response_model=AdminProfileRead)
def approve_profile(
    profile_id: int,
    payload: AdminModerationDecisionRequest,
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(get_current_admin_user),
):
    return moderation_service.approve_profile(db, profile_id, current_admin, payload)


@router.post("/profiles/{profile_id}/block", response_model=AdminProfileRead)
def block_profile_for_revision(
    profile_id: int,
    payload: AdminModerationDecisionRequest,
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(get_current_admin_user),
):
    return moderation_service.block_profile_for_revision(db, profile_id, current_admin, payload)
