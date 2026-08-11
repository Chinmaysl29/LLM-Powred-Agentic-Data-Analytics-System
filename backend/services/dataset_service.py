from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from backend.core.config import settings


async def save_dataset(upload: UploadFile) -> dict:
    suffix = Path(upload.filename or "").suffix.lower()
    if suffix not in settings.allowed_extension_set:
        raise ValueError(f"Unsupported file type: {suffix or 'missing extension'}")

    dataset_id = str(uuid4())
    target = settings.upload_dir / f"{dataset_id}{suffix}"
    size = 0
    with target.open("wb") as destination:
        while chunk := await upload.read(1024 * 1024):
            size += len(chunk)
            if size > settings.max_upload_size_mb * 1024 * 1024:
                target.unlink(missing_ok=True)
                raise ValueError("Uploaded file exceeds the configured size limit")
            destination.write(chunk)

    return {
        "dataset_id": dataset_id,
        "filename": upload.filename or target.name,
        "path": str(target.relative_to(settings.upload_dir.parent)),
        "size_bytes": size,
        "uploaded_at": datetime.now(timezone.utc),
        "status": "uploaded",
    }
