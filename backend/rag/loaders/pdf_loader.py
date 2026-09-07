"""PDF Document Loader for RAG ingestion.

Uses pypdf with PyMuPDF (fitz) fallback to extract clean text,
page counts, and embedded document metadata.
"""

import io
import logging
from pathlib import Path
from typing import Any
from uuid import uuid4

import pypdf

from backend.app.schemas.document_loader import LoadedDocument
from backend.rag.loaders.base_loader import BaseDocumentLoader

logger = logging.getLogger(__name__)


class PDFLoader(BaseDocumentLoader):
    """Loader extracting structured text from PDF documents."""

    def supported_extensions(self) -> list[str]:
        return [".pdf"]

    def load(
        self,
        file_input: str | Path | bytes,
        filename: str | None = None,
        **kwargs: Any,
    ) -> LoadedDocument:
        raw_bytes, resolved_name = self._read_bytes_and_filename(file_input, filename)
        logger.info("Loading PDF document '%s' (%d bytes)", resolved_name, len(raw_bytes))

        text_pages: list[str] = []
        page_count = 0
        doc_title: str | None = None
        doc_author: str | None = None

        # Strategy 1: Primary extraction with pypdf
        try:
            stream = io.BytesIO(raw_bytes)
            reader = pypdf.PdfReader(stream)
            page_count = len(reader.pages)

            if reader.metadata:
                doc_title = reader.metadata.get("/Title") or reader.metadata.get("title")
                doc_author = reader.metadata.get("/Author") or reader.metadata.get("author")

            for i, page in enumerate(reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text_pages.append(page_text)
                except Exception as page_exc:
                    logger.warning("Could not extract page %d in '%s': %s", i + 1, resolved_name, page_exc)

        except Exception as pypdf_exc:
            logger.warning("pypdf parsing encountered issue on '%s': %s; attempting PyMuPDF fallback", resolved_name, pypdf_exc)

        # Strategy 2: High-fidelity fallback with PyMuPDF (fitz) if pypdf got empty content
        full_text = "\n\n".join(text_pages).strip()
        if not full_text:
            try:
                import fitz

                doc = fitz.open(stream=raw_bytes, filetype="pdf")
                page_count = len(doc)
                meta = doc.metadata or {}
                doc_title = doc_title or meta.get("title")
                doc_author = doc_author or meta.get("author")

                fallback_pages = []
                for page in doc:
                    fallback_pages.append(page.get_text("text"))
                full_text = "\n\n".join(fallback_pages)
                logger.info("PyMuPDF fallback extracted text across %d pages for '%s'", page_count, resolved_name)
            except Exception as fitz_exc:
                logger.warning("PyMuPDF fallback failed for '%s': %s", resolved_name, fitz_exc)

        normalized_content = self.normalize_text(full_text)
        metadata = self.build_metadata(
            filename=resolved_name,
            file_type="pdf",
            size=len(raw_bytes),
            content=normalized_content,
            page_count=page_count,
            title=doc_title,
            author=doc_author,
        )

        return LoadedDocument(
            document_id=str(uuid4()),
            content=normalized_content,
            metadata=metadata,
        )
