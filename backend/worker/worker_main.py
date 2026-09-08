from rq import Worker

from backend.common.logging import configure_logging
from backend.common.queue import QUEUE_NAME, get_redis_connection

configure_logging()

if __name__ == "__main__":
    worker = Worker([QUEUE_NAME], connection=get_redis_connection())
    worker.work()
