"""Importar este pacote registra todas as tabelas em `Base.metadata`."""

from app.models.dm import DMConversation
from app.models.event import EventMvpVote, MatchEvent
from app.models.group import Channel, Group, GroupMember, MemberRole, Role
from app.models.group_invite import GroupInvite
from app.models.home import GangHome
from app.models.invite import InviteCode
from app.models.message import Message, MessageReaction, MessageRead
from app.models.push import PushSubscription
from app.models.refresh_token import RefreshToken
from app.models.user import User

__all__ = [
    "Channel",
    "DMConversation",
    "EventMvpVote",
    "GangHome",
    "Group",
    "GroupInvite",
    "GroupMember",
    "InviteCode",
    "MatchEvent",
    "MemberRole",
    "Message",
    "MessageReaction",
    "MessageRead",
    "PushSubscription",
    "RefreshToken",
    "Role",
    "User",
]
