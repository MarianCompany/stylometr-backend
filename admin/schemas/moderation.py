from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from admin.schemas.pagination import PaginatedResponse


class AdminProfileListItem(BaseModel):
    id: int
    name: str
    user_id: int
    user_email: EmailStr | None
    is_public: bool
    moderation_status: str | None
    moderation_comment: str | None
    moderated_by: int | None
    moderated_at: datetime | None
    texts_count: int
    created_at: datetime
    updated_at: datetime


class AdminProfileRead(AdminProfileListItem):
    internal_notes: str | None = None


class AdminModerationDecisionRequest(BaseModel):
    comment: str | None = Field(default=None, max_length=500)


class AdminProfileTextListItem(BaseModel):
    id: int
    user_id: int
    file_id: int | None
    char_count: int
    short_content: str
    created_at: datetime
    updated_at: datetime


AdminProfilesPage = PaginatedResponse[AdminProfileListItem]
AdminProfileTextsPage = PaginatedResponse[AdminProfileTextListItem]
