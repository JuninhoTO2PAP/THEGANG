"""Atalhos usados pelos testes. Não configura ambiente."""

from app.models import User
from sqlalchemy import select
from sqlalchemy.orm import Session


def user_by_name(session: Session, username: str) -> User:
    user = session.scalar(select(User).where(User.username == username))
    assert user is not None
    return user
