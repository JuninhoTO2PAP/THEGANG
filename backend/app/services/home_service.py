"""Home THE GANG: banner, recado do admin, próximo evento e online."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import GangHome, User
from app.schemas.home import HomeUpdate, OnlineMember
from app.services.ws_hub import hub
from app.utils.time import utcnow

HOME_ID = 1


def ensure_home(db: Session) -> GangHome:
    row = db.get(GangHome, HOME_ID)
    if row is not None:
        return row
    now = utcnow()
    row = GangHome(
        id=HOME_ID,
        banner_title="THE GANG",
        banner_subtitle="Tropa Free Fire",
        admin_note="Bem-vindos. Respeito no time, foco no jogo.",
        next_event_title="Ranked da tropa",
        next_event_at=None,
        updated_at=now,
        updated_by=None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_online(db: Session) -> list[OnlineMember]:
    users = db.scalars(select(User).order_by(User.nickname)).all()
    online: list[OnlineMember] = []
    for member in users:
        presence = getattr(member, "presence", "online") or "online"
        is_online = (hub.is_online(member.id) or bool(member.is_online)) and presence != "invisible"
        if not is_online:
            continue
        online.append(
            OnlineMember(
                id=member.id,
                username=member.username,
                nickname=member.nickname,
                avatar_url=member.avatar_url,
                is_admin=member.is_admin,
                presence=presence,
                status_text=member.status_text,
                ff_role=member.ff_role,
                ff_nick=member.ff_nick,
            )
        )
    return online


def get_home(db: Session) -> tuple[GangHome, list[OnlineMember]]:
    return ensure_home(db), list_online(db)


def update_home(db: Session, user: User, data: HomeUpdate) -> GangHome:
    if not user.is_admin:
        raise AppError(403, "Só o administrador pode editar a Home.")
    row = ensure_home(db)
    row.banner_title = data.banner_title
    row.banner_subtitle = data.banner_subtitle
    row.admin_note = data.admin_note
    row.next_event_title = data.next_event_title
    row.next_event_at = data.next_event_at
    row.updated_at = utcnow()
    row.updated_by = user.id
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
