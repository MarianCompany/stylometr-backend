from fastapi import APIRouter, Depends, Query

from admin.dependencies.auth import get_current_admin_user
from admin.schemas.logs import AdminActionLogsPage
from admin.services import logs as logs_service
from db import models

router = APIRouter(prefix="/logs", tags=["admin-logs"])


@router.get("", response_model=AdminActionLogsPage)
def list_action_logs(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    current_admin: models.User = Depends(get_current_admin_user),
):
    return logs_service.list_action_logs(page, per_page)
