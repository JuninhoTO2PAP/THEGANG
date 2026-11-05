"""Perfil do membro logado."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.errors import AppError
from app.core.security import hash_password, verify_password
from app.db.session import get_db
from app.models import User
from app.schemas.user import AccentUpdate, PasswordChange, StatusUpdate, UserPublic, UserUpdate
from app.services.ws_hub import hub
from app.utils.time import utcnow

router = APIRouter()


@router.get("/me", response_model=UserPublic)
def get_me(user: Annotated[User, Depends(get_current_user)]) -> User:
    return user


@router.patch("/me", response_model=UserPublic)
def update_me(
    body: UserUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Atualiza apelido e @usuário. Avatar sobe em /api/uploads/avatar."""
    if body.username != user.username:
        taken = db.scalar(
            select(User.id).where(User.username == body.username, User.id != user.id)
        )
        if taken is not None:
            raise AppError(409, "Esse @usuário já está em uso.")
        user.username = body.username

    user.nickname = body.nickname
    if "ff_id" in body.model_fields_set:
        user.ff_id = body.ff_id
    if "ff_nick" in body.model_fields_set:
        user.ff_nick = body.ff_nick
    if "ff_role" in body.model_fields_set:
        user.ff_role = body.ff_role
    if "ff_region" in body.model_fields_set:
        user.ff_region = body.ff_region
    if body.banner_theme is not None:
        user.banner_theme = body.banner_theme
    user.last_seen = utcnow()
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.delete("/me/avatar", response_model=UserPublic)
def clear_avatar(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Remove a foto de perfil (o arquivo antigo pode ficar em disco)."""
    user.avatar_url = None
    user.last_seen = utcnow()
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/me/accent", response_model=UserPublic)
def update_accent(
    body: AccentUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Grava a cor de destaque na conta, para voltar igual em qualquer aparelho."""
    user.accent = body.accent
    user.last_seen = utcnow()
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/me/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    body: PasswordChange,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    if not verify_password(body.current_password, user.hashed_password):
        raise AppError(400, "Senha atual incorreta.")
    if body.current_password == body.new_password:
        raise AppError(400, "A nova senha deve ser diferente da atual.")
    user.hashed_password = hash_password(body.new_password)
    user.last_seen = utcnow()
    db.add(user)
    db.commit()


@router.patch("/me/status", response_model=UserPublic)
async def update_status(
    body: StatusUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    user.presence = body.presence
    user.status_text = body.status_text
    user.is_online = body.presence != "invisible"
    user.last_seen = utcnow()
    db.add(user)
    db.commit()
    db.refresh(user)
    await hub.broadcast_status(
        user.id,
        presence=user.presence,
        status_text=user.status_text,
        is_online=user.is_online,
    )
    return user
