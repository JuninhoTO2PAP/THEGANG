"""perfil FF + home THE GANG

Revision ID: e5f0a1b2c3d4
Revises: d4e9f2a3b1c0
Create Date: 2026-10-27
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e5f0a1b2c3d4"
down_revision: Union[str, None] = "d4e9f2a3b1c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("ff_id", sa.String(length=32), nullable=True))
        batch.add_column(sa.Column("ff_nick", sa.String(length=32), nullable=True))
        batch.add_column(sa.Column("ff_role", sa.String(length=16), nullable=True))
        batch.add_column(sa.Column("ff_region", sa.String(length=16), nullable=True))
        batch.add_column(
            sa.Column("banner_theme", sa.String(length=16), server_default="gold", nullable=False)
        )

    op.create_table(
        "gang_home",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("banner_title", sa.String(length=80), nullable=False, server_default="THE GANG"),
        sa.Column(
            "banner_subtitle",
            sa.String(length=160),
            nullable=False,
            server_default="Tropa Free Fire",
        ),
        sa.Column("admin_note", sa.Text(), nullable=False, server_default=""),
        sa.Column("next_event_title", sa.String(length=120), nullable=True),
        sa.Column("next_event_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("updated_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("gang_home")
    with op.batch_alter_table("users") as batch:
        batch.drop_column("banner_theme")
        batch.drop_column("ff_region")
        batch.drop_column("ff_role")
        batch.drop_column("ff_nick")
        batch.drop_column("ff_id")
