from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from admin.schemas.moderation import (
    AdminModerationDecisionRequest,
    AdminProfileListItem,
    AdminProfileRead,
    AdminProfileTextListItem,
)
from admin.schemas.pagination import PaginatedResponse
from admin.utils.pagination import paginate_query
from db import crud, models

MODERATION_STATUS_PENDING = "pending"
MODERATION_STATUS_APPROVED = "approved"
MODERATION_STATUS_REVISION_REQUIRED = "revision_required"


def _get_profile_or_404(db: Session, profile_id: int) -> models.AuthorProfile:
    profile = crud.get_profile_by_id(db, profile_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Профиль не найден")
    return profile


def _count_profile_texts(db: Session, profile_id: int) -> int:
    return (
        db.query(func.count(models.AuthorProfileText.id))
        .filter(models.AuthorProfileText.profile_id == profile_id)
        .scalar()
        or 0
    )


def _serialize_profile_list_item(db: Session, profile: models.AuthorProfile) -> AdminProfileListItem:
    return AdminProfileListItem(
        id=profile.id,
        name=profile.name,
        user_id=profile.user_id,
        user_email=profile.user.email if profile.user else None,
        is_public=profile.is_public,
        moderation_status=profile.moderation_status,
        moderation_comment=profile.moderation_comment,
        moderated_by=profile.moderated_by,
        moderated_at=profile.moderated_at,
        texts_count=_count_profile_texts(db, profile.id),
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


def _serialize_profile_read(db: Session, profile: models.AuthorProfile) -> AdminProfileRead:
    return AdminProfileRead(
        **_serialize_profile_list_item(db, profile).model_dump(),
        internal_notes=None,
    )


def list_profiles(
    db: Session,
    page: int,
    per_page: int,
) -> PaginatedResponse[AdminProfileListItem]:
    query = db.query(models.AuthorProfile).order_by(
        models.AuthorProfile.created_at.desc(),
        models.AuthorProfile.id.desc(),
    )
    profiles, meta = paginate_query(query, page, per_page)
    return PaginatedResponse(
        data=[_serialize_profile_list_item(db, profile) for profile in profiles],
        meta=meta,
    )


def list_pending_profiles(
    db: Session,
    page: int,
    per_page: int,
) -> PaginatedResponse[AdminProfileListItem]:
    query = (
        db.query(models.AuthorProfile)
        .filter(models.AuthorProfile.moderation_status == MODERATION_STATUS_PENDING)
        .order_by(models.AuthorProfile.created_at.desc(), models.AuthorProfile.id.desc())
    )
    profiles, meta = paginate_query(query, page, per_page)
    return PaginatedResponse(
        data=[_serialize_profile_list_item(db, profile) for profile in profiles],
        meta=meta,
    )


def get_profile(db: Session, profile_id: int) -> AdminProfileRead:
    return _serialize_profile_read(db, _get_profile_or_404(db, profile_id))


def approve_profile(
    db: Session,
    profile_id: int,
    moderator: models.User,
    payload: AdminModerationDecisionRequest,
) -> AdminProfileRead:
    profile = _get_profile_or_404(db, profile_id)
    profile.is_public = True
    profile.moderation_status = MODERATION_STATUS_APPROVED
    profile.moderation_comment = payload.comment
    profile.moderated_by = moderator.id
    profile.moderated_at = datetime.utcnow()
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return _serialize_profile_read(db, profile)


def block_profile_for_revision(
    db: Session,
    profile_id: int,
    moderator: models.User,
    payload: AdminModerationDecisionRequest,
) -> AdminProfileRead:
    profile = _get_profile_or_404(db, profile_id)
    profile.is_public = False
    profile.moderation_status = MODERATION_STATUS_REVISION_REQUIRED
    profile.moderation_comment = payload.comment
    profile.moderated_by = moderator.id
    profile.moderated_at = datetime.utcnow()
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return _serialize_profile_read(db, profile)


def list_profile_texts(
    db: Session,
    profile_id: int,
    page: int,
    per_page: int,
) -> PaginatedResponse[AdminProfileTextListItem]:
    _get_profile_or_404(db, profile_id)
    query = (
        db.query(models.Text)
        .join(models.AuthorProfileText, models.AuthorProfileText.text_id == models.Text.id)
        .filter(models.AuthorProfileText.profile_id == profile_id)
        .order_by(models.AuthorProfileText.created_at.desc(), models.Text.id.desc())
    )
    texts, meta = paginate_query(query, page, per_page)
    return PaginatedResponse(
        data=[
            AdminProfileTextListItem(
                id=text.id,
                user_id=text.user_id,
                file_id=text.file_id,
                char_count=text.char_count,
                short_content=text.short_content,
                created_at=text.created_at,
                updated_at=text.updated_at,
            )
            for text in texts
        ],
        meta=meta,
    )
