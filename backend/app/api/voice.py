"""Voz e vídeo via LiveKit."""

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import User
from app.services import message_extra, push_service, voice_service

router = APIRouter()


class VoiceTokenRequest(BaseModel):
    channel_id: int = Field(ge=1)


class VoiceTokenResponse(BaseModel):
    token: str
    url: str
    room: str
    identity: str
    channel_id: int
    group_id: int


@router.post("/token", response_model=VoiceTokenResponse)
def create_token(
    body: VoiceTokenRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    token = voice_service.create_voice_token(db, user, channel_id=body.channel_id)
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
