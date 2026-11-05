"""Agrupa os routers da API sob `/api`."""

from fastapi import APIRouter

from app.api import (
    admin,
    auth,
    channels,
    dm,
    events,
    groups,
    home,
    messages,
    push,
    uploads,
    users,
    voice,
    ws,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(home.router, prefix="/home", tags=["home"])
api_router.include_router(events.router, prefix="/events", tags=["events"])
api_router.include_router(groups.router, prefix="/groups", tags=["groups"])
api_router.include_router(channels.router, prefix="/channels", tags=["channels"])
api_router.include_router(messages.router, prefix="/messages", tags=["messages"])
api_router.include_router(dm.router, prefix="/dm", tags=["dm"])
api_router.include_router(uploads.router, prefix="/uploads", tags=["uploads"])
api_router.include_router(ws.router, prefix="/ws", tags=["websocket"])
api_router.include_router(push.router, prefix="/push", tags=["push"])
api_router.include_router(voice.router, prefix="/voice", tags=["voice"])
