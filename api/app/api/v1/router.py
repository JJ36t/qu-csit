"""API v1 router aggregation."""
from __future__ import annotations

from fastapi import APIRouter

api_router = APIRouter()


# Routers are included lazily so the app still boots even before all
# feature routers exist. Phase 0 only wires auth (stub) so /health works
# in isolation during scaffold.
def _wire():
    try:
        from app.api.v1.endpoints import auth

        api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
    except Exception as exc:  # pragma: no cover
        import logging

        logging.getLogger("app").warning("auth router not wired: %s", exc)

    try:
        from app.api.v1.endpoints import admin

        api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
    except Exception as exc:  # pragma: no cover
        import logging

        logging.getLogger("app").warning("admin router not wired: %s", exc)

    try:
        from app.api.v1.endpoints import meta

        api_router.include_router(meta.router, tags=["meta"])
    except Exception as exc:  # pragma: no cover
        import logging

        logging.getLogger("app").warning("meta router not wired: %s", exc)


_wire()
