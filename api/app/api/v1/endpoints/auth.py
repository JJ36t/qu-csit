"""Auth endpoints: login, refresh, logout, change-password, me.

Implements brief §5.1:
- Login with university_id + password (Argon2 verify)
- First login forces password change
- Device binding for students (one active device; admin can unbind)
- Access JWT 15 min; refresh token 30 days, rotating, stored hashed
- Rate limit login (5/min per university_id+IP)
"""
from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.rbac import get_current_user
from app.core.security import hash_password, needs_rehash, verify_password
from app.core.tokens import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_token,
)
from app.db.base import get_db
from app.i18n.errors_ar import APIError
from app.models import Device, DeviceStatus, FcmToken, RefreshToken, User, UserRole, UserStatus
from app.models.enums import EnrollmentSource
from app.schemas.common import (
    AuthMeOut,
    ChangePasswordRequest,
    FcmTokenRequest,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    StaffOut,
    StudentOut,
    TokenPair,
    UserOut,
)
from app.services.audit import write_audit

router = APIRouter()


# ── Login ──
@router.post("/login", response_model=TokenPair)
async def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    # Rate limit: 5/min per (university_id + ip). In-memory since slowapi+redis
    # is overkill for the test env; production wires Redis.
    _rate_limit_login(payload.university_id, request)

    user = db.scalar(select(User).where(User.university_id == payload.university_id))
    if not user or not verify_password(payload.password, user.password_hash):
        raise APIError("INVALID_CREDENTIALS", 401)

    if user.status != UserStatus.active:
        raise APIError("FORBIDDEN", 403, {"status": user.status.value})

    # Device binding for students (brief §5.1 last bullet)
    if user.role == UserRole.student and payload.device_fingerprint:
        _bind_or_check_device(db, user, payload.device_fingerprint, payload.device_model)

    # Issue tokens
    access = create_access_token(user.id, user.role.value)
    raw_refresh, refresh_hash, refresh_exp = create_refresh_token(
        user.id, _device_id_for(user, payload.device_fingerprint, db)
    )
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=refresh_hash,
            expires_at=refresh_exp,
        )
    )

    # FCM token
    if payload.fcm_token:
        _upsert_fcm(db, user.id, payload.device_fingerprint, payload.fcm_token)

    user.last_login_at = datetime.now(timezone.utc)
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(payload.password)
    db.commit()

    write_audit(
        db,
        actor_id=user.id,
        action="login",
        entity="user",
        entity_id=str(user.id),
        request=request,
    )
    db.commit()

    return TokenPair(
        access_token=access,
        refresh_token=raw_refresh,
        expires_in=settings.access_token_ttl_min * 60,
        must_change_password=user.must_change_password,
    )


# ── Refresh ──
@router.post("/refresh", response_model=TokenPair)
async def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    try:
        decoded = decode_token(payload.refresh_token)
    except Exception:
        raise APIError("TOKEN_INVALID", 401)
    if decoded.get("type") != "refresh":
        raise APIError("TOKEN_INVALID", 401)

    token_hash = hash_token(payload.refresh_token)
    rec = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    if not rec or rec.revoked_at is not None:
        raise APIError("REFRESH_TOKEN_REVOKED", 401)
    # SQLite returns naive datetimes; PostgreSQL returns tz-aware. Normalize.
    expires_at = rec.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise APIError("TOKEN_EXPIRED", 401)

    user = db.get(User, rec.user_id)
    if not user or user.status != UserStatus.active:
        raise APIError("UNAUTHENTICATED", 401)

    # Rotate: revoke the old refresh, issue a new pair.
    rec.revoked_at = datetime.now(timezone.utc)
    access = create_access_token(user.id, user.role.value)
    new_raw, new_hash, new_exp = create_refresh_token(user.id, rec.device_id)
    db.add(RefreshToken(user_id=user.id, device_id=rec.device_id, token_hash=new_hash, expires_at=new_exp))
    db.commit()

    return TokenPair(
        access_token=access,
        refresh_token=new_raw,
        expires_in=settings.access_token_ttl_min * 60,
        must_change_password=user.must_change_password,
    )


