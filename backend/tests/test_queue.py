import os

import pytest

from backend.common import queue as queue_module

TEST_REDIS_URL = os.environ.get("TEST_REDIS_URL", "redis://localhost:6379/0")


@pytest.fixture
def redis_settings(monkeypatch):
    settings = queue_module.get_settings()
    monkeypatch.setattr(settings, "redis_url", TEST_REDIS_URL)
    return settings


def test_get_queue_enqueues_job_against_real_redis(redis_settings):
    q = queue_module.get_queue()
    q.empty()

    job = q.enqueue("backend.worker.tasks.process_feedback", "some-feedback-id")

    assert job.args == ("some-feedback-id",)
    assert q.count == 1

    q.empty()
