"""API de grupos Discord-like: canais, cargos e membros."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas.group import (
    ChannelCreate,
    ChannelPublic,
    GroupCreate,
    GroupInviteCreate,
    GroupInvitePublic,
    GroupJoinRequest,
    GroupPublic,
    GroupUpdate,
    MemberPublic,
    MemberRolesUpdate,
    RoleCreate,
    RolePublic,
    RoleUpdate,
    TeamTransferRequest,
)
from app.services import group_service

router = APIRouter()


def _invite_public(invite) -> GroupInvitePublic:
    return GroupInvitePublic(
        id=invite.id,
        group_id=invite.group_id,
        code=invite.code,
        created_by=invite.created_by,
        max_uses=invite.max_uses,
        uses=invite.uses,
        expires_at=invite.expires_at,
        created_at=invite.created_at,
        link_path=f"/join/{invite.code}",
    )


def _group_public(group, perms: int) -> GroupPublic:
    return GroupPublic(
        id=group.id,
        name=group.name,
        display_name=group_service.team_label(group.name),
        description=group.description,
        icon_url=group.icon_url,
        is_private=group.is_private,
        created_by=group.created_by,
        created_at=group.created_at,
        my_permissions=perms,
    )


@router.get("", response_model=list[GroupPublic])
def list_groups(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[GroupPublic]:
    if user.is_admin:
        group_service.ensure_team_groups(db, owner=user)
    return [_group_public(g, p) for g, p in group_service.list_groups_for_user(db, user)]


@router.post("", response_model=GroupPublic, status_code=status.HTTP_201_CREATED)
def create_group(
    body: GroupCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GroupPublic:
    group, perms = group_service.create_group(db, user, body)
    return _group_public(group, perms)


@router.post("/join", response_model=GroupPublic)
def join_group(
    body: GroupJoinRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GroupPublic:
    group = group_service.join_group_by_code(db, user, body.code)
    perms = group_service._member_permissions(db, group.id, user.id)
    return _group_public(group, perms)


@router.post("/transfer-team")
def transfer_team(
    body: TeamTransferRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    """Sobe/desce membro entre THE GANG A e THE GANG B (só dono do app)."""
    return group_service.transfer_member_team(
        db, user, target_user_id=body.user_id, to_team=body.to_team
    )


@router.patch("/{group_id}", response_model=GroupPublic)
def update_group(
    group_id: int,
    body: GroupUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GroupPublic:
    group = group_service.update_group(db, user, group_id, body)
    perms = group_service._member_permissions(db, group.id, user.id)
    return _group_public(group, perms)


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_group(
    group_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    group_service.delete_group(db, user, group_id)


@router.get("/{group_id}/channels", response_model=list[ChannelPublic])
def list_channels(
    group_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[ChannelPublic]:
    return [
        ChannelPublic.model_validate(c)
        for c in group_service.list_channels(db, user, group_id)
    ]


@router.post(
    "/{group_id}/channels",
    response_model=ChannelPublic,
    status_code=status.HTTP_201_CREATED,
)
def create_channel(
    group_id: int,
    body: ChannelCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ChannelPublic:
    return ChannelPublic.model_validate(group_service.create_channel(db, user, group_id, body))


@router.get("/{group_id}/roles", response_model=list[RolePublic])
def list_roles(
    group_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[RolePublic]:
    return [RolePublic.model_validate(r) for r in group_service.list_roles(db, user, group_id)]


@router.post(
    "/{group_id}/roles",
    response_model=RolePublic,
    status_code=status.HTTP_201_CREATED,
)
def create_role(
    group_id: int,
    body: RoleCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> RolePublic:
    return RolePublic.model_validate(group_service.create_role(db, user, group_id, body))


@router.patch("/{group_id}/roles/{role_id}", response_model=RolePublic)
def update_role(
    group_id: int,
    role_id: int,
    body: RoleUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> RolePublic:
    return RolePublic.model_validate(
        group_service.update_role(db, user, group_id, role_id, body)
    )


@router.delete("/{group_id}/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role(
    group_id: int,
    role_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    group_service.delete_role(db, user, group_id, role_id)


@router.get("/{group_id}/members", response_model=list[MemberPublic])
def list_members(
    group_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[MemberPublic]:
    return [MemberPublic.model_validate(m) for m in group_service.list_members(db, user, group_id)]


@router.put("/{group_id}/members/{user_id}/roles", response_model=MemberPublic)
def set_roles(
    group_id: int,
    user_id: int,
    body: MemberRolesUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> MemberPublic:
    return MemberPublic.model_validate(
        group_service.set_member_roles(db, user, group_id, user_id, body.role_ids)
    )


@router.post(
    "/{group_id}/invites",
    response_model=GroupInvitePublic,
    status_code=status.HTTP_201_CREATED,
)
def create_group_invite(
    group_id: int,
    body: GroupInviteCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GroupInvitePublic:
    invite = group_service.create_group_invite(
        db,
        user,
        group_id,
        expires_in_days=body.expires_in_days,
        max_uses=body.max_uses,
    )
    return _invite_public(invite)


@router.get("/{group_id}/invites", response_model=list[GroupInvitePublic])
def list_group_invites(
    group_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[GroupInvitePublic]:
    return [_invite_public(i) for i in group_service.list_group_invites(db, user, group_id)]
