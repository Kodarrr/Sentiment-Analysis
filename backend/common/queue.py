import redis
from rq import Queue

from backend.common.config import get_settings

QUEUE_NAME = "sentiment_analysis"


def get_redis_connection() -> redis.Redis:
    return redis.from_url(get_settings().redis_url)


def get_queue() -> Queue:
    return Queue(QUEUE_NAME, connection=get_redis_connection())
