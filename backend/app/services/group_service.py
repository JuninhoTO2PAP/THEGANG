"""Grupos, canais internos, cargos e permissões."""

import re

from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.errors import AppError
from app.core.permissions import ADMIN_PERMS, CPT_PERMS, MEMBER_PERMS, Perm, has_perm
from app.models import (
    Channel,
    EventMvpVote,
    Group,
    GroupInvite,
    GroupMember,
    MatchEvent,
    MemberRole,
    Message,
    MessageReaction,
    MessageRead,
    Role,
    User,
)
from app.schemas.group import ChannelCreate, GroupCreate, GroupUpdate, RoleCreate, RoleUpdate
from app.utils.time import utcnow


def _member_permissions(db: Session, group_id: int, user_id: int) -> int:
    roles = db.scalars(
        select(Role)
        .join(MemberRole, MemberRole.role_id == Role.id)
        .where(Role.group_id == group_id, MemberRole.user_id == user_id)
    ).all()
    perms = 0
    for role in roles:
        perms |= role.permissions
    # Cargo padrão (@everyone) sempre conta.
    default = db.scalar(
        select(Role).where(Role.group_id == group_id, Role.is_default.is_(True))
    )
    if default is not None:
        perms |= default.permissions
    return perms


def require_group_member(db: Session, group_id: int, user: User) -> Group:
    group = db.get(Group, group_id)
    if group is None:
        raise AppError(404, "Grupo não encontrado.")
    membership = db.get(GroupMember, (group_id, user.id))
    if membership is None:
        raise AppError(403, "Você não participa deste grupo.")
    return group


def require_perm(db: Session, group_id: int, user: User, flag: int) -> int:
    require_group_member(db, group_id, user)
    perms = _member_permissions(db, group_id, user.id)
    if not has_perm(perms, flag):
        raise AppError(403, "Sem permissão para isso.")
    return perms


def list_groups_for_user(db: Session, user: User) -> list[tuple[Group, int]]:
    groups = db.scalars(
        select(Group)
        .join(GroupMember, GroupMember.group_id == Group.id)
        .where(GroupMember.user_id == user.id)
        .order_by(Group.name)
    ).all()
    return [(group, _member_permissions(db, group.id, user.id)) for group in groups]


DEFAULT_GROUP_NAME = "the-gang"  # legado
# Slugs (GroupCreate normaliza para minúsculo/hífen). Labels só na UI.
TEAM_A_NAME = "the-gang-a"
TEAM_B_NAME = "the-gang-b"
TEAM_LABELS = {
    TEAM_A_NAME: "THE GANG A",
    TEAM_B_NAME: "THE GANG B",
    DEFAULT_GROUP_NAME: "THE GANG A",
}
TEAM_NAMES = (TEAM_A_NAME, TEAM_B_NAME)
PROTECTED_GROUP_NAMES = {
    DEFAULT_GROUP_NAME,
    TEAM_A_NAME,
    TEAM_B_NAME,
    "THE GANG A",
    "THE GANG B",
}


def team_name(team: str) -> str:
    key = (team or "a").strip().lower()
    if key == "b":
        return TEAM_B_NAME
    return TEAM_A_NAME


def _norm_name(name: str) -> str:
    return re.sub(r"\s+", "-", (name or "").strip().lower())


def team_label(name: str) -> str:
    key = _norm_name(name)
    if key in {"the-gang", "the-gang-a"}:
        return "THE GANG A"
    if key == "the-gang-b":
        return "THE GANG B"
    return TEAM_LABELS.get(name, name)


# Nomes que a interface já desenha com a foto A/B. O duplicado com esse nome sai;
# fica o grupo que ainda aparecia com iniciais (ex.: the-gang-A).
_ALREADY_ICON = {
    "a": {"the-gang-a", "the-gang", "THE GANG A"},
    "b": {"the-gang-b", "THE GANG B"},
}
_TEAM_A_ALIASES = {"the-gang", "the-gang-a"}
_TEAM_B_ALIASES = {"the-gang-b"}


