"""Compat — a lógica de canal/grupo está em group_service."""

from app.services.group_service import (  # noqa: F401
    create_channel,
    get_channel_in_group,
    list_channels,
    list_messages,
    post_message,
)
