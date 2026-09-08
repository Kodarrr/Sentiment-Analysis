import redis
from fastapi import APIRouter, Response, status
from sqlalchemy import text

from backend.common.config import get_settings
from backend.common.db import engine

router = APIRouter(tags=["health"])
settings = get_settings()


@router.get("/health")
def health() -> dict:
    """Liveness probe: process is up and serving requests."""
    return {"status": "ok"}


@router.get("/ready")
def ready(response: Response) -> dict:
    """Readiness probe: dependencies (Postgres, Redis) are reachable."""
    checks = {"database": _check_database(), "redis": _check_redis()}
    all_ok = all(checks.values())
    response.status_code = status.HTTP_200_OK if all_ok else status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "ok" if all_ok else "unavailable", "checks": checks}


def _check_database() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def _check_redis() -> bool:
    try:
        client = redis.from_url(settings.redis_url, socket_connect_timeout=1)
        return bool(client.ping())
    except Exception:
        return False
