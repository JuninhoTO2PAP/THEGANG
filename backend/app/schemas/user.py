"""Dados públicos de um membro. A senha nunca sai da API."""

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


FF_ROLES = {"cpt", "r1", "r2", "r3", "suporte"}
FF_REGIONS = {"BR", "LATAM", "NA", "EU", "ASIA", "OTHER"}
BANNER_THEMES = {"gold", "ember", "navy", "violet", "forest", "crimson"}


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: EmailStr
    nickname: str
    avatar_url: str | None
    is_admin: bool
    is_online: bool
    presence: str = "online"
    status_text: str | None = None
    ff_id: str | None = None
    ff_nick: str | None = None
    ff_role: str | None = None
    ff_region: str | None = None
    banner_theme: str = "gold"
    last_seen: datetime | None
    created_at: datetime


class StatusUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    presence: str = Field(default="online")
    status_text: str | None = Field(default=None, max_length=120)

    @field_validator("presence")
    @classmethod
    def _presence(cls, value: str) -> str:
        allowed = {"online", "away", "dnd", "invisible"}
        cleaned = value.strip().lower()
        if cleaned not in allowed:
            raise ValueError("Presence inválida. Use online, away, dnd ou invisible.")
        return cleaned

    @field_validator("status_text")
    @classmethod
    def _status_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class PasswordChange(BaseModel):
    """Troca de senha autenticada."""

    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def _new_password(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Senha muito longa.")
        if not any(c.isalpha() for c in value) or not any(c.isdigit() for c in value):
            raise ValueError("Nova senha precisa de letras e números.")
        return value


class UserUpdate(BaseModel):
    """Edição de perfil (apelido, @usuário e carta Free Fire)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    nickname: str = Field(min_length=2, max_length=32)
    username: str = Field(min_length=3, max_length=32)
    ff_id: str | None = Field(default=None, max_length=32)
    ff_nick: str | None = Field(default=None, max_length=32)
    ff_role: str | None = Field(default=None, max_length=16)
    ff_region: str | None = Field(default=None, max_length=16)
    banner_theme: str | None = Field(default=None, max_length=16)

    @field_validator("nickname")
    @classmethod
    def _nickname(cls, value: str) -> str:
        if not (2 <= len(value) <= 32):
            raise ValueError("Apelido deve ter entre 2 e 32 caracteres.")
        return value

    @field_validator("username")
    @classmethod
    def _username(cls, value: str) -> str:
        cleaned = value.lstrip("@").lower()
        if not re.fullmatch(r"[a-z0-9_]{3,32}", cleaned):
            raise ValueError("Usuário deve ter 3–32 caracteres: letras, números ou _.")
        return cleaned

    @field_validator("ff_id", "ff_nick")
    @classmethod
    def _optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("ff_role")
    @classmethod
    def _ff_role(cls, value: str | None) -> str | None:
        if value is None or value.strip() == "":
            return None
        cleaned = value.strip().lower()
        if cleaned not in FF_ROLES:
            raise ValueError("Função inválida. Use CPT, R1, R2, R3 ou SUPORTE.")
        return cleaned

    @field_validator("ff_region")
    @classmethod
    def _ff_region(cls, value: str | None) -> str | None:
        if value is None or value.strip() == "":
            return None
        cleaned = value.strip().upper()
        if cleaned not in FF_REGIONS:
            raise ValueError("Região inválida.")
        return cleaned

    @field_validator("banner_theme")
    @classmethod
    def _banner(cls, value: str | None) -> str | None:
        if value is None or value.strip() == "":
            return None
        cleaned = value.strip().lower()
        if cleaned not in BANNER_THEMES:
            raise ValueError("Tema de banner inválido.")
        return cleaned
