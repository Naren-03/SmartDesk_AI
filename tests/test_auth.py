from datetime import UTC, datetime, timedelta

import jwt
import pytest
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
        raise RuntimeError("MongoDB server not available")
    except ConfigurationError:
        raise RuntimeError("MongoDB configuration error")
    except OperationFailure as e:
        raise RuntimeError(f"MongoDB operation failed: {e}")

    database = mongo_client[settings.mongo_test_db]
    try:
        database.users.delete_many({})
        yield database
    finally:
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


def test_login_rejects_invalid_credentials(client, database):
    client.post("/api/v1/users/register", json=register_payload())

    response = client.post(
        "/api/v1/users/login",
        json={"email": "alice@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_login_rejects_unknown_email(client, database):
    response = client.post(
        "/api/v1/users/login",
        json={"email": "unknown@example.com", "password": "password123"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_me_rejects_invalid_jwt(client, database):
    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": "Bearer not-a-valid-jwt"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"


def test_me_rejects_expired_jwt(client, database):
    expired_token = jwt.encode(
        {
            "sub": "alice@example.com",
            "exp": datetime.now(UTC) - timedelta(minutes=1),
        },
        settings.secret_key,
        algorithm=settings.algorithm,
    )

    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"


def test_me_requires_authorization_header(client, database):
    response = client.get("/api/v1/users/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


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


def test_admin_route_requires_authentication(client, database):
    response = client.post(
        "/api/v1/users/admin/users/register",
        json={
            "username": "Second Admin",
            "email": "second-admin@example.com",
            "password": "admin-password-2",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_me_can_update_profile(client, database):
    client.post("/api/v1/users/register", json=register_payload())
    login_response = client.post(
        "/api/v1/users/login",
        json={"email": "alice@example.com", "password": "password123"},
    )

    response = client.patch(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {login_response.json()['access_token']}"},
        json={
            "username": "Alice Updated",
            "email": "ALICE@EXAMPLE.com",
            "password": "new-password-456",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "username": "Alice Updated",
        "email": "alice@example.com",
        "role": "user",
    }

    database_user = database.users.find_one({"email": "alice@example.com"})
    assert database_user["username"] == "Alice Updated"
    assert database_user["hashed_password"] != "new-password-456"


def test_admin_can_list_users(client, database):
    database.users.insert_many(
        [
            {
                "username": "Admin",
                "email": "admin@example.com",
                "hashed_password": get_password_hash("admin-password"),
                "role": "superuser",
                "created_at": datetime.now(UTC),
            },
            {
                "username": "Alice",
                "email": "alice@example.com",
                "hashed_password": get_password_hash("password123"),
                "role": "user",
                "created_at": datetime.now(UTC),
            },
        ]
    )
    login_response = client.post(
        "/api/v1/users/login",
        json={"email": "admin@example.com", "password": "admin-password"},
    )

    response = client.get(
        "/api/v1/users/admin/users",
        headers={"Authorization": f"Bearer {login_response.json()['access_token']}"},
    )

    assert response.status_code == 200
    users = response.json()
    assert [user["username"] for user in users] == ["Admin", "Alice"]
    assert all(user["id"] for user in users)
    assert users[0]["email"] == "admin@example.com"
    assert users[0]["role"] == "superuser"
    assert users[1]["email"] == "alice@example.com"
    assert users[1]["role"] == "user"

    normal_users_response = client.get(
        "/api/v1/users/admin/users?role=user",
        headers={"Authorization": f"Bearer {login_response.json()['access_token']}"},
    )
    superusers_response = client.get(
        "/api/v1/users/admin/users?role=superuser",
        headers={"Authorization": f"Bearer {login_response.json()['access_token']}"},
    )

    assert [user["email"] for user in normal_users_response.json()] == [
        "alice@example.com"
    ]
    assert [user["email"] for user in superusers_response.json()] == [
        "admin@example.com"
    ]


def test_admin_can_get_update_and_delete_user(client, database):
    database.users.insert_many(
        [
            {
                "username": "Admin",
                "email": "admin@example.com",
                "hashed_password": get_password_hash("admin-password"),
                "role": "superuser",
                "created_at": datetime.now(UTC),
            },
            {
                "username": "Alice",
                "email": "alice@example.com",
                "hashed_password": get_password_hash("password123"),
                "role": "user",
                "created_at": datetime.now(UTC),
            },
        ]
    )
    alice = database.users.find_one({"email": "alice@example.com"})
    login_response = client.post(
        "/api/v1/users/login",
        json={"email": "admin@example.com", "password": "admin-password"},
    )
    headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

    get_response = client.get(f"/api/v1/users/admin/users/{alice['_id']}", headers=headers)
    update_response = client.patch(
        f"/api/v1/users/admin/users/{alice['_id']}",
        headers=headers,
        json={"username": "Alice Updated"},
    )
    delete_response = client.delete(
        f"/api/v1/users/admin/users/{alice['_id']}", headers=headers
    )

    assert get_response.status_code == 200
    assert get_response.json()["id"] == str(alice["_id"])
    assert update_response.status_code == 200
    assert update_response.json()["username"] == "Alice Updated"
    assert delete_response.status_code == 204
    assert database.users.find_one({"_id": alice["_id"]}) is None


def test_normal_user_cannot_list_admin_users(client, database):
    client.post("/api/v1/users/register", json=register_payload())
    login_response = client.post(
        "/api/v1/users/login",
        json={"email": "alice@example.com", "password": "password123"},
    )

    response = client.get(
        "/api/v1/users/admin/users",
        headers={"Authorization": f"Bearer {login_response.json()['access_token']}"},
    )

    assert response.status_code == 403
