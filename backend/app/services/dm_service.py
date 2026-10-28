"""Conversas privadas 1:1."""

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.errors import AppError
from app.models import DMConversation, Message, User
from app.utils.time import utcnow


def _pair(a: int, b: int) -> tuple[int, int]:
    return (a, b) if a < b else (b, a)


def get_or_create_dm(db: Session, me: User, other_id: int) -> DMConversation:
    if other_id == me.id:
        raise AppError(400, "Não dá para abrir DM consigo mesmo.")
    other = db.get(User, other_id)
    if other is None:
        raise AppError(404, "Usuário não encontrado.")
    a, b = _pair(me.id, other_id)
    conv = db.scalar(
        select(DMConversation).where(
            DMConversation.user_a_id == a, DMConversation.user_b_id == b
        )
    )
    if conv is not None:
        return conv
    conv = DMConversation(user_a_id=a, user_b_id=b, created_at=utcnow())
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


def list_dms(db: Session, me: User) -> list[dict]:
    rows = db.scalars(
        select(DMConversation)
        .where(or_(DMConversation.user_a_id == me.id, DMConversation.user_b_id == me.id))
        .order_by(DMConversation.id.desc())
    ).all()
    result = []
    for conv in rows:
        other_id = conv.user_b_id if conv.user_a_id == me.id else conv.user_a_id
        other = db.get(User, other_id)
        last = db.scalar(
            select(Message)
            .where(Message.dm_conversation_id == conv.id)
            .order_by(Message.id.desc())
            .limit(1)
        )
        result.append(
            {
                "id": conv.id,
                "created_at": conv.created_at,
                "other": {
                    "id": other.id if other else other_id,
                    "username": other.username if other else "?",
                    "nickname": other.nickname if other else "?",
                    "avatar_url": other.avatar_url if other else None,
                    "is_admin": other.is_admin if other else False,
                    "is_online": other.is_online if other else False,
                },
                "last_message": (
                    {
                        "id": last.id,
                        "content": last.content,
                        "created_at": last.created_at,
                        "attachment_url": last.attachment_url,
                    }
                    if last
                    else None
                ),
            }
        )
    return result


def require_dm_member(db: Session, me: User, conversation_id: int) -> DMConversation:
    conv = db.get(DMConversation, conversation_id)
    if conv is None:
        raise AppError(404, "Conversa não encontrada.")
    if me.id not in {conv.user_a_id, conv.user_b_id}:
        raise AppError(403, "Você não participa desta DM.")
    return conv


def list_dm_messages(
    db: Session,
    me: User,
    conversation_id: int,
    *,
    limit: int = 50,
    before_id: int | None = None,
) -> list[Message]:
    require_dm_member(db, me, conversation_id)
    query = (
        select(Message)
        .options(joinedload(Message.sender))
        .where(Message.dm_conversation_id == conversation_id)
        .order_by(Message.id.desc())
        .limit(min(limit, 100))
    )
    if before_id is not None:
        query = query.where(Message.id < before_id)
    rows = list(db.scalars(query).unique().all())
    rows.reverse()
    return rows


def post_dm_message(
    db: Session,
    me: User,
    conversation_id: int,
    content: str,
    *,
    attachment_url: str | None = None,
    attachment_type: str | None = None,
    reply_to_id: int | None = None,
) -> Message:
    from app.services import message_extra

    require_dm_member(db, me, conversation_id)
    if not content.strip() and not attachment_url:
        raise AppError(400, "Mensagem vazia.")
    reply_id = message_extra.resolve_reply_target(
        db, me, channel_id=None, dm_id=conversation_id, reply_to_id=reply_to_id
    )
    message = Message(
        channel_id=None,
        dm_conversation_id=conversation_id,
        sender_id=me.id,
        content=content.strip(),
        attachment_url=attachment_url,
        attachment_type=attachment_type,
        reply_to_id=reply_id,
        created_at=utcnow(),
        edited_at=None,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    _ = message.sender
    return message


def dm_peer_ids(conv: DMConversation) -> list[int]:
    return [conv.user_a_id, conv.user_b_id]
