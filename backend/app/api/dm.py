"""Mensagens diretas 1:1."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas.dm import DMConversationPublic, DMOpenRequest
from app.schemas.group import MessageCreate, MessagePublic
from app.services import dm_service, message_extra, push_service
from app.services.ws_hub import hub

router = APIRouter()


@router.get("", response_model=list[DMConversationPublic])
def list_conversations(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[dict]:
    rows = dm_service.list_dms(db, user)
    for row in rows:
        other = row.get("other") or {}
        other["is_online"] = hub.is_online(other.get("id", 0))
    return rows


@router.post("", response_model=DMConversationPublic, status_code=status.HTTP_201_CREATED)
def open_dm(
    body: DMOpenRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    conv = dm_service.get_or_create_dm(db, user, body.user_id)
    rows = dm_service.list_dms(db, user)
    match = next((r for r in rows if r["id"] == conv.id), None)
    if match is None:
        other_id = conv.user_b_id if conv.user_a_id == user.id else conv.user_a_id
        other = db.get(User, other_id)
        match = {
            "id": conv.id,
            "created_at": conv.created_at,
            "other": {
                "id": other.id if other else other_id,
                "username": other.username if other else "?",
                "nickname": other.nickname if other else "?",
                "avatar_url": other.avatar_url if other else None,
                "is_admin": other.is_admin if other else False,
                "is_online": hub.is_online(other_id),
            },
            "last_message": None,
        }
    else:
        match["other"]["is_online"] = hub.is_online(match["other"]["id"])
    return match


@router.get("/{conversation_id}/messages", response_model=list[MessagePublic])
def list_messages(
    conversation_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    before_id: Annotated[int | None, Query()] = None,
) -> list[MessagePublic]:
    messages = dm_service.list_dm_messages(
        db, user, conversation_id, limit=limit, before_id=before_id
    )
    return message_extra.messages_public(db, messages, user)


@router.post(
    "/{conversation_id}/messages",
    response_model=MessagePublic,
    status_code=status.HTTP_201_CREATED,
)
async def create_message(
    conversation_id: int,
    body: MessageCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> MessagePublic:
    message = dm_service.post_dm_message(
        db,
        user,
        conversation_id,
        body.content,
        attachment_url=body.attachment_url,
        attachment_type=body.attachment_type,
        reply_to_id=body.reply_to_id,
    )
    public = message_extra.message_public(db, message, user)
    conv = dm_service.require_dm_member(db, user, conversation_id)
    peers = dm_service.dm_peer_ids(conv)
    await hub.broadcast_dm(
        conversation_id,
        {"type": "message", "message": public.model_dump(mode="json"), "dm_id": conversation_id},
        peers,
    )
    push_service.notify_users(
        db,
        peers,
        title=f"DM de {user.nickname}",
        body=message.content[:120] or "Nova mensagem privada",
        data={"type": "dm", "dm_id": conversation_id, "message_id": message.id},
        skip_user=user.id,
    )
    return public
