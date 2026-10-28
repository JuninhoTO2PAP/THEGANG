"""Tabelas mínimas do modelo."""

from app.db.session import engine
from sqlalchemy import inspect

EXPECTED = {
    "users",
    "invite_codes",
    "refresh_tokens",
    "groups",
    "group_members",
    "roles",
    "member_roles",
    "channels",
    "dm_conversations",
    "messages",
    "message_reads",
    "push_subscriptions",
}


# channel_members foi substituído por group_members + member_roles


def test_tabelas_do_modelo():
    names = set(inspect(engine).get_table_names())
    assert EXPECTED <= names
