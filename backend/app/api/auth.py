"""Cadastro, login e convites."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_admin, get_current_user
from app.core.limiter import limiter
from app.db.session import get_db
from app.models import User
from app.schemas.auth import (
    AuthResponse,
    InviteCreate,
    InvitePublic,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
)
from app.schemas.user import UserPublic
from app.services import auth_service

router = APIRouter()


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def register(
    request: Request,
    body: RegisterRequest,
    db: Annotated[Session, Depends(get_db)],
) -> AuthResponse:
    """Cria a conta se o convite ainda estiver aberto e devolve a sessão."""
    user, tokens = auth_service.register_user(db, body)
    return AuthResponse(user=UserPublic.model_validate(user), tokens=tokens)


@router.post("/login", response_model=AuthResponse)
@limiter.limit("5/minute")
def login(
    request: Request,
    body: LoginRequest,
    db: Annotated[Session, Depends(get_db)],
) -> AuthResponse:
    """Entra com e-mail ou nome de usuário. Limitado a 5 tentativas por minuto."""
    user, tokens = auth_service.login_user(db, body)
    return AuthResponse(user=UserPublic.model_validate(user), tokens=tokens)


@router.post("/refresh", response_model=AuthResponse)
@limiter.limit("30/minute")
def refresh(
    request: Request,
    body: RefreshRequest,
    db: Annotated[Session, Depends(get_db)],
) -> AuthResponse:
    """Gira o refresh token. O token antigo deixa de valer."""
    user, tokens = auth_service.refresh_session(db, body.refresh_token)
    return AuthResponse(user=UserPublic.model_validate(user), tokens=tokens)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(body: LogoutRequest, db: Annotated[Session, Depends(get_db)]) -> None:
    """Revoga o refresh token. O access token curto continua até expirar."""
    auth_service.logout_user(db, body.refresh_token)


@router.get("/me", response_model=UserPublic)
def me(user: Annotated[User, Depends(get_current_user)]) -> User:
    """Quem está autenticado neste access token."""
    return user


@router.post("/invites", response_model=InvitePublic, status_code=status.HTTP_201_CREATED)
def create_invite(
    body: InviteCreate,
    admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> InvitePublic:
    """Gera um código de uso único. Só administrador."""
    invite = auth_service.create_invite(db, admin, body)
    return InvitePublic.model_validate(invite)


@router.get("/invites", response_model=list[InvitePublic])
def get_invites(
    _admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> list[InvitePublic]:
    """Lista convites do time, inclusive os já usados."""
    return [InvitePublic.model_validate(item) for item in auth_service.list_invites(db)]


@router.delete("/invites/{invite_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_invite(
    invite_id: int,
    _admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Apaga um convite, usado ou não. Só administrador."""
    auth_service.delete_invite(db, invite_id)
