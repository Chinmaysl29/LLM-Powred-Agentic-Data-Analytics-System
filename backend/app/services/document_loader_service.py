"""Document Loader Service for RAG ingestion orchestration.

Provides high-level document ingestion interfaces for single files,
raw byte uploads, and directory batch processing across all supported formats.
"""

import logging
from pathlib import Path
from typing import Any

from backend.app.schemas.document_loader import LoadedDocument
from backend.rag.loaders.loader_factory import (
    DocumentLoaderFactory,
    get_default_loader_factory,
)

logger = logging.getLogger(__name__)


class DocumentLoaderService:
    """Service orchestrating document ingestion and normalization for RAG."""

    def __init__(self, factory: DocumentLoaderFactory | None = None) -> None:
        self._factory = factory or get_default_loader_factory()

    @property
    def factory(self) -> DocumentLoaderFactory:
        """Access loader factory."""
        return self._factory

    def load_file(
        self,
        file_path: str | Path,
        filename: str | None = None,
        **kwargs: Any,
    ) -> LoadedDocument:
        """Load and normalize a document from a local filesystem path."""
        path = Path(file_path)
        resolved_name = filename or path.name
        logger.info("DocumentLoaderService loading file: %s", path)
        return self._factory.load(file_input=path, filename=resolved_name, **kwargs)

    def load_bytes(
        self,
        content: bytes,
        filename: str,
        **kwargs: Any,
    ) -> LoadedDocument:
        """Load and normalize a document directly from raw uploaded bytes."""
        logger.info("DocumentLoaderService loading %d bytes as '%s'", len(content), filename)
        return self._factory.load(file_input=content, filename=filename, **kwargs)

    def load_directory(
        self,
        directory_path: str | Path,
        recursive: bool = True,
        extensions: list[str] | None = None,
        **kwargs: Any,
    ) -> list[LoadedDocument]:
        """Batch load all matching documents within a directory."""
        dir_path = Path(directory_path)
        if not dir_path.exists() or not dir_path.is_dir():
            raise NotADirectoryError(f"Directory not found or invalid: {dir_path}")

        allowed_exts = set(extensions or self._factory.supported_extensions())
        allowed_exts = {ext.lower().strip() for ext in allowed_exts}

        documents: list[LoadedDocument] = []
        pattern = "**/*" if recursive else "*"

        logger.info("Batch loading documents from directory '%s' (pattern=%s)", dir_path, pattern)

        for file_path in dir_path.glob(pattern):
            if file_path.is_file():
                if file_path.suffix.lower() in allowed_exts:
                    try:
                        doc = self.load_file(file_path=file_path, **kwargs)
                        documents.append(doc)
                    except Exception as exc:
                        logger.error("Failed to load file '%s': %s", file_path, exc, exc_info=True)

        logger.info("Batch loading completed: successfully parsed %d documents", len(documents))
        return documents

    def supported_extensions(self) -> list[str]:
        """Return all supported file extensions."""
        return self._factory.supported_extensions()


_service_instance = DocumentLoaderService()


def get_document_loader_service() -> DocumentLoaderService:
    """FastAPI dependency provider for DocumentLoaderService."""
    return _service_instance
