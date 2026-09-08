import os

import pytest
import redis as redis_lib
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.common import models  # noqa: F401  (registers models on Base.metadata)
from backend.common.db import Base

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg2://feedback:feedback@localhost:5432/feedback",
)
TEST_REDIS_URL = os.environ.get("TEST_REDIS_URL", "redis://localhost:6379/0")


@pytest.fixture(scope="session", autouse=True)
def flush_test_redis():
    # Dedicated test Redis instance: RQ queues and slowapi's rate-limit counters
    # both live here, so start each test session from a clean slate.
    redis_lib.from_url(TEST_REDIS_URL).flushdb()


@pytest.fixture(scope="session")
def engine():
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db_session(engine):
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)()

    yield session

    session.close()
    transaction.rollback()
    connection.close()
