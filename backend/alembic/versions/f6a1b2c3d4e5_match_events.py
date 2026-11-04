"""eventos de call + mvp votes

Revision ID: f6a1b2c3d4e5
Revises: e5f0a1b2c3d4
Create Date: 2026-10-27
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f6a1b2c3d4e5"
down_revision: Union[str, None] = "e5f0a1b2c3d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "match_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("group_id", sa.Integer(), sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel_id", sa.Integer(), sa.ForeignKey("channels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("event_type", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="live"),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("placement", sa.Integer(), nullable=True),
        sa.Column("booyah_count", sa.Integer(), nullable=True),
        sa.Column("kills", sa.Integer(), nullable=True),
        sa.Column("points", sa.Integer(), nullable=True),
        sa.Column("is_win", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("mvp_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_match_events_group_id", "match_events", ["group_id"])
    op.create_index("ix_match_events_channel_id", "match_events", ["channel_id"])

    op.create_table(
        "event_mvp_votes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "event_id",
            sa.Integer(),
            sa.ForeignKey("match_events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("voter_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "candidate_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("event_id", "voter_id", name="uq_mvp_vote_voter"),
    )
    op.create_index("ix_event_mvp_votes_event_id", "event_mvp_votes", ["event_id"])


def downgrade() -> None:
    op.drop_table("event_mvp_votes")
    op.drop_index("ix_match_events_channel_id", table_name="match_events")
    op.drop_index("ix_match_events_group_id", table_name="match_events")
    op.drop_table("match_events")
