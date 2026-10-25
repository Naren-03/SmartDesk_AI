from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class DocumentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class DocumentMetadata(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str | None = None
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    owner_id: str
    filename: str | None = None
    content_type: str | None = None
    size_bytes: int | None = Field(default=None, ge=0)
    storage_key: str | None = None
    checksum_sha256: str | None = None
    status: DocumentStatus = DocumentStatus.PENDING
    created_at: datetime
    updated_at: datetime
    processed_at: datetime | None = None
    failure_reason: str | None = None