def _purge_group(db: Session, group: Group) -> None:
    """Apaga um grupo duplicado sem a trava dos times oficiais."""
    event_ids = list(db.scalars(select(MatchEvent.id).where(MatchEvent.group_id == group.id)))
    if event_ids:
        db.execute(delete(EventMvpVote).where(EventMvpVote.event_id.in_(event_ids)))
        db.execute(delete(MatchEvent).where(MatchEvent.id.in_(event_ids)))

    channel_ids = list(db.scalars(select(Channel.id).where(Channel.group_id == group.id)))
    if channel_ids:
        msg_ids = list(db.scalars(select(Message.id).where(Message.channel_id.in_(channel_ids))))
        if msg_ids:
            db.execute(delete(MessageReaction).where(MessageReaction.message_id.in_(msg_ids)))
            db.execute(delete(MessageRead).where(MessageRead.message_id.in_(msg_ids)))
            db.execute(update(Message).where(Message.reply_to_id.in_(msg_ids)).values(reply_to_id=None))
            db.execute(delete(Message).where(Message.id.in_(msg_ids)))
        db.execute(delete(Channel).where(Channel.id.in_(channel_ids)))

    role_ids = list(db.scalars(select(Role.id).where(Role.group_id == group.id)))
    if role_ids:
        db.execute(delete(MemberRole).where(MemberRole.role_id.in_(role_ids)))
        db.execute(delete(Role).where(Role.id.in_(role_ids)))

    db.execute(delete(GroupInvite).where(GroupInvite.group_id == group.id))
    db.execute(delete(GroupMember).where(GroupMember.group_id == group.id))
    db.delete(group)
    db.flush()


def _collapse_team(
    db: Session, canonical: str, aliases: set[str], already_icon: set[str]
) -> Group | None:
    matches = [g for g in db.scalars(select(Group)).all() if _norm_name(g.name) in aliases]
    if not matches:
        return None
    plain = [g for g in matches if g.name not in already_icon]
    keeper = min(plain or matches, key=lambda g: g.id)
    for group in matches:
        if group.id != keeper.id:
            _purge_group(db, group)
    if keeper.name != canonical:
        keeper.name = canonical
        db.add(keeper)
        db.flush()
    return keeper


def _ensure_cpt_role(db: Session, group: Group) -> Role:
    now = utcnow()
    role = db.scalar(
        select(Role).where(Role.group_id == group.id, Role.name == "CPT")
    )
    if role is None:
        role = Role(
            group_id=group.id,
            name="CPT",
            color="#f0b232",
            position=50,
            permissions=CPT_PERMS,
            is_default=False,
            created_at=now,
        )
        db.add(role)
        db.flush()
    elif role.permissions != CPT_PERMS:
        role.permissions = CPT_PERMS
        db.add(role)
    return role


def _ensure_owner_in_group(db: Session, group: Group, owner: User) -> None:
    now = utcnow()
    membership = db.get(GroupMember, (group.id, owner.id))
    if membership is None:
        db.add(GroupMember(group_id=group.id, user_id=owner.id, joined_at=now))
    admin_role = db.scalar(
        select(Role).where(Role.group_id == group.id, Role.name == "Admin")
    )
    if admin_role is not None:
        link = db.scalar(
            select(MemberRole).where(
                MemberRole.role_id == admin_role.id, MemberRole.user_id == owner.id
            )
        )
        if link is None:
            db.add(MemberRole(role_id=admin_role.id, user_id=owner.id))


def ensure_default_group(db: Session, owner: User | None = None) -> Group:
    """Compat: devolve o time A (e garante A+B)."""
    a, _b = ensure_team_groups(db, owner=owner)
    return a


def ensure_team_groups(
    db: Session, owner: User | None = None
) -> tuple[Group, Group]:
    """Garante the-gang-a e the-gang-b; o dono do app fica nos dois."""
    creator = owner if owner is not None and owner.is_admin else None
    if creator is None:
        creator = db.scalar(select(User).where(User.is_admin.is_(True)).order_by(User.id))
    if creator is None:
        raise AppError(500, "Não há administrador para criar os times.")

    _collapse_team(db, TEAM_A_NAME, _TEAM_A_ALIASES, _ALREADY_ICON["a"])
    _collapse_team(db, TEAM_B_NAME, _TEAM_B_ALIASES, _ALREADY_ICON["b"])

    groups: list[Group] = []
    for name, description in (
        (TEAM_A_NAME, "Time A do THE GANG"),
        (TEAM_B_NAME, "Time B do THE GANG"),
    ):
        existing = db.scalar(select(Group).where(Group.name == name))
        if existing is None:
            group, _ = create_group(
                db,
                creator,
                GroupCreate(name=name, description=description, is_private=True),
            )
        else:
            group = existing
            if group.description != description:
                group.description = description
                db.add(group)
        _ensure_cpt_role(db, group)
        _ensure_owner_in_group(db, group, creator)
        groups.append(group)

    db.commit()
    for g in groups:
        db.refresh(g)
    return groups[0], groups[1]


