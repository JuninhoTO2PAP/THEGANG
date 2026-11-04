"""Entrada e saída de cadastro, login e convites."""

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.schemas.user import UserPublic


class RegisterRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    invite_code: str = Field(min_length=4, max_length=64)
    username: str = Field(min_length=3, max_length=32)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    nickname: str = Field(min_length=2, max_length=32)

    @field_validator("invite_code")
    @classmethod
    def _code(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("username")
    @classmethod
    def _username(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9_]{3,32}", value):
            raise ValueError("Usuário deve ter 3–32 caracteres: letras, números ou _.")
        return value.lower()

    @field_validator("nickname")
    @classmethod
    def _nickname(cls, value: str) -> str:
        if not (2 <= len(value) <= 32):
            raise ValueError("Apelido deve ter entre 2 e 32 caracteres.")
        return value

    @field_validator("password")
    @classmethod
    def _password(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Senha muito longa para o bcrypt (máximo 72 bytes).")
        return value


class LoginRequest(BaseModel):
    """`login` aceita e-mail ou nome de usuário."""

    model_config = ConfigDict(str_strip_whitespace=True)

    login: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class AuthResponse(BaseModel):
    user: UserPublic
    tokens: TokenPair


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=10)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=10)


class InviteCreate(BaseModel):
    # None = sem expiração (ilimitado).
    expires_in_days: int | None = Field(default=7, ge=1, le=90)


class InvitePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    created_by: int
    used_by: int | None
    used_at: datetime | None
    expires_at: datetime | None
    created_at: datetime
