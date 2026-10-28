"""groups roles and nested channels

Revision ID: b7c2e91f4a10
Revises: 2584990d1bbe
Create Date: 2026-10-26 22:40:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b7c2e91f4a10"
down_revision: Union[str, Sequence[str], None] = "2584990d1bbe"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Schema antigo de "canal = grupo" dá lugar a grupo + canais internos.
    op.drop_table("message_reads")
    op.drop_table("messages")
    op.drop_table("channel_members")
    op.drop_table("channels")

    op.create_table(
        "groups",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=40), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("icon_url", sa.String(length=512), nullable=True),
        sa.Column("is_private", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name=op.f("fk_groups_created_by_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_groups")),
    )
    with op.batch_alter_table("groups", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_groups_name"), ["name"], unique=True)

    op.create_table(
        "group_members",
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["group_id"], ["groups.id"], name=op.f("fk_group_members_group_id_groups"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_group_members_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("group_id", "user_id", name=op.f("pk_group_members")),
    )

    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=40), nullable=False),
        sa.Column("color", sa.String(length=7), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("permissions", sa.Integer(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["group_id"], ["groups.id"], name=op.f("fk_roles_group_id_groups"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_roles")),
        sa.UniqueConstraint("group_id", "name", name="uq_roles_group_name"),
    )
    with op.batch_alter_table("roles", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_roles_group_id"), ["group_id"], unique=False)

    op.create_table(
        "member_roles",
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["role_id"], ["roles.id"], name=op.f("fk_member_roles_role_id_roles"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_member_roles_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("role_id", "user_id", name=op.f("pk_member_roles")),
    )

    op.create_table(
        "channels",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=40), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("channel_type", sa.String(length=10), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name=op.f("fk_channels_created_by_users")
        ),
        sa.ForeignKeyConstraint(
            ["group_id"], ["groups.id"], name=op.f("fk_channels_group_id_groups"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_channels")),
        sa.UniqueConstraint("group_id", "name", name="uq_channels_group_name"),
    )
    with op.batch_alter_table("channels", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_channels_group_id"), ["group_id"], unique=False)

    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("channel_id", sa.Integer(), nullable=True),
        sa.Column("dm_conversation_id", sa.Integer(), nullable=True),
        sa.Column("sender_id", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("attachment_url", sa.String(length=512), nullable=True),
        sa.Column("attachment_type", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "(channel_id IS NOT NULL AND dm_conversation_id IS NULL) OR "
            "(channel_id IS NULL AND dm_conversation_id IS NOT NULL)",
            name=op.f("ck_messages_one_target"),
        ),
        sa.ForeignKeyConstraint(
            ["channel_id"],
            ["channels.id"],
            name=op.f("fk_messages_channel_id_channels"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["dm_conversation_id"],
            ["dm_conversations.id"],
            name=op.f("fk_messages_dm_conversation_id_dm_conversations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["sender_id"], ["users.id"], name=op.f("fk_messages_sender_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_messages")),
    )
    with op.batch_alter_table("messages", schema=None) as batch_op:
        batch_op.create_index("ix_messages_channel_id_id", ["channel_id", "id"], unique=False)
        batch_op.create_index(
            "ix_messages_dm_conversation_id_id", ["dm_conversation_id", "id"], unique=False
        )

    op.create_table(
        "message_reads",
        sa.Column("message_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["messages.id"],
            name=op.f("fk_message_reads_message_id_messages"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_message_reads_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("message_id", "user_id", name=op.f("pk_message_reads")),
    )


def downgrade() -> None:
    raise NotImplementedError("Downgrade não suportado nesta migração.")
