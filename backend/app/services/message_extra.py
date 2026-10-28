"""Reações, pin e serialização enriquecida de mensagens."""

from __future__ import annotations

import re
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.errors import AppError
from app.core.permissions import Perm, has_perm
from app.models import Channel, GroupMember, Message, MessageReaction, User
from app.schemas.group import (
    MessageAuthor,
    MessagePublic,
    ReactionPublic,
    ReplyPreview,
)
from app.services import dm_service, group_service
from app.utils.time import utcnow

MENTION_RE = re.compile(r"@([a-z0-9_]{3,32})", re.I)


def message_public(db: Session, message: Message, viewer: User | None = None) -> MessagePublic:
    viewer_id = viewer.id if viewer else None
    reactions = _reactions_for(db, [message.id], viewer_id).get(message.id, [])
    reply_preview = None
    if message.reply_to_id:
        parent = db.get(Message, message.reply_to_id)
        if parent is not None:
            nick = parent.sender.nickname if parent.sender else "?"
            reply_preview = ReplyPreview(
                id=parent.id,
                content=(parent.content or "")[:140],
                sender_nickname=nick,
            )
    sender = message.sender
    return MessagePublic(
        id=message.id,
        channel_id=message.channel_id,
        content=message.content,
        attachment_url=message.attachment_url,
        attachment_type=message.attachment_type,
        reply_to_id=message.reply_to_id,
        reply_to=reply_preview,
        pinned_at=message.pinned_at,
        pinned_by=message.pinned_by,
        created_at=message.created_at,
        edited_at=message.edited_at,
        sender=MessageAuthor(
            id=sender.id,
            username=sender.username,
            nickname=sender.nickname,
            avatar_url=sender.avatar_url,
            is_admin=sender.is_admin,
            presence=getattr(sender, "presence", "online") or "online",
            status_text=getattr(sender, "status_text", None),
        ),
        reactions=reactions,
    )


def messages_public(db: Session, rows: list[Message], viewer: User | None = None) -> list[MessagePublic]:
    if not rows:
        return []
    viewer_id = viewer.id if viewer else None
    reaction_map = _reactions_for(db, [m.id for m in rows], viewer_id)
    parent_ids = [m.reply_to_id for m in rows if m.reply_to_id]
    parents = {}
    if parent_ids:
        for parent in db.scalars(
            select(Message).options(joinedload(Message.sender)).where(Message.id.in_(parent_ids))
        ).unique():
            parents[parent.id] = parent
    result = []
    for message in rows:
        reply_preview = None
        parent = parents.get(message.reply_to_id) if message.reply_to_id else None
        if parent is not None:
            reply_preview = ReplyPreview(
                id=parent.id,
                content=(parent.content or "")[:140],
                sender_nickname=parent.sender.nickname if parent.sender else "?",
            )
        sender = message.sender
        result.append(
            MessagePublic(
                id=message.id,
                channel_id=message.channel_id,
                content=message.content,
                attachment_url=message.attachment_url,
                attachment_type=message.attachment_type,
                reply_to_id=message.reply_to_id,
                reply_to=reply_preview,
                pinned_at=message.pinned_at,
                pinned_by=message.pinned_by,
                created_at=message.created_at,
                edited_at=message.edited_at,
                sender=MessageAuthor(
                    id=sender.id,
                    username=sender.username,
                    nickname=sender.nickname,
                    avatar_url=sender.avatar_url,
                    is_admin=sender.is_admin,
                    presence=getattr(sender, "presence", "online") or "online",
                    status_text=getattr(sender, "status_text", None),
                ),
                reactions=reaction_map.get(message.id, []),
            )
        )
    return result


