"""status, reply, pin, reactions

Revision ID: d4e9f2a3b1c0
Revises: c3d8a1b2e4f5
Create Date: 2026-10-27
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4e9f2a3b1c0"
down_revision: Union[str, None] = "c3d8a1b2e4f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("presence", sa.String(length=16), server_default="online", nullable=False))
        batch.add_column(sa.Column("status_text", sa.String(length=120), nullable=True))

    with op.batch_alter_table("messages") as batch:
        batch.add_column(sa.Column("reply_to_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("pinned_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("pinned_by", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_messages_reply_to", "messages", ["reply_to_id"], ["id"])
        batch.create_foreign_key("fk_messages_pinned_by", "users", ["pinned_by"], ["id"])

    op.create_table(
        "message_reactions",
        sa.Column("message_id", sa.Integer(), sa.ForeignKey("messages.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("emoji", sa.String(length=32), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_message_reactions_message_id", "message_reactions", ["message_id"])


def downgrade() -> None:
    op.drop_index("ix_message_reactions_message_id", table_name="message_reactions")
    op.drop_table("message_reactions")
    with op.batch_alter_table("messages") as batch:
        batch.drop_constraint("fk_messages_pinned_by", type_="foreignkey")
        batch.drop_constraint("fk_messages_reply_to", type_="foreignkey")
        batch.drop_column("pinned_by")
        batch.drop_column("pinned_at")
        batch.drop_column("reply_to_id")
    with op.batch_alter_table("users") as batch:
        batch.drop_column("status_text")
        batch.drop_column("presence")
