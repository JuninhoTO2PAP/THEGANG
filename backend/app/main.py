"""Ponto de entrada da API THE GANG."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.errors import AppError
from app.core.limiter import limiter


@asynccontextmanager
async def lifespan(_app: FastAPI):
    uploads = Path(settings.uploads_dir)
    uploads.mkdir(parents=True, exist_ok=True)
    (uploads / "avatars").mkdir(parents=True, exist_ok=True)
    (uploads / "chat").mkdir(parents=True, exist_ok=True)
    # Garante THE GANG A/B + CPT no boot (dono do app nos dois).
    try:
        from sqlalchemy import select

        from app.db.session import SessionLocal
        from app.models import User
        from app.services.group_service import ensure_team_groups

        db = SessionLocal()
        try:
            admin = db.scalar(select(User).where(User.is_admin.is_(True)).order_by(User.id))
            if admin is not None:
                ensure_team_groups(db, owner=admin)
        finally:
            db.close()
    except Exception:
        pass
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    summary="API privada do time THE GANG",
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Fotos e anexos ficam em disco local (plano S3 depois).
app.mount("/uploads", StaticFiles(directory=settings.uploads_dir), name="uploads")


@app.exception_handler(AppError)
def handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(RateLimitExceeded)
def handle_rate_limit(_request: Request, _exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"detail": "Muitas tentativas. Espere um minuto e tente de novo."},
    )


@app.get("/", tags=["meta"])
def root() -> dict:
    return {
        "app": settings.app_name,
        "docs": "/docs",
        "health": "/api/health",
    }


@app.get("/api/health", tags=["meta"])
def health() -> dict:
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "stage": "etapa-1-auth",
    }


app.include_router(api_router, prefix="/api")
