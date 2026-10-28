"""Canais/grupos e mensagens."""

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ChannelCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=2, max_length=40)
    description: str = Field(default="", max_length=255)
    is_private: bool = False

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        cleaned = re.sub(r"\s+", "-", value.strip().lower())
        if not (2 <= len(cleaned) <= 40) or not re.fullmatch(r"[\w\-]+", cleaned, flags=re.UNICODE):
            raise ValueError("Nome inválido. Use letras, números, hífen ou underline.")
        return cleaned


class ChannelPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    is_private: bool
    created_at: datetime


class MessageAuthor(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    nickname: str
    avatar_url: str | None
    is_admin: bool


class MessagePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    channel_id: int | None
    content: str
    attachment_url: str | None
    attachment_type: str | None
    created_at: datetime
    edited_at: datetime | None
    sender: MessageAuthor
