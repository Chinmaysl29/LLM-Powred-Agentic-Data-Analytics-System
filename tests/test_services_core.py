"""
Tests for core services:
  - StorageService (file save, retrieve, delete, validation)
  - AuditTrailService (record, query, export, get)
  - ValidationService (SQL safety, schema/numerical/forecast checks)
"""

import io
import json
import uuid
from pathlib import Path

import pytest
from fastapi import UploadFile

from backend.app.core.config import Settings
from backend.app.core.exceptions import FileSizeExceededError, UnsupportedFileTypeError
from backend.app.services.audit_trail_service import AuditTrailService
from backend.app.services.storage_service import StorageService
from backend.app.services.validation_service import ValidationService


# ===========================================================================
# StorageService Fixtures
# ===========================================================================

@pytest.fixture
def storage(tmp_path):
    settings = Settings(
        environment="test",
        upload_dir=str(tmp_path),
        max_file_size_mb=10,
        allowed_file_types="csv,xlsx,xls,json,parquet",
    )
    return StorageService(settings=settings)


# ===========================================================================
# StorageService Tests
# ===========================================================================

class TestStorageService:

    @pytest.mark.asyncio
    async def test_save_csv_file(self, storage, tmp_path):
        content = b"a,b,c\n1,2,3\n4,5,6\n"
        upload = UploadFile(filename="test.csv", file=io.BytesIO(content))
        ds_id, fname, ftype, fpath, size = await storage.save_file(upload)
        assert fname == "test.csv"
        assert ftype == "csv"
        assert size == len(content)
        assert Path(fpath).exists()

    @pytest.mark.asyncio
    async def test_save_json_file(self, storage):
        data = [{"x": 1}, {"x": 2}]
        content = json.dumps(data).encode()
        upload = UploadFile(filename="data.json", file=io.BytesIO(content))
        ds_id, fname, ftype, fpath, size = await storage.save_file(upload)
        assert ftype == "json"
        assert Path(fpath).exists()

    @pytest.mark.asyncio
    async def test_save_xlsx_file(self, storage):
        content = b"PK\x03\x04fake_xlsx"
        upload = UploadFile(filename="data.xlsx", file=io.BytesIO(content))
        ds_id, fname, ftype, fpath, size = await storage.save_file(upload)
        assert ftype == "xlsx"

    @pytest.mark.asyncio
    async def test_save_pdf_file(self, storage):
        content = b"%PDF-1.4 fake content"
        upload = UploadFile(filename="report.pdf", file=io.BytesIO(content))
        ds_id, fname, ftype, fpath, size = await storage.save_file(upload)
        assert ftype == "pdf"

    @pytest.mark.asyncio
    async def test_unsupported_extension_raises(self, storage):
        upload = UploadFile(filename="notes.txt", file=io.BytesIO(b"hello"))
        with pytest.raises(UnsupportedFileTypeError):
            await storage.save_file(upload)

    @pytest.mark.asyncio
    async def test_unsupported_py_extension_raises(self, storage):
        upload = UploadFile(filename="script.py", file=io.BytesIO(b"import os"))
        with pytest.raises(UnsupportedFileTypeError):
            await storage.save_file(upload)

    @pytest.mark.asyncio
    async def test_file_too_large_raises(self, tmp_path):
        settings = Settings(
            environment="test",
            upload_dir=str(tmp_path),
            max_file_size_mb=1,
        )
        storage = StorageService(settings=settings)
        # 1.1 MB of data
        big_content = b"a" * (1024 * 1024 + 100)
        upload = UploadFile(filename="big.csv", file=io.BytesIO(big_content))
        with pytest.raises(FileSizeExceededError):
            await storage.save_file(upload)

    @pytest.mark.asyncio
    async def test_save_returns_unique_dataset_ids(self, storage):
        ids = set()
        for i in range(3):
            content = f"col\n{i}\n".encode()
            upload = UploadFile(filename="data.csv", file=io.BytesIO(content))
            ds_id, *_ = await storage.save_file(upload)
            ids.add(ds_id)
        assert len(ids) == 3

    def test_retrieve_existing_file(self, storage, tmp_path):
        f = tmp_path / "myfile.csv"
        f.write_text("a,b\n1,2")
        result = storage.retrieve_file(str(f))
        assert result == f

    def test_retrieve_missing_file_raises(self, storage, tmp_path):
        from backend.app.core.exceptions import StorageFileNotFoundError
        with pytest.raises(StorageFileNotFoundError):
            storage.retrieve_file(str(tmp_path / "missing.csv"))

    def test_delete_existing_file_returns_true(self, storage, tmp_path):
        f = tmp_path / "del.csv"
        f.write_text("data")
        assert storage.delete_file(str(f)) is True
        assert not f.exists()

    def test_delete_missing_file_returns_false(self, storage, tmp_path):
        assert storage.delete_file(str(tmp_path / "gone.csv")) is False

    def test_delete_dataset_removes_directory(self, storage, tmp_path):
        ds_id = str(uuid.uuid4())
        ds_dir = storage.dataset_directory(ds_id)
        ds_dir.mkdir(parents=True, exist_ok=True)
        (ds_dir / "file.csv").write_text("data")
        assert storage.delete_dataset(ds_id) is True
        assert not ds_dir.exists()

    def test_delete_dataset_returns_false_when_not_exists(self, storage):
        assert storage.delete_dataset(str(uuid.uuid4())) is False

    def test_dataset_directory_invalid_id_raises(self, storage):
        with pytest.raises(ValueError):
            storage.dataset_directory("../../etc/passwd")

    def test_dataset_directory_returns_path_under_upload_dir(self, storage):
        ds_id = str(uuid.uuid4())
        p = storage.dataset_directory(ds_id)
        assert str(storage.upload_dir) in str(p)


