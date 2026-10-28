"""Web Push (VAPID) — inscrição e envio."""

from __future__ import annotations

import base64
import json
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import BASE_DIR, settings
from app.core.errors import AppError
from app.models import PushSubscription, User
from app.utils.time import utcnow

logger = logging.getLogger(__name__)
_VAPID_FILE = BASE_DIR / ".vapid.json"


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _ensure_vapid_keys() -> tuple[str, str]:
    if settings.vapid_public_key and settings.vapid_private_key:
        return settings.vapid_public_key, settings.vapid_private_key
    if _VAPID_FILE.exists():
        data = json.loads(_VAPID_FILE.read_text(encoding="utf-8"))
        settings.vapid_public_key = data["public_key"]
        settings.vapid_private_key = data["private_key"]
        return data["public_key"], data["private_key"]

    from cryptography.hazmat.primitives.asymmetric import ec

    private_key = ec.generate_private_key(ec.SECP256R1())
    private_num = private_key.private_numbers().private_value
    public_bytes = private_key.public_key().public_bytes(
        encoding=__import__(
            "cryptography.hazmat.primitives.serialization", fromlist=["Encoding"]
        ).Encoding.X962,
        format=__import__(
            "cryptography.hazmat.primitives.serialization", fromlist=["PublicFormat"]
        ).PublicFormat.UncompressedPoint,
    )
    public_b64 = _b64url(public_bytes)
    private_b64 = _b64url(private_num.to_bytes(32, "big"))
    _VAPID_FILE.write_text(
        json.dumps({"public_key": public_b64, "private_key": private_b64}),
        encoding="utf-8",
    )
    settings.vapid_public_key = public_b64
    settings.vapid_private_key = private_b64
    return public_b64, private_b64


def get_vapid_public_key() -> str:
    public, _ = _ensure_vapid_keys()
    return public


def subscribe(db: Session, user: User, endpoint: str, keys: dict) -> PushSubscription:
    if not endpoint or not keys.get("p256dh") or not keys.get("auth"):
        raise AppError(400, "Inscrição push inválida.")
    existing = db.scalar(select(PushSubscription).where(PushSubscription.endpoint == endpoint))
    payload = json.dumps(keys)
    if existing is not None:
        existing.user_id = user.id
        existing.keys_json = payload
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing
    row = PushSubscription(
        user_id=user.id,
        endpoint=endpoint,
        keys_json=payload,
        created_at=utcnow(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def unsubscribe(db: Session, user: User, endpoint: str) -> None:
    row = db.scalar(
        select(PushSubscription).where(
            PushSubscription.endpoint == endpoint, PushSubscription.user_id == user.id
        )
    )
    if row is not None:
        db.delete(row)
        db.commit()


def send_to_user(db: Session, user_id: int, title: str, body: str, data: dict | None = None) -> int:
    try:
        public, private = _ensure_vapid_keys()
    except Exception:
        return 0
    try:
        from pywebpush import WebPushException, webpush
    except ImportError:
        logger.warning("pywebpush não instalado; push ignorado.")
        return 0

    rows = list(
        db.scalars(select(PushSubscription).where(PushSubscription.user_id == user_id)).all()
    )
    sent = 0
    dead: list[PushSubscription] = []
    payload = json.dumps(
        {"title": title, "body": body, "data": data or {}},
        ensure_ascii=False,
    )
    for row in rows:
        keys = json.loads(row.keys_json)
        subscription_info = {
            "endpoint": row.endpoint,
            "keys": {"p256dh": keys["p256dh"], "auth": keys["auth"]},
        }
        try:
            webpush(
                subscription_info=subscription_info,
                data=payload,
                vapid_private_key=private,
                vapid_claims={"sub": settings.vapid_contact},
            )
            sent += 1
        except WebPushException as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status in {404, 410}:
                dead.append(row)
            else:
                logger.warning("push falhou user=%s: %s", user_id, exc)
        except Exception as exc:
            logger.warning("push erro user=%s: %s", user_id, exc)
    for row in dead:
        db.delete(row)
    if dead:
        db.commit()
    return sent


def notify_users(
    db: Session,
    user_ids: list[int],
    *,
    title: str,
    body: str,
    data: dict | None = None,
    skip_user: int | None = None,
) -> None:
    for uid in set(user_ids):
        if skip_user is not None and uid == skip_user:
            continue
        user = db.get(User, uid)
        if user is None or user.presence == "dnd":
            continue
        send_to_user(db, uid, title, body, data)
