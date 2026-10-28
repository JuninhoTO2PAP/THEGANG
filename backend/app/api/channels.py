"""Mensagens e metadados de canal interno do grupo."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas.group import MessageCreate, MessagePublic
from app.services import group_service, message_extra, push_service
from app.services.ws_hub import hub

router = APIRouter()


@router.get("/{channel_id}/messages", response_model=list[MessagePublic])
def list_messages(
    channel_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    before_id: Annotated[int | None, Query()] = None,
) -> list[MessagePublic]:
    messages = group_service.list_messages(
        db, user, channel_id, limit=limit, before_id=before_id
    )
    return message_extra.messages_public(db, messages, user)


@router.get("/{channel_id}/pins", response_model=list[MessagePublic])
def list_pins(
    channel_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[MessagePublic]:
    return message_extra.messages_public(
        db, message_extra.list_pinned(db, user, channel_id), user
    )


@router.post(
    "/{channel_id}/messages",
    response_model=MessagePublic,
    status_code=status.HTTP_201_CREATED,
)
async def create_message(
    channel_id: int,
    body: MessageCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> MessagePublic:
    message = group_service.post_message(
        db,
        user,
        channel_id,
        body.content,
        attachment_url=body.attachment_url,
        attachment_type=body.attachment_type,
        reply_to_id=body.reply_to_id,
    )
    public = message_extra.message_public(db, message, user)
    await hub.broadcast_channel(
        channel_id,
        {"type": "message", "message": public.model_dump(mode="json")},
    )
    # Push: menções
    mentioned = message_extra.mention_user_ids(db, message.content)
    if mentioned:
        push_service.notify_users(
            db,
            mentioned,
            title=f"{user.nickname} mencionou você",
            body=message.content[:120] or "Nova menção",
            data={"type": "mention", "channel_id": channel_id, "message_id": message.id},
            skip_user=user.id,
        )
    return public
