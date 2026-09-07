"""Document Loader Factory for dynamic format dispatching.

Maintains a registry of specialized loaders and automatically routes
files to their appropriate parser based on file extension.
"""

import logging
from pathlib import Path
from typing import Any

from backend.app.schemas.document_loader import LoadedDocument
from backend.rag.loaders.base_loader import BaseDocumentLoader
from backend.rag.loaders.csv_loader import CSVLoader
from backend.rag.loaders.docx_loader import DocxLoader
from backend.rag.loaders.json_loader import JSONLoader
from backend.rag.loaders.pdf_loader import PDFLoader
from backend.rag.loaders.txt_loader import TxtLoader
from backend.rag.loaders.xlsx_loader import XlsxLoader

logger = logging.getLogger(__name__)


class DocumentLoaderFactory:
    """Factory and registry dispatching files to format-specific loaders."""

    def __init__(self) -> None:
        self._loaders: dict[str, BaseDocumentLoader] = {}
        self._default_loader = TxtLoader()
        self._register_core_loaders()

    def register_loader(self, loader: BaseDocumentLoader) -> None:
        """Register a loader for its declared extensions."""
        for ext in loader.supported_extensions():
            clean_ext = ext.lower().strip()
            if not clean_ext.startswith("."):
                clean_ext = f".{clean_ext}"
            self._loaders[clean_ext] = loader
            logger.debug("Registered %s for extension %s", loader.__class__.__name__, clean_ext)

    def get_loader(self, filename_or_ext: str) -> BaseDocumentLoader:
        """Retrieve the matching loader for a filename or extension."""
        path = Path(filename_or_ext)
        ext = path.suffix.lower() if path.suffix else filename_or_ext.lower()
        if not ext.startswith("."):
            ext = f".{ext}"

        loader = self._loaders.get(ext)
        if loader:
            return loader

        logger.warning("No specialized loader found for '%s'; falling back to plain text loader", ext)
        return self._default_loader

    def load(
        self,
        file_input: str | Path | bytes,
        filename: str | None = None,
        **kwargs: Any,
    ) -> LoadedDocument:
        """Resolve loader by filename and execute loading."""
        if isinstance(file_input, (str, Path)):
            resolved_filename = filename or Path(file_input).name
        else:
            resolved_filename = filename or "document.txt"

        loader = self.get_loader(resolved_filename)
        return loader.load(file_input=file_input, filename=resolved_filename, **kwargs)

    def supported_extensions(self) -> list[str]:
        """List all currently supported file extensions."""
        return list(self._loaders.keys())

    def _register_core_loaders(self) -> None:
        """Bootstrap the 6 core document loaders."""
        self.register_loader(PDFLoader())
        self.register_loader(DocxLoader())
        self.register_loader(TxtLoader())
        self.register_loader(CSVLoader())
        self.register_loader(XlsxLoader())
        self.register_loader(JSONLoader())


# Global default factory singleton
_default_factory = DocumentLoaderFactory()


def get_default_loader_factory() -> DocumentLoaderFactory:
    """Return the global DocumentLoaderFactory singleton."""
    return _default_factory
