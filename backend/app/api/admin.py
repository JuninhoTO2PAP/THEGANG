"""Painel do administrador do app. Membros comuns recebem 403."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_admin
from app.db.session import get_db
from app.models import User
from app.schemas.admin import AdminMember, AdminPasswordReset
from app.services import admin_service

router = APIRouter()


@router.get("/members", response_model=list[AdminMember])
def list_members(
    _admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> list[AdminMember]:
    """Contas do time: login, função, ID e quem está online."""
    return admin_service.list_members(db)


@router.post("/members/{user_id}/password", status_code=status.HTTP_204_NO_CONTENT)
def reset_member_password(
    user_id: int,
    body: AdminPasswordReset,
    _admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Define uma senha nova quando a pessoa perdeu a antiga. A senha velha não é revelada."""
    admin_service.reset_password(db, user_id, body.new_password)


@router.delete("/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_member(
    user_id: int,
    admin: Annotated[User, Depends(get_current_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Apaga a conta. O administrador não pode apagar a própria."""
    admin_service.delete_member(db, admin, user_id)
