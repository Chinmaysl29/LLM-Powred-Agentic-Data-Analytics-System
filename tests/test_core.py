"""
Tests for backend/app/core/ — config, exceptions, security (JWT + password hashing).
Covers every Settings field, every custom exception, and every security helper.
"""

import uuid
from datetime import timedelta
from unittest.mock import patch

import pytest

from backend.app.core.config import Settings, get_settings
from backend.app.core.exceptions import (
    ChromaConnectionError,
    CleaningRecommendationError,
    CorruptedFileError,
    DataProfilingError,
    DataQualityError,
    DataRetrievalError,
    DatasetNotFoundError,
    DatabaseConnectionError,
    DomainError,
    DuplicateVersionError,
    FileSizeExceededError,
    ForecastingDatasetValidationError,
    ForecastingError,
    InfrastructureError,
    IntentClassificationError,
    MetadataExtractionError,
    QualityAssessmentError,
    RecommendationError,
    RecommendationValidationError,
    RedisConnectionError,
    StorageError,
    StorageFileNotFoundError,
    UnsupportedFileTypeError,
    ValidationException,
    VersionNotFoundError,
    VersioningError,
)
from backend.app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
    verify_token,
)


# ===========================================================================
# Settings / Config Tests
# ===========================================================================

class TestSettings:
    """Tests for Settings model with default and override values."""

    def test_default_settings_are_valid(self):
        s = Settings(_env_file=None, environment="test")
        assert s.app_name in ("Enterprise AI Data Analyst OS", "AI Data Analyst OS")
        assert s.app_version == "1.0.0"
        assert s.environment == "test"
        assert s.debug is False

    def test_environment_normalises_testing_to_test(self):
        s = Settings(environment="testing")
        assert s.environment == "test"

    def test_environment_rejects_invalid(self):
        with pytest.raises(ValueError):
            Settings(environment="production_bad")

    def test_all_valid_environments_accepted(self):
        for env in ("development", "test", "staging", "production"):
            s = Settings(environment=env)
            assert s.environment == env

    def test_postgres_dsn_uses_database_url_override(self):
        s = Settings(
            environment="test",
            database_url="postgresql+psycopg://user:pass@host:5432/db",
        )
        assert s.postgres_dsn == "postgresql+psycopg://user:pass@host:5432/db"

    def test_postgres_dsn_built_from_parts(self):
        s = Settings(
            _env_file=None,
            environment="test",
            postgres_host="myhost",
            postgres_port=5433,
            postgres_db="mydb",
            postgres_user="myuser",
            postgres_password="mypass",
            database_url=None,
        )
        dsn = s.postgres_dsn
        assert "myhost" in dsn
        assert "mydb" in dsn
        assert "myuser" in dsn
        assert "5433" in dsn

    def test_allowed_extension_set_parses_correctly(self):
        s = Settings(environment="test", allowed_file_types="csv,xlsx,json,parquet")
        exts = s.allowed_extension_set
        assert ".csv" in exts
        assert ".xlsx" in exts
        assert ".json" in exts
        assert ".parquet" in exts

    def test_allowed_extension_strips_leading_dot(self):
        s = Settings(environment="test", allowed_file_types=".csv,.xlsx")
        exts = s.allowed_extension_set
        assert ".csv" in exts
        assert ".xlsx" in exts

    def test_upload_path_creates_directory(self, tmp_path):
        s = Settings(environment="test", upload_dir=str(tmp_path / "uploads"))
        path = s.upload_path
        assert path.exists()
        assert path.is_dir()

    def test_jwt_secret_key_is_secret_str(self):
        s = Settings(environment="test", jwt_secret_key="super-secret-key-123")
        secret_val = s.jwt_secret_key.get_secret_value()
        assert secret_val == "super-secret-key-123"

    def test_get_settings_returns_same_instance(self):
        """lru_cache must return the same singleton."""
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2

    def test_groq_api_key_optional(self):
        s = Settings(environment="test", groq_api_key=None)
        assert s.groq_api_key is None

    def test_rag_config_defaults(self):
        s = Settings(environment="test")
        assert s.rag_chunk_size == 1000
        assert s.rag_chunk_overlap == 200
        assert s.top_k_documents == 5

    def test_database_pool_bounds(self):
        with pytest.raises(Exception):
            Settings(environment="test", database_pool_size=0)


