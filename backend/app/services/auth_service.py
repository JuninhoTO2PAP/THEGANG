"""Cadastro por convite, sessão JWT e códigos de admin."""

import secrets
from datetime import timedelta

import jwt
from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_against_user_or_dummy,
)
from app.models import InviteCode, RefreshToken, User
from app.schemas.auth import InviteCreate, LoginRequest, RegisterRequest, TokenPair
from app.services.group_service import add_user_to_public_groups, ensure_default_group
from app.utils.time import utcnow

_INVITE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _password_bytes_ok(password: str) -> None:
    if len(password.encode("utf-8")) > 72:
        raise AppError(401, "Usuário ou senha incorretos.")


def _find_user(db: Session, login: str) -> User | None:
    """E-mail se houver @; caso contrário, nome de usuário. Ambos sem diferenciar maiúsculas."""
    normalized = login.strip().lower()
    if "@" in normalized:
        return db.scalar(select(User).where(User.email == normalized))
    return db.scalar(select(User).where(User.username == normalized))


def _invite_is_open(invite: InviteCode | None) -> bool:
    """Convite some da mesma forma se não existe, já foi usado ou venceu."""
    if invite is None or invite.used_by is not None:
        return False
    if invite.expires_at is not None and invite.expires_at <= utcnow():
        return False
    return True


def issue_tokens(db: Session, user: User) -> TokenPair:
    """Grava um refresh novo e devolve o par. Quem chama dá o commit."""
    refresh, jti = create_refresh_token(user.id)
    now = utcnow()
    db.add(
        RefreshToken(
            user_id=user.id,
            jti=jti,
            revoked=False,
            expires_at=now + timedelta(days=settings.refresh_token_expire_days),
            created_at=now,
        )
    )
    db.flush()
    return TokenPair(
        access_token=create_access_token(user.id),
        refresh_token=refresh,
        expires_in=settings.access_token_expire_minutes * 60,
    )


def register_user(db: Session, data: RegisterRequest) -> tuple[User, TokenPair]:
    """Consome o convite, cria o membro e já entra nos canais públicos."""
    invite = db.scalar(select(InviteCode).where(InviteCode.code == data.invite_code))
    if invite is None or not _invite_is_open(invite):
        raise AppError(400, "Convite inválido ou expirado.")

    username = data.username.lower()
    email = str(data.email).lower()
    taken = db.scalar(select(User.id).where(or_(User.username == username, User.email == email)))
    if taken is not None:
        raise AppError(409, "Usuário ou e-mail já cadastrado.")

    now = utcnow()
    user = User(
        username=username,
        email=email,
        hashed_password=hash_password(data.password),
        nickname=data.nickname,
        avatar_url=None,
        is_admin=False,
        is_online=False,
        last_seen=now,
        created_at=now,
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise AppError(409, "Usuário ou e-mail já cadastrado.") from exc

    invite.used_by = user.id
    invite.used_at = now
    ensure_default_group(db, owner=db.get(User, invite.created_by))
    add_user_to_public_groups(db, user)

    tokens = issue_tokens(db, user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AppError(409, "Usuário ou e-mail já cadastrado.") from exc
    db.refresh(user)
    return user, tokens


def login_user(db: Session, data: LoginRequest) -> tuple[User, TokenPair]:
    """Confere a senha. Se o login não existe, ainda assim roda o bcrypt.

    Isso evita responder mais rápido quando o nome está errado do que
    quando a senha está errada.
    """
    _password_bytes_ok(data.password)
    user = _find_user(db, data.login)
    hashed = user.hashed_password if user is not None else None
    if not verify_against_user_or_dummy(data.password, hashed) or user is None:
        raise AppError(401, "Usuário ou senha incorretos.")

    user.last_seen = utcnow()
    tokens = issue_tokens(db, user)
    db.commit()
    db.refresh(user)
    return user, tokens


def _revoke_all(db: Session, user_id: int) -> None:
    db.execute(update(RefreshToken).where(RefreshToken.user_id == user_id).values(revoked=True))


def refresh_session(db: Session, refresh_token: str) -> tuple[User, TokenPair]:
    """Troca o refresh por um par novo. Reusar um refresh já gasto derruba as sessões."""
    payload = decode_token(refresh_token, expected_type="refresh")
    try:
        user_id = int(payload["sub"])
        jti = str(payload["jti"])
    except (KeyError, TypeError, ValueError) as exc:
        raise AppError(401, "Refresh token inválido.") from exc

    row = db.scalar(select(RefreshToken).where(RefreshToken.jti == jti))
    if row is None or row.user_id != user_id:
        raise AppError(401, "Refresh token inválido.")

    # Alguém apresentou um refresh que já tinha sido rodado: trata como roubo
    # e invalida os outros aparelhos desse membro.
    if row.revoked:
        _revoke_all(db, user_id)
        db.commit()
        raise AppError(401, "Sessão invalidada. Entre de novo.")

    if row.expires_at <= utcnow():
        raise AppError(401, "Sessão expirada. Entre de novo.")

    user = db.get(User, user_id)
    if user is None:
        raise AppError(401, "Refresh token inválido.")

    row.revoked = True
    tokens = issue_tokens(db, user)
    db.commit()
    db.refresh(user)
    return user, tokens


def logout_user(db: Session, refresh_token: str) -> None:
    """Revoga o refresh apresentado. Access token segue válido até expirar (minutos)."""
    try:
        payload = jwt.decode(
            refresh_token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"verify_exp": False},
        )
    except jwt.PyJWTError:
        return
    if payload.get("type") != "refresh" or not payload.get("jti"):
        return
    row = db.scalar(select(RefreshToken).where(RefreshToken.jti == str(payload["jti"])))
    if row is not None and not row.revoked:
        row.revoked = True
        db.commit()


def create_invite(db: Session, admin: User, data: InviteCreate) -> InviteCode:
    now = utcnow()
    invite = InviteCode(
        code=_new_invite_code(db),
        created_by=admin.id,
        used_by=None,
        used_at=None,
        expires_at=(
            now + timedelta(days=data.expires_in_days)
            if data.expires_in_days is not None
            else None
        ),
        created_at=now,
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)
    return invite


def list_invites(db: Session) -> list[InviteCode]:
    return list(db.scalars(select(InviteCode).order_by(InviteCode.id.desc())).all())


def _new_invite_code(db: Session) -> str:
    for _ in range(5):
        body = "".join(secrets.choice(_INVITE_ALPHABET) for _ in range(8))
        code = f"GANG-{body}"
        exists = db.scalar(select(InviteCode.id).where(InviteCode.code == code))
        if exists is None:
            return code
    raise AppError(500, "Não foi possível gerar um convite. Tente de novo.")
