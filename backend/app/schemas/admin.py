"""Painel do administrador. A senha nunca é devolvida."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class AdminMember(BaseModel):
    id: int
    username: str
    email: EmailStr
    nickname: str
    avatar_url: str | None = None
    is_admin: bool
    is_online: bool
    presence: str
    status_text: str | None = None
    ff_id: str | None = None
    ff_nick: str | None = None
    ff_role: str | None = None
    ff_region: str | None = None
    team: str | None = None
    last_seen: datetime | None = None
    created_at: datetime


class AdminPasswordReset(BaseModel):
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def _new_password(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Senha muito longa.")
        if not any(c.isalpha() for c in value) or not any(c.isdigit() for c in value):
            raise ValueError("Nova senha precisa de letras e números.")
        return value