# ===========================================================================
# Exception Hierarchy Tests
# ===========================================================================

class TestInfrastructureExceptions:
    """Tests for InfrastructureError and its subclasses."""

    def test_infrastructure_error_base(self):
        exc = InfrastructureError("base infra error")
        assert exc.message == "base infra error"
        assert exc.error_code == "INFRASTRUCTURE_ERROR"
        assert str(exc) == "base infra error"

    def test_database_connection_error(self):
        exc = DatabaseConnectionError("db down")
        assert exc.error_code == "DATABASE_UNAVAILABLE"
        assert isinstance(exc, InfrastructureError)

    def test_redis_connection_error(self):
        exc = RedisConnectionError("redis down")
        assert exc.error_code == "REDIS_UNAVAILABLE"
        assert isinstance(exc, InfrastructureError)

    def test_chroma_connection_error(self):
        exc = ChromaConnectionError("chroma down")
        assert exc.error_code == "CHROMA_UNAVAILABLE"
        assert isinstance(exc, InfrastructureError)


class TestDomainExceptions:
    """Tests for DomainError hierarchy."""

    def test_domain_error_base(self):
        exc = DomainError("something went wrong", details={"key": "value"})
        assert exc.message == "something went wrong"
        assert exc.details == {"key": "value"}
        assert exc.error_code == "DOMAIN_ERROR"

    def test_dataset_not_found_error(self):
        exc = DatasetNotFoundError("not found")
        assert exc.error_code == "DATASET_NOT_FOUND"
        assert exc.status_code == 404
        assert isinstance(exc, DomainError)

    def test_corrupted_file_error(self):
        exc = CorruptedFileError("bad file")
        assert exc.error_code == "CORRUPTED_FILE"
        assert exc.status_code == 422

    def test_data_retrieval_error(self):
        exc = DataRetrievalError("retrieval fail")
        assert exc.error_code == "DATA_RETRIEVAL_ERROR"

    def test_storage_error_base(self):
        exc = StorageError("storage fail")
        assert exc.error_code == "STORAGE_ERROR"

    def test_unsupported_file_type_error(self):
        exc = UnsupportedFileTypeError("bad type")
        assert exc.error_code == "UNSUPPORTED_FILE_TYPE"
        assert exc.status_code == 400

    def test_file_size_exceeded_error(self):
        exc = FileSizeExceededError("too big")
        assert exc.error_code == "FILE_SIZE_EXCEEDED"
        assert exc.status_code == 400

    def test_storage_file_not_found_error(self):
        exc = StorageFileNotFoundError("missing file")
        assert exc.error_code == "STORAGE_FILE_NOT_FOUND"
        assert exc.status_code == 404
        assert isinstance(exc, FileNotFoundError)

    def test_metadata_extraction_error(self):
        exc = MetadataExtractionError("meta fail")
        assert exc.error_code == "METADATA_EXTRACTION_ERROR"

    def test_data_profiling_error(self):
        exc = DataProfilingError("profile fail")
        assert exc.error_code == "DATA_PROFILING_ERROR"

    def test_data_quality_error(self):
        exc = DataQualityError("quality fail")
        assert exc.error_code == "DATA_QUALITY_ERROR"

    def test_quality_assessment_error_is_data_quality_error(self):
        exc = QualityAssessmentError("qa fail")
        assert isinstance(exc, DataQualityError)

    def test_versioning_error(self):
        exc = VersioningError("versioning fail")
        assert exc.error_code == "VERSIONING_ERROR"

    def test_duplicate_version_error(self):
        exc = DuplicateVersionError("dup ver")
        assert exc.error_code == "DUPLICATE_VERSION"
        assert exc.status_code == 409

    def test_version_not_found_error(self):
        exc = VersionNotFoundError("ver not found")
        assert exc.error_code == "VERSION_NOT_FOUND"
        assert exc.status_code == 404

    def test_cleaning_recommendation_error(self):
        exc = CleaningRecommendationError("clean fail")
        assert exc.error_code == "CLEANING_RECOMMENDATION_ERROR"

    def test_intent_classification_error(self):
        exc = IntentClassificationError("intent fail")
        assert exc.error_code == "INTENT_CLASSIFICATION_ERROR"

    def test_validation_exception(self):
        exc = ValidationException("validation fail")
        assert exc.error_code == "VALIDATION_ERROR"
        assert exc.status_code == 422

    def test_forecasting_error(self):
        exc = ForecastingError("forecast fail")
        assert exc.error_code == "FORECASTING_ERROR"

    def test_forecasting_dataset_validation_error(self):
        exc = ForecastingDatasetValidationError("fc val fail")
        assert exc.error_code == "FORECASTING_VALIDATION_ERROR"
        assert isinstance(exc, ForecastingError)

    def test_recommendation_error(self):
        exc = RecommendationError("rec fail")
        assert exc.error_code == "RECOMMENDATION_ERROR"

    def test_recommendation_validation_error(self):
        exc = RecommendationValidationError("rec val fail")
        assert exc.error_code == "RECOMMENDATION_VALIDATION_ERROR"
        assert isinstance(exc, RecommendationError)


