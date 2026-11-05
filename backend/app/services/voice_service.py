"""Tokens LiveKit para call de voz/vídeo/tela."""

import json
import urllib.error
import urllib.request
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

    room = room_name(channel.group_id, channel.id)
    now = utcnow()
    identity = participant_identity(user.id)
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
        "metadata": json.dumps(
            {
                "username": user.username,
                "nickname": user.nickname,
                "ff_role": user.ff_role or "",
            }
        ),
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


def room_name(group_id: int, channel_id: int) -> str:
    return f"group-{group_id}-ch-{channel_id}"


def participant_identity(user_id: int) -> str:
    return f"user-{user_id}"


def remove_livekit_participant(room: str, identity: str) -> None:
    """Tira a pessoa da sala. 404 da LiveKit significa que ela já saiu."""
    if not settings.livekit_url or not settings.livekit_api_key or not settings.livekit_api_secret:
        raise AppError(503, "LiveKit não configurado.")
    host = settings.livekit_url.replace("wss://", "https://").replace("ws://", "http://").rstrip("/")
    now = utcnow()
    token = jwt.encode(
        {
            "iss": settings.livekit_api_key,
            "sub": "the-gang-api",
            "nbf": int(now.timestamp()) - 10,
            "exp": int((now + timedelta(minutes=1)).timestamp()),
            "video": {"roomAdmin": True, "room": room},
        },
        settings.livekit_api_secret,
        algorithm="HS256",
    )
    request = urllib.request.Request(
        f"{host}/twirp/livekit.RoomService/RemoveParticipant",
        data=json.dumps({"room": room, "identity": identity}).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            response.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return
        raise AppError(502, "Não foi possível expulsar da call.") from exc
    except urllib.error.URLError as exc:
        raise AppError(502, "A call não respondeu.") from exc
