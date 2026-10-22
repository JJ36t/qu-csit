"""RBAC: FastAPI dependencies for current user, role checks, and scope checks.

The SERVER is the only authority (brief §1 rule 2). Every endpoint must
verify role + scope on the server, never trust the client.
"""
from __future__ import annotations

import uuid
from typing import Any, Callable

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.tokens import decode_token
from app.db.base import get_db
from app.i18n.errors_ar import APIError
from app.models import User, UserRole
from app.models.enums import UserStatus


def _extract_bearer(request: Request) -> str:
    auth = request.headers.get("Authorization") or ""
    if not auth.startswith("Bearer "):
        raise APIError("UNAUTHENTICATED", 401)
    return auth[7:].strip()


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    raw = _extract_bearer(request)
    try:
        payload = decode_token(raw)
    except Exception as exc:  # expired / invalid
        from jwt import ExpiredSignatureError

        if isinstance(exc, ExpiredSignatureError):
            raise APIError("TOKEN_EXPIRED", 401)
        raise APIError("TOKEN_INVALID", 401, {"reason": type(exc).__name__})

    if payload.get("type") != "access":
        raise APIError("TOKEN_INVALID", 401)

    user_id = payload.get("sub")
    if not user_id:
        raise APIError("TOKEN_INVALID", 401)

    user = db.get(User, uuid.UUID(user_id))
    if not user or user.status != UserStatus.active:
        raise APIError("UNAUTHENTICATED", 401)

    request.state.current_user = user
    request.state.access_token = raw
    return user


def require_roles(*roles: UserRole) -> Callable[..., User]:
    allowed = set(roles)

    def _dep(user: User = Depends(get_current_user)) -> User:
        if UserRole(user.role) not in allowed:
            raise APIError("ROLE_NOT_ALLOWED", 403)
        return user

    return _dep


def require_instructor_or_higher(
    user: User = Depends(get_current_user),
) -> User:
    allowed = {UserRole.instructor, UserRole.dept_admin, UserRole.college_admin, UserRole.system_admin}
    if UserRole(user.role) not in allowed:
        raise APIError("ROLE_NOT_ALLOWED", 403)
    return user


def require_dept_admin_or_higher(
    user: User = Depends(get_current_user),
) -> User:
    allowed = {UserRole.dept_admin, UserRole.college_admin, UserRole.system_admin}
    if UserRole(user.role) not in allowed:
        raise APIError("ROLE_NOT_ALLOWED", 403)
    return user


def require_college_admin_or_higher(
    user: User = Depends(get_current_user),
) -> User:
    allowed = {UserRole.college_admin, UserRole.system_admin}
    if UserRole(user.role) not in allowed:
        raise APIError("ROLE_NOT_ALLOWED", 403)
    return user


def require_system_admin(user: User = Depends(get_current_user)) -> User:
    if UserRole(user.role) != UserRole.system_admin:
        raise APIError("ROLE_NOT_ALLOWED", 403)
    return user


def get_user_department_id(user: User) -> uuid.UUID | None:
    """Helper: a user's department, regardless of role."""
    if user.student:
        return user.student.department_id
    if user.staff and user.staff.department_id:
        return user.staff.department_id
    return None


def assert_in_same_department(
    user: User, target_department_id: uuid.UUID | None
) -> None:
    """dept_admin scope check. College/system admin bypass."""
    if UserRole(user.role) in (UserRole.college_admin, UserRole.system_admin):
        return
    if UserRole(user.role) != UserRole.dept_admin:
        raise APIError("OUT_OF_SCOPE", 403)
    my_dept = get_user_department_id(user)
    if my_dept is None or target_department_id is None or my_dept != target_department_id:
        raise APIError("OUT_OF_SCOPE", 403)


def assert_is_offering_instructor(user: User, offering) -> None:  # type: ignore[no-untyped-def]
    """Only the assigned instructor (or admin+) may manage a session."""
    if UserRole(user.role) in (UserRole.dept_admin, UserRole.college_admin, UserRole.system_admin):
        return
    if UserRole(user.role) != UserRole.instructor:
        raise APIError("OUT_OF_SCOPE", 403)
    if not user.staff or offering.instructor_id != user.staff.user_id:
        raise APIError("NOT_SESSION_INSTRUCTOR", 403)


# Convenience: anything (used by audit code that wants the user without enforcing role)
def maybe_user(request: Request) -> User | None:
    return getattr(request.state, "current_user", None)


def audit_dict(obj: Any) -> dict[str, Any]:
    """Best-effort dict snapshot of a model instance for audit logs."""
    if obj is None:
        return {}
    if hasattr(obj, "__dict__"):
        out: dict[str, Any] = {}
        for k, v in obj.__dict__.items():
            if k.startswith("_"):
                continue
            try:
                import json

                json.dumps(v, default=str)
                out[k] = v
            except Exception:
                out[k] = str(v)
        return out
    return {"value": str(obj)}
