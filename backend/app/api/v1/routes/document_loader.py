"""API routes for Document Loader Layer in RAG subsystem."""

import logging
from typing import Any
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from backend.app.schemas.document_loader import (
    BatchDocumentUploadResponse,
    DocumentUploadResponse,
    LoadedDocument,
)
from backend.app.services.document_loader_service import (
    DocumentLoaderService,
    get_document_loader_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["Document Loader"])


@router.post(
    "/load",
    response_model=DocumentUploadResponse,
    summary="Upload and extract structured content from a document",
)
async def load_single_document(
    file: UploadFile = File(..., description="Document file to parse (PDF, DOCX, CSV, XLSX, TXT, JSON)"),
    service: DocumentLoaderService = Depends(get_document_loader_service),
) -> DocumentUploadResponse:
    """Read an uploaded document, extract content and metadata, and return standardized LoadedDocument."""
    filename = file.filename or "uploaded_document"
    logger.info("Received document upload request for '%s'", filename)

    try:
        raw_bytes = await file.read()
        if not raw_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty",
            )

        document = service.load_bytes(content=raw_bytes, filename=filename)
        return DocumentUploadResponse(
            status="success",
            document=document,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to parse document '%s': %s", filename, exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load document '{filename}': {str(exc)}",
        )


@router.post(
    "/load-batch",
    response_model=BatchDocumentUploadResponse,
    summary="Upload and batch-load multiple documents",
)
async def load_batch_documents(
    files: list[UploadFile] = File(..., description="Multiple document files to parse"),
    service: DocumentLoaderService = Depends(get_document_loader_service),
) -> BatchDocumentUploadResponse:
    """Batch upload and parse multiple documents, aggregating results and errors."""
    logger.info("Received batch document upload request with %d files", len(files))

    loaded_docs: list[LoadedDocument] = []
    failed_files: list[dict[str, str]] = []

    for f in files:
        fname = f.filename or "unnamed_document"
        try:
            content_bytes = await f.read()
            if not content_bytes:
                failed_files.append({"filename": fname, "error": "File is empty"})
                continue

            doc = service.load_bytes(content=content_bytes, filename=fname)
            loaded_docs.append(doc)
        except Exception as exc:
            logger.warning("Error processing batch file '%s': %s", fname, exc)
            failed_files.append({"filename": fname, "error": str(exc)})

    return BatchDocumentUploadResponse(
        status="success" if loaded_docs else ("partial_success" if failed_files else "failed"),
        total_loaded=len(loaded_docs),
        documents=loaded_docs,
        failed_files=failed_files,
    )


@router.get(
    "/supported-formats",
    response_model=list[str],
    summary="List all supported document extensions",
)
async def get_supported_formats(
    service: DocumentLoaderService = Depends(get_document_loader_service),
) -> list[str]:
    """Return all document extensions supported by the loader layer."""
    return service.supported_extensions()
