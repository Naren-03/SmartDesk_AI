from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from pymongo import MongoClient
from pymongo.errors import ConfigurationError, ConnectionFailure, OperationFailure

from authentication.user.utils import create_access_token, get_password_hash
from core.config import settings
from document.request import DocumentCreateRequest, DocumentUpdateRequest
from document.response import DocumentListResponse, DocumentResponse
from main import app


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
    except OperationFailure as error:
        raise RuntimeError(f"MongoDB operation failed: {error}")

    database = mongo_client[settings.mongo_test_db]
    try:
        database.users.delete_many({})
        database.documents.delete_many({})
        yield database
    finally:
        database.users.delete_many({})
        database.documents.delete_many({})
        mongo_client.close()


def create_test_user(database, email: str):
    user = {
        "username": email.split("@")[0],
        "email": email,
        "hashed_password": get_password_hash("password123"),
        "role": "user",
        "is_active": True,
        "created_at": datetime.now(UTC),
    }
    return database.users.insert_one(user).inserted_id


def auth_headers(email: str):
    token = create_access_token({"sub": email})
    return {"Authorization": f"Bearer {token}"}


def test_document_create_request_accepts_editable_metadata():
    request = DocumentCreateRequest(
        title="Company Handbook",
        description="Internal policies",
    )

    assert request.model_dump() == {
        "title": "Company Handbook",
        "description": "Internal policies",
    }


def test_document_update_request_allows_partial_updates():
    request = DocumentUpdateRequest(title="Updated Handbook")

    assert request.model_dump(exclude_unset=True) == {"title": "Updated Handbook"}


def test_document_list_response_has_pagination_contract():
    response = DocumentListResponse(
        items=[],
        total=0,
        page=1,
        page_size=20,
        pages=0,
    )

    assert response.items == []
    assert response.total == 0
    assert "storage_key" not in DocumentResponse.model_fields


def test_create_and_list_documents(client, database):
    create_test_user(database, "alice@example.com")
    headers = auth_headers("alice@example.com")

    create_response = client.post(
        "/api/v1/documents",
        headers=headers,
        json={"title": "Company Handbook", "description": "Policies"},
    )

    assert create_response.status_code == 201
    created_document = create_response.json()
    assert created_document["title"] == "Company Handbook"
    assert created_document["description"] == "Policies"
    assert created_document["status"] == "pending"
    assert created_document["filename"] is None

    list_response = client.get("/api/v1/documents", headers=headers)

    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1
    assert list_response.json()["items"][0]["id"] == created_document["id"]


def test_document_crud_is_limited_to_owner(client, database):
    create_test_user(database, "alice@example.com")
    create_test_user(database, "bob@example.com")
    alice_headers = auth_headers("alice@example.com")
    bob_headers = auth_headers("bob@example.com")

    create_response = client.post(
        "/api/v1/documents",
        headers=alice_headers,
        json={"title": "Alice Document"},
    )
    document_id = create_response.json()["id"]

    get_response = client.get(f"/api/v1/documents/{document_id}", headers=alice_headers)
    update_response = client.patch(
        f"/api/v1/documents/{document_id}",
        headers=alice_headers,
        json={"title": "Updated Document"},
    )
    delete_response = client.delete(
        f"/api/v1/documents/{document_id}", headers=alice_headers
    )
    other_user_response = client.get(
        f"/api/v1/documents/{document_id}", headers=bob_headers
    )

    assert get_response.status_code == 200
    assert update_response.status_code == 200
    assert update_response.json()["title"] == "Updated Document"
    assert delete_response.status_code == 204
    assert other_user_response.status_code == 404
    assert other_user_response.json() == {
        "code": "NOT_FOUND",
        "message": "Document not found",
        "details": None,
    }


def test_document_endpoints_reject_invalid_id(client, database):
    create_test_user(database, "alice@example.com")
    headers = auth_headers("alice@example.com")

    response = client.get("/api/v1/documents/not-an-object-id", headers=headers)

    assert response.status_code == 404
    assert response.json() == {
        "code": "NOT_FOUND",
        "message": "Document not found",
        "details": None,
    }
