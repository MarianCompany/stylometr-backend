from datetime import datetime
from pydantic import BaseModel, Field


class ProfileTextCreate(BaseModel):
    content: str = Field(min_length=1)


class ProfileTextRead(BaseModel):
    id: int
    content: str
    file_id: int | None
    char_count: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProfileTextListItem(BaseModel):
    id: int
    char_count: int
    short_content: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
