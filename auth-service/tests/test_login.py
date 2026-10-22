from datetime import timedelta
from unittest.mock import MagicMock

import pytest
from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash

import app as service


@pytest.fixture
def client():
    service.app.config["TESTING"] = True

    with service.app.test_client() as client:
        yield client


@pytest.fixture
def database(monkeypatch):
    connection = MagicMock()
    cursor = connection.cursor.return_value.__enter__.return_value

    monkeypatch.setattr(
        service,
        "get_connection",
        lambda: connection,
    )

    return connection, cursor


def test_correct_login(client, database):
    connection, cursor = database
    cursor.fetchone.return_value = {
        "id": 1,
        "password_hash": generate_password_hash("test-password"),
    }

    response = client.post(
        "/auth/login",
        json={
            "username": "student1",
            "password": "test-password",
        },
    )

    assert response.status_code == 200
    assert response.json["access_token"]
    assert response.json["token_type"] == "Bearer"
    assert response.json["expires_in"] == 900
    connection.close.assert_called_once()


def test_wrong_password(client, database):
    _, cursor = database
    cursor.fetchone.return_value = {
        "id": 1,
        "password_hash": generate_password_hash("correct-password"),
    }

    response = client.post(
        "/auth/login",
        json={
            "username": "student1",
            "password": "wrong-password",
        },
    )

    assert response.status_code == 401
    assert "access_token" not in response.json


def test_unknown_user(client, database):
    _, cursor = database
    cursor.fetchone.return_value = None

    response = client.post(
        "/auth/login",
        json={
            "username": "unknown",
            "password": "test-password",
        },
    )

    assert response.status_code == 401
    assert response.json["error"] == "Invalid username or password"


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"username": "student1"},
        {"username": "", "password": "test-password"},
        {"username": "student1", "password": 123},
    ],
)
def test_invalid_login_input(client, payload):
    response = client.post("/auth/login", json=payload)

    assert response.status_code == 400


def test_verify_valid_token(client):
    with service.app.app_context():
        token = create_access_token(identity="1")

    response = client.post(
        "/auth/verify",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json["user_id"] == 1


def test_verify_missing_token(client):
    response = client.post("/auth/verify")

    assert response.status_code == 401


def test_verify_invalid_token(client):
    response = client.post(
        "/auth/verify",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 422


def test_verify_expired_token(client):
    with service.app.app_context():
        token = create_access_token(
            identity="1",
            expires_delta=timedelta(seconds=-60),
        )

    response = client.post(
        "/auth/verify",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401