# ===========================================================================
# Security Tests — Password Hashing
# ===========================================================================

class TestPasswordHashing:
    """Tests for bcrypt hash_password / verify_password."""

    def test_hash_password_returns_non_empty_string(self):
        h = hash_password("mysecret")
        assert isinstance(h, str)
        assert len(h) > 20

    def test_hash_is_not_plaintext(self):
        h = hash_password("mysecret")
        assert h != "mysecret"

    def test_verify_correct_password_returns_true(self):
        h = hash_password("correct-horse-battery-staple")
        assert verify_password("correct-horse-battery-staple", h) is True

    def test_verify_wrong_password_returns_false(self):
        h = hash_password("correct-password")
        assert verify_password("wrong-password", h) is False

    def test_two_hashes_of_same_password_differ(self):
        h1 = hash_password("same")
        h2 = hash_password("same")
        # bcrypt uses random salt — hashes must differ
        assert h1 != h2

    def test_both_hashes_verify_against_same_plaintext(self):
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert verify_password("same", h1) is True
        assert verify_password("same", h2) is True

    def test_empty_string_can_be_hashed(self):
        # bcrypt handles empty strings — no crash expected
        h = hash_password("")
        assert verify_password("", h) is True


# ===========================================================================
# Security Tests — JWT create_access_token / verify_token
# ===========================================================================

class TestJWT:
    """Tests for JWT token creation and verification via core/security.py."""

    def _settings_with_secret(self) -> Settings:
        return Settings(
            environment="test",
            jwt_secret_key="test-secret-key-for-tests-only",
            jwt_algorithm="HS256",
            access_token_expire_minutes=60,
        )

    def test_create_access_token_returns_string(self):
        s = self._settings_with_secret()
        token = create_access_token({"sub": "user-1", "role": "analyst"}, settings=s)
        assert isinstance(token, str)
        assert len(token) > 10

    def test_verify_token_returns_payload(self):
        s = self._settings_with_secret()
        token = create_access_token({"sub": "user-99", "email": "x@x.com"}, settings=s)
        payload = verify_token(token, settings=s)
        assert payload["sub"] == "user-99"
        assert payload["email"] == "x@x.com"

    def test_token_contains_exp_and_iat(self):
        s = self._settings_with_secret()
        token = create_access_token({"sub": "u"}, settings=s)
        payload = verify_token(token, settings=s)
        assert "exp" in payload
        assert "iat" in payload

    def test_expired_token_raises(self):
        s = self._settings_with_secret()
        token = create_access_token(
            {"sub": "user-x"}, settings=s, expires_delta=timedelta(seconds=-1)
        )
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            verify_token(token, settings=s)
        assert exc_info.value.status_code == 401

    def test_invalid_token_string_raises(self):
        s = self._settings_with_secret()
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            verify_token("not.a.valid.token", settings=s)

    def test_wrong_secret_raises(self):
        s1 = self._settings_with_secret()
        s2 = Settings(
            environment="test",
            jwt_secret_key="completely-different-secret",
            jwt_algorithm="HS256",
        )
        token = create_access_token({"sub": "u"}, settings=s1)
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            verify_token(token, settings=s2)

    def test_custom_expiry_respected(self):
        s = self._settings_with_secret()
        long_token = create_access_token(
            {"sub": "u"}, settings=s, expires_delta=timedelta(hours=24)
        )
        payload = verify_token(long_token, settings=s)
        assert payload["sub"] == "u"

    def test_missing_jwt_secret_raises_runtime_error(self):
        s = Settings(environment="test", jwt_secret_key=None)
        with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
            create_access_token({"sub": "u"}, settings=s)
