"""Membro do time."""

from datetime import datetime

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import UTCDateTime


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    nickname: Mapped[str] = mapped_column(String(32))
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_online: Mapped[bool] = mapped_column(Boolean, default=False)
    presence: Mapped[str] = mapped_column(String(16), default="online")
    status_text: Mapped[str | None] = mapped_column(String(120), nullable=True)
    ff_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ff_nick: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ff_role: Mapped[str | None] = mapped_column(String(16), nullable=True)
    ff_region: Mapped[str | None] = mapped_column(String(16), nullable=True)
    banner_theme: Mapped[str] = mapped_column(String(16), default="gold")
    accent: Mapped[str] = mapped_column(String(16), default="gold")
    last_seen: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
