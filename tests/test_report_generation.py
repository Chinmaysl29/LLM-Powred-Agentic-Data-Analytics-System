"""Tests for Phase 8.4: Report Generation Engine."""

import os
from pathlib import Path
import pytest
from backend.reports.report_generator import ReportGenerator


@pytest.fixture
def generator(tmp_path):
    return ReportGenerator(output_dir=tmp_path)


def test_generate_executive_pdf_valid(generator):
    """Test Case: Generate Executive PDF -> file exists and is valid."""
    result = generator.generate(
        report_type="Executive Summary",
        format_type="pdf",
        title="Q3 Executive Performance Brief",
    )
    assert "report_id" in result
    assert result["report_id"].startswith("rep_")
    assert "file_url" in result
    assert result["file_url"].endswith(".pdf")

    # File must exist on disk and be non-empty
    file_path = Path(result["file_path"])
    assert file_path.exists()
    assert file_path.stat().st_size > 1000

    # Verify PDF magic bytes
    with open(file_path, "rb") as f:
        header = f.read(5)
    assert header == b"%PDF-"


def test_generate_docx_report(generator):
    """Verify DOCX document generation."""
    result = generator.generate(
        report_type="Analytics Report",
        format_type="docx",
    )
    assert result["format"] == "docx"
    file_path = Path(result["file_path"])
    assert file_path.exists()
    assert file_path.stat().st_size > 500


def test_generate_excel_report(generator):
    """Verify Excel workbook generation."""
    result = generator.generate(
        report_type="Forecast Report",
        format_type="xlsx",
    )
    assert result["format"] == "xlsx"
    file_path = Path(result["file_path"])
    assert file_path.exists()
    assert file_path.stat().st_size > 500


def test_generate_pptx_report(generator):
    """Verify PowerPoint presentation generation."""
    result = generator.generate(
        report_type="Recommendations Report",
        format_type="pptx",
    )
    assert result["format"] == "pptx"
    file_path = Path(result["file_path"])
    assert file_path.exists()
    assert file_path.stat().st_size > 500


def test_all_four_report_types(generator):
    """Verify all 4 required report types run without errors."""
    types = [
        "Executive Summary",
        "Analytics Report",
        "Forecast Report",
        "Recommendations Report",
    ]
    for rt in types:
        res = generator.generate(report_type=rt, format_type="pdf")
        assert Path(res["file_path"]).exists()
