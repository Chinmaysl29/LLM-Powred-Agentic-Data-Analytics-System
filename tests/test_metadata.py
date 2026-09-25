"""Dedicated unit tests for Phase 2.3 Metadata Extraction & Persistence."""

import io
import json
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.config import Settings
from backend.app.core.exceptions import MetadataExtractionError
from backend.app.models.base import Base
from backend.app.models.dataset import Dataset
from backend.app.models.dataset_metadata import DatasetMetadata
from backend.app.repositories.dataset_metadata_repository import DatasetMetadataRepository
from backend.app.repositories.dataset_repository import DatasetRepository
from backend.app.services.metadata_extraction_service import MetadataExtractionService
from backend.app.services.metadata_service import MetadataService
from backend.app.services.storage_service import StorageService


@pytest.fixture
def in_memory_db() -> Session:
    """Isolated in-memory SQLite database for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def storage_service(tmp_path: Path) -> StorageService:
    settings = Settings(_env_file=None, upload_dir=str(tmp_path), max_file_size_mb=10)
    return StorageService(settings=settings)


@pytest.fixture
def metadata_service(storage_service: StorageService) -> MetadataExtractionService:
    return MetadataExtractionService(storage_service=storage_service)


def test_checklist_alias_compatibility(storage_service: StorageService) -> None:
    """Checklist alias MetadataService is identical to MetadataExtractionService."""
    assert MetadataService is MetadataExtractionService
    instance = MetadataService(storage_service=storage_service)
    assert isinstance(instance, MetadataExtractionService)


def test_metadata_extraction_csv(
    metadata_service: MetadataExtractionService, tmp_path: Path
) -> None:
    """Extract metadata accurately from a CSV file."""
    csv_file = tmp_path / "sample.csv"
    csv_file.write_text(
        "id,name,age,salary,is_active\n"
        "1,Alice,30,75000.5,true\n"
        "2,Bob,,60000.0,false\n"
        "3,Charlie,25,,true\n"
    )

    metadata = metadata_service.extract_metadata("ds-1", str(csv_file), "csv")

    assert metadata.dataset_id == "ds-1"
    assert metadata.row_count == 3
    assert metadata.column_count == 5
    assert metadata.column_names == ["id", "name", "age", "salary", "is_active"]

    # Check ColumnMetadata stats
    col_map = {col.name: col for col in metadata.columns_metadata}
    assert col_map["age"].null_count == 1
    assert col_map["age"].null_percentage == pytest.approx(1 / 3)
    assert col_map["salary"].null_count == 1
    assert col_map["name"].null_count == 0

    # Check classifications
    assert "id" in metadata.classifications.numeric
    assert "name" in metadata.classifications.categorical
    assert "is_active" in metadata.classifications.boolean


def test_metadata_extraction_json(
    metadata_service: MetadataExtractionService, tmp_path: Path
) -> None:
    """Extract metadata accurately from a JSON records file."""
    json_file = tmp_path / "records.json"
    data = [
        {"product": "Laptop", "price": 1200, "in_stock": True},
        {"product": "Mouse", "price": 25, "in_stock": True},
        {"product": "Keyboard", "price": 75, "in_stock": False},
    ]
    json_file.write_text(json.dumps(data))

    metadata = metadata_service.extract_metadata("ds-json", str(json_file), "json")

    assert metadata.dataset_id == "ds-json"
    assert metadata.row_count == 3
    assert metadata.column_count == 3
    assert set(metadata.column_names) == {"product", "price", "in_stock"}
    assert "product" in metadata.classifications.categorical
    assert "price" in metadata.classifications.numeric
    assert "in_stock" in metadata.classifications.boolean


def test_metadata_extraction_xlsx(
    metadata_service: MetadataExtractionService, tmp_path: Path
) -> None:
    """Extract metadata accurately from an Excel XLSX file."""
    xlsx_file = tmp_path / "data.xlsx"
    df = pd.DataFrame({
        "order_id": [101, 102],
        "customer": ["Acme", "Beta"],
        "amount": [99.5, 149.0],
    })
    df.to_excel(xlsx_file, index=False)

    metadata = metadata_service.extract_metadata("ds-xlsx", str(xlsx_file), "xlsx")

    assert metadata.dataset_id == "ds-xlsx"
    assert metadata.row_count == 2
    assert metadata.column_count == 3
    assert "order_id" in metadata.column_names


def test_metadata_extraction_unsupported_type(
    metadata_service: MetadataExtractionService, tmp_path: Path
) -> None:
    """Extracting metadata from an unsupported file type raises MetadataExtractionError / ValueError."""
    txt_file = tmp_path / "plain.txt"
    txt_file.write_text("just text")

    with pytest.raises((MetadataExtractionError, ValueError)):
        metadata_service.extract_metadata("ds-invalid", str(txt_file), "txt")


def test_dataset_metadata_repository_crud(in_memory_db: Session) -> None:
    """DatasetMetadataRepository can create, get, update, and delete metadata."""
    dataset_repo = DatasetRepository(db=in_memory_db)
    dataset = Dataset(
        dataset_id="meta-ds",
        dataset_name="Meta Test",
        file_name="meta.csv",
        file_type="csv",
        file_path="/path/meta.csv",
        version=1,
        status="uploaded",
    )
    dataset_repo.create(dataset)

    meta_repo = DatasetMetadataRepository(db=in_memory_db)
    meta_record = DatasetMetadata(
        dataset_id="meta-ds",
        row_count=100,
        column_count=5,
        column_names=["a", "b", "c", "d", "e"],
        column_types={"a": "int64", "b": "object", "c": "float64", "d": "bool", "e": "datetime64"},
        columns_metadata=[{"name": "a", "type": "int64", "null_count": 0, "null_percentage": 0.0, "unique_count": 100}],
        classifications={"numeric": ["a", "c"], "categorical": ["b"], "datetime": ["e"], "boolean": ["d"]},
    )

    created = meta_repo.create(meta_record)
    assert created.dataset_id == "meta-ds"
    assert created.row_count == 100

    retrieved = meta_repo.get("meta-ds")
    assert retrieved is not None
    assert retrieved.row_count == 100
    assert len(retrieved.column_names) == 5

    updated = meta_repo.update("meta-ds", row_count=150)
    assert updated is not None
    assert updated.row_count == 150

    assert meta_repo.delete("meta-ds") is True
    assert meta_repo.get("meta-ds") is None
    assert meta_repo.delete("non-existent") is False
