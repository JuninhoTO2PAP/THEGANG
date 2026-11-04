"""team A/B nos convites de cadastro

Revision ID: g7b2c3d4e5f6
Revises: f6a1b2c3d4e5
Create Date: 2026-11-04
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "g7b2c3d4e5f6"
down_revision: Union[str, None] = "f6a1b2c3d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("invite_codes") as batch:
        batch.add_column(sa.Column("team", sa.String(length=1), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("invite_codes") as batch:
        batch.drop_column("team")
