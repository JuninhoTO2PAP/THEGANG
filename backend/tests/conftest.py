"""Ambiente de teste isolado. As variáveis entram antes de importar o app."""

import os

os.environ["ENVIRONMENT"] = "test"
os.environ["SECRET_KEY"] = "test-secret-key-the-gang-etapa1-ok"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["CORS_ORIGINS"] = "http://localhost:5173"
os.environ["BCRYPT_ROUNDS"] = "12"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "15"
os.environ["REFRESH_TOKEN_EXPIRE_DAYS"] = "7"

import pytest  # noqa: E402
from app.core.limiter import limiter  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.seed import run_seed  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture(autouse=True)
def database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    limiter.reset()
    yield
    limiter.reset()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(database):  # noqa: ARG001 — fixture garante o schema
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def seeded(database):  # noqa: ARG001
    """Aplica o seed e fecha a sessão antes do teste chamar a API."""
    session = SessionLocal()
    try:
        run_seed(session)
    finally:
        session.close()
