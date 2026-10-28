"""Mensagem de canal ou de DM, leituras, reações e pin."""

from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import UTCDateTime


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint(
            "(channel_id IS NOT NULL AND dm_conversation_id IS NULL) OR "
            "(channel_id IS NULL AND dm_conversation_id IS NOT NULL)",
            name="one_target",
        ),
        Index("ix_messages_channel_id_id", "channel_id", "id"),
        Index("ix_messages_dm_conversation_id_id", "dm_conversation_id", "id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    channel_id: Mapped[int | None] = mapped_column(
        ForeignKey("channels.id", ondelete="CASCADE"), nullable=True
    )
    dm_conversation_id: Mapped[int | None] = mapped_column(
        ForeignKey("dm_conversations.id", ondelete="CASCADE"), nullable=True
    )
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    content: Mapped[str] = mapped_column(Text, default="")
    attachment_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    attachment_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reply_to_id: Mapped[int | None] = mapped_column(
        ForeignKey("messages.id", ondelete="SET NULL"), nullable=True
    )
    pinned_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    pinned_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
    edited_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)

    sender = relationship("User", foreign_keys=[sender_id], lazy="joined")
    reply_to = relationship("Message", remote_side="Message.id", lazy="select")


class MessageRead(Base):
    __tablename__ = "message_reads"

    message_id: Mapped[int] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    read_at: Mapped[datetime] = mapped_column(UTCDateTime)


class MessageReaction(Base):
    __tablename__ = "message_reactions"

    message_id: Mapped[int] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    emoji: Mapped[str] = mapped_column(String(32), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
