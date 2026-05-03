from datetime import datetime
from typing import Any

from pydantic import BaseModel

from admin.schemas.pagination import PaginatedResponse


class AdminActionLogRead(BaseModel):
    id: int
    actor_user_id: int | None
    action: str
    target_type: str | None
    target_id: int | None
    metadata: dict[str, Any] | None
    created_at: datetime


AdminActionLogsPage = PaginatedResponse[AdminActionLogRead]
