"""Schemas de DM."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DMPeer(BaseModel):
    id: int
    username: str
    nickname: str
    avatar_url: str | None
    is_admin: bool
    is_online: bool = False


class DMLastMessage(BaseModel):
    id: int
    content: str
    created_at: datetime
    attachment_url: str | None = None


class DMConversationPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    other: DMPeer
    last_message: DMLastMessage | None = None


class DMOpenRequest(BaseModel):
    user_id: int = Field(ge=1)
