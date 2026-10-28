"""Conversa privada entre dois membros.

`user_a_id` é sempre o id menor. Assim o par (1, 2) e (2, 1)
não vira duas conversas.
"""

from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import UTCDateTime


class DMConversation(Base):
    __tablename__ = "dm_conversations"
    __table_args__ = (
        UniqueConstraint("user_a_id", "user_b_id", name="uq_dm_pair"),
        CheckConstraint("user_a_id < user_b_id", name="user_order"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_a_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    user_b_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