def _reactions_for(
    db: Session, message_ids: list[int], viewer_id: int | None
) -> dict[int, list[ReactionPublic]]:
    if not message_ids:
        return {}
    rows = db.scalars(
        select(MessageReaction).where(MessageReaction.message_id.in_(message_ids))
    ).all()
    counts: dict[int, dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        counts[row.message_id][row.emoji].append(row.user_id)
    out: dict[int, list[ReactionPublic]] = {}
    for mid, emojis in counts.items():
        out[mid] = [
            ReactionPublic(
                emoji=emoji,
                count=len(uids),
                me=viewer_id in uids if viewer_id is not None else False,
            )
            for emoji, uids in sorted(emojis.items(), key=lambda x: (-len(x[1]), x[0]))
        ]
    return out


def _can_access_message(db: Session, user: User, message: Message) -> None:
    if message.channel_id is not None:
        group_service.get_channel_in_group(db, user, message.channel_id)
    elif message.dm_conversation_id is not None:
        dm_service.require_dm_member(db, user, message.dm_conversation_id)
    else:
        raise AppError(404, "Mensagem não encontrada.")


def toggle_reaction(db: Session, user: User, message_id: int, emoji: str) -> Message:
    emoji = emoji.strip()[:32]
    if not emoji:
        raise AppError(400, "Emoji inválido.")
    message = db.get(Message, message_id)
    if message is None:
        raise AppError(404, "Mensagem não encontrada.")
    _can_access_message(db, user, message)
    existing = db.get(MessageReaction, (message_id, user.id, emoji))
    if existing is not None:
        db.delete(existing)
    else:
        db.add(
            MessageReaction(
                message_id=message_id,
                user_id=user.id,
                emoji=emoji,
                created_at=utcnow(),
            )
        )
    db.commit()
    db.refresh(message)
    _ = message.sender
    return message


def pin_message(db: Session, user: User, message_id: int, *, pinned: bool) -> Message:
    message = db.get(Message, message_id)
    if message is None:
        raise AppError(404, "Mensagem não encontrada.")
    if message.channel_id is None:
        raise AppError(400, "Só mensagens de canal podem ser fixadas.")
    channel = group_service.get_channel_in_group(db, user, message.channel_id)
    perms = group_service._member_permissions(db, channel.group_id, user.id)
    if not has_perm(perms, Perm.MANAGE_CHANNELS):
        raise AppError(403, "Sem permissão para fixar mensagens.")
    if pinned:
        message.pinned_at = utcnow()
        message.pinned_by = user.id
    else:
        message.pinned_at = None
        message.pinned_by = None
    db.commit()
    db.refresh(message)
    _ = message.sender
    return message


def list_pinned(db: Session, user: User, channel_id: int) -> list[Message]:
    group_service.get_channel_in_group(db, user, channel_id)
    rows = list(
        db.scalars(
            select(Message)
            .options(joinedload(Message.sender))
            .where(Message.channel_id == channel_id, Message.pinned_at.is_not(None))
            .order_by(Message.pinned_at.desc())
        ).unique()
    )
    return rows


def resolve_reply_target(
    db: Session, user: User, *, channel_id: int | None, dm_id: int | None, reply_to_id: int | None
) -> int | None:
    if reply_to_id is None:
        return None
    parent = db.get(Message, reply_to_id)
    if parent is None:
        raise AppError(400, "Mensagem de resposta não encontrada.")
    if channel_id is not None and parent.channel_id != channel_id:
        raise AppError(400, "Resposta precisa ser do mesmo canal.")
    if dm_id is not None and parent.dm_conversation_id != dm_id:
        raise AppError(400, "Resposta precisa ser da mesma DM.")
    _can_access_message(db, user, parent)
    return parent.id


def mention_user_ids(db: Session, content: str) -> list[int]:
    names = {m.group(1).lower() for m in MENTION_RE.finditer(content or "")}
    if not names:
        return []
    users = db.scalars(select(User).where(User.username.in_(names))).all()
    return [u.id for u in users]


def channel_member_ids(db: Session, channel_id: int) -> list[int]:
    channel = db.get(Channel, channel_id)
    if channel is None:
        return []
    return list(
        db.scalars(
            select(GroupMember.user_id).where(GroupMember.group_id == channel.group_id)
        ).all()
    )
