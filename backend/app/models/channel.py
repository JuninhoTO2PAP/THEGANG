"""Compat: Channel mora em models.group (canais dentro do grupo)."""

from app.models.group import Channel, Group, GroupMember, MemberRole, Role

__all__ = ["Channel", "Group", "GroupMember", "MemberRole", "Role"]
