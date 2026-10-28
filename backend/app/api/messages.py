"""Editar, apagar, buscar, reagir, pin e marcar leitura."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas.group import MessagePublic, MessageUpdate, ReactionCreate
from app.services import dm_service, group_service, message_extra
from app.services.ws_hub import hub

router = APIRouter()


class ReadRequest(BaseModel):
    message_ids: list[int] = Field(min_length=1, max_length=100)


@router.patch("/{message_id}", response_model=MessagePublic)
async def edit_message(
    message_id: int,
    body: MessageUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> MessagePublic:
    message = group_service.edit_message(db, user, message_id, body.content)
    public = message_extra.message_public(db, message, user)
    payload = {"type": "message_update", "message": public.model_dump(mode="json")}
    if message.channel_id is not None:
        await hub.broadcast_channel(message.channel_id, payload)
    elif message.dm_conversation_id is not None:
        conv = dm_service.require_dm_member(db, user, message.dm_conversation_id)
        await hub.broadcast_dm(
            message.dm_conversation_id, payload, dm_service.dm_peer_ids(conv)
        )
    return public


@router.delete("/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_message(
    message_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    info = group_service.delete_message(db, user, message_id)
    payload = {
        "type": "message_delete",
        "id": info["id"],
        "channel_id": info["channel_id"],
        "dm_id": info["dm_conversation_id"],
    }
    if info["channel_id"] is not None:
        await hub.broadcast_channel(info["channel_id"], payload)
    elif info["dm_conversation_id"] is not None:
        conv = dm_service.require_dm_member(db, user, info["dm_conversation_id"])
        await hub.broadcast_dm(
            info["dm_conversation_id"], payload, dm_service.dm_peer_ids(conv)
        )


@router.post("/{message_id}/reactions", response_model=MessagePublic)
async def react(
    message_id: int,
    body: ReactionCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> MessagePublic:
    message = message_extra.toggle_reaction(db, user, message_id, body.emoji)
    public = message_extra.message_public(db, message, user)
    payload = {"type": "message_update", "message": public.model_dump(mode="json")}
    if message.channel_id is not None:
        await hub.broadcast_channel(message.channel_id, payload)
    elif message.dm_conversation_id is not None:
        conv = dm_service.require_dm_member(db, user, message.dm_conversation_id)
        await hub.broadcast_dm(
            message.dm_conversation_id, payload, dm_service.dm_peer_ids(conv)
        )
    return public


@router.post("/{message_id}/pin", response_model=MessagePublic)
async def pin(
    message_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> MessagePublic:
    message = message_extra.pin_message(db, user, message_id, pinned=True)
    public = message_extra.message_public(db, message, user)
    await hub.broadcast_channel(
        message.channel_id,
        {"type": "message_update", "message": public.model_dump(mode="json")},
    )
    return public


@router.delete("/{message_id}/pin", response_model=MessagePublic)
async def unpin(
    message_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> MessagePublic:
    message = message_extra.pin_message(db, user, message_id, pinned=False)
    public = message_extra.message_public(db, message, user)
    await hub.broadcast_channel(
        message.channel_id,
        {"type": "message_update", "message": public.model_dump(mode="json")},
    )
    return public


@router.get("/search", response_model=list[MessagePublic])
def search_messages(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    q: Annotated[str, Query(min_length=2, max_length=100)],
    group_id: Annotated[int | None, Query()] = None,
    channel_id: Annotated[int | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 30,
) -> list[MessagePublic]:
    rows = group_service.search_messages(
        db, user, group_id=group_id, channel_id=channel_id, q=q, limit=limit
    )
    return message_extra.messages_public(db, rows, user)


@router.post("/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_read(
    body: ReadRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    group_service.mark_messages_read(db, user, body.message_ids)
    await hub.send_user(
        user.id,
        {"type": "read", "message_ids": body.message_ids, "user_id": user.id},
    )
