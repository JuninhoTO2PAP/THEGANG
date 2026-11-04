"""Dados iniciais: admin juninho + grupo padrão THE GANG.

Uso:

    python -m app.db.seed
    python -m app.db.reset
"""

import os
import sys

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.session import SessionLocal, engine
from app.models import User
from app.services.home_service import ensure_home
from app.utils.time import utcnow

ADMIN_USERNAME = "juninho"
ADMIN_EMAIL = "juninho@example.com"
ADMIN_NICKNAME = "Juninho"
ADMIN_PASSWORD = "paraiba123"


def run_seed(db: Session) -> bool:
    """Cria o juninho (se preciso) e garante o grupo padrão. Devolve True se criou o admin."""
    created = False
    existing = db.scalar(select(User).where(User.username == ADMIN_USERNAME))
    if existing is None:
        now = utcnow()
        existing = User(
            username=ADMIN_USERNAME,
            email=ADMIN_EMAIL,
            hashed_password=hash_password(ADMIN_PASSWORD),
            nickname=ADMIN_NICKNAME,
            avatar_url=None,
            is_admin=True,
            is_online=False,
            last_seen=now,
            created_at=now,
        )
        db.add(existing)
        db.commit()
        db.refresh(existing)
        created = True

    from app.services.group_service import ensure_team_groups

    ensure_team_groups(db, owner=existing)
    ensure_home(db)
    return created


def main() -> None:
    from app.core.config import settings

    # Em produção só com SEED_ON_BOOT=1 (primeiro deploy Railway).
    if settings.environment == "production" and os.getenv("SEED_ON_BOOT", "").strip() != "1":
        raise SystemExit(
            "O seed de demonstração não roda com ENVIRONMENT=production "
            "(use SEED_ON_BOOT=1 no primeiro boot)."
        )
    if not inspect(engine).has_table("users"):
        raise SystemExit("Banco sem tabelas. Rode antes: alembic upgrade head")

    db = SessionLocal()
    try:
        created = run_seed(db)
    finally:
        db.close()

    if created:
        print("Seed aplicado.")
        print(f"Admin: {ADMIN_USERNAME} / {ADMIN_PASSWORD}")
        print("Grupo padrão: the-gang (público).")
    else:
        print(f"Admin {ADMIN_USERNAME} já existia. Grupo padrão garantido.")


if __name__ == "__main__":
    sys.exit(main())