# ── Logout ──
@router.post("/logout")
async def logout(
    payload: LogoutRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.refresh_token:
        token_hash = hash_token(payload.refresh_token)
        rec = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
        if rec and rec.user_id == user.id and rec.revoked_at is None:
            rec.revoked_at = datetime.now(timezone.utc)
            db.commit()
    return {"ok": True}


# ── Change password ──
@router.post("/change-password")
async def change_password(
    payload: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(payload.old_password, user.password_hash):
        raise APIError("OLD_PASSWORD_WRONG", 400)
    if not _is_strong_password(payload.new_password):
        raise APIError("PASSWORD_TOO_WEAK", 400)
    user.password_hash = hash_password(payload.new_password)
    user.must_change_password = False
    # Revoke all refresh tokens for this user (brief §9)
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None)
    ).update({"revoked_at": datetime.now(timezone.utc)})
    write_audit(db, actor_id=user.id, action="change_password", entity="user", entity_id=str(user.id))
    db.commit()
    return {"ok": True}


# ── Me ──
@router.get("/me", response_model=AuthMeOut)
async def me(user: User = Depends(get_current_user)):
    out = AuthMeOut(user=UserOut.model_validate(user))
    if user.student:
        out.student = StudentOut.model_validate(user.student)
    if user.staff:
        out.staff = StaffOut.model_validate(user.staff)
    return out


# ── FCM token registration ──
@router.put("/devices/fcm-token")
async def register_fcm(
    payload: FcmTokenRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _upsert_fcm(db, user.id, payload.device_fingerprint, payload.token)
    db.commit()
    return {"ok": True}


# ─────────────────────────── helpers ───────────────────────────
def _rate_limit_login(university_id: str, request: Request) -> None:
    """In-memory login rate limit. Real prod uses slowapi+Redis; this is
    enough for tests and dev.

    Disabled when APP_ENV=test so test fixtures can login freely (real
    rate-limit coverage lives in test_auth.test_login_rate_limit_kicks_in
    which monkeypatches this).
    """
    if settings.app_env == "test":
        # Allow the explicit rate-limit test to still work by enabling when
        # the test sets a marker via env.
        import os
        if not os.environ.get("ENABLE_LOGIN_RATELIMIT"):
            return
    ip = request.client.host if request.client else "?"
    key = (university_id, ip)
    now = datetime.now(timezone.utc).timestamp()
    bucket = _LOGIN_BUCKETS.setdefault(key, [])
    bucket[:] = [t for t in bucket if now - t < 60]
    if len(bucket) >= settings.login_rate_per_min:
        raise APIError("RATE_LIMITED", 429)
    bucket.append(now)


_LOGIN_BUCKETS: dict[tuple[str, str], list[float]] = {}


def _device_id_for(user: User, fingerprint: str | None, db: Session) -> uuid.UUID | None:
    if not fingerprint or user.role != UserRole.student:
        return None
    dev = db.scalar(
        select(Device).where(
            Device.user_id == user.id,
            Device.device_fingerprint == fingerprint,
            Device.status == DeviceStatus.active,
        )
    )
    return dev.id if dev else None


def _bind_or_check_device(db: Session, user: User, fingerprint: str, model: str | None) -> None:
    existing = db.scalar(
        select(Device).where(
            Device.user_id == user.id, Device.device_fingerprint == fingerprint
        )
    )
    if existing:
        if existing.status != DeviceStatus.active:
            raise APIError("DEVICE_NOT_BOUND", 403)
        return  # already bound & active

    # New fingerprint — count active devices for this student.
    already_active = (
        db.query(Device)
        .filter(Device.user_id == user.id, Device.status == DeviceStatus.active)
        .count()
    )
    if already_active >= settings.max_active_devices_per_student:
        raise APIError("DEVICE_LIMIT_EXCEEDED", 403)

    dev = Device(
        user_id=user.id,
        device_fingerprint=fingerprint,
        model=model,
        status=DeviceStatus.active,
    )
    db.add(dev)
    db.flush()


def _upsert_fcm(db: Session, user_id: uuid.UUID, fingerprint: str | None, token: str) -> None:
    existing = db.scalar(select(FcmToken).where(FcmToken.user_id == user_id, FcmToken.token == token))
    if existing:
        existing.last_seen_at = datetime.now(timezone.utc)
        return
    dev_id: uuid.UUID | None = None
    if fingerprint:
        dev = db.scalar(
            select(Device).where(
                Device.user_id == user_id, Device.device_fingerprint == fingerprint
            )
        )
        dev_id = dev.id if dev else None
    db.add(FcmToken(user_id=user_id, device_id=dev_id, token=token))


def _is_strong_password(p: str) -> bool:
    return (
        len(p) >= 8
        and any(c.isdigit() for c in p)
        and any(c.isalpha() for c in p)
    )


# Re-exported for type-check only.
_ = (secrets, EnrollmentSource)
