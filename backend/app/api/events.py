"""API de eventos de call + stats + MVP."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas.event import (
    EventFinish,
    EventPublic,
    EventStart,
    MvpVoteBody,
    TeamStatsPublic,
)
from app.services import event_service
from app.services.ws_hub import hub

router = APIRouter()


async def _push(channel_id: int, payload: dict) -> None:
    await hub.broadcast_channel(channel_id, {"type": "match_event", "event": payload})


@router.get("/stats", response_model=TeamStatsPublic)
def stats(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    group_id: int | None = Query(default=None),
) -> TeamStatsPublic:
    return event_service.team_stats(db, user, group_id)


@router.get("/recent", response_model=list[EventPublic])
def recent(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[EventPublic]:
    return [EventPublic.model_validate(e) for e in event_service.recent_events(db, user)]


@router.get("/active", response_model=EventPublic | None)
def active(
    channel_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> EventPublic | None:
    data = event_service.active_event_public(db, user, channel_id)
    return EventPublic.model_validate(data) if data else None


@router.get("/{event_id}", response_model=EventPublic)
def get_one(
    event_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> EventPublic:
    return EventPublic.model_validate(event_service.get_event(db, user, event_id))


@router.post("/start", response_model=EventPublic)
async def start(
    body: EventStart,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> EventPublic:
    data = event_service.start_event(db, user, body)
    await _push(body.channel_id, data)
    return EventPublic.model_validate(data)


@router.post("/{event_id}/finish", response_model=EventPublic)
async def finish(
    event_id: int,
    body: EventFinish,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> EventPublic:
    data = event_service.finish_event(db, user, event_id, body)
    await _push(data["channel_id"], data)
    return EventPublic.model_validate(data)


@router.post("/{event_id}/mvp-vote", response_model=EventPublic)
async def mvp_vote(
    event_id: int,
    body: MvpVoteBody,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> EventPublic:
    data = event_service.vote_mvp(db, user, event_id, body.candidate_id)
    await _push(data["channel_id"], data)
    return EventPublic.model_validate(data)


@router.post("/{event_id}/close-mvp", response_model=EventPublic)
async def close_mvp(
    event_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> EventPublic:
    data = event_service.close_mvp(db, user, event_id)
    await _push(data["channel_id"], data)
    return EventPublic.model_validate(data)
