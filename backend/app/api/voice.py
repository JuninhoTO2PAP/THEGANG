"""Voz e vídeo via LiveKit."""

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.errors import AppError
from app.db.session import get_db
from app.models import Channel, GroupMember, User
from app.services import event_service, message_extra, push_service, voice_service
from app.services.ws_hub import hub

router = APIRouter()


class VoiceTokenRequest(BaseModel):
    channel_id: int = Field(ge=1)


class VoiceKickRequest(BaseModel):
    channel_id: int = Field(ge=1)
    user_id: int = Field(ge=1)


class VoiceTokenResponse(BaseModel):
    token: str
    url: str
    room: str
    identity: str
    channel_id: int
    group_id: int


@router.get("/roster")
def voice_roster(
    _user: Annotated[User, Depends(get_current_user)],
) -> list[dict]:
    """Quem está em cada call, visível mesmo para quem não entrou na sala."""
    return hub.voice_calls()


@router.post("/here", status_code=204)
async def voice_here(
    body: VoiceTokenRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Quem está na call avisa o servidor, para a lista aparecer fora da sala."""
    channel = db.get(Channel, body.channel_id)
    if channel is None or channel.channel_type != "voice":
        return
    if db.get(GroupMember, (channel.group_id, user.id)) is None:
        return
    await hub.mark_user_voice(
        user.id,
        {
            "user_id": user.id,
            "channel_id": channel.id,
            "group_id": channel.group_id,
            "nickname": user.nickname,
            "username": user.username,
            "avatar_url": user.avatar_url,
        },
    )


@router.post("/leave", status_code=204)
async def leave_voice(
    user: Annotated[User, Depends(get_current_user)],
) -> None:
    await hub.mark_user_voice(user.id, None)


@router.post("/kick", status_code=204)
async def kick_from_call(
    body: VoiceKickRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """CPT expulsa alguém que está na call. A conta da pessoa continua existindo."""
    if body.user_id == user.id:
        raise AppError(400, "Você não pode se expulsar.")
    channel = db.get(Channel, body.channel_id)
    if channel is None or channel.channel_type != "voice":
        raise AppError(404, "Chamada não encontrada.")
    if not event_service.can_run_call_event(db, channel.group_id, user):
        raise AppError(403, "Só o CPT pode expulsar da call.")
    target = db.get(User, body.user_id)
    if target is None or db.get(GroupMember, (channel.group_id, target.id)) is None:
        raise AppError(404, "Pessoa não encontrada nessa chamada.")
    if target.is_admin:
        raise AppError(403, "Não dá para expulsar o administrador.")
    await asyncio.to_thread(
        voice_service.remove_livekit_participant,
        voice_service.room_name(channel.group_id, channel.id),
        voice_service.participant_identity(target.id),
    )
    await hub.mark_user_voice(target.id, None)


@router.post("/token", response_model=VoiceTokenResponse)
async def create_token(
    body: VoiceTokenRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    token = voice_service.create_voice_token(db, user, channel_id=body.channel_id)
    await hub.mark_user_voice(
        user.id,
        {
            "user_id": user.id,
            "channel_id": token["channel_id"],
            "group_id": token["group_id"],
            "nickname": user.nickname,
            "username": user.username,
            "avatar_url": user.avatar_url,
        },
    )
    peers = message_extra.channel_member_ids(db, body.channel_id)
    push_service.notify_users(
        db,
        peers,
        title=f"{user.nickname} entrou na call",
        body="Toque para juntar-se à sala de voz.",
        data={"type": "call", "channel_id": body.channel_id},
        skip_user=user.id,
    )
    return token
