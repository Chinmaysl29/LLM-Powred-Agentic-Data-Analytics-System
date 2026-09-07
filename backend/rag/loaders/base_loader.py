"""Base Document Loader class for the RAG ingestion pipeline.

Defines the abstract interface for all format-specific loaders and
provides universal text normalization and metadata enrichment utilities.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
import logging
from pathlib import Path
import re
from typing import Any
from uuid import uuid4

from backend.app.schemas.document_loader import DocumentMetadata, LoadedDocument

logger = logging.getLogger(__name__)


class BaseDocumentLoader(ABC):
    """Abstract base class that all file format loaders must implement."""

    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """Return list of lowercase file extensions supported by this loader (e.g. ['.pdf'])."""
        pass

    @abstractmethod
    def load(
        self,
        file_input: str | Path | bytes,
        filename: str | None = None,
        **kwargs: Any,
    ) -> LoadedDocument:
        """Parse raw file or path and return standardized LoadedDocument."""
        pass

    def _read_bytes_and_filename(
        self,
        file_input: str | Path | bytes,
        filename: str | None = None,
    ) -> tuple[bytes, str]:
        """Normalize file input into raw bytes and a resolved filename."""
        if isinstance(file_input, bytes):
            resolved_name = filename or f"document_{uuid4().hex[:8]}"
            return file_input, resolved_name

        path = Path(file_input)
        if not path.exists():
            raise FileNotFoundError(f"Document file not found at path: {path}")

        resolved_name = filename or path.name
        content_bytes = path.read_bytes()
        return content_bytes, resolved_name

    def normalize_text(self, raw_text: str) -> str:
        """Universal text cleaner for ingested document content.

        - Standardizes line endings to UNIX '\n'
        - Removes null bytes and non-printable control characters (except tabs & newlines)
        - Collapses excess blank lines to a maximum of 2
        - Strips trailing whitespace per line
        """
        if not raw_text:
            return ""

        # Remove null characters
        text = raw_text.replace("\x00", "")

        # Standardize line breaks
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Replace form feed / vertical tabs with clean newlines
        text = text.replace("\x0c", "\n\n").replace("\x0b", "\n")

        # Strip trailing whitespace on each line
        lines = [line.rstrip() for line in text.split("\n")]
        text = "\n".join(lines)

        # Collapse 3+ consecutive newlines into 2
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text.strip()

    def build_metadata(
        self,
        filename: str,
        file_type: str,
        size: int,
        content: str,
        page_count: int | None = None,
        sheet_names: list[str] | None = None,
        row_count: int | None = None,
        column_count: int | None = None,
        title: str | None = None,
        author: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> DocumentMetadata:
        """Construct a standardized DocumentMetadata instance with computed word/line counts."""
        line_count = len(content.split("\n")) if content else 0
        word_count = len(content.split()) if content else 0
        char_count = len(content)

        clean_type = file_type.lstrip(".").lower()

        meta_dict = {
            "filename": filename,
            "file_type": clean_type,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            "size": size,
            "page_count": page_count,
            "line_count": line_count,
            "word_count": word_count,
            "char_count": char_count,
            "sheet_names": sheet_names,
            "row_count": row_count,
            "column_count": column_count,
            "title": title,
            "author": author,
        }
        if extra:
            meta_dict.update(extra)

        return DocumentMetadata(**meta_dict)
