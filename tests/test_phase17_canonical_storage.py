"""Phase 17.11 canonical storage contracts."""

import asyncio
import io
import json
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.core.config import Settings
from backend.app.models.base import Base
from backend.app.models.dataset import Dataset
from backend.app.repositories.dataset_repository import DatasetRepository
from backend.app.services.dataset_json_service import DatasetJsonService
from backend.app.services.dataset_loader import DatasetLoader
from backend.app.services.storage_service import StorageService


def test_canonical_json_parquet_and_loader(tmp_path: Path):
    async def scenario():
        storage = StorageService(Settings(_env_file=None, upload_dir=str(tmp_path)))
        uploaded = UploadFile(filename="sales.csv", file=io.BytesIO(b"product,revenue\nA,10\nB,20\n"))
        dataset_id, name, kind, original_path, size = await storage.save_file(uploaded)
        artifacts = DatasetJsonService(storage).materialize(dataset_id, "Sales", original_path, kind)
        assert Path(artifacts["json_path"]).exists()
        payload = json.loads(Path(artifacts["json_path"]).read_text(encoding="utf-8"))
        assert payload["records"][0]["product"] == "A"
        dataset = Dataset(dataset_id=dataset_id, dataset_name="Sales", file_name=name, file_type=kind, file_path=original_path, original_path=original_path, size_bytes=size, **artifacts)
        loaded = DatasetLoader().load_dataframe(dataset)
        assert list(loaded["revenue"]) == [10, 20]
    asyncio.run(scenario())


def test_dataset_registry_persists_canonical_paths():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    repo = DatasetRepository(session)
    dataset = Dataset(dataset_id="catalog-1", dataset_name="Catalog", file_name="a.csv", file_type="csv", file_path="/source/a.csv", original_path="/source/a.csv", json_path="/artifacts/data.json", canonical_path="/canonical/data.parquet", canonical_format="parquet", content_hash="a" * 64, row_count=2, column_count=3, status="ready")
    repo.create(dataset)
    stored = repo.get("catalog-1")
    assert stored and stored.canonical_format == "parquet" and stored.row_count == 2
