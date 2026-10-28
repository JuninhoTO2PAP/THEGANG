"""Apaga todos os dados e deixa só o admin juninho.

Uso (a partir de backend/):

    python -m app.db.reset
"""

from sqlalchemy import text

import app.models  # noqa: F401
from app.core.config import settings
from app.db.base import Base
from app.db.seed import ADMIN_PASSWORD, ADMIN_USERNAME, run_seed
from app.db.session import SessionLocal, engine


def wipe_all() -> None:
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
        if settings.database_url.startswith("sqlite"):
            exists = conn.execute(
                text(
                    "SELECT 1 FROM sqlite_master "
                    "WHERE type='table' AND name='sqlite_sequence'"
                )
            ).scalar()
            if exists:
                conn.execute(text("DELETE FROM sqlite_sequence"))


def main() -> None:
    if settings.environment == "production":
        raise SystemExit("Reset não roda em produção.")

    wipe_all()
    db = SessionLocal()
    try:
        created = run_seed(db)
    finally:
        db.close()

    if not created:
        raise SystemExit("Falha: seed não criou o admin após o wipe.")
    print("Banco limpo.")
    print(f"Única conta: {ADMIN_USERNAME} / {ADMIN_PASSWORD} (admin)")
    print("Crie grupos no app. Cargos Admin/membro vêm junto.")


if __name__ == "__main__":
    main()
