from datetime import datetime
from pydantic import BaseModel, Field


class ProfileCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)


class ProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)


class ProfileRead(BaseModel):
    id: int
    name: str
    user_id: int
    is_public: bool
    moderated_by: int | None
    moderation_status: str | None
    moderation_comment: str | None
    moderated_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProfileListItem(BaseModel):
    id: int
    name: str
    is_public: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
