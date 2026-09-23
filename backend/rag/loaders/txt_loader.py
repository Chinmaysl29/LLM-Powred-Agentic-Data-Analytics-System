"""TXT Document Loader for RAG ingestion.

Loads raw text, markdown, log, and documentation files with
automatic multi-encoding fallback (UTF-8, UTF-8-SIG, Latin-1, CP1252).
"""

import logging
from pathlib import Path
from typing import Any
from uuid import uuid4

from backend.app.schemas.document_loader import LoadedDocument
from backend.rag.loaders.base_loader import BaseDocumentLoader

logger = logging.getLogger(__name__)


class TxtLoader(BaseDocumentLoader):
    """Loader extracting text from plain text, markdown, and log files."""

    def supported_extensions(self) -> list[str]:
        return [".txt", ".log", ".md", ".rst"]

    def load(
        self,
        file_input: str | Path | bytes,
        filename: str | None = None,
        **kwargs: Any,
    ) -> LoadedDocument:
        raw_bytes, resolved_name = self._read_bytes_and_filename(file_input, filename)
        logger.info("Loading text document '%s' (%d bytes)", resolved_name, len(raw_bytes))

        # Decode with fallback encodings
        encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]
        decoded_text = ""
        used_encoding = "utf-8"

        for enc in encodings:
            try:
                decoded_text = raw_bytes.decode(enc)
                used_encoding = enc
                break
            except UnicodeDecodeError:
                continue

        if not decoded_text and raw_bytes:
            decoded_text = raw_bytes.decode("utf-8", errors="replace")

        ext = Path(resolved_name).suffix.lstrip(".").lower() or "txt"
        normalized_content = self.normalize_text(decoded_text)

        metadata = self.build_metadata(
            filename=resolved_name,
            file_type=ext,
            size=len(raw_bytes),
            content=normalized_content,
            extra={"encoding": used_encoding},
        )

        return LoadedDocument(
            document_id=str(uuid4()),
            content=normalized_content,
            metadata=metadata,
        )
