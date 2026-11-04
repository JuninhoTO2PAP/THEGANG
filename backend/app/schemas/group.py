"""Schemas de grupo, canal interno, cargo e membro."""

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class GroupCreate(BaseModel):
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


class GroupUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=2, max_length=40)
    description: str | None = Field(default=None, max_length=255)


class GroupPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    icon_url: str | None
    is_private: bool
    created_by: int
    created_at: datetime
    my_permissions: int = 0


class ChannelCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=2, max_length=40)
    description: str = Field(default="", max_length=255)
    channel_type: str = Field(default="text")

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        cleaned = re.sub(r"\s+", "-", value.strip().lower())
        if not (2 <= len(cleaned) <= 40) or not re.fullmatch(r"[\w\-]+", cleaned, flags=re.UNICODE):
            raise ValueError("Nome inválido.")
        return cleaned

    @field_validator("channel_type")
    @classmethod
    def _type(cls, value: str) -> str:
        if value not in {"text", "voice"}:
            raise ValueError("Tipo deve ser text ou voice.")
        return value


class ChannelPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    group_id: int
    name: str
    description: str
    channel_type: str
    position: int
    created_at: datetime


class RoleCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=2, max_length=40)
    color: str = Field(default="#99aab5", max_length=7)
    permissions: int = Field(default=0)
    is_admin: bool = False

    @field_validator("color")
    @classmethod
    def _color(cls, value: str) -> str:
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
            raise ValueError("Cor deve ser hex (#RRGGBB).")
        return value.lower()


class RoleUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=2, max_length=40)
    color: str | None = None
    permissions: int | None = None
    is_admin: bool | None = None


class RolePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    group_id: int
    name: str
    color: str
    position: int
    permissions: int
    is_default: bool
    created_at: datetime


class MemberPublic(BaseModel):
    id: int
    username: str
    nickname: str
    avatar_url: str | None
    is_admin: bool
    role_ids: list[int]
    joined_at: datetime
    is_online: bool = False
    presence: str = "online"
    status_text: str | None = None
    ff_id: str | None = None
    ff_nick: str | None = None
    ff_role: str | None = None
    ff_region: str | None = None
    banner_theme: str = "gold"


class MemberRolesUpdate(BaseModel):
    role_ids: list[int]


class MessageAuthor(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    nickname: str
    avatar_url: str | None
    is_admin: bool
    presence: str = "online"
    status_text: str | None = None


class ReactionPublic(BaseModel):
    emoji: str
    count: int
    me: bool = False


class ReplyPreview(BaseModel):
    id: int
    content: str
    sender_nickname: str


class MessagePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    channel_id: int | None
    content: str
    attachment_url: str | None
    attachment_type: str | None
    reply_to_id: int | None = None
    reply_to: ReplyPreview | None = None
    pinned_at: datetime | None = None
    pinned_by: int | None = None
    created_at: datetime
    edited_at: datetime | None
    sender: MessageAuthor
    reactions: list[ReactionPublic] = []


class MessageCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    content: str = Field(default="", max_length=4000)
    attachment_url: str | None = None
    attachment_type: str | None = None
    reply_to_id: int | None = None


class MessageUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    content: str = Field(min_length=1, max_length=4000)


class ReactionCreate(BaseModel):
    emoji: str = Field(min_length=1, max_length=32)


class GroupInviteCreate(BaseModel):
    # 0 = nunca expira.
    expires_in_days: int = Field(default=7, ge=0, le=90)
    max_uses: int | None = Field(default=None, ge=1, le=1000)


class GroupInvitePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    group_id: int
    code: str
    created_by: int
    max_uses: int | None
    uses: int
    expires_at: datetime | None
    created_at: datetime
    link_path: str = ""


class GroupJoinRequest(BaseModel):
    code: str = Field(min_length=4, max_length=64)
