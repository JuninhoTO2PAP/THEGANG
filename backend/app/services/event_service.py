"""Eventos Diário / Intensivo / Campeonato na call."""

from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.permissions import Perm, has_perm
from app.models import EventMvpVote, Group, GroupMember, MatchEvent, User
from app.schemas.event import EventFinish, EventHistory, EventStart, HistoryEvent, MvpCandidate, MvpRank, TeamStatsPublic
from app.services import group_service
from app.utils.time import utcnow


def _is_group_owner(db: Session, group_id: int, user: User) -> bool:
    """Dono = criador do grupo, admin do app, ou cargo Administrador no grupo."""
    if user.is_admin:
        return True
    group = db.get(Group, group_id)
    if group is not None and group.created_by == user.id:
        return True
    perms = group_service._member_permissions(db, group_id, user.id)
    return has_perm(perms, Perm.ADMINISTRATOR)


def _can_start_event(db: Session, group_id: int, user: User) -> bool:
    """Dono do app / dono do grupo / Admin / CPT (START_EVENTS)."""
    if _is_group_owner(db, group_id, user):
        return True
    perms = group_service._member_permissions(db, group_id, user.id)
    return has_perm(perms, Perm.START_EVENTS)


def can_run_call_event(db: Session, group_id: int, user: User) -> bool:
    """CPT ou dono: iniciar evento e expulsar da call."""
    return _can_start_event(db, group_id, user)


def _elapsed(event: MatchEvent) -> int:
    end = event.ended_at or utcnow()
    return max(0, int((end - event.started_at).total_seconds()))


def _serialize(
    db: Session,
    event: MatchEvent,
    *,
    viewer: User | None = None,
) -> dict:
    owner = db.get(User, event.owner_id)
    mvp = db.get(User, event.mvp_user_id) if event.mvp_user_id else None
    votes = db.scalars(select(EventMvpVote).where(EventMvpVote.event_id == event.id)).all()
    tally = Counter(v.candidate_id for v in votes)
    members = db.scalars(
        select(User)
        .join(GroupMember, GroupMember.user_id == User.id)
        .where(GroupMember.group_id == event.group_id)
        .order_by(User.nickname)
    ).all()
    candidates = [
        MvpCandidate(
            id=m.id,
            nickname=m.nickname,
            username=m.username,
            avatar_url=m.avatar_url,
            votes=tally.get(m.id, 0),
        )
        for m in members
    ]
    my_vote = None
    if viewer is not None:
        mine = next((v for v in votes if v.voter_id == viewer.id), None)
        my_vote = mine.candidate_id if mine else None
    return {
        "id": event.id,
        "group_id": event.group_id,
        "channel_id": event.channel_id,
        "owner_id": event.owner_id,
        "owner_nickname": owner.nickname if owner else "",
        "event_type": event.event_type,
        "status": event.status,
        "started_at": event.started_at,
        "ended_at": event.ended_at,
        "placement": event.placement,
        "booyah_count": event.booyah_count,
        "kills": event.kills,
        "points": event.points,
        "is_win": bool(event.is_win),
        "mvp_user_id": event.mvp_user_id,
        "mvp_nickname": mvp.nickname if mvp else None,
        "my_vote_candidate_id": my_vote,
        "candidates": candidates,
        "elapsed_seconds": _elapsed(event),
    }


def get_active_for_channel(db: Session, user: User, channel_id: int) -> MatchEvent | None:
    channel = group_service.get_channel_in_group(db, user, channel_id)
    return db.scalar(
        select(MatchEvent)
        .where(
            MatchEvent.channel_id == channel.id,
            MatchEvent.status.in_(("live", "voting")),
        )
        .order_by(MatchEvent.id.desc())
    )


def get_event(db: Session, user: User, event_id: int) -> dict:
    event = db.get(MatchEvent, event_id)
    if event is None:
        raise AppError(404, "Evento não encontrado.")
    group_service.require_group_member(db, event.group_id, user)
    return _serialize(db, event, viewer=user)


