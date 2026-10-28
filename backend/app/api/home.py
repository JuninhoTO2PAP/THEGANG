"""Home THE GANG."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas.home import HomePublic, HomeUpdate
from app.services import home_service

router = APIRouter()


@router.get("", response_model=HomePublic)
def get_home(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> HomePublic:
    row, online = home_service.get_home(db)
    return HomePublic(
        banner_title=row.banner_title,
        banner_subtitle=row.banner_subtitle,
        admin_note=row.admin_note,
        next_event_title=row.next_event_title,
        next_event_at=row.next_event_at,
        updated_at=row.updated_at,
        online=online,
    )


@router.patch("", response_model=HomePublic)
def patch_home(
    body: HomeUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> HomePublic:
    row = home_service.update_home(db, user, body)
    _, online = home_service.get_home(db)
    return HomePublic(
        banner_title=row.banner_title,
        banner_subtitle=row.banner_subtitle,
        admin_note=row.admin_note,
        next_event_title=row.next_event_title,
        next_event_at=row.next_event_at,
        updated_at=row.updated_at,
        online=online,
    )
