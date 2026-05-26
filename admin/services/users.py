from datetime import datetime
from typing import List

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from admin.schemas.pagination import PaginatedResponse
from admin.schemas.users import (
    AdminRoleChangeRequest,
    AdminRoleChangeResponse,
    AdminUserBanResponse,
    AdminUserListItem,
    AdminUserProfileListItem,
    AdminUserRead,
    AdminUserTextListItem, AdminUserRole,
)
from admin.utils.pagination import paginate_query
from db import crud, models


def _role_name(user: models.User) -> str | None:
    return user.role.name if user.role else None


def _is_blocked(user: models.User) -> bool:
    return not user.is_active


def _count_user_profiles(db: Session, user_id: int) -> int:
    return (
        db.query(func.count(models.AuthorProfile.id))
        .filter(models.AuthorProfile.user_id == user_id)
        .scalar()
        or 0
    )


def _count_user_texts(db: Session, user_id: int) -> int:
    return db.query(func.count(models.Text.id)).filter(models.Text.user_id == user_id).scalar() or 0


def _serialize_user_list_item(user: models.User) -> AdminUserListItem:
    return AdminUserListItem(
        id=user.id,
        email=user.email,
        nickname=user.nickname,
        role_id=user.role_id,
        role=_role_name(user),
        is_active=user.is_active,
        is_blocked=_is_blocked(user),
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def _serialize_user_read(db: Session, user: models.User) -> AdminUserRead:
    return AdminUserRead(
        **_serialize_user_list_item(user).model_dump(),
        profiles_count=_count_user_profiles(db, user.id),
        texts_count=_count_user_texts(db, user.id),
        internal_notes=None,
    )


def _get_user_or_404(db: Session, user_id: int) -> models.User:
    user = crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")
    return user

def list_roles(db: Session) -> list[AdminUserRole]:
    roles: List[models.UserRole] = db.query(models.UserRole)

    return [
        AdminUserRole(
            id=role.id,
            name=role.name,
        )
        for role in roles
    ]


def list_users(db: Session, page: int, per_page: int) -> PaginatedResponse[AdminUserListItem]:
    query = db.query(models.User).order_by(models.User.created_at.desc(), models.User.id.desc())
    users, meta = paginate_query(query, page, per_page)
    return PaginatedResponse(
        data=[_serialize_user_list_item(user) for user in users],
        meta=meta,
    )


def get_user(db: Session, user_id: int) -> AdminUserRead:
    return _serialize_user_read(db, _get_user_or_404(db, user_id))


def ban_user(
    db: Session,
    user_id: int,
    reason: str | None = None,
) -> AdminUserBanResponse:
    user = _get_user_or_404(db, user_id)
    user.is_active = False
    db.add(user)
    db.commit()
    db.refresh(user)
    return AdminUserBanResponse(user=_serialize_user_read(db, user), reason=reason)


def change_user_role(
    db: Session,
    user_id: int,
    payload: AdminRoleChangeRequest,
) -> AdminRoleChangeResponse:
    user = _get_user_or_404(db, user_id)
    if payload.role_id is None and payload.role_name is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="role_id or role_name is required",
        )
    if payload.role_id is not None:
        role = db.query(models.UserRole).filter(models.UserRole.id == payload.role_id).first()
        if not role:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    user.role_id = payload.role_id
    db.add(user)
    db.commit()
    db.refresh(user)

    return AdminRoleChangeResponse(
        user_id=user.id,
        role_id=payload.role_id,
    )


def list_user_profiles(
    db: Session,
    user_id: int,
    page: int,
    per_page: int,
) -> PaginatedResponse[AdminUserProfileListItem]:
    _get_user_or_404(db, user_id)
    query = (
        db.query(models.AuthorProfile)
        .filter(models.AuthorProfile.user_id == user_id)
        .order_by(models.AuthorProfile.created_at.desc(), models.AuthorProfile.id.desc())
    )
    profiles, meta = paginate_query(query, page, per_page)
    return PaginatedResponse(
        data=[
            AdminUserProfileListItem(
                id=profile.id,
                name=profile.name,
                user_id=profile.user_id,
                is_public=profile.is_public,
                moderation_status=profile.moderation_status,
                moderation_comment=profile.moderation_comment,
                moderated_by=profile.moderated_by,
                moderated_at=profile.moderated_at,
                created_at=profile.created_at,
                updated_at=profile.updated_at,
            )
            for profile in profiles
        ],
        meta=meta,
    )


def list_user_texts(
    db: Session,
    user_id: int,
    page: int,
    per_page: int,
) -> PaginatedResponse[AdminUserTextListItem]:
    _get_user_or_404(db, user_id)
    query = (
        db.query(models.Text)
        .filter(models.Text.user_id == user_id)
        .order_by(models.Text.created_at.desc(), models.Text.id.desc())
    )
    texts, meta = paginate_query(query, page, per_page)
    return PaginatedResponse(
        data=[
            AdminUserTextListItem(
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
