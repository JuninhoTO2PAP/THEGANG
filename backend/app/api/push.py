"""Web Push — inscrição e chave pública VAPID."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import User
from app.services import push_service

router = APIRouter()


class PushKeys(BaseModel):
    p256dh: str
    auth: str


class PushSubscribeRequest(BaseModel):
    endpoint: str = Field(min_length=8)
    keys: PushKeys


class PushUnsubscribeRequest(BaseModel):
    endpoint: str = Field(min_length=8)


class VapidPublic(BaseModel):
    public_key: str


@router.get("/vapid-public-key", response_model=VapidPublic)
def vapid_public_key() -> VapidPublic:
    return VapidPublic(public_key=push_service.get_vapid_public_key())


@router.post("/subscribe", status_code=status.HTTP_204_NO_CONTENT)
def subscribe(
    body: PushSubscribeRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    push_service.subscribe(db, user, body.endpoint, body.keys.model_dump())


@router.delete("/subscribe", status_code=status.HTTP_204_NO_CONTENT)
def unsubscribe(
    body: PushUnsubscribeRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    push_service.unsubscribe(db, user, body.endpoint)
