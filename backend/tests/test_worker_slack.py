import requests

from backend.worker import slack as slack_module


class FakeResponse:
    def __init__(self, status_code=200):
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"status {self.status_code}")


def test_skips_when_webhook_url_not_configured(monkeypatch):
    settings = slack_module.get_settings()
    monkeypatch.setattr(settings, "slack_webhook_url", "")
    called = False

    def fake_post(*args, **kwargs):
        nonlocal called
        called = True
        return FakeResponse()

    monkeypatch.setattr(slack_module.requests, "post", fake_post)

    result = slack_module.send_negative_feedback_alert("fb-1", "user-1", "bad", 0.9)

    assert result is False
    assert called is False


def test_posts_payload_when_webhook_configured(monkeypatch):
    settings = slack_module.get_settings()
    monkeypatch.setattr(settings, "slack_webhook_url", "https://hooks.slack.test/abc")
    captured = {}

    def fake_post(url, json, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        return FakeResponse(200)

    monkeypatch.setattr(slack_module.requests, "post", fake_post)

    result = slack_module.send_negative_feedback_alert("fb-1", "user-1", "terrible", 0.95)

    assert result is True
    assert captured["url"] == "https://hooks.slack.test/abc"
    assert "user-1" in captured["json"]["text"]
    assert "fb-1" in captured["json"]["text"]
    assert "terrible" in captured["json"]["text"]


def test_returns_false_and_does_not_raise_on_request_failure(monkeypatch):
    settings = slack_module.get_settings()
    monkeypatch.setattr(settings, "slack_webhook_url", "https://hooks.slack.test/abc")

    def fake_post(*args, **kwargs):
        raise requests.ConnectionError("boom")

    monkeypatch.setattr(slack_module.requests, "post", fake_post)

    result = slack_module.send_negative_feedback_alert("fb-1", "user-1", "bad", 0.9)

    assert result is False


def test_returns_false_on_http_error_status(monkeypatch):
    settings = slack_module.get_settings()
    monkeypatch.setattr(settings, "slack_webhook_url", "https://hooks.slack.test/abc")
    monkeypatch.setattr(slack_module.requests, "post", lambda *a, **k: FakeResponse(500))

    result = slack_module.send_negative_feedback_alert("fb-1", "user-1", "bad", 0.9)

    assert result is False
