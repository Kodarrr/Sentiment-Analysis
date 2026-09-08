from typing import Annotated

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from backend.api.dependencies import get_current_user
from backend.api.main import app
from backend.common.db import get_db
from backend.common.models import AdminUser


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


protected_test_app = FastAPI()


@protected_test_app.get("/_protected_test_route")
def _protected_test_route(user: Annotated[AdminUser, Depends(get_current_user)]) -> dict:
    return {"email": user.email}


@pytest.fixture
def protected_client(db_session):
    def override_get_db():
        yield db_session

    protected_test_app.dependency_overrides[get_db] = override_get_db
    yield TestClient(protected_test_app)
    protected_test_app.dependency_overrides.clear()


def test_register_creates_admin_user(client):
    response = client.post(
        "/api/v1/auth/register", json={"email": "admin@example.com", "password": "hunter22"}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "admin@example.com"
    assert "password" not in body
    assert "hashed_password" not in body


def test_register_rejects_duplicate_email(client):
    client.post(
        "/api/v1/auth/register", json={"email": "admin@example.com", "password": "hunter22"}
    )

    response = client.post(
        "/api/v1/auth/register", json={"email": "admin@example.com", "password": "different1"}
    )

    assert response.status_code == 409


def test_register_rejects_short_password(client):
    response = client.post(
        "/api/v1/auth/register", json={"email": "admin@example.com", "password": "short"}
    )

    assert response.status_code == 422


def test_login_returns_token_for_valid_credentials(client):
    client.post(
        "/api/v1/auth/register", json={"email": "admin@example.com", "password": "hunter22"}
    )

    response = client.post(
        "/api/v1/auth/login", json={"email": "admin@example.com", "password": "hunter22"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert len(body["access_token"]) > 20


def test_login_rejects_wrong_password(client):
    client.post(
        "/api/v1/auth/register", json={"email": "admin@example.com", "password": "hunter22"}
    )

    response = client.post(
        "/api/v1/auth/login", json={"email": "admin@example.com", "password": "wrong-password"}
    )

    assert response.status_code == 401


def test_login_rejects_unknown_email(client):
    response = client.post(
        "/api/v1/auth/login", json={"email": "nobody@example.com", "password": "hunter22"}
    )

    assert response.status_code == 401


def test_protected_route_rejects_missing_token(protected_client):
    response = protected_client.get("/_protected_test_route")

    assert response.status_code == 403


def test_protected_route_rejects_invalid_token(protected_client):
    response = protected_client.get(
        "/_protected_test_route", headers={"Authorization": "Bearer not-a-real-token"}
    )

    assert response.status_code == 401


def test_protected_route_accepts_valid_token(client, protected_client):
    client.post(
        "/api/v1/auth/register", json={"email": "admin@example.com", "password": "hunter22"}
    )
    login_response = client.post(
        "/api/v1/auth/login", json={"email": "admin@example.com", "password": "hunter22"}
    )
    token = login_response.json()["access_token"]

    response = protected_client.get(
        "/_protected_test_route", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert response.json() == {"email": "admin@example.com"}
