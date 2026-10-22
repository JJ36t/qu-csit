"""API v1 router aggregation."""
from __future__ import annotations

from fastapi import APIRouter

api_router = APIRouter()


def _wire():
    import logging

    log = logging.getLogger("app")

    for module_name, prefix, tags in [
        ("auth", "/auth", ["auth"]),
        ("meta", "", ["meta"]),
        ("timetable", "/timetable", ["timetable"]),
        ("announcements", "/announcements", ["announcements"]),
        ("attendance", "", ["attendance"]),  # routes mounted at root: /sessions/..., /attendance/...
    ]:
        try:
            mod = __import__(f"app.api.v1.endpoints.{module_name}", fromlist=["router"])
            api_router.include_router(mod.router, prefix=prefix, tags=tags)
        except Exception as exc:  # pragma: no cover
            log.warning("%s router not wired: %s", module_name, exc)

    # announcements.py also has public_router (no auth) and notifications_router
    try:
        from app.api.v1.endpoints.announcements import public_router, notifications_router
        api_router.include_router(public_router, prefix="/public", tags=["public"])
        api_router.include_router(notifications_router, prefix="/notifications", tags=["notifications"])
    except Exception as exc:  # pragma: no cover
        log.warning("public/notifications router not wired: %s", exc)

    # admin routers — split across modules
    try:
        from app.api.v1.endpoints.timetable import admin_router as timetable_admin_router
        api_router.include_router(timetable_admin_router, prefix="/admin/timetable", tags=["admin"])
    except Exception as exc:  # pragma: no cover
        log.warning("admin/timetable router not wired: %s", exc)

    for module_name, prefix in [
        ("admin", "/admin"),
        ("academic_admin", "/admin"),
    ]:
        try:
            mod = __import__(f"app.api.v1.endpoints.{module_name}", fromlist=["router"])
            api_router.include_router(mod.router, prefix=prefix, tags=["admin"])
        except Exception as exc:  # pragma: no cover
            log.warning("%s router not wired: %s", module_name, exc)


_wire()