def create_group(db: Session, user: User, data: GroupCreate) -> tuple[Group, int]:
    if not user.is_admin:
        raise AppError(403, "Só o administrador do app pode criar grupos.")
    now = utcnow()
    group = Group(
        name=data.name,
        description=data.description or "",
        icon_url=None,
        is_private=data.is_private,
        created_by=user.id,
        created_at=now,
    )
    db.add(group)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise AppError(409, "Já existe um grupo com esse nome.") from exc

    everyone = Role(
        group_id=group.id,
        name="@everyone",
        color="#99aab5",
        position=0,
        permissions=MEMBER_PERMS,
        is_default=True,
        created_at=now,
    )
    admin_role = Role(
        group_id=group.id,
        name="Admin",
        color="#e74c3c",
        position=100,
        permissions=ADMIN_PERMS,
        is_default=False,
        created_at=now,
    )
    cpt_role = Role(
        group_id=group.id,
        name="CPT",
        color="#f0b232",
        position=50,
        permissions=CPT_PERMS,
        is_default=False,
        created_at=now,
    )
    db.add_all([everyone, admin_role, cpt_role])
    db.flush()

    members = [user] if data.is_private else list(db.scalars(select(User)).all())
    for member in members:
        db.add(GroupMember(group_id=group.id, user_id=member.id, joined_at=now))
    db.add(MemberRole(role_id=admin_role.id, user_id=user.id))

    geral = Channel(
        group_id=group.id,
        name="geral",
        description="Conversa principal",
        channel_type="text",
        position=0,
        created_by=user.id,
        created_at=now,
    )
    voice = Channel(
        group_id=group.id,
        name="voz",
        description="Call do grupo",
        channel_type="voice",
        position=1,
        created_by=user.id,
        created_at=now,
    )
    db.add_all([geral, voice])
    db.commit()
    db.refresh(group)
    return group, _member_permissions(db, group.id, user.id)


def update_group(db: Session, user: User, group_id: int, data: GroupUpdate) -> Group:
    require_perm(db, group_id, user, Perm.MANAGE_GROUP)
    group = db.get(Group, group_id)
    assert group is not None
    if data.name is not None:
        group.name = data.name
    if data.description is not None:
        group.description = data.description
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AppError(409, "Já existe um grupo com esse nome.") from exc
    db.refresh(group)
    return group


def delete_group(db: Session, user: User, group_id: int) -> None:
    """Apaga o grupo e tudo ligado a ele. Grupo padrão THE GANG é protegido."""
    require_perm(db, group_id, user, Perm.MANAGE_GROUP)
    group = db.get(Group, group_id)
    assert group is not None
    if _norm_name(group.name) in _TEAM_A_ALIASES | _TEAM_B_ALIASES or group.name in PROTECTED_GROUP_NAMES:
        raise AppError(400, "Os times THE GANG A/B não podem ser apagados.")
    if not user.is_admin and group.created_by != user.id:
        my = _member_permissions(db, group_id, user.id)
        if not has_perm(my, Perm.ADMINISTRATOR):
            raise AppError(403, "Só o dono do grupo ou um admin pode apagá-lo.")

    channel_ids = list(db.scalars(select(Channel.id).where(Channel.group_id == group_id)))
    if channel_ids:
        db.execute(delete(Message).where(Message.channel_id.in_(channel_ids)))
        db.execute(delete(Channel).where(Channel.id.in_(channel_ids)))

    role_ids = list(db.scalars(select(Role.id).where(Role.group_id == group_id)))
    if role_ids:
        db.execute(delete(MemberRole).where(MemberRole.role_id.in_(role_ids)))
        db.execute(delete(Role).where(Role.id.in_(role_ids)))

    db.execute(delete(GroupInvite).where(GroupInvite.group_id == group_id))
    db.execute(delete(GroupMember).where(GroupMember.group_id == group_id))
    db.delete(group)
    db.commit()


def list_channels(db: Session, user: User, group_id: int) -> list[Channel]:
    require_perm(db, group_id, user, Perm.VIEW_CHANNELS)
    return list(
        db.scalars(
            select(Channel)
            .where(Channel.group_id == group_id)
            .order_by(Channel.position, Channel.id)
        ).all()
    )


