from backend.common.queue import get_retry_policy


def test_retry_policy_uses_exponential_backoff():
    policy = get_retry_policy()

    assert policy.max == 3
    assert policy.intervals == [10, 20, 40]
