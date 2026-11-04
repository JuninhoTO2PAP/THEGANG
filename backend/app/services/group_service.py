"""Grupos, canais internos, cargos e permissões."""

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.errors import AppError
from app.core.permissions import ADMIN_PERMS, MEMBER_PERMS, Perm, has_perm
from app.models import (
    Channel,
    Group,
    GroupInvite,
    GroupMember,
    MemberRole,
    Message,
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


DEFAULT_GROUP_NAME = "the-gang"
DEFAULT_GROUP_DESCRIPTION = "Grupo principal do THE GANG — entre pelo convite do admin."


def ensure_default_group(db: Session, owner: User | None = None) -> Group:
    """Garante o grupo público padrão onde novos membros entram no cadastro."""
    existing = db.scalar(select(Group).where(Group.name == DEFAULT_GROUP_NAME))
    if existing is not None:
        if existing.is_private:
            existing.is_private = False
            db.add(existing)
            db.flush()
        return existing

    creator = owner if owner is not None and owner.is_admin else None
    if creator is None:
        creator = db.scalar(select(User).where(User.is_admin.is_(True)).order_by(User.id))
    if creator is None:
        raise AppError(500, "Não há administrador para criar o grupo padrão.")

    group, _ = create_group(
        db,
        creator,
        GroupCreate(
            name=DEFAULT_GROUP_NAME,
            description=DEFAULT_GROUP_DESCRIPTION,
            is_private=False,
        ),
    )
    return group


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
    db.add_all([everyone, admin_role])
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
    if group.name == DEFAULT_GROUP_NAME:
        raise AppError(400, "O grupo padrão THE GANG não pode ser apagado.")
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
    """No cadastro, entra em todos os grupos públicos com cargo padrão."""
    now = utcnow()
    publics = db.scalars(select(Group).where(Group.is_private.is_(False))).all()
    for group in publics:
        exists = db.get(GroupMember, (group.id, user.id))
        if exists is None:
            db.add(GroupMember(group_id=group.id, user_id=user.id, joined_at=now))


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
