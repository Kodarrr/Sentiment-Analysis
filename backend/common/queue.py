import redis
from rq import Queue, Retry

from backend.common.config import get_settings

QUEUE_NAME = "sentiment_analysis"


def get_redis_connection() -> redis.Redis:
    return redis.from_url(get_settings().redis_url)


def get_queue() -> Queue:
    return Queue(QUEUE_NAME, connection=get_redis_connection())


def get_retry_policy() -> Retry:
    """Exponential backoff: base, base*2, base*4, ... for max_retries attempts.

    Failed jobs that exhaust their retries land in the queue's
    FailedJobRegistry, which serves as our dead-letter queue.
    """
    settings = get_settings()
    intervals = [settings.retry_backoff_base_seconds * (2**i) for i in range(settings.max_retries)]
    return Retry(max=settings.max_retries, interval=intervals)
