from decimal import Decimal
from unittest.mock import MagicMock

import pymysql
import pytest
import requests

import app as service


@pytest.fixture
def client():
    service.app.config["TESTING"] = True

    with service.app.test_client() as client:
        yield client


@pytest.fixture
def dependencies(monkeypatch):
    # Pretend Authentication verified the token as user 1.
    auth_response = MagicMock()
    auth_response.status_code = 200
    auth_response.json.return_value = {"user_id": 1}

    auth_call = MagicMock(return_value=auth_response)
    monkeypatch.setattr(service.requests, "post", auth_call)

    # Replace MySQL with a mock connection.
    connection = MagicMock()
    cursor = connection.cursor.return_value.__enter__.return_value
    cursor.lastrowid = 10

    database_call = MagicMock(return_value=connection)
    monkeypatch.setattr(service, "get_connection", database_call)

    return auth_call, database_call, connection, cursor


def submit_grade(client, payload):
    return client.post(
        "/api/grades",
        json=payload,
        headers={"Authorization": "Bearer test-token"},
    )


def test_valid_grade(client, dependencies):
    auth_call, _, connection, cursor = dependencies

    response = submit_grade(
        client,
        {"course_name": "CIT3495", "grade": "85.50"},
    )

    assert response.status_code == 201
    assert response.json["id"] == 10

    # Check the values sent to the database.
    parameters = cursor.execute.call_args.args[1]
    assert parameters == (1, "CIT3495", Decimal("85.50"))

    connection.commit.assert_called_once()
    connection.close.assert_called_once()

    auth_call.assert_called_once_with(
        f"{service.AUTH_URL}/auth/verify",
        headers={"Authorization": "Bearer test-token"},
        timeout=5,
    )


def test_missing_token(client, dependencies):
    auth_call, database_call, _, _ = dependencies

    response = client.post(
        "/api/grades",
        json={"course_name": "CIT3495", "grade": 85},
    )

    assert response.status_code == 401
    auth_call.assert_not_called()
    database_call.assert_not_called()


@pytest.mark.parametrize("auth_status", [401, 422])
def test_rejected_token(client, dependencies, auth_status):
    auth_call, database_call, _, _ = dependencies
    auth_call.return_value.status_code = auth_status

    response = submit_grade(
        client,
        {"course_name": "CIT3495", "grade": 85},
    )

    assert response.status_code == 401
    database_call.assert_not_called()


@pytest.mark.parametrize(
    "payload",
    [
        {"course_name": "", "grade": 85},
        {"course_name": "   ", "grade": 85},
        {"course_name": "x" * 101, "grade": 85},
        {"course_name": "CIT3495", "grade": -1},
        {"course_name": "CIT3495", "grade": 101},
        {"course_name": "CIT3495", "grade": "abc"},
        {"course_name": "CIT3495", "grade": True},
        {"course_name": "CIT3495", "grade": "NaN"},
        {"course_name": "CIT3495", "grade": "85.555"},
        {"course_name": "CIT3495"},
    ],
)
def test_invalid_grade_input(client, dependencies, payload):
    _, database_call, _, _ = dependencies

    response = submit_grade(client, payload)

    assert response.status_code == 400
    database_call.assert_not_called()


@pytest.mark.parametrize("grade", ["0", "100"])
def test_grade_boundaries(client, dependencies, grade):
    response = submit_grade(
        client,
        {"course_name": "CIT3495", "grade": grade},
    )

    assert response.status_code == 201


def test_user_id_comes_from_token(client, dependencies):
    _, _, _, cursor = dependencies

    response = submit_grade(
        client,
        {
            "course_name": "CIT3495",
            "grade": 85,
            "user_id": 999,
        },
    )

    assert response.status_code == 201

    parameters = cursor.execute.call_args.args[1]
    assert parameters[0] == 1  # Verified identity, not browser value 999.


def test_authentication_unavailable(client, dependencies):
    auth_call, database_call, _, _ = dependencies
    auth_call.side_effect = requests.exceptions.ConnectionError()

    response = submit_grade(
        client,
        {"course_name": "CIT3495", "grade": 85},
    )

    assert response.status_code == 503
    database_call.assert_not_called()


def test_database_unavailable(client, dependencies):
    _, database_call, _, _ = dependencies
    database_call.side_effect = pymysql.err.OperationalError(
        2003,
        "Connection failed",
    )

    response = submit_grade(
        client,
        {"course_name": "CIT3495", "grade": 85},
    )

    assert response.status_code == 503