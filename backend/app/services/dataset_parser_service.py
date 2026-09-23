"""Parse supported source files into safe tabular or document representations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


@dataclass
class ParsedDataset:
    dataframe: pd.DataFrame | None
    document: dict[str, Any] | None = None


class DatasetParserService:
    """Single parser boundary for CSV, Excel, JSON, and PDF uploads."""

    def parse(self, path: str | Path, file_type: str) -> ParsedDataset:
        source = Path(path)
        normalized_type = file_type.lower().lstrip(".")
        if normalized_type == "csv":
            return ParsedDataset(pd.read_csv(source))
        if normalized_type in {"xlsx", "xls"}:
            return ParsedDataset(pd.read_excel(source))
        if normalized_type == "json":
            return ParsedDataset(pd.read_json(source))
        if normalized_type == "pdf":
            return ParsedDataset(None, self._parse_pdf(source))
        raise ValueError(f"Unsupported dataset file type: {file_type}")

    @staticmethod
    def _parse_pdf(source: Path) -> dict[str, Any]:
        try:
            import fitz
        except ImportError as exc:  # pragma: no cover - production dependency
            raise RuntimeError("PDF parsing requires PyMuPDF") from exc
        document = fitz.open(source)
        pages: list[dict[str, Any]] = []
        tables: list[dict[str, Any]] = []
        for number, page in enumerate(document, start=1):
            pages.append({"page": number, "text": page.get_text("text")})
            try:
                for table in page.find_tables().tables:
                    tables.append({"page": number, "records": table.extract()})
            except (AttributeError, RuntimeError):
                pass
        return {"pages": pages, "tables": tables}
