"""Home pública do THE GANG (banner, recado, próximo evento)."""

from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import UTCDateTime


class GangHome(Base):
    __tablename__ = "gang_home"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # singleton = 1
    banner_title: Mapped[str] = mapped_column(String(80), default="THE GANG")
    banner_subtitle: Mapped[str] = mapped_column(String(160), default="Tropa Free Fire")
    admin_note: Mapped[str] = mapped_column(Text, default="")
    next_event_title: Mapped[str | None] = mapped_column(String(120), nullable=True)
    next_event_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime)
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
