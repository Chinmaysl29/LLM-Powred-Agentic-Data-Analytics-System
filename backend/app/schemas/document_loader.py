"""Pydantic schemas for Phase 5.1 Document Loader Layer.

Defines data models for document ingestion, metadata extraction,
content normalization, and structured document representation for the RAG subsystem.
"""

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4
from pydantic import BaseModel, ConfigDict, Field


class DocumentMetadata(BaseModel):
    """Metadata extracted from ingested documents."""

    model_config = ConfigDict(from_attributes=True, extra="allow")

    filename: str = Field(..., description="Original filename of the document")
    file_type: str = Field(..., description="Normalized document format extension (e.g. pdf, docx, csv, xlsx, txt, json)")
    uploaded_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="UTC ISO timestamp of document ingestion",
    )
    size: int = Field(..., ge=0, description="Size of the raw document file in bytes")

    # Enriched analytical metadata
    page_count: int | None = Field(default=None, description="Number of pages (for PDF)")
    line_count: int | None = Field(default=None, description="Number of lines in normalized text")
    word_count: int | None = Field(default=None, description="Estimated total word count")
    char_count: int | None = Field(default=None, description="Total character count")
    sheet_names: list[str] | None = Field(default=None, description="List of worksheet names (for Excel)")
    row_count: int | None = Field(default=None, description="Number of rows (for tabular CSV/Excel)")
    column_count: int | None = Field(default=None, description="Number of columns (for tabular CSV/Excel)")
    title: str | None = Field(default=None, description="Document title extracted from document properties")
    author: str | None = Field(default=None, description="Document author extracted from document properties")


class LoadedDocument(BaseModel):
    """Standardized ingested document object ready for downstream RAG chunking and embedding."""

    model_config = ConfigDict(from_attributes=True)

    document_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique UUID identifier for the loaded document",
    )
    content: str = Field(..., description="Cleaned, normalized text content extracted from the file")
    metadata: DocumentMetadata = Field(..., description="Comprehensive file and structural metadata")

    @property
    def filename(self) -> str:
        """Convenience property to access metadata filename."""
        return self.metadata.filename



class DocumentUploadResponse(BaseModel):
    """API response envelope for a single document loading operation."""

    model_config = ConfigDict(from_attributes=True)

    status: str = Field(default="success", description="Status indicator")
    document: LoadedDocument = Field(..., description="Structured loaded document")


class BatchDocumentUploadResponse(BaseModel):
    """API response envelope for batch document loading operations."""

    model_config = ConfigDict(from_attributes=True)

    status: str = Field(default="success", description="Status indicator")
    total_loaded: int = Field(..., description="Total documents successfully parsed")
    documents: list[LoadedDocument] = Field(default_factory=list, description="Array of loaded documents")
    failed_files: list[dict[str, str]] = Field(
        default_factory=list, description="Records of any files that failed to parse"
    )
