from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "text/plain",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
CHUNK_SIZE = 1024 * 1024


class LocalStorageService:
    def __init__(self, root: str | Path, max_size_bytes: int):
        self.root = Path(root)
        self.max_size_bytes = max_size_bytes

    async def save_upload(
        self,
        upload: UploadFile,
        owner_id: str,
        document_id: str,
    ) -> dict[str, str | int]:
        if upload.content_type not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Unsupported document type",
            )

        original_name = Path(upload.filename or "document").name
        extension = Path(original_name).suffix.lower()
        storage_name = f"{document_id}-{uuid4().hex}{extension}"
        storage_key = f"{owner_id}/{storage_name}"
        destination = self.root / owner_id / storage_name
        destination.parent.mkdir(parents=True, exist_ok=True)

        checksum = sha256()
        size_bytes = 0
        try:
            with destination.open("wb") as output:
                while chunk := await upload.read(CHUNK_SIZE):
                    size_bytes += len(chunk)
                    if size_bytes > self.max_size_bytes:
                        raise HTTPException(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail="Document exceeds the maximum allowed size",
                        )
                    checksum.update(chunk)
                    output.write(chunk)
        except Exception:
            destination.unlink(missing_ok=True)
            raise
        finally:
            await upload.close()

        return {
            "filename": original_name,
            "content_type": upload.content_type,
            "size_bytes": size_bytes,
            "storage_key": storage_key,
            "checksum_sha256": checksum.hexdigest(),
        }

    def delete(self, storage_key: str | None) -> None:
        if not storage_key:
            return

        candidate = (self.root / storage_key).resolve()
        root = self.root.resolve()
        if root not in candidate.parents:
            raise ValueError("Storage key escapes the storage root")
        candidate.unlink(missing_ok=True)
