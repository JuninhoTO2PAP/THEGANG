"""Schemas de eventos de call."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

EVENT_TYPES = {"diario", "intensivo", "campeonato"}


class EventStart(BaseModel):
    channel_id: int = Field(ge=1)
    event_type: str

    @field_validator("event_type")
    @classmethod
    def _type(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if cleaned not in EVENT_TYPES:
            raise ValueError("Tipo inválido. Use diario, intensivo ou campeonato.")
        return cleaned


class EventFinish(BaseModel):
    placement: int = Field(ge=1, le=50)
    booyah_count: int = Field(ge=0, le=50)
    kills: int = Field(ge=0, le=9999)
    points: int = Field(ge=0, le=999999)


class MvpVoteBody(BaseModel):
    candidate_id: int = Field(ge=1)


class MvpCandidate(BaseModel):
    id: int
    nickname: str
    username: str
    avatar_url: str | None
    votes: int = 0


class EventPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    group_id: int
    channel_id: int
    owner_id: int
    owner_nickname: str = ""
    event_type: str
    status: str
    started_at: datetime
    ended_at: datetime | None = None
    placement: int | None = None
    booyah_count: int | None = None
    kills: int | None = None
    points: int | None = None
    is_win: bool = False
    mvp_user_id: int | None = None
    mvp_nickname: str | None = None
    my_vote_candidate_id: int | None = None
    candidates: list[MvpCandidate] = []
    elapsed_seconds: int = 0


class TeamStatsPublic(BaseModel):
    wins: int = 0
    booyah_total: int = 0
    kills_total: int = 0
    points_total: int = 0
    events_total: int = 0
    diario: int = 0
    intensivo: int = 0
    campeonato: int = 0


class HistoryEvent(BaseModel):
    id: int
    event_type: str
    status: str
    started_at: datetime
    ended_at: datetime | None = None
    placement: int | None = None
    booyah_count: int | None = None
    kills: int | None = None
    points: int | None = None
    is_win: bool = False
    mvp_nickname: str | None = None
    owner_nickname: str = ""


class MvpRank(BaseModel):
    nickname: str
    mvp_count: int


class EventHistory(BaseModel):
    events: list[HistoryEvent] = []
    ranking: list[MvpRank] = []
    kills_avg: float = 0
    points_total: int = 0
    events_total: int = 0
