"""group invites table

Revision ID: c3d8a1b2e4f5
Revises: b7c2e91f4a10
Create Date: 2026-10-26 22:50:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3d8a1b2e4f5"
down_revision: Union[str, Sequence[str], None] = "b7c2e91f4a10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "group_invites",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("max_uses", sa.Integer(), nullable=True),
        sa.Column("uses", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name=op.f("fk_group_invites_created_by_users")
        ),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["groups.id"],
            name=op.f("fk_group_invites_group_id_groups"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_group_invites")),
    )
    with op.batch_alter_table("group_invites", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_group_invites_code"), ["code"], unique=True)
        batch_op.create_index(batch_op.f("ix_group_invites_group_id"), ["group_id"], unique=False)


def downgrade() -> None:
    op.drop_table("group_invites")
