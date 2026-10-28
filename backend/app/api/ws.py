"""WebSocket: presença, mensagens ao vivo, digitando e leituras."""

from __future__ import annotations

import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import decode_token
from app.db.session import SessionLocal
from app.models import User
from app.services.ws_hub import hub
from app.utils.time import utcnow

router = APIRouter()


def _user_from_token(db: Session, token: str | None) -> User | None:
    if not token:
        return None
    try:
        payload = decode_token(token, expected_type="access")
        user_id = int(payload["sub"])
    except (AppError, KeyError, TypeError, ValueError):
        return None
    return db.get(User, user_id)


def _set_online(db: Session, user: User, online: bool) -> None:
    user.is_online = online
    user.last_seen = utcnow()
    db.add(user)
    db.commit()


@router.websocket("/")
async def websocket_endpoint(websocket: WebSocket) -> None:
    token = websocket.query_params.get("token")
    db = SessionLocal()
    try:
        user = _user_from_token(db, token)
        if user is None:
            await websocket.close(code=4401)
            return
        user_id = user.id
        client = await hub.connect(user_id, websocket)
        _set_online(db, user, True)
        await hub.broadcast_presence(user_id, True)
        await client.ws.send_text(
            json.dumps(
                {
                    "type": "hello",
                    "user_id": user_id,
                    "online_user_ids": list(hub.online_user_ids()),
                }
            )
        )
    finally:
        db.close()

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
            await _handle(client, data)
    except WebSocketDisconnect:
        pass
    finally:
        went_offline = await hub.disconnect(client)
        if went_offline:
            db = SessionLocal()
            try:
                u = db.get(User, user_id)
                if u is not None:
                    _set_online(db, u, False)
            finally:
                db.close()
            await hub.broadcast_presence(user_id, False)


async def _handle(client, data: dict) -> None:
    kind = data.get("type")
    if kind == "subscribe_channel":
        channel_id = data.get("channel_id")
        if isinstance(channel_id, int):
            await hub.subscribe_channel(client, channel_id)
        return
    if kind == "subscribe_dm":
        dm_id = data.get("dm_id")
        if isinstance(dm_id, int):
            await hub.subscribe_dm(client, dm_id)
        return
    if kind == "typing":
        channel_id = data.get("channel_id")
        dm_id = data.get("dm_id")
        payload = {
            "type": "typing",
            "user_id": client.user_id,
            "channel_id": channel_id,
            "dm_id": dm_id,
        }
        if isinstance(channel_id, int):
            await hub.broadcast_channel(channel_id, payload, skip_user=client.user_id)
        elif isinstance(dm_id, int):
            await hub.broadcast_dm(dm_id, payload, list(data.get("peer_ids") or []))
        return
    if kind == "ping":
        await client.ws.send_text(json.dumps({"type": "pong"}))