def create_channel(db: Session, user: User, group_id: int, data: ChannelCreate) -> Channel:
    require_perm(db, group_id, user, Perm.MANAGE_CHANNELS)
    max_pos = db.scalar(
        select(func.coalesce(func.max(Channel.position), -1)).where(Channel.group_id == group_id)
    )
    channel = Channel(
        group_id=group_id,
        name=data.name,
        description=data.description or "",
        channel_type=data.channel_type,
        position=(max_pos or 0) + 1,
        created_by=user.id,
        created_at=utcnow(),
    )
    db.add(channel)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AppError(409, "Já existe um canal com esse nome neste grupo.") from exc
    db.refresh(channel)
    return channel


def get_channel_in_group(db: Session, user: User, channel_id: int) -> Channel:
    channel = db.get(Channel, channel_id)
    if channel is None:
        raise AppError(404, "Canal não encontrado.")
    require_perm(db, channel.group_id, user, Perm.VIEW_CHANNELS)
    return channel


def list_messages(
    db: Session,
    user: User,
    channel_id: int,
    *,
    limit: int = 50,
    before_id: int | None = None,
) -> list[Message]:
    channel = get_channel_in_group(db, user, channel_id)
    if channel.channel_type != "text":
        raise AppError(400, "Só canais de texto têm histórico de mensagens.")
    query = (
        select(Message)
        .options(joinedload(Message.sender))
        .where(Message.channel_id == channel_id)
        .order_by(Message.id.desc())
        .limit(min(limit, 100))
    )
    if before_id is not None:
        query = query.where(Message.id < before_id)
    rows = list(db.scalars(query).unique().all())
    rows.reverse()
    return rows


