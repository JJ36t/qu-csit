"""Sentry integration — no-op in dev unless SENTRY_DSN is set.

Wire this in main() to capture unhandled exceptions in production.
"""
from __future__ import annotations

import logging

from app.core.config import settings

logger = logging.getLogger("app.sentry")

_sentry_initialized = False


def init_sentry() -> None:
    """Initialize Sentry SDK if SENTRY_DSN is set. No-op otherwise."""
    global _sentry_initialized
    if _sentry_initialized:
        return
    if not settings.sentry_dsn:
        logger.debug("SENTRY_DSN not set — skipping Sentry init (dev mode)")
        return
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.app_env,
            traces_sample_rate=0.1 if settings.app_env == "production" else 1.0,
            send_default_pii=False,  # privacy: don't send PII
            integrations=[
                FastApiIntegration(),
                SqlalchemyIntegration(),
                LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
            ],
            before_send=_scrub_sensitive,
        )
        _sentry_initialized = True
        logger.info("Sentry initialized (env=%s)", settings.app_env)
    except ImportError:
        logger.warning("sentry-sdk not installed — skipping")
    except Exception as exc:
        logger.warning("Sentry init failed: %s", exc)


def _scrub_sensitive(event: dict, hint: dict) -> dict | None:
    """Strip sensitive fields from Sentry events before sending."""
    if "request" in event:
        req = event["request"]
        # Strip Authorization header
        if "headers" in req:
            req["headers"] = {
                k: ("***" if k.lower() == "authorization" else v)
                for k, v in req["headers"].items()
            }
        # Strip body (might contain passwords)
        if "data" in req:
            data = req["data"]
            if isinstance(data, dict):
                for sensitive_key in ("password", "old_password", "new_password", "secret", "token"):
                    if sensitive_key in data:
                        data[sensitive_key] = "***"
    return event
