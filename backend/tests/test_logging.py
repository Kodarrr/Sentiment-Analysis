import json
import logging

from backend.common.logging import JSONFormatter, correlation_id_var


def make_record(msg="hello", **extra) -> logging.LogRecord:
    record = logging.LogRecord(
        name="test.logger", level=logging.INFO, pathname=__file__, lineno=1,
        msg=msg, args=(), exc_info=None,
    )
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_formats_standard_fields_as_json():
    formatted = JSONFormatter().format(make_record("hello world"))

    payload = json.loads(formatted)
    assert payload["message"] == "hello world"
    assert payload["level"] == "INFO"
    assert payload["logger"] == "test.logger"
    assert "timestamp" in payload


def test_includes_correlation_id_when_set():
    token = correlation_id_var.set("corr-123")
    try:
        payload = json.loads(JSONFormatter().format(make_record()))
    finally:
        correlation_id_var.reset(token)

    assert payload["correlation_id"] == "corr-123"


def test_omits_correlation_id_when_unset():
    payload = json.loads(JSONFormatter().format(make_record()))

    assert "correlation_id" not in payload


def test_includes_extra_fields():
    record = make_record("processed", feedback_id="fb-1", sentiment_score=0.97)

    payload = json.loads(JSONFormatter().format(record))

    assert payload["feedback_id"] == "fb-1"
    assert payload["sentiment_score"] == 0.97


def test_excludes_internal_record_attributes():
    payload = json.loads(JSONFormatter().format(make_record()))

    assert "args" not in payload
    assert "msg" not in payload
    assert "levelno" not in payload
