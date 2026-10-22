"""Application settings — loaded from environment with sane defaults.

Load order (highest precedence first):
  1. Real OS environment variables exported in the shell (set by docker-compose
     or CI).
  2. Values in `api/.env` (loaded explicitly below).
  3. Field defaults on this class.

We explicitly load `api/.env` early so a project-local file is honored when
the OS environment doesn't override it. Real OS env vars still win — that's
what lets docker-compose inject `DATABASE_URL`/`REDIS_URL` via `environment:`.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load api/.env into the process environment before Settings reads it.
# - In dev (APP_ENV=development or unset): .env WINS over stale OS env
#   exports (the sandbox shell has unrelated DATABASE_URL exports).
# - In test (APP_ENV=test): .env is NOT loaded — CI env vars win.
# - In staging/production: docker-compose sets real env vars AFTER the
#   container starts; .env is NOT loaded so those win.
import os as _os

_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
_app_env = _os.environ.get("APP_ENV", "development")
if _ENV_FILE.exists() and _app_env == "development":
    load_dotenv(_ENV_FILE, override=True)
elif _ENV_FILE.exists() and _app_env not in ("test", "staging", "production"):
    load_dotenv(_ENV_FILE, override=False)  # prod: real env vars win
# test/staging/production: .env is NOT loaded at all — only real env vars used


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE) if _ENV_FILE.exists() else None,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──
    app_name: str = "QU-CSIT API"
    app_env: Literal["development", "test", "staging", "production"] = "development"
    app_debug: bool = True
    app_timezone: str = "Asia/Baghdad"
    app_week_start: str = "sunday"
    app_package_id: str = "iq.edu.qu.csit"

    # ── Database ──
    database_url: str = "sqlite:///./dev.db"
    db_pool_size: int = 10
    db_max_overflow: int = 20

    # ── Redis ──
    redis_url: str = ""

    # ── Security ──
    jwt_secret: str = "change-me"
    jwt_alg: str = "HS256"
    access_token_ttl_min: int = 15
    refresh_token_ttl_days: int = 30
    login_rate_per_min: int = 5

    # Argon2
    argon2_memory_kib: int = 19456
    argon2_time_cost: int = 2
    argon2_parallelism: int = 1

    # ── Attendance rules ──
    late_threshold_minutes: int = 15
    absence_limit_percent: int = 25
    late_counts_as_absence: bool = False

    # ── Device binding ──
    max_active_devices_per_student: int = 1

    # ── Storage ──
    storage_backend: Literal["local", "s3"] = "local"
    storage_local_dir: str = "./storage"
    storage_base_url: str = "http://localhost:8000/storage"
    s3_bucket: str = ""
    s3_region: str = "eu-central-1"

    # Uploads
    upload_max_bytes: int = 52_428_800
    upload_allowed_mime: str = "application/pdf,video/mp4,image/png,image/jpeg"

    # ── FCM ──
    firebase_credentials_json: str = ""

    # ── CORS ──
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # ── Sentry ──
    sentry_dsn: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def allowed_mime_list(self) -> list[str]:
        return [m.strip() for m in self.upload_allowed_mime.split(",") if m.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
