"""Meta endpoints: versioning, config flags the client may read."""
from __future__ import annotations

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()


@router.get("/config")
async def public_config():
    """Client-readable config (no secrets)."""
    return {
        "app_name": settings.app_name,
        "package_id": settings.app_package_id,
        "timezone": settings.app_timezone,
        "week_start": settings.app_week_start,
        "maintenance": False,
        "min_app_version": "0.1.0",
    }
