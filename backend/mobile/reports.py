"""
Phase 12.8.5 — Mobile Reports Module
Provides mobile-friendly report previewing (PDF, Excel, PowerPoint),
secure deep-link sharing, and offline download bundling.
"""

from typing import Dict, Any, List, Optional
import time
import uuid
import logging
from pydantic import BaseModel, Field

logger = logging.getLogger("backend.mobile.reports")


class MobileReportItem(BaseModel):
    report_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    format: str # "pdf", "excel", "pptx"
    category: str
    file_size_kb: float
    created_at: float = Field(default_factory=time.time)
    download_url: str
    preview_data: Dict[str, Any] = Field(default_factory=dict)


class MobileReportsService:
    """
    Manages document viewing, multi-format previews, mobile sharing links,
    and mobile download bundles.
    """

    def __init__(self):
        self._reports: Dict[str, MobileReportItem] = {}
        self._init_sample_reports()

    def _init_sample_reports(self):
        pdf_rep = MobileReportItem(
            report_id="rep-pdf-q3",
            title="Q3 Executive Financial Summary",
            format="pdf",
            category="finance",
            file_size_kb=1420.5,
            download_url="/api/v1/mobile/reports/rep-pdf-q3/download",
            preview_data={"page_count": 14, "table_of_contents": ["Revenue", "COGS", "EBITDA", "Outlook"]}
        )
        excel_rep = MobileReportItem(
            report_id="rep-xls-sales",
            title="Sales Pipeline Cohort Matrix",
            format="excel",
            category="sales",
            file_size_kb=850.0,
            download_url="/api/v1/mobile/reports/rep-xls-sales/download",
            preview_data={"sheets": ["Overview", "Deals", "Reps"], "row_count": 420}
        )
        ppt_rep = MobileReportItem(
            report_id="rep-ppt-board",
            title="Board Strategy Presentation",
            format="pptx",
            category="executive",
            file_size_kb=3200.0,
            download_url="/api/v1/mobile/reports/rep-ppt-board/download",
            preview_data={"slide_count": 22, "aspect_ratio": "16:9"}
        )
        self._reports[pdf_rep.report_id] = pdf_rep
        self._reports[excel_rep.report_id] = excel_rep
        self._reports[ppt_rep.report_id] = ppt_rep

    def list_reports(self, category: Optional[str] = None) -> List[MobileReportItem]:
        """List reports available to the mobile user."""
        items = list(self._reports.values())
        if category:
            items = [i for i in items if i.category == category]
        return items

    def open_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        """Open a report for viewing on mobile."""
        rep = self._reports.get(report_id)
        if not rep:
            return None
        return {
            "report": rep.model_dump(),
            "viewer_type": f"mobile_{rep.format}_viewer",
            "opened_at": time.time()
        }

    def share_report(self, report_id: str, share_target: str = "slack") -> Dict[str, Any]:
        """Generate mobile native share sheet link / deep link."""
        rep = self._reports.get(report_id)
        if not rep:
            return {"success": False, "error": "Report not found"}

        deep_link = f"analystos://reports/{report_id}?action=view"
        web_link = f"https://analystos.enterprise.com/reports/{report_id}"

        logger.info("Shared report %s via %s", report_id, share_target)
        return {
            "success": True,
            "report_id": report_id,
            "deep_link": deep_link,
            "web_link": web_link,
            "share_target": share_target
        }

    def download_report(self, report_id: str) -> Dict[str, Any]:
        """Prepare downloadable binary payload or local storage bundle."""
        rep = self._reports.get(report_id)
        if not rep:
            return {"success": False, "error": "Report not found"}

        return {
            "success": True,
            "report_id": report_id,
            "filename": f"{rep.title.replace(' ', '_')}.{rep.format}",
            "file_size_kb": rep.file_size_kb,
            "content_stream": f"BASE64_STREAM_OF_{rep.format.upper()}",
            "cacheable": True
        }
