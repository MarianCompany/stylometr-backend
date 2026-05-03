from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from admin.schemas.pagination import PaginatedResponse


class AdminUserRole(BaseModel):
    id: int
    name: str

class AdminUserListItem(BaseModel):
    id: int
    email: EmailStr
    nickname: str
    role_id: int | None
    role: str | None
    is_active: bool
    is_blocked: bool
    created_at: datetime
    updated_at: datetime


class AdminUserRead(AdminUserListItem):
    profiles_count: int
    texts_count: int
    internal_notes: str | None = None


class AdminUserBanRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class AdminUserBanResponse(BaseModel):
    user: AdminUserRead
    reason: str | None = None


class AdminRoleChangeRequest(BaseModel):
    role_id: int | None = None
    role_name: str | None = Field(default=None, min_length=2, max_length=50)
    reason: str | None = Field(default=None, max_length=500)


class AdminRoleChangeResponse(BaseModel):
    user_id: int
    role_id: int


class AdminUserProfileListItem(BaseModel):
    id: int
    name: str
    user_id: int
    is_public: bool
    moderation_status: str | None
    moderation_comment: str | None
    moderated_by: int | None
    moderated_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AdminUserTextListItem(BaseModel):
    id: int
    user_id: int
    file_id: int | None
    char_count: int
    short_content: str
    created_at: datetime
    updated_at: datetime


AdminUsersPage = PaginatedResponse[AdminUserListItem]
AdminUserProfilesPage = PaginatedResponse[AdminUserProfileListItem]
AdminUserTextsPage = PaginatedResponse[AdminUserTextListItem]
