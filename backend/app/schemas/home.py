"""Home THE GANG + membros online."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class OnlineMember(BaseModel):
    id: int
    username: str
    nickname: str
    avatar_url: str | None
    is_admin: bool
    presence: str = "online"
    status_text: str | None = None
    ff_role: str | None = None
    ff_nick: str | None = None


class HomePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    banner_title: str
    banner_subtitle: str
    admin_note: str
    next_event_title: str | None
    next_event_at: datetime | None
    updated_at: datetime
    online: list[OnlineMember] = []


class HomeUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    banner_title: str = Field(min_length=2, max_length=80)
    banner_subtitle: str = Field(default="", max_length=160)
    admin_note: str = Field(default="", max_length=2000)
    next_event_title: str | None = Field(default=None, max_length=120)
    next_event_at: datetime | None = None

    @field_validator("next_event_title")
    @classmethod
    def _event_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None
