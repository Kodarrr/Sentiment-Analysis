import logging

from rq import Worker

from backend.common.queue import QUEUE_NAME, get_redis_connection

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    worker = Worker([QUEUE_NAME], connection=get_redis_connection())
    worker.work()
