"""Hub de WebSocket: presença, fan-out de mensagens e digitando."""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from dataclasses import dataclass, field

from fastapi import WebSocket


@dataclass
class Client:
    user_id: int
    ws: WebSocket
    channels: set[int] = field(default_factory=set)
    dms: set[int] = field(default_factory=set)
    voice: dict | None = None


class ConnectionHub:
    def __init__(self) -> None:
        self._clients: dict[int, list[Client]] = defaultdict(list)
        self._voice: dict[int, dict] = {}
        self._lock = asyncio.Lock()

    async def connect(self, user_id: int, ws: WebSocket) -> Client:
        await ws.accept()
        client = Client(user_id=user_id, ws=ws)
        async with self._lock:
            self._clients[user_id].append(client)
        return client

    async def disconnect(self, client: Client) -> bool:
        """Remove o cliente. Devolve True se o usuário ficou sem conexões."""
        voice_changed = False
        async with self._lock:
            bucket = self._clients.get(client.user_id, [])
            if client in bucket:
                bucket.remove(client)
            if client.voice is not None:
                replacement = next((other.voice for other in bucket if other.voice), None)
                if replacement:
                    self._voice[client.user_id] = replacement
                else:
                    self._voice.pop(client.user_id, None)
                voice_changed = True
            went_offline = False
            if not bucket and client.user_id in self._clients:
                del self._clients[client.user_id]
                self._voice.pop(client.user_id, None)
                went_offline = True
            calls = list(self._voice.values()) if voice_changed or went_offline else None
        if calls is not None:
            await self._broadcast_all({"type": "voice_state", "calls": calls})
        return went_offline

    def voice_calls(self) -> list[dict]:
        return list(self._voice.values())

    async def set_voice(self, client: Client, info: dict | None) -> None:
        async with self._lock:
            client.voice = info
            if info is None:
                replacement = next(
                    (other.voice for other in self._clients.get(client.user_id, []) if other is not client and other.voice),
                    None,
                )
                if replacement:
                    self._voice[client.user_id] = replacement
                else:
                    self._voice.pop(client.user_id, None)
            else:
                self._voice[client.user_id] = info
            calls = list(self._voice.values())
        await self._broadcast_all({"type": "voice_state", "calls": calls})

    async def mark_user_voice(self, user_id: int, info: dict | None) -> None:
        """Marca a call pelo HTTP, para quem não está na sala também ver a lista."""
        async with self._lock:
            clients = list(self._clients.get(user_id, []))
            if info is None:
                for client in clients:
                    client.voice = None
                self._voice.pop(user_id, None)
            else:
                if clients:
                    clients[-1].voice = info
                self._voice[user_id] = info
            calls = list(self._voice.values())
        await self._broadcast_all({"type": "voice_state", "calls": calls})

    def is_online(self, user_id: int) -> bool:
        return bool(self._clients.get(user_id))

    def online_user_ids(self) -> set[int]:
        return set(self._clients.keys())

    async def subscribe_channel(self, client: Client, channel_id: int) -> None:
        client.channels.add(channel_id)

    async def subscribe_dm(self, client: Client, conversation_id: int) -> None:
        client.dms.add(conversation_id)

    async def send_user(self, user_id: int, payload: dict) -> None:
        dead: list[Client] = []
        for client in list(self._clients.get(user_id, [])):
            try:
                await client.ws.send_text(json.dumps(payload, default=str))
            except Exception:
                dead.append(client)
        for client in dead:
            await self.disconnect(client)

    async def broadcast_channel(self, channel_id: int, payload: dict, *, skip_user: int | None = None) -> None:
        async with self._lock:
            snapshot = [(uid, list(clients)) for uid, clients in self._clients.items()]
        for user_id, clients in snapshot:
            if skip_user is not None and user_id == skip_user:
                continue
            for client in clients:
                if channel_id in client.channels:
                    try:
                        await client.ws.send_text(json.dumps(payload, default=str))
                    except Exception:
                        await self.disconnect(client)

    async def broadcast_dm(self, conversation_id: int, payload: dict, user_ids: list[int]) -> None:
        for user_id in user_ids:
            await self.send_user(user_id, payload)

    async def broadcast_presence(self, user_id: int, is_online: bool) -> None:
        payload = {"type": "presence", "user_id": user_id, "is_online": is_online}
        await self._broadcast_all(payload)

    async def broadcast_status(
        self,
        user_id: int,
        *,
        presence: str,
        status_text: str | None,
        is_online: bool,
    ) -> None:
        await self._broadcast_all(
            {
                "type": "status",
                "user_id": user_id,
                "presence": presence,
                "status_text": status_text,
                "is_online": is_online,
            }
        )

    async def _broadcast_all(self, payload: dict) -> None:
        async with self._lock:
            snapshot = [list(clients) for clients in self._clients.values()]
        for clients in snapshot:
            for client in clients:
                try:
                    await client.ws.send_text(json.dumps(payload, default=str))
                except Exception:
                    await self.disconnect(client)


hub = ConnectionHub()
