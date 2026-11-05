"""cor de destaque na conta e funções COACH / R1 / R2 / R3 / SUP

Revision ID: h8c3d4e5f6a7
Revises: g7b2c3d4e5f6
Create Date: 2026-11-05
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "h8c3d4e5f6a7"
down_revision: Union[str, None] = "g7b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(
            sa.Column("accent", sa.String(length=16), nullable=False, server_default="gold")
        )
    op.execute(
        "UPDATE users SET ff_role = 'coach' "
        "WHERE lower(ff_role) IN ('cpt', 'igl', 'coach')"
    )
    op.execute(
        "UPDATE users SET ff_role = 'sup' "
        "WHERE lower(ff_role) IN ('suporte', 'support')"
    )


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.drop_column("accent")
