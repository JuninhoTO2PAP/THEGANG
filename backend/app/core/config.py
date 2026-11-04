"""Configuração lida do ambiente. Nenhum segredo fica no código."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, ValidationError, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ (pais: core -> app -> backend)
BASE_DIR = Path(__file__).resolve().parents[2]


def normalize_database_url(url: str) -> str:
    """Resolve SQLite relativo e adapta URL do Render/Railway (postgres://)."""
    url = (url or "").strip().strip('"').strip("'")
    lower = url.lower()

    # Render/Heroku entregam postgres:// ou postgresql:// (driver padrão = psycopg2).
    # Este projeto usa psycopg v3 → sqlalchemy precisa de postgresql+psycopg://
    for prefix in ("postgres://", "postgresql://"):
        if lower.startswith(prefix) and "+psycopg" not in lower.split("://", 1)[0]:
            url = "postgresql+psycopg://" + url[len(prefix) :]
            break

    # TLS só na URL externa do Render (host *.render.com). Interna não precisa.
    host_part = url.split("@")[-1].lower() if "@" in url else ""
    if (
        url.startswith("postgresql+psycopg://")
        and "sslmode=" not in url.lower()
        and "render.com" in host_part
    ):
        url = url + ("&" if "?" in url else "?") + "sslmode=require"

    prefix = "sqlite:///./"
    if url.startswith(prefix):
        relative = url[len(prefix) :]
        path = (BASE_DIR / relative).resolve()
        return "sqlite:///" + path.as_posix()
    return url


class Settings(BaseSettings):
    """Variáveis de ambiente da API."""

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "THE GANG"
    app_version: str = "0.1.0"
    environment: Literal["development", "test", "production", "staging"] = "development"
    allow_sqlite: bool = False

    secret_key: str = Field(min_length=16)
    jwt_algorithm: Literal["HS256"] = "HS256"
    access_token_expire_minutes: int = Field(default=15, ge=5, le=60)
    refresh_token_expire_days: int = Field(default=7, ge=1, le=30)
    bcrypt_rounds: int = Field(default=12, ge=12, le=16)

    database_url: str = "sqlite:///./thegang.db"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    uploads_dir: str = ""

    livekit_url: str = ""
    livekit_api_key: str = ""
    livekit_api_secret: str = ""

    vapid_public_key: str = ""
    vapid_private_key: str = ""
    vapid_contact: str = "mailto:admin@example.com"

    @field_validator("database_url")
    @classmethod
    def _normalize_database_url(cls, value: str) -> str:
        return normalize_database_url(value)

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @model_validator(mode="after")
    def _finalize(self) -> "Settings":
        if not self.uploads_dir:
            self.uploads_dir = str((BASE_DIR / "uploads").resolve())
        if self.environment == "production":
            self._check_production()
        return self

    def _check_production(self) -> None:
        """Produção não sobe com segredo de exemplo, SQLite ou HTTP."""
        weak = self.secret_key.startswith("sua_chave") or "troque" in self.secret_key
        if weak or len(self.secret_key) < 32:
            raise ValueError("Em produção, SECRET_KEY precisa ser longa e exclusiva.")
        if self.database_url.startswith("sqlite") and not self.allow_sqlite:
            raise ValueError(
                "Em produção, DATABASE_URL deve ser PostgreSQL "
                "(ou defina ALLOW_SQLITE=true para staging/tunnel)."
            )
        if not self.cors_origin_list:
            raise ValueError("Em produção, defina CORS_ORIGINS.")
        if any(origin.startswith("http://") for origin in self.cors_origin_list):
            raise ValueError("Em produção, CORS_ORIGINS deve usar HTTPS.")


@lru_cache
def get_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as exc:
        raise RuntimeError(
            "Configuração inválida. Copie backend/.env.example para backend/.env "
            "e defina SECRET_KEY."
        ) from exc


settings = get_settings()
