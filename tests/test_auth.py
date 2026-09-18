from datetime import UTC, datetime

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError
from pymongo import MongoClient
from pymongo.errors import ConfigurationError, ConnectionFailure, OperationFailure

from authentication.user.request import UserRequest
from authentication.user.utils import (
    create_access_token,
    decode_access_token,
    get_password_hash,
)
from core.config import settings
from main import app


def test_request_validation_rejects_short_password():
    with pytest.raises(ValidationError):
        UserRequest(username="alice", email="alice@example.com", password="short")


def test_access_token_round_trip():
    token = create_access_token({"sub": "alice@example.com"})

    assert decode_access_token(token)["sub"] == "alice@example.com"


@pytest.fixture()
def client(database):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def database(monkeypatch):
    monkeypatch.setattr(settings, "mongo_db", settings.mongo_test_db)
    mongo_client = MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=2000)
    try:
        mongo_client.admin.command("ping")

    except ConnectionFailure:
        raise HTTPException(status_code=500, detail="MongoDB server not available")
    except ConfigurationError:
        raise HTTPException(status_code=500, detail="MongoDB configuration error")
    except OperationFailure as e:
        raise HTTPException(status_code=500, detail=f"MongoDB operation failed: {e}")

    database = mongo_client[settings.mongo_test_db]
    database.users.delete_many({})
    yield database
    database.users.delete_many({})
    mongo_client.close()


def register_payload(email="alice@example.com"):
    return {
        "username": "Alice",
        "email": email,
        "password": "password123",
    }


def test_register_persists_user_in_mongodb(client, database):
    response = client.post(
        "/api/v1/users/register", json=register_payload("Alice@Example.com")
    )

    assert response.status_code == 201
    assert response.json() == {
        "username": "Alice",
        "email": "alice@example.com",
        "role": "user",
    }

    stored_user = database.users.find_one({"email": "alice@example.com"})
    assert stored_user is not None
    assert stored_user["username"] == "Alice"
    assert stored_user["role"] == "user"
    assert stored_user["hashed_password"] != "password123"


def test_register_rejects_duplicate_email(client, database):
    payload = register_payload()

    assert client.post("/api/v1/users/register", json=payload).status_code == 201
    duplicate_response = client.post("/api/v1/users/register", json=payload)

    assert duplicate_response.status_code == 409


def test_login_and_me_use_persisted_user(client, database):
    client.post("/api/v1/users/register", json=register_payload())

    login_response = client.post(
        "/api/v1/users/login",
        json={"email": "alice@example.com", "password": "password123"},
    )
    token = login_response.json()["access_token"]
    profile_response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert login_response.status_code == 200
    assert profile_response.status_code == 200
    assert profile_response.json()["email"] == "alice@example.com"


def test_admin_route_requires_superuser(client, database):
    database.users.insert_one(
        {
            "username": "Admin",
            "email": "admin@example.com",
            "hashed_password": get_password_hash("admin-password"),
            "role": "superuser",
            "created_at": datetime.now(UTC),
        }
    )
    login_response = client.post(
        "/api/v1/users/login",
        json={"email": "admin@example.com", "password": "admin-password"},
    )
    token = login_response.json()["access_token"]

    response = client.post(
        "/api/v1/users/admin/users/register",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "username": "Second Admin",
            "email": "second-admin@example.com",
            "password": "admin-password-2",
        },
    )

    assert response.status_code == 201
    stored_user = database.users.find_one({"email": "second-admin@example.com"})
    assert stored_user["role"] == "superuser"


def test_normal_user_cannot_create_admin(client, database):
    client.post("/api/v1/users/register", json=register_payload())
    login_response = client.post(
        "/api/v1/users/login",
        json={"email": "alice@example.com", "password": "password123"},
    )

    response = client.post(
        "/api/v1/users/admin/users/register",
        headers={"Authorization": f"Bearer {login_response.json()['access_token']}"},
        json={
            "username": "Second Admin",
            "email": "second-admin@example.com",
            "password": "admin-password-2",
        },
    )

    assert response.status_code == 403
