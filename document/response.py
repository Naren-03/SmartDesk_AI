from datetime import datetime

from pydantic import BaseModel

from document.models import DocumentStatus


class DocumentResponse(BaseModel):
    id: str
    title: str
    description: str | None = None
    owner_id: str
    filename: str | None = None
    content_type: str | None = None
    size_bytes: int | None = None
    status: DocumentStatus
    created_at: datetime
    updated_at: datetime
    processed_at: datetime | None = None
    failure_reason: str | None = None


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    total: int
    page: int
    page_size: int
    pages: int
