"""Eventos de call (Diário / Intensivo / Campeonato) + voto MVP."""

from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import UTCDateTime


class MatchEvent(Base):
    __tablename__ = "match_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), index=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey("channels.id", ondelete="CASCADE"), index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    event_type: Mapped[str] = mapped_column(String(20))  # diario | intensivo | campeonato
    status: Mapped[str] = mapped_column(String(20), default="live")  # live | voting | closed
    started_at: Mapped[datetime] = mapped_column(UTCDateTime)
    ended_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    placement: Mapped[int | None] = mapped_column(Integer, nullable=True)
    booyah_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    kills: Mapped[int | None] = mapped_column(Integer, nullable=True)
    points: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_win: Mapped[bool] = mapped_column(Boolean, default=False)
    mvp_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)


class EventMvpVote(Base):
    __tablename__ = "event_mvp_votes"
    __table_args__ = (UniqueConstraint("event_id", "voter_id", name="uq_mvp_vote_voter"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("match_events.id", ondelete="CASCADE"), index=True)
    voter_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    candidate_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
