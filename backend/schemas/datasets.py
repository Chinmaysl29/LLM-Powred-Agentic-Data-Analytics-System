"""Dataset response schemas (backward-compatible alias for app schemas)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DatasetResponse(BaseModel):
    """Schema representing a persisted dataset entity."""

    model_config = ConfigDict(from_attributes=True)

    dataset_id: str
    dataset_name: str | None = None
    file_name: str | None = None
    file_type: str | None = None
    file_path: str | None = None
    version: int = 1
    status: str = "uploaded"
    created_at: datetime | None = None
    updated_at: datetime | None = None
