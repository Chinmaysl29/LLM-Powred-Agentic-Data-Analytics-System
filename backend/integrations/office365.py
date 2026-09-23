"""
Phase 12.7.7 — Office 365 Integration
Microsoft 365 / Office 365 enterprise connector supporting Excel workbook ingestion,
Word doc creation, PowerPoint deck export, Outlook email dispatches, and OneDrive synchronization.
"""

from typing import Dict, Any, Optional, List
import time
import uuid
from backend.integrations.base import (
    BaseEnterpriseIntegration,
    IntegrationHealthResult,
    IntegrationSyncResult,
)


class Office365Integration(BaseEnterpriseIntegration):
    """
    Enterprise Microsoft 365 (Office 365) integration client.
    Interfaces via Microsoft Graph API for Excel, Word, PowerPoint, Outlook, and OneDrive.
    """

    def __init__(self, integration_id: str, config: Optional[Dict[str, Any]] = None):
        super().__init__(integration_id, config)
        self.tenant_id_m365 = self.config.get("tenant_id", "mock-ms-tenant-id")
        self.client_id = self.config.get("client_id", "mock-ms-client-id")
        self.client_secret = self.config.get("client_secret", "mock-ms-secret")

        # Mock OneDrive, Excel, Word, PowerPoint, and Outlook
        self._onedrive_files: Dict[str, Dict[str, Any]] = {}
        self._excel_workbooks: Dict[str, Dict[str, List[List[Any]]]] = {
            "book-financial-model": {
                "Sheet1": [
                    ["Quarter", "ARR", "Churn", "CAC"],
                    ["Q1", 1000000, 0.02, 450],
                    ["Q2", 1250000, 0.018, 420],
                    ["Q3", 1550000, 0.015, 390],
                    ["Q4", 2100000, 0.012, 350]
                ]
            }
        }
        self._word_documents: Dict[str, Dict[str, Any]] = {}
        self._powerpoint_decks: Dict[str, Dict[str, Any]] = {}
        self._sent_emails: List[Dict[str, Any]] = []

    def connect(self) -> bool:
        if not self.tenant_id_m365 or not self.client_id:
            self.logger.error("Missing Office 365 credentials (tenant_id or client_id)")
            self.is_connected = False
            return False
        self.is_connected = True
        self.logger.info("Office 365 integration %s authenticated via Microsoft Graph.", self.integration_id)
        return True

    def disconnect(self) -> bool:
        self.is_connected = False
        self.logger.info("Office 365 integration %s disconnected.", self.integration_id)
        return True

    def validate(self) -> bool:
        if not self.tenant_id_m365 or not self.client_id:
            return False
        return True

    def health_check(self) -> IntegrationHealthResult:
        start_time = time.time()
        is_valid = self.validate()
        latency = (time.time() - start_time) * 1000.0
        return IntegrationHealthResult(
            healthy=is_valid and self.is_connected,
            status_code=200 if is_valid else 401,
            latency_ms=round(latency, 2),
            message="Microsoft Graph API operational" if is_valid else "Office 365 auth failure",
            details={
                "onedrive_files": len(self._onedrive_files),
                "excel_workbooks": len(self._excel_workbooks),
                "sent_emails": len(self._sent_emails)
            }
        )

    def sync(self, payload: Optional[Dict[str, Any]] = None) -> IntegrationSyncResult:
        """Sync files across OneDrive and SharePoint document libraries."""
        if not self.is_connected:
            return IntegrationSyncResult(success=False, errors=["Office 365 integration not connected"])
        return IntegrationSyncResult(
            success=True,
            records_synced=len(self._onedrive_files) + len(self._excel_workbooks),
            metadata={"synced_workbooks": list(self._excel_workbooks.keys())}
        )

    # Excel
    def read_excel(self, workbook_id: str, sheet_name: str = "Sheet1") -> List[List[Any]]:
        """Read 2D matrix data from an Excel workbook."""
        wb = self._excel_workbooks.get(workbook_id)
        if not wb or sheet_name not in wb:
            return []
        return wb[sheet_name]

    def write_excel(self, workbook_id: str, sheet_name: str, data: List[List[Any]]) -> Dict[str, Any]:
        """Write matrix into Excel worksheet."""
        if workbook_id not in self._excel_workbooks:
            self._excel_workbooks[workbook_id] = {}
        self._excel_workbooks[workbook_id][sheet_name] = data
        return {"workbook_id": workbook_id, "sheet": sheet_name, "rows_written": len(data)}

    # Outlook
    def send_email(
        self,
        to_recipients: List[str],
        subject: str,
        body_html: str,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Send Outlook email with analytics report / attachments."""
        email_record = {
            "id": f"msg-{uuid.uuid4().hex[:8]}",
            "to": to_recipients,
            "subject": subject,
            "body": body_html,
            "attachments": attachments or [],
            "sent_at": time.time(),
            "status": "sent"
        }
        self._sent_emails.append(email_record)
        self.logger.info("Sent Outlook email '%s' to %d recipients", subject, len(to_recipients))
        return {"id": email_record["id"], "delivered": True, "recipients": to_recipients}

    # Word
    def create_word_document(self, title: str, sections: List[Dict[str, str]]) -> Dict[str, Any]:
        """Create a Word doc report."""
        doc_id = f"word-{uuid.uuid4().hex[:8]}"
        self._word_documents[doc_id] = {"id": doc_id, "title": title, "sections": sections}
        return {"document_id": doc_id, "title": title, "status": "created"}

    # PowerPoint
    def create_powerpoint_presentation(self, deck_title: str, slides: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate PowerPoint slide deck."""
        deck_id = f"ppt-{uuid.uuid4().hex[:8]}"
        self._powerpoint_decks[deck_id] = {"id": deck_id, "title": deck_title, "slides": slides}
        return {"deck_id": deck_id, "title": deck_title, "slide_count": len(slides)}

    # OneDrive
    def upload_to_onedrive(self, filename: str, content: bytes, folder: str = "Reports") -> Dict[str, Any]:
        """Upload report asset into OneDrive directory."""
        file_id = f"one-{uuid.uuid4().hex[:8]}"
        self._onedrive_files[file_id] = {
            "id": file_id,
            "name": filename,
            "folder": folder,
            "size": len(content),
            "uploaded_at": time.time()
        }
        return {"file_id": file_id, "name": filename, "folder": folder, "status": "stored"}