def active_event_public(db: Session, user: User, channel_id: int) -> dict | None:
    event = get_active_for_channel(db, user, channel_id)
    if event is None:
        return None
    return _serialize(db, event, viewer=user)


def start_event(db: Session, user: User, data: EventStart) -> dict:
    channel = group_service.get_channel_in_group(db, user, data.channel_id)
    if channel.channel_type != "voice":
        raise AppError(400, "Eventos só começam em canal de voz.")
    if not _can_start_event(db, channel.group_id, user):
        raise AppError(
            403,
            "Só o CPT ou o dono pode iniciar Diário, Intensivo ou Campeonato.",
        )
    existing = db.scalar(
        select(MatchEvent).where(
            MatchEvent.channel_id == channel.id,
            MatchEvent.status.in_(("live", "voting")),
        )
    )
    if existing is not None:
        raise AppError(409, "Já existe um evento em andamento nesta call.")

    now = utcnow()
    event = MatchEvent(
        group_id=channel.group_id,
        channel_id=channel.id,
        owner_id=user.id,
        event_type=data.event_type,
        status="live",
        started_at=now,
        created_at=now,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return _serialize(db, event, viewer=user)


def finish_event(db: Session, user: User, event_id: int, data: EventFinish) -> dict:
    event = db.get(MatchEvent, event_id)
    if event is None:
        raise AppError(404, "Evento não encontrado.")
    group_service.require_group_member(db, event.group_id, user)
    if event.owner_id != user.id:
        raise AppError(403, "Só o dono do evento pode finalizar.")
    if event.status != "live":
        raise AppError(400, "Este evento já foi finalizado.")

    event.ended_at = utcnow()
    event.placement = data.placement
    event.booyah_count = data.booyah_count
    event.kills = data.kills
    event.points = data.points
    event.is_win = data.placement == 1
    event.status = "voting"
    db.add(event)
    db.commit()
    db.refresh(event)
    return _serialize(db, event, viewer=user)


def vote_mvp(db: Session, user: User, event_id: int, candidate_id: int) -> dict:
    event = db.get(MatchEvent, event_id)
    if event is None:
        raise AppError(404, "Evento não encontrado.")
    group_service.require_group_member(db, event.group_id, user)
    if event.status != "voting":
        raise AppError(400, "A votação de MVP não está aberta.")
    membership = db.get(GroupMember, (event.group_id, candidate_id))
    if membership is None:
        raise AppError(400, "Candidato inválido.")

    existing = db.scalar(
        select(EventMvpVote).where(
            EventMvpVote.event_id == event.id,
            EventMvpVote.voter_id == user.id,
        )
    )
    now = utcnow()
    if existing is None:
        db.add(
            EventMvpVote(
                event_id=event.id,
                voter_id=user.id,
                candidate_id=candidate_id,
                created_at=now,
            )
        )
    else:
        existing.candidate_id = candidate_id
        db.add(existing)
    db.commit()
    db.refresh(event)
    return _serialize(db, event, viewer=user)


def close_mvp(db: Session, user: User, event_id: int) -> dict:
    event = db.get(MatchEvent, event_id)
    if event is None:
        raise AppError(404, "Evento não encontrado.")
    group_service.require_group_member(db, event.group_id, user)
    if event.owner_id != user.id:
        raise AppError(403, "Só o dono pode encerrar a votação.")
    if event.status != "voting":
        raise AppError(400, "Evento não está em votação.")

    votes = db.scalars(select(EventMvpVote).where(EventMvpVote.event_id == event.id)).all()
    if votes:
        tally = Counter(v.candidate_id for v in votes)
        winner_id, _ = tally.most_common(1)[0]
        event.mvp_user_id = winner_id
    event.status = "closed"
    db.add(event)
    db.commit()
    db.refresh(event)
    return _serialize(db, event, viewer=user)


def team_stats(db: Session, user: User, group_id: int | None = None) -> TeamStatsPublic:
    """Totais do time (todos os grupos do usuário ou um grupo)."""
    if group_id is not None:
        group_service.require_group_member(db, group_id, user)
        group_ids = [group_id]
    else:
        group_ids = list(
            db.scalars(select(GroupMember.group_id).where(GroupMember.user_id == user.id))
        )
    if not group_ids:
        return TeamStatsPublic()

    closed = select(MatchEvent).where(
        MatchEvent.group_id.in_(group_ids),
        MatchEvent.status.in_(("voting", "closed")),
        MatchEvent.placement.is_not(None),
    )
    events = list(db.scalars(closed))
    wins = sum(1 for e in events if e.is_win)
    return TeamStatsPublic(
        wins=wins,
        booyah_total=sum(e.booyah_count or 0 for e in events),
        kills_total=sum(e.kills or 0 for e in events),
        points_total=sum(e.points or 0 for e in events),
        events_total=len(events),
        diario=sum(1 for e in events if e.event_type == "diario"),
        intensivo=sum(1 for e in events if e.event_type == "intensivo"),
        campeonato=sum(1 for e in events if e.event_type == "campeonato"),
    )


def event_history(db: Session, user: User, group_id: int | None = None) -> EventHistory:
    """Partidas já registradas e o ranking de MVP do time."""
    if group_id is not None:
        group_service.require_group_member(db, group_id, user)
        group_ids = [group_id]
    else:
        group_ids = list(
            db.scalars(select(GroupMember.group_id).where(GroupMember.user_id == user.id))
        )
    if not group_ids:
        return EventHistory()

    rows = list(
        db.scalars(
            select(MatchEvent)
            .where(MatchEvent.group_id.in_(group_ids))
            .order_by(MatchEvent.id.desc())
            .limit(40)
        ).all()
    )
    finished = [event for event in rows if event.placement is not None]
    kills_total = sum(event.kills or 0 for event in finished)
    points_total = sum(event.points or 0 for event in finished)
    mvp_ids = [event.mvp_user_id for event in rows if event.mvp_user_id]
    tally = Counter(mvp_ids)
    ranking: list[MvpRank] = []
    if tally:
        people = {
            person.id: person.nickname
            for person in db.scalars(select(User).where(User.id.in_(tally.keys()))).all()
        }
        ranking = [
            MvpRank(nickname=people.get(user_id, "—"), mvp_count=count)
            for user_id, count in tally.most_common()
        ]
    events = []
    for event in rows:
        owner = db.get(User, event.owner_id)
        mvp = db.get(User, event.mvp_user_id) if event.mvp_user_id else None
        events.append(
            HistoryEvent(
                id=event.id,
                event_type=event.event_type,
                status=event.status,
                started_at=event.started_at,
                ended_at=event.ended_at,
                placement=event.placement,
                booyah_count=event.booyah_count,
                kills=event.kills,
                points=event.points,
                is_win=bool(event.is_win),
                mvp_nickname=mvp.nickname if mvp else None,
                owner_nickname=owner.nickname if owner else "",
            )
        )
    return EventHistory(
        events=events,
        ranking=ranking,
        kills_avg=round(kills_total / len(finished), 1) if finished else 0,
        points_total=points_total,
        events_total=len(finished),
    )


def recent_events(db: Session, user: User, *, limit: int = 10) -> list[dict]:
    group_ids = list(
        db.scalars(select(GroupMember.group_id).where(GroupMember.user_id == user.id))
    )
    if not group_ids:
        return []
    rows = db.scalars(
        select(MatchEvent)
        .where(MatchEvent.group_id.in_(group_ids), MatchEvent.placement.is_not(None))
        .order_by(MatchEvent.ended_at.desc(), MatchEvent.id.desc())
        .limit(limit)
    ).all()
    return [_serialize(db, e, viewer=user) for e in rows]