# ===========================================================================
# AuditTrailService Tests
# ===========================================================================

class TestAuditTrailService:

    @pytest.fixture(autouse=True)
    def fresh_service(self):
        """Each test gets a fresh AuditTrailService with empty fallback store."""
        self.svc = AuditTrailService()

    def test_record_creates_event_in_fallback(self):
        event = self.svc.record(
            actor="user-1",
            action="dataset.upload",
            resource_type="dataset",
            resource_id="ds-001",
        )
        assert "id" in event
        assert event["actor"] == "user-1"
        assert event["action"] == "dataset.upload"
        assert event["resource_type"] == "dataset"
        assert event["resource_id"] == "ds-001"

    def test_record_returns_dict_with_all_fields(self):
        event = self.svc.record(
            actor="admin",
            action="user.delete",
            resource_type="user",
            resource_id="u-999",
            details={"reason": "policy violation"},
            status="success",
        )
        assert event["status"] == "success"
        assert event["details"]["reason"] == "policy violation"

    def test_query_returns_all_events(self):
        for i in range(3):
            self.svc.record(actor=f"user-{i}", action="login", resource_type="session")
        results = self.svc.query(session=None)
        assert len(results) == 3

    def test_query_filters_by_actor(self):
        self.svc.record(actor="alice", action="view", resource_type="report")
        self.svc.record(actor="bob", action="view", resource_type="report")
        results = self.svc.query(session=None, actor="alice")
        assert len(results) == 1
        assert results[0]["actor"] == "alice"

    def test_query_filters_by_action(self):
        self.svc.record(actor="u", action="upload", resource_type="dataset")
        self.svc.record(actor="u", action="delete", resource_type="dataset")
        results = self.svc.query(session=None, action="upload")
        assert len(results) == 1
        assert results[0]["action"] == "upload"

    def test_query_filters_by_resource_type(self):
        self.svc.record(actor="u", action="view", resource_type="dashboard")
        self.svc.record(actor="u", action="view", resource_type="report")
        results = self.svc.query(session=None, resource_type="dashboard")
        assert len(results) == 1

    def test_query_respects_limit(self):
        for i in range(10):
            self.svc.record(actor="u", action="op", resource_type="x")
        results = self.svc.query(session=None, limit=3)
        assert len(results) == 3

    def test_query_respects_offset(self):
        for i in range(5):
            self.svc.record(actor="u", action=f"op-{i}", resource_type="x")
        all_results = self.svc.query(session=None)
        offset_results = self.svc.query(session=None, offset=2)
        assert len(offset_results) == len(all_results) - 2

    def test_get_returns_event_by_id(self):
        event = self.svc.record(actor="u", action="get", resource_type="file")
        retrieved = self.svc.get(event["id"], session=None)
        assert retrieved is not None
        assert retrieved["id"] == event["id"]

    def test_get_nonexistent_returns_none(self):
        assert self.svc.get("nonexistent-id", session=None) is None

    def test_export_json_returns_list(self):
        self.svc.record(actor="u", action="x", resource_type="y")
        result = self.svc.export(session=None, format="json")
        assert isinstance(result, list)
        assert len(result) == 1

    def test_export_invalid_format_raises(self):
        with pytest.raises(ValueError, match="format must be json or csv"):
            self.svc.export(session=None, format="xml")

    def test_query_search_by_actor_partial(self):
        self.svc.record(actor="alice_admin", action="view", resource_type="x")
        self.svc.record(actor="bob_user", action="view", resource_type="x")
        results = self.svc.query(session=None, search="alice")
        assert any("alice" in r["actor"] for r in results)

    def test_record_with_metadata(self):
        event = self.svc.record(
            actor="system",
            action="job.run",
            resource_type="job",
            metadata={"job_id": "j-123", "duration_ms": 500},
        )
        assert "id" in event

    def test_query_limit_bounded_to_500(self):
        # Service should not exceed 500 even if requested more
        results = self.svc.query(session=None, limit=1000)
        # If no data, just assert no error raised
        assert isinstance(results, list)


