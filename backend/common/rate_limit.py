from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.common.config import get_settings

limiter = Limiter(key_func=get_remote_address, storage_uri=get_settings().redis_url)


def feedback_rate_limit() -> str:
    """Evaluated per-request by slowapi, so RATE_LIMIT_PER_MINUTE stays configurable at runtime."""
    return f"{get_settings().rate_limit_per_minute}/minute"
