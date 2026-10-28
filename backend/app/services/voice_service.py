"""Tokens LiveKit para call de voz/vídeo/tela."""

from datetime import timedelta

import jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError
from app.core.permissions import Perm, has_perm
from app.models import User
from app.services import group_service
from app.utils.time import utcnow


def create_voice_token(
    db: Session,
    user: User,
    *,
    channel_id: int,
) -> dict:
    if not settings.livekit_url or not settings.livekit_api_key or not settings.livekit_api_secret:
        raise AppError(
            503,
            "LiveKit não configurado. Defina LIVEKIT_URL, LIVEKIT_API_KEY e LIVEKIT_API_SECRET.",
        )
    channel = group_service.get_channel_in_group(db, user, channel_id)
    if channel.channel_type != "voice":
        raise AppError(400, "Só canais de voz emitem token de call.")
    perms = group_service._member_permissions(db, channel.group_id, user.id)
    if not has_perm(perms, Perm.CONNECT_VOICE):
        raise AppError(403, "Sem permissão para entrar na call.")

    room = f"group-{channel.group_id}-ch-{channel.id}"
    now = utcnow()
    identity = f"user-{user.id}"
    video_grant = {
        "roomJoin": True,
        "room": room,
        "canPublish": True,
        "canSubscribe": True,
        "canPublishData": True,
    }
    payload = {
        "iss": settings.livekit_api_key,
        "sub": identity,
        "name": user.nickname,
        "nbf": int(now.timestamp()) - 10,
        "exp": int((now + timedelta(hours=6)).timestamp()),
        "video": video_grant,
        "metadata": f'{{"username":"{user.username}","nickname":"{user.nickname}"}}',
    }
    token = jwt.encode(payload, settings.livekit_api_secret, algorithm="HS256")
    return {
        "token": token,
        "url": settings.livekit_url,
        "room": room,
        "identity": identity,
        "channel_id": channel.id,
        "group_id": channel.group_id,
    }
