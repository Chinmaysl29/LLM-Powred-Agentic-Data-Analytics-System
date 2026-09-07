"""Phase 12.3.7 — Report Sharing Module.

Supports multi-format report sharing (PDF, Excel, PPT), team & workspace scopes,
and secure download authorization.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import Dict, List, Optional, Set
import uuid

logger = logging.getLogger(__name__)

SUPPORTED_FORMATS = {"PDF", "EXCEL", "PPT"}
SUPPORTED_SCOPES = {"WORKSPACE", "TEAM", "DIRECT_USER"}


@dataclass
class ReportShareRecord:
    id: uuid.UUID
    tenant_id: uuid.UUID
    workspace_id: uuid.UUID
    report_id: str
    format: str  # "PDF", "EXCEL", "PPT"
    owner_id: uuid.UUID
    scope: str  # "WORKSPACE", "TEAM", "DIRECT_USER"
    permission: str  # "VIEW", "DOWNLOAD", "EXPORT"
    team_id: Optional[uuid.UUID] = None
    recipient_ids: Set[uuid.UUID] = field(default_factory=set)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ReportSharingService:
    """Service governing export and sharing permissions for generated reports."""

    def __init__(self) -> None:
        self._shares: Dict[uuid.UUID, ReportShareRecord] = {}
        self._report_shares: Dict[str, List[uuid.UUID]] = {}

    def share_report(
        self,
        tenant_id: uuid.UUID | str,
        workspace_id: uuid.UUID | str,
        report_id: str,
        format: str,
        owner_id: uuid.UUID | str,
        scope: str = "WORKSPACE",
        team_id: Optional[uuid.UUID | str] = None,
        recipient_ids: Optional[List[uuid.UUID | str]] = None,
        permission: str = "DOWNLOAD",
    ) -> ReportShareRecord:
        """Configure sharing rules for a report format."""
        fmt_clean = format.upper()
        if fmt_clean not in SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported report format '{format}'. Supported: {sorted(SUPPORTED_FORMATS)}")

        scope_clean = scope.upper()
        if scope_clean not in SUPPORTED_SCOPES:
            raise ValueError(f"Invalid scope '{scope}'. Supported: {sorted(SUPPORTED_SCOPES)}")

        tid = uuid.UUID(str(tenant_id)) if isinstance(tenant_id, str) else tenant_id
        wid = uuid.UUID(str(workspace_id)) if isinstance(workspace_id, str) else workspace_id
        oid = uuid.UUID(str(owner_id)) if isinstance(owner_id, str) else owner_id
        tmid = uuid.UUID(str(team_id)) if team_id else None
        rcp_set = {uuid.UUID(str(r)) for r in (recipient_ids or [])}

        if scope_clean == "TEAM" and not tmid:
            raise ValueError("team_id is required for TEAM scope.")
        if scope_clean == "DIRECT_USER" and not rcp_set:
            raise ValueError("recipient_ids cannot be empty for DIRECT_USER scope.")

        share_id = uuid.uuid4()
        record = ReportShareRecord(
            id=share_id,
            tenant_id=tid,
            workspace_id=wid,
            report_id=report_id,
            format=fmt_clean,
            owner_id=oid,
            scope=scope_clean,
            permission=permission.upper(),
            team_id=tmid,
            recipient_ids=rcp_set,
        )

        self._shares[share_id] = record
        if report_id not in self._report_shares:
            self._report_shares[report_id] = []
        self._report_shares[report_id].append(share_id)

        logger.info(
            "Report '%s' (%s) shared with scope %s by user %s",
            report_id,
            fmt_clean,
            scope_clean,
            oid,
        )
        return record

    def can_download_report(
        self,
        report_id: str,
        format: str,
        user_id: uuid.UUID | str,
        workspace_id: uuid.UUID | str,
        team_ids: Optional[List[uuid.UUID | str]] = None,
    ) -> bool:
        """Validate if a user is authorized to download the report in the requested format."""
        fmt_clean = format.upper()
        uid = uuid.UUID(str(user_id)) if isinstance(user_id, str) else user_id
        wid = uuid.UUID(str(workspace_id)) if isinstance(workspace_id, str) else workspace_id
        user_teams: Set[uuid.UUID] = {uuid.UUID(str(t)) for t in (team_ids or [])}

        share_ids = self._report_shares.get(report_id, [])
        matching_shares = [
            self._shares[sid]
            for sid in share_ids
            if self._shares[sid].format == fmt_clean
        ]

        if not matching_shares:
            return False

        for share in matching_shares:
            # Owner check
            if share.owner_id == uid:
                return True
            # Workspace scope
            if share.scope == "WORKSPACE" and share.workspace_id == wid:
                return True
            # Team scope
            if share.scope == "TEAM" and share.team_id in user_teams:
                return True
            # Direct user scope
            if share.scope == "DIRECT_USER" and uid in share.recipient_ids:
                return True

        return False

    def generate_download_url(
        self,
        report_id: str,
        format: str,
        user_id: uuid.UUID | str,
        workspace_id: uuid.UUID | str,
        team_ids: Optional[List[uuid.UUID | str]] = None,
    ) -> str:
        """Generate download link if authorization succeeds."""
        if not self.can_download_report(report_id, format, user_id, workspace_id, team_ids):
            raise PermissionError(f"User {user_id} does not have download permissions for report {report_id} ({format}).")

        ext = format.lower()
        if ext == "excel":
            ext = "xlsx"
        return f"/api/v1/reports/{report_id}/download.{ext}"
