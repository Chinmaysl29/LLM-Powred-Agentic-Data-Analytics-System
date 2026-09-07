"""JSON Document Loader for RAG ingestion.

Parses JSON and JSONL files, formatting nested data structures
into clean, hierarchical, and semantically searchable text.
"""

import json
import logging
from pathlib import Path
from typing import Any
from uuid import uuid4

from backend.app.schemas.document_loader import LoadedDocument
from backend.rag.loaders.base_loader import BaseDocumentLoader

logger = logging.getLogger(__name__)


class JSONLoader(BaseDocumentLoader):
    """Loader parsing JSON and JSONL documents into readable text."""

    def supported_extensions(self) -> list[str]:
        return [".json", ".jsonl"]

    def load(
        self,
        file_input: str | Path | bytes,
        filename: str | None = None,
        **kwargs: Any,
    ) -> LoadedDocument:
        raw_bytes, resolved_name = self._read_bytes_and_filename(file_input, filename)
        logger.info("Loading JSON document '%s' (%d bytes)", resolved_name, len(raw_bytes))

        # Decode
        try:
            text_data = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            text_data = raw_bytes.decode("latin-1")

        is_jsonl = resolved_name.endswith(".jsonl")
        item_count = 0
        sections: list[str] = [f"# JSON Document: {resolved_name}", ""]

        if is_jsonl:
            lines = text_data.strip().split("\n")
            item_count = len(lines)
            sections.append(f"JSON Lines Records ({item_count:,}):\n")
            for i, line in enumerate(lines[:1000]):
                line_str = line.strip()
                if line_str:
                    try:
                        parsed = json.loads(line_str)
                        sections.append(f"Record {i + 1}: {json.dumps(parsed, indent=2)}")
                    except Exception:
                        sections.append(f"Record {i + 1}: {line_str}")
        else:
            try:
                data = json.loads(text_data)
                if isinstance(data, list):
                    item_count = len(data)
                    sections.append(f"Array of {item_count} Items:\n")
                elif isinstance(data, dict):
                    item_count = len(data.keys())
                    sections.append(f"Object with {item_count} Root Keys:\n")
                sections.append(json.dumps(data, indent=2, ensure_ascii=False))
            except json.JSONDecodeError as exc:
                logger.warning("Could not parse JSON in '%s': %s; falling back to raw text", resolved_name, exc)
                sections.append(text_data)

        full_text = "\n".join(sections)
        normalized_content = self.normalize_text(full_text)

        ext = "jsonl" if is_jsonl else "json"
        metadata = self.build_metadata(
            filename=resolved_name,
            file_type=ext,
            size=len(raw_bytes),
            content=normalized_content,
            extra={"record_count": item_count},
        )

        return LoadedDocument(
            document_id=str(uuid4()),
            content=normalized_content,
            metadata=metadata,
        )