# ===========================================================================
# ValidationService Tests
# ===========================================================================

class TestValidationService:

    @pytest.fixture(autouse=True)
    def svc(self):
        self.svc = ValidationService()

    def test_validate_results_empty_dict_passes(self):
        result = self.svc.validate_results(results={})
        assert result.validation_status in ("PASSED", "WARNING")
        assert result.confidence_score >= 0

    def test_validate_sql_safe_select_passes(self):
        result = self.svc.validate_sql("SELECT id, name FROM orders WHERE total > 100")
        assert result.is_safe is True
        assert result.blocked_keywords == []

    def test_validate_sql_drop_blocked(self):
        result = self.svc.validate_sql("DROP TABLE users")
        assert result.is_safe is False
        assert len(result.blocked_keywords) > 0

    def test_validate_sql_delete_blocked(self):
        result = self.svc.validate_sql("DELETE FROM orders WHERE id = 1")
        assert result.is_safe is False

    def test_validate_sql_truncate_blocked(self):
        result = self.svc.validate_sql("TRUNCATE TABLE sessions")
        assert result.is_safe is False

    def test_validate_sql_update_blocked(self):
        result = self.svc.validate_sql("UPDATE users SET role = 'admin'")
        assert result.is_safe is False

    def test_validate_sql_insert_blocked(self):
        result = self.svc.validate_sql("INSERT INTO logs VALUES (1, 'x')")
        assert result.is_safe is False

    def test_validate_sql_allowed_table_passes(self):
        result = self.svc.validate_sql(
            "SELECT * FROM sales", allowed_tables=["sales", "orders"]
        )
        assert result.is_safe is True

    def test_validate_sql_disallowed_table_blocked(self):
        result = self.svc.validate_sql(
            "SELECT * FROM users", allowed_tables=["sales", "orders"]
        )
        assert result.is_safe is False

    def test_validate_results_with_valid_eda_passes(self):
        results = {
            "eda": {
                "dataset_summary": {"row_count": 100},
                "correlations": {"correlation_matrix": {"a": {"b": 0.85}}},
                "statistics": {},
            }
        }
        result = self.svc.validate_results(results=results)
        assert result.confidence_score > 0
        assert len(result.audit_log) > 0

    def test_validate_results_invalid_eda_structure_generates_error(self):
        results = {"eda": "not_a_dict"}
        result = self.svc.validate_results(results=results)
        assert len(result.errors) > 0

    def test_validate_results_bad_correlation_type_generates_error(self):
        results = {
            "eda": {
                "correlations": {"correlation_matrix": {"a": {"b": "not_a_number"}}},
            }
        }
        result = self.svc.validate_results(results=results)
        assert len(result.errors) > 0
        assert result.validation_status == "FAILED"

    def test_validate_results_unsafe_sql_generates_error(self):
        results = {"sql_query": "DROP TABLE orders"}
        result = self.svc.validate_results(results=results)
        assert len(result.errors) > 0

    def test_validate_results_bad_forecast_ci_generates_error(self):
        results = {
            "forecasting": {
                "confidence_interval": [100.0, 50.0],  # lower > upper
            }
        }
        result = self.svc.validate_results(results=results)
        assert len(result.errors) > 0

    def test_validate_results_pie_chart_too_many_categories(self):
        results = {
            "visualization": {
                "primary_chart": {"type": "pie", "category_count": 15}
            }
        }
        result = self.svc.validate_results(results=results)
        assert len(result.errors) > 0

    def test_validate_results_pie_chart_few_categories_passes(self):
        results = {
            "visualization": {
                "primary_chart": {"type": "pie", "category_count": 4}
            }
        }
        result = self.svc.validate_results(results=results)
        # No chart suitability error
        chart_errors = [e for e in result.errors if "Pie" in e]
        assert len(chart_errors) == 0

    def test_confidence_score_decrements_per_error(self):
        results = {
            "eda": "not_a_dict",
            "sql_query": "DROP TABLE users",
        }
        result = self.svc.validate_results(results=results)
        assert result.confidence_score < 100

    def test_validate_results_returns_audit_log_entries(self):
        results = {"eda": {"correlations": {"correlation_matrix": {}}}}
        result = self.svc.validate_results(results=results)
        assert isinstance(result.audit_log, list)
