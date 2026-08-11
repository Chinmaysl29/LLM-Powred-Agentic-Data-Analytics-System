from datetime import datetime
from pydantic import BaseModel, ConfigDict


class DatasetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    dataset_id: str
    filename: str
    path: str
    size_bytes: int
    uploaded_at: datetime
    status: str
