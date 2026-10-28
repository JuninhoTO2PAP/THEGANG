"""Upload de avatar e imagens do chat."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Request, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.limiter import limiter
from app.db.session import get_db
from app.models import User
from app.schemas.user import UserPublic
from app.services import upload_service
from app.utils.time import utcnow

router = APIRouter()


class ChatImagePublic(BaseModel):
    url: str
    mime: str


@router.post("/avatar", response_model=UserPublic)
@limiter.limit("10/minute")
async def upload_avatar(
    request: Request,
    file: Annotated[UploadFile, File(...)],
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Recebe foto do PC, valida e atualiza o perfil."""
    url = await upload_service.save_avatar(file, user.id)
    user.avatar_url = url
    user.last_seen = utcnow()
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/chat-image", response_model=ChatImagePublic)
@limiter.limit("30/minute")
async def upload_chat_image(
    request: Request,
    file: Annotated[UploadFile, File(...)],
    user: Annotated[User, Depends(get_current_user)],
) -> ChatImagePublic:
    url, mime = await upload_service.save_chat_image(file, user.id)
    return ChatImagePublic(url=url, mime=mime)