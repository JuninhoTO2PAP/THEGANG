"""Senha (bcrypt) e JWT (access curto + refresh com jti)."""

from datetime import timedelta
from uuid import uuid4

import jwt

from app.core.bcrypt_compat import ensure_bcrypt_compat
from app.core.config import settings
from app.core.errors import AppError
from app.utils.time import utcnow

_pwd_context = None
_dummy_hash: str | None = None


def get_pwd_context():
    """Contexto bcrypt com custo configurável (mínimo 12).

    O import do passlib fica aqui dentro para o ajuste de compatibilidade
    do bcrypt rodar antes da biblioteca ler a versão.
    """
    global _pwd_context
    if _pwd_context is None:
        ensure_bcrypt_compat()
        from passlib.context import CryptContext

        _pwd_context = CryptContext(
            schemes=["bcrypt"],
            deprecated="auto",
            bcrypt__rounds=settings.bcrypt_rounds,
        )
    return _pwd_context


def hash_password(password: str) -> str:
    return get_pwd_context().hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return get_pwd_context().verify(password, hashed)
    except Exception:
        return False


def _dummy_password_hash() -> str:
    """Hash fixo para gastar o mesmo tempo quando o usuário não existe."""
    global _dummy_hash
    if _dummy_hash is None:
        _dummy_hash = hash_password("senha-ficticia-the-gang")
    return _dummy_hash


def verify_against_user_or_dummy(password: str, hashed: str | None) -> bool:
    """Confere a senha. Sem hash de usuário, queima o tempo num hash fictício."""
    if hashed is None:
        verify_password(password, _dummy_password_hash())
        return False
    return verify_password(password, hashed)


def create_access_token(user_id: int) -> str:
    now = utcnow()
    payload = {
        "sub": str(user_id),
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: int, jti: str | None = None) -> tuple[str, str]:
    """Devolve (token, jti). O jti é o que gravamos para poder revogar."""
    now = utcnow()
    token_id = jti or str(uuid4())
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "jti": token_id,
        "iat": now,
        "exp": now + timedelta(days=settings.refresh_token_expire_days),
    }
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)
    return token, token_id


def decode_token(token: str, expected_type: str) -> dict:
    """Decodifica e exige o tipo (`access` ou `refresh`)."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise AppError(401, "Sessão expirada. Entre de novo.") from exc
    except jwt.PyJWTError as exc:
        raise AppError(401, "Token inválido.") from exc
    if payload.get("type") != expected_type:
        raise AppError(401, "Token inválido.")
    return payload