def post_message(
    db: Session,
    user: User,
    channel_id: int,
    content: str,
    *,
    attachment_url: str | None = None,
    attachment_type: str | None = None,
    reply_to_id: int | None = None,
) -> Message:
    from app.services import message_extra

    channel = get_channel_in_group(db, user, channel_id)
    if channel.channel_type != "text":
        raise AppError(400, "Não dá para enviar texto em canal de voz.")
    require_perm(db, channel.group_id, user, Perm.SEND_MESSAGES)
    text = (content or "").strip()
    if not text and not attachment_url:
        raise AppError(400, "Mensagem vazia.")
    reply_id = message_extra.resolve_reply_target(
        db, user, channel_id=channel_id, dm_id=None, reply_to_id=reply_to_id
    )
    message = Message(
        channel_id=channel_id,
        dm_conversation_id=None,
        sender_id=user.id,
        content=text,
        attachment_url=attachment_url,
        attachment_type=attachment_type,
        reply_to_id=reply_id,
        created_at=utcnow(),
        edited_at=None,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    _ = message.sender
    return message


def edit_message(db: Session, user: User, message_id: int, content: str) -> Message:
    from app.services import dm_service

    message = db.get(Message, message_id)
    if message is None:
        raise AppError(404, "Mensagem não encontrada.")
    if message.sender_id != user.id:
        raise AppError(403, "Só o autor pode editar.")
    if message.channel_id is not None:
        get_channel_in_group(db, user, message.channel_id)
    elif message.dm_conversation_id is not None:
        dm_service.require_dm_member(db, user, message.dm_conversation_id)
    message.content = content.strip()
    message.edited_at = utcnow()
    db.commit()
    db.refresh(message)
    _ = message.sender
    return message


def delete_message(db: Session, user: User, message_id: int) -> dict:
    from app.services import dm_service

    message = db.get(Message, message_id)
    if message is None:
        raise AppError(404, "Mensagem não encontrada.")
    channel_id = message.channel_id
    dm_id = message.dm_conversation_id
    if channel_id is not None:
        channel = get_channel_in_group(db, user, channel_id)
        is_mod = has_perm(
            _member_permissions(db, channel.group_id, user.id), Perm.MANAGE_CHANNELS
        )
    elif dm_id is not None:
        dm_service.require_dm_member(db, user, dm_id)
        is_mod = False
    else:
        is_mod = False
    if message.sender_id != user.id and not is_mod:
        raise AppError(403, "Sem permissão para apagar.")
    info = {"id": message.id, "channel_id": channel_id, "dm_conversation_id": dm_id}
    db.delete(message)
    db.commit()
    return info


def search_messages(
    db: Session,
    user: User,
    *,
    group_id: int | None = None,
    channel_id: int | None = None,
    q: str,
    limit: int = 30,
) -> list[Message]:
    query_text = q.strip()
    if len(query_text) < 2:
        raise AppError(400, "Busca precisa de pelo menos 2 caracteres.")
    stmt = select(Message).options(joinedload(Message.sender)).where(
        Message.content.ilike(f"%{query_text}%")
    )
    if channel_id is not None:
        get_channel_in_group(db, user, channel_id)
        stmt = stmt.where(Message.channel_id == channel_id)
    elif group_id is not None:
        require_group_member(db, group_id, user)
        channel_ids = list(
            db.scalars(select(Channel.id).where(Channel.group_id == group_id)).all()
        )
        stmt = stmt.where(Message.channel_id.in_(channel_ids or [-1]))
    else:
        raise AppError(400, "Informe group_id ou channel_id.")
    rows = list(
        db.scalars(stmt.order_by(Message.id.desc()).limit(min(limit, 50))).unique().all()
    )
    return rows


def mark_messages_read(db: Session, user: User, message_ids: list[int]) -> None:
    from app.models import MessageRead

    now = utcnow()
    for mid in message_ids:
        message = db.get(Message, mid)
        if message is None:
            continue
        if message.channel_id is not None:
            try:
                get_channel_in_group(db, user, message.channel_id)
            except AppError:
                continue
        existing = db.get(MessageRead, (mid, user.id))
        if existing is None:
            db.add(MessageRead(message_id=mid, user_id=user.id, read_at=now))
    db.commit()


def list_roles(db: Session, user: User, group_id: int) -> list[Role]:
    require_group_member(db, group_id, user)
    return list(
        db.scalars(
            select(Role).where(Role.group_id == group_id).order_by(Role.position.desc(), Role.id)
        ).all()
    )


def create_role(db: Session, user: User, group_id: int, data: RoleCreate) -> Role:
    require_perm(db, group_id, user, Perm.MANAGE_ROLES)
    if data.name.lower() in {"@everyone", "everyone"}:
        raise AppError(400, "Esse nome de cargo é reservado.")
    perms = ADMIN_PERMS if data.is_admin else data.permissions
    if data.is_admin:
        perms = ADMIN_PERMS
    elif perms & Perm.ADMINISTRATOR:
        # Só quem já é admin pode criar outro admin — already required MANAGE_ROLES;
        # exigir ADMINISTRATOR explícito para conceder admin.
        my = _member_permissions(db, group_id, user.id)
        if not has_perm(my, Perm.ADMINISTRATOR):
            raise AppError(403, "Só Admin pode criar cargo com poder total.")
    max_pos = db.scalar(
        select(func.coalesce(func.max(Role.position), 0)).where(Role.group_id == group_id)
    )
    role = Role(
        group_id=group_id,
        name=data.name,
        color=data.color,
        position=(max_pos or 0) + 1,
        permissions=perms,
        is_default=False,
        created_at=utcnow(),
    )
    db.add(role)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AppError(409, "Já existe um cargo com esse nome.") from exc
    db.refresh(role)
    return role


def update_role(db: Session, user: User, group_id: int, role_id: int, data: RoleUpdate) -> Role:
    require_perm(db, group_id, user, Perm.MANAGE_ROLES)
    role = db.get(Role, role_id)
    if role is None or role.group_id != group_id:
        raise AppError(404, "Cargo não encontrado.")
    if role.is_default and data.name is not None:
        raise AppError(400, "Não dá para renomear @everyone.")
    if data.name is not None:
        role.name = data.name
    if data.color is not None:
        if not data.color.startswith("#") or len(data.color) != 7:
            raise AppError(400, "Cor inválida.")
        role.color = data.color.lower()
    if data.is_admin is True:
        my = _member_permissions(db, group_id, user.id)
        if not has_perm(my, Perm.ADMINISTRATOR):
            raise AppError(403, "Só Admin pode promover cargo a Admin.")
        role.permissions = ADMIN_PERMS
    elif data.permissions is not None:
        if data.permissions & Perm.ADMINISTRATOR and not has_perm(
            _member_permissions(db, group_id, user.id), Perm.ADMINISTRATOR
        ):
            raise AppError(403, "Só Admin pode conceder poder total.")
        role.permissions = data.permissions
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AppError(409, "Já existe um cargo com esse nome.") from exc
    db.refresh(role)
    return role


def delete_role(db: Session, user: User, group_id: int, role_id: int) -> None:
    require_perm(db, group_id, user, Perm.MANAGE_ROLES)
    role = db.get(Role, role_id)
    if role is None or role.group_id != group_id:
        raise AppError(404, "Cargo não encontrado.")
    if role.is_default:
        raise AppError(400, "Não dá para apagar @everyone.")
    db.delete(role)
    db.commit()


def list_members(db: Session, user: User, group_id: int) -> list[dict]:
    require_group_member(db, group_id, user)
    rows = db.execute(
        select(User, GroupMember.joined_at)
        .join(GroupMember, GroupMember.user_id == User.id)
        .where(GroupMember.group_id == group_id)
        .order_by(User.nickname)
    ).all()
    result = []
    for member, joined_at in rows:
        role_ids = list(
            db.scalars(
                select(MemberRole.role_id)
                .join(Role, Role.id == MemberRole.role_id)
                .where(MemberRole.user_id == member.id, Role.group_id == group_id)
            ).all()
        )
        from app.services.ws_hub import hub

        presence = getattr(member, "presence", "online") or "online"
        online = (hub.is_online(member.id) or bool(member.is_online)) and presence != "invisible"
        result.append(
            {
                "id": member.id,
                "username": member.username,
                "nickname": member.nickname,
                "avatar_url": member.avatar_url,
                "is_admin": member.is_admin,
                "role_ids": role_ids,
                "joined_at": joined_at,
                "is_online": online,
                "presence": presence,
                "status_text": getattr(member, "status_text", None),
                "ff_id": getattr(member, "ff_id", None),
                "ff_nick": getattr(member, "ff_nick", None),
                "ff_role": getattr(member, "ff_role", None),
                "ff_region": getattr(member, "ff_region", None),
                "banner_theme": getattr(member, "banner_theme", None) or "gold",
            }
        )
    return result


def set_member_roles(
    db: Session, actor: User, group_id: int, target_user_id: int, role_ids: list[int]
) -> dict:
    require_perm(db, group_id, actor, Perm.MANAGE_ROLES)
    membership = db.get(GroupMember, (group_id, target_user_id))
    if membership is None:
        raise AppError(404, "Membro não está neste grupo.")

    roles = list(
        db.scalars(select(Role).where(Role.group_id == group_id, Role.id.in_(role_ids))).all()
    )
    if len(roles) != len(set(role_ids)):
        raise AppError(400, "Um ou mais cargos são inválidos.")
    if any(role.is_default for role in roles):
        raise AppError(400, "@everyone é automático; não atribua manualmente.")

    my = _member_permissions(db, group_id, actor.id)
    if any(role.permissions & Perm.ADMINISTRATOR for role in roles) and not has_perm(
        my, Perm.ADMINISTRATOR
    ):
        raise AppError(403, "Só Admin pode atribuir cargo Admin.")
    if any(role.name == "CPT" for role in roles) and not actor.is_admin:
        raise AppError(403, "Só o dono do app pode atribuir o cargo CPT.")

    # Remove cargos atuais do grupo (exceto não há member_role para default).
    current_ids = list(
        db.scalars(
            select(MemberRole.role_id)
            .join(Role, Role.id == MemberRole.role_id)
            .where(MemberRole.user_id == target_user_id, Role.group_id == group_id)
        ).all()
    )
    if current_ids:
        db.execute(
            delete(MemberRole).where(
                MemberRole.user_id == target_user_id, MemberRole.role_id.in_(current_ids)
            )
        )
    for role_id in role_ids:
        db.add(MemberRole(role_id=role_id, user_id=target_user_id))
    db.commit()

    target = db.get(User, target_user_id)
    assert target is not None
    from app.services.ws_hub import hub

    return {
        "id": target.id,
        "username": target.username,
        "nickname": target.nickname,
        "avatar_url": target.avatar_url,
        "is_admin": target.is_admin,
        "role_ids": role_ids,
        "joined_at": membership.joined_at,
        "is_online": hub.is_online(target.id) or bool(target.is_online),
    }


def add_user_to_public_groups(db: Session, user: User) -> None:
    """Legado: não usa mais no cadastro (cadastro vai para time A ou B)."""
    now = utcnow()
    publics = db.scalars(select(Group).where(Group.is_private.is_(False))).all()
    for group in publics:
        exists = db.get(GroupMember, (group.id, user.id))
        if exists is None:
            db.add(GroupMember(group_id=group.id, user_id=user.id, joined_at=now))


def add_user_to_team(db: Session, user: User, team: str) -> Group:
    """Coloca o usuário só no time A ou B (cargo padrão @everyone)."""
    ensure_team_groups(db)
    name = team_name(team)
    group = db.scalar(select(Group).where(Group.name == name))
    if group is None:
        raise AppError(500, f"Time {name} não encontrado.")
    now = utcnow()
    if db.get(GroupMember, (group.id, user.id)) is None:
        db.add(GroupMember(group_id=group.id, user_id=user.id, joined_at=now))
    return group


def transfer_member_team(
    db: Session, actor: User, *, target_user_id: int, to_team: str
) -> dict:
    """Dono do app sobe/desce membro entre THE GANG A e THE GANG B."""
    if not actor.is_admin:
        raise AppError(403, "Só o dono do app pode mover membros entre times.")
    target = db.get(User, target_user_id)
    if target is None:
        raise AppError(404, "Usuário não encontrado.")
    if target.is_admin:
        raise AppError(400, "O dono do app já está nos dois times.")

    team_a, team_b = ensure_team_groups(db, owner=actor)
    dest = team_b if (to_team or "a").lower() == "b" else team_a
    source = team_a if dest.id == team_b.id else team_b

    now = utcnow()
    # Remove cargos + membership no time de origem (se estiver).
    src_role_ids = list(
        db.scalars(
            select(MemberRole.role_id)
            .join(Role, Role.id == MemberRole.role_id)
            .where(MemberRole.user_id == target.id, Role.group_id == source.id)
        ).all()
    )
    if src_role_ids:
        db.execute(
            delete(MemberRole).where(
                MemberRole.user_id == target.id, MemberRole.role_id.in_(src_role_ids)
            )
        )
    src_member = db.get(GroupMember, (source.id, target.id))
    if src_member is not None:
        db.delete(src_member)

    if db.get(GroupMember, (dest.id, target.id)) is None:
        db.add(GroupMember(group_id=dest.id, user_id=target.id, joined_at=now))
    db.commit()
    return {
        "user_id": target.id,
        "username": target.username,
        "nickname": target.nickname,
        "from_group": source.name,
        "to_group": dest.name,
        "to_team": "b" if dest.name == TEAM_B_NAME else "a",
    }


def create_group_invite(
    db: Session,
    user: User,
    group_id: int,
    *,
    expires_in_days: int = 7,
    max_uses: int | None = None,
):
    import secrets
    from datetime import timedelta

    from app.models import GroupInvite

    require_perm(db, group_id, user, Perm.MANAGE_GROUP)
    now = utcnow()
    code = f"GRP-{secrets.token_hex(4).upper()}"
    invite = GroupInvite(
        group_id=group_id,
        code=code,
        created_by=user.id,
        max_uses=max_uses,
        uses=0,
        expires_at=(
            None if expires_in_days == 0 else now + timedelta(days=expires_in_days)
        ),
        created_at=now,
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)
    return invite


def join_group_by_code(db: Session, user: User, code: str) -> Group:
    from app.models import GroupInvite

    invite = db.scalar(select(GroupInvite).where(GroupInvite.code == code.strip().upper()))
    if invite is None:
        raise AppError(400, "Convite de grupo inválido.")
    if invite.expires_at and invite.expires_at <= utcnow():
        raise AppError(400, "Convite de grupo expirado.")
    if invite.max_uses is not None and invite.uses >= invite.max_uses:
        raise AppError(400, "Convite de grupo esgotado.")
    existing = db.get(GroupMember, (invite.group_id, user.id))
    if existing is None:
        db.add(GroupMember(group_id=invite.group_id, user_id=user.id, joined_at=utcnow()))
    invite.uses += 1
    db.commit()
    group = db.get(Group, invite.group_id)
    assert group is not None
    return group


def list_group_invites(db: Session, user: User, group_id: int):
    from app.models import GroupInvite

    require_perm(db, group_id, user, Perm.MANAGE_GROUP)
    return list(
        db.scalars(
            select(GroupInvite)
            .where(GroupInvite.group_id == group_id)
            .order_by(GroupInvite.id.desc())
        ).all()
    )
