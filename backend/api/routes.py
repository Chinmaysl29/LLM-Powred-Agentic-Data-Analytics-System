from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.schemas.datasets import DatasetResponse
from backend.services.dataset_service import save_dataset

router = APIRouter()


@router.post("/datasets/upload", response_model=DatasetResponse, status_code=201, tags=["datasets"])
async def upload_dataset(file: UploadFile = File(...)) -> DatasetResponse:
    try:
        return await save_dataset(file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
