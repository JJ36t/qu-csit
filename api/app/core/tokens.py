"""JWT issue + verify. Access 15 min, Refresh 30 days."""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from app.core.config import settings


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(
    user_id: str | uuid.UUID,
    role: str,
    extra: dict[str, Any] | None = None,
) -> str:
    now = _now()
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.access_token_ttl_min)).timestamp()),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_alg)


def create_refresh_token(user_id: str | uuid.UUID, device_id: str | uuid.UUID | None = None) -> tuple[str, str, datetime]:
    """Returns (raw_token, token_hash, expires_at). Caller stores the hash."""
    now = _now()
    expires_at = now + timedelta(days=settings.refresh_token_ttl_days)
    payload = {
        "sub": str(user_id),
        "device": str(device_id) if device_id else None,
        "type": "refresh",
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_alg)
    return token, hash_token(token), expires_at


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_alg])
