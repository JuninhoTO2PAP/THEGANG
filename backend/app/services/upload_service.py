"""Upload de avatar e imagens do chat com validação de MIME."""

import re
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings
from app.core.errors import AppError

MAX_IMAGE_BYTES = 5 * 1024 * 1024
ALLOWED = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def _detect_mime(header: bytes) -> str | None:
    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if header.startswith(b"RIFF") and b"WEBP" in header[:16]:
        return "image/webp"
    return None


def _subdir(name: str) -> Path:
    path = Path(settings.uploads_dir) / name
    path.mkdir(parents=True, exist_ok=True)
    return path


async def _save_image(file: UploadFile, user_id: int, folder: str, prefix: str) -> tuple[str, str]:
    if not file.filename:
        raise AppError(400, "Arquivo sem nome.")
    raw = await file.read()
    if not raw:
        raise AppError(400, "Arquivo vazio.")
    if len(raw) > MAX_IMAGE_BYTES:
        raise AppError(400, "Imagem deve ter no máximo 5MB.")
    mime = _detect_mime(raw[:32])
    if mime is None or mime not in ALLOWED:
        raise AppError(400, "Use JPG, PNG ou WEBP.")
    ext = ALLOWED[mime]
    safe_stem = re.sub(r"[^a-zA-Z0-9_-]+", "", Path(file.filename).stem)[:24] or prefix
    filename = f"u{user_id}_{safe_stem}_{uuid.uuid4().hex[:10]}{ext}"
    destination = _subdir(folder) / filename
    if not destination.resolve().is_relative_to(_subdir(folder).resolve()):
        raise AppError(400, "Nome de arquivo inválido.")
    destination.write_bytes(raw)
    return f"/uploads/{folder}/{filename}", mime


async def save_avatar(file: UploadFile, user_id: int) -> str:
    url, _ = await _save_image(file, user_id, "avatars", "avatar")
    return url


async def save_chat_image(file: UploadFile, user_id: int) -> tuple[str, str]:
    return await _save_image(file, user_id, "chat", "img")
