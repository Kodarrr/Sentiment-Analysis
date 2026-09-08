import uuid

from fastapi.testclient import TestClient

from backend.api.main import app
from backend.api.middleware import CORRELATION_ID_HEADER


def test_generates_correlation_id_when_absent():
    client = TestClient(app)

    response = client.get("/health")

    correlation_id = response.headers.get(CORRELATION_ID_HEADER)
    assert correlation_id is not None
    uuid.UUID(correlation_id)  # raises if not a valid UUID


def test_echoes_provided_correlation_id():
    client = TestClient(app)

    response = client.get("/health", headers={CORRELATION_ID_HEADER: "my-trace-id"})

    assert response.headers.get(CORRELATION_ID_HEADER) == "my-trace-id"
