"""Lista de contas para o dono do app. Senha fica só como hash."""

from collections import defaultdict

from sqlalchemy import delete, or_, select, update
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import hash_password
from app.models import (
    Channel,
    DMConversation,
    GangHome,
    Group,
    GroupInvite,
    GroupMember,
    InviteCode,
    MatchEvent,
    Message,
    User,
)
from app.schemas.admin import AdminMember
from app.services.auth_service import revoke_sessions
from app.services.group_service import TEAM_NAMES, team_label
from app.services.ws_hub import hub
from app.utils.time import utcnow


def list_members(db: Session) -> list[AdminMember]:
    users = list(db.scalars(select(User).order_by(User.nickname)).all())
    teams: dict[int, list[str]] = defaultdict(list)
    rows = db.execute(
        select(GroupMember.user_id, Group.name)
        .join(Group, Group.id == GroupMember.group_id)
        .where(Group.name.in_(TEAM_NAMES))
    ).all()
    for user_id, name in rows:
        label = team_label(name)
        if label not in teams[user_id]:
            teams[user_id].append(label)

    invite_by_user = {
        user_id: code
        for user_id, code in db.execute(
            select(InviteCode.used_by, InviteCode.code).where(InviteCode.used_by.is_not(None))
        ).all()
        if user_id is not None
    }

    members: list[AdminMember] = []
    for user in users:
        presence = user.presence or "online"
        is_online = (hub.is_online(user.id) or bool(user.is_online)) and presence != "invisible"
        members.append(
            AdminMember(
                id=user.id,
                username=user.username,
                email=user.email,
                nickname=user.nickname,
                avatar_url=user.avatar_url,
                is_admin=user.is_admin,
                is_online=is_online,
                presence=presence,
                status_text=user.status_text,
                ff_id=user.ff_id,
                ff_nick=user.ff_nick,
                ff_role=user.ff_role,
                ff_region=user.ff_region,
                team=" · ".join(teams.get(user.id, [])) or None,
                invite_code=invite_by_user.get(user.id),
                last_seen=user.last_seen,
                created_at=user.created_at,
            )
        )
    members.sort(key=lambda item: (not item.is_online, item.nickname.lower()))
    return members


def reset_password(db: Session, user_id: int, new_password: str) -> None:
    target = db.get(User, user_id)
    if target is None:
        raise AppError(404, "Pessoa não encontrada.")
    target.hashed_password = hash_password(new_password)
    target.last_seen = utcnow()
    revoke_sessions(db, target.id)
    db.add(target)
    db.commit()


def delete_member(db: Session, actor: User, user_id: int) -> None:
    """Apaga a conta e o que só ela usa. A conta de administrador fica."""
    target = db.get(User, user_id)
    if target is None:
        raise AppError(404, "Pessoa não encontrada.")
    if target.is_admin or target.id == actor.id:
        raise AppError(400, "A conta de administrador não pode ser apagada.")

    keeper = actor.id
    db.execute(update(InviteCode).where(InviteCode.created_by == target.id).values(created_by=keeper))
    db.execute(delete(InviteCode).where(InviteCode.used_by == target.id))
    db.execute(update(GroupInvite).where(GroupInvite.created_by == target.id).values(created_by=keeper))
    db.execute(update(Group).where(Group.created_by == target.id).values(created_by=keeper))
    db.execute(update(Channel).where(Channel.created_by == target.id).values(created_by=keeper))
    db.execute(update(MatchEvent).where(MatchEvent.owner_id == target.id).values(owner_id=keeper))
    db.execute(update(MatchEvent).where(MatchEvent.mvp_user_id == target.id).values(mvp_user_id=None))
    db.execute(update(GangHome).where(GangHome.updated_by == target.id).values(updated_by=keeper))
    db.execute(update(Message).where(Message.pinned_by == target.id).values(pinned_by=None))

    dm_ids = list(
        db.scalars(
            select(DMConversation.id).where(
                or_(DMConversation.user_a_id == target.id, DMConversation.user_b_id == target.id)
            )
        ).all()
    )
    if dm_ids:
        db.execute(delete(Message).where(Message.dm_conversation_id.in_(dm_ids)))
        db.execute(delete(DMConversation).where(DMConversation.id.in_(dm_ids)))

    db.execute(delete(Message).where(Message.sender_id == target.id))
    revoke_sessions(db, target.id)
    db.flush()
    db.delete(target)
    db.commit()
