from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from admin.dependencies.auth import get_current_admin_user
from admin.schemas.users import (
    AdminRoleChangeRequest,
    AdminRoleChangeResponse,
    AdminUserBanRequest,
    AdminUserBanResponse,
    AdminUserProfilesPage,
    AdminUserRead,
    AdminUsersPage,
    AdminUserTextsPage, AdminUserRole,
)
from admin.services import users as users_service
from db import models
from db.session import get_db

router = APIRouter(prefix="/users", tags=["admin-users"])

@router.get("/roles", response_model=list[AdminUserRole])
def list_roles(
    db: Session = Depends(get_db),
):
    return users_service.list_roles(db)

@router.get("", response_model=AdminUsersPage)
def list_users(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(get_current_admin_user),
):
    return users_service.list_users(db, page, per_page)


@router.get("/{user_id}", response_model=AdminUserRead)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(get_current_admin_user),
):
    return users_service.get_user(db, user_id)


@router.post(
    "/{user_id}/ban",
    response_model=AdminUserBanResponse,
    status_code=status.HTTP_200_OK,
)
def ban_user(
    user_id: int,
    payload: AdminUserBanRequest,
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(get_current_admin_user),
):
    return users_service.ban_user(db, user_id, payload.reason)


@router.post(
    "/{user_id}/role-change",
    response_model=AdminRoleChangeResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def change_user_role(
    user_id: int,
    payload: AdminRoleChangeRequest,
    db: Session = Depends(get_db),
):
    return users_service.change_user_role(db, user_id, payload)


@router.get("/{user_id}/profiles", response_model=AdminUserProfilesPage)
def list_user_profiles(
    user_id: int,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(get_current_admin_user),
):
    return users_service.list_user_profiles(db, user_id, page, per_page)


@router.get("/{user_id}/texts", response_model=AdminUserTextsPage)
def list_user_texts(
    user_id: int,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(get_current_admin_user),
):
    return users_service.list_user_texts(db, user_id, page, per_page)
