"""Lista de contas para o dono do app. Senha fica só como hash."""

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import hash_password
from app.models import Group, GroupMember, User
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
