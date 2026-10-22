"""arq worker entrypoint — runs background jobs (FCM pushes, session
generation, course-end archival, etc.).

In dev (no Redis), jobs run inline via the API's enqueue fallback, so the
worker is only strictly needed in staging/prod.
"""
from __future__ import annotations

import logging

from arq.connections import RedisSettings

from app.core.config import settings

logger = logging.getLogger("worker")
logging.basicConfig(level=logging.INFO)


async def startup(ctx):
    logger.info("worker started")


async def shutdown(ctx):
    logger.info("worker stopped")


async def ping(ctx):
    return "pong"


class WorkerSettings:
    functions = [ping]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = (
        RedisSettings.from_dsn(settings.redis_url) if settings.redis_url else None
    )


if __name__ == "__main__":
    # Local dev convenience
    if not settings.redis_url:
        logger.error("REDIS_URL not set — worker requires Redis. Use Docker Compose.")
        raise SystemExit(1)
    from arq import run_worker

    run_worker(WorkerSettings)  # type: ignore[arg-type]
