"""Relógio da aplicação. Tudo em UTC."""

from datetime import datetime, timezone


def utcnow() -> datetime:
    """Retorna o instante atual com fuso UTC."""
    return datetime.now(timezone.utc)
