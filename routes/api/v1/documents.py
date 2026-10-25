from datetime import UTC, datetime

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Response, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from authentication.user.dependencies import get_current_user
from core.pagination import Pagination
from db.session import get_db
from document.request import DocumentCreateRequest, DocumentUpdateRequest
from document.response import DocumentListResponse, DocumentResponse

router = APIRouter()


async def get_owned_document(
    db: AsyncIOMotorDatabase,
    document_id: str,
    owner_id: str,
) -> dict:
    if not ObjectId.is_valid(document_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    document = await db.documents.find_one(
        {"_id": ObjectId(document_id), "owner_id": owner_id}
    )
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    return document


def to_document_response(document: dict) -> DocumentResponse:
    return DocumentResponse(
        id=str(document["_id"]),
        title=document["title"],
        description=document.get("description"),
        owner_id=document["owner_id"],
        filename=document.get("filename"),
        content_type=document.get("content_type"),
        size_bytes=document.get("size_bytes"),
        status=document["status"],
        created_at=document["created_at"],
        updated_at=document["updated_at"],
        processed_at=document.get("processed_at"),
        failure_reason=document.get("failure_reason"),
    )


@router.post("", response_model=DocumentResponse, status_code=201)
async def create_document(
    document_request: DocumentCreateRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    now = datetime.now(UTC)
    document = {
        "title": document_request.title.strip(),
        "description": document_request.description,
        "owner_id": str(current_user["_id"]),
        "filename": None,
        "content_type": None,
        "size_bytes": None,
        "storage_key": None,
        "checksum_sha256": None,
        "status": "pending",
        "created_at": now,
        "updated_at": now,
        "processed_at": None,
        "failure_reason": None,
    }
    result = await db.documents.insert_one(document)
    document["_id"] = result.inserted_id
    return to_document_response(document)


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    pagination: Pagination,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    query = {"owner_id": str(current_user["_id"])}
    total = await db.documents.count_documents(query)
    documents = (
        await db.documents.find(query)
        .sort("created_at", -1)
        .skip(pagination.skip)
        .limit(pagination.page_size)
        .to_list(length=pagination.page_size)
    )
    pages = (total + pagination.page_size - 1) // pagination.page_size
    return DocumentListResponse(
        items=[to_document_response(document) for document in documents],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=pages,
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    document = await get_owned_document(
        db, document_id, owner_id=str(current_user["_id"])
    )
    return to_document_response(document)


@router.patch("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: str,
    document_update: DocumentUpdateRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    document = await get_owned_document(
        db, document_id, owner_id=str(current_user["_id"])
    )
    update_data = document_update.model_dump(exclude_unset=True)
    if "title" in update_data:
        update_data["title"] = update_data["title"].strip()

    if update_data:
        update_data["updated_at"] = datetime.now(UTC)
        await db.documents.update_one(
            {"_id": document["_id"]},
            {"$set": update_data},
        )
        document.update(update_data)

    return to_document_response(document)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    document = await get_owned_document(
        db, document_id, owner_id=str(current_user["_id"])
    )
    await db.documents.delete_one({"_id": document["_id"]})
    return Response(status_code=status.HTTP_204_NO_CONTENT)
