"""Phase 12.3.6 — Dashboard Sharing Module.

Manages access scopes (Private, Team, Workspace, Public Links) and validates
user and link authorization on dashboards.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import logging
import secrets
from typing import Dict, List, Optional, Set
import uuid

logger = logging.getLogger(__name__)


@dataclass
class DashboardShareRecord:
    id: uuid.UUID
    tenant_id: uuid.UUID
    workspace_id: uuid.UUID
    dashboard_id: str
    owner_id: uuid.UUID
    scope: str  # "PRIVATE", "TEAM", "WORKSPACE", "PUBLIC_LINK"
    permission: str  # "VIEW", "EDIT"
    team_id: Optional[uuid.UUID] = None
    share_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class DashboardSharingService:
    """Service handling multi-scope dashboard sharing and authorization."""

    def __init__(self) -> None:
        # In-memory registry for dashboard share permissions
        self._shares: Dict[uuid.UUID, DashboardShareRecord] = {}
        # Fast lookup by dashboard_id
        self._dashboard_shares: Dict[str, List[uuid.UUID]] = {}
        # Token lookup
        self._token_to_share: Dict[str, uuid.UUID] = {}

    def share_dashboard(
        self,
        tenant_id: uuid.UUID | str,
        workspace_id: uuid.UUID | str,
        dashboard_id: str,
        owner_id: uuid.UUID | str,
        scope: str = "WORKSPACE",
        team_id: Optional[uuid.UUID | str] = None,
        permission: str = "VIEW",
        expires_in_hours: Optional[int] = None,
    ) -> DashboardShareRecord:
        """Create or update a dashboard sharing configuration."""
        tid = uuid.UUID(str(tenant_id)) if isinstance(tenant_id, str) else tenant_id
        wid = uuid.UUID(str(workspace_id)) if isinstance(workspace_id, str) else workspace_id
        oid = uuid.UUID(str(owner_id)) if isinstance(owner_id, str) else owner_id
        tmid = uuid.UUID(str(team_id)) if team_id else None

        scope_clean = scope.upper()
        if scope_clean not in {"PRIVATE", "TEAM", "WORKSPACE", "PUBLIC_LINK"}:
            raise ValueError(f"Invalid scope '{scope}'. Allowed: PRIVATE, TEAM, WORKSPACE, PUBLIC_LINK")

        if scope_clean == "TEAM" and not tmid:
            raise ValueError("team_id is required when sharing with TEAM scope.")

        token = secrets.token_urlsafe(32) if scope_clean == "PUBLIC_LINK" else None
        expires_at = (
            datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)
            if expires_in_hours
            else None
        )

        share_id = uuid.uuid4()
        record = DashboardShareRecord(
            id=share_id,
            tenant_id=tid,
            workspace_id=wid,
            dashboard_id=dashboard_id,
            owner_id=oid,
            scope=scope_clean,
            permission=permission.upper(),
            team_id=tmid,
            share_token=token,
            expires_at=expires_at,
            is_active=True,
        )

        self._shares[share_id] = record
        if dashboard_id not in self._dashboard_shares:
            self._dashboard_shares[dashboard_id] = []
        self._dashboard_shares[dashboard_id].append(share_id)

        if token:
            self._token_to_share[token] = share_id

        logger.info(
            "Dashboard '%s' shared with scope %s (permission=%s)",
            dashboard_id,
            scope_clean,
            permission,
        )
        return record

    def revoke_access(self, dashboard_id: str, share_id: Optional[uuid.UUID | str] = None) -> int:
        """Revoke one or all shares for a dashboard."""
        revoked_count = 0
        now = datetime.now(timezone.utc)

        if share_id:
            sid = uuid.UUID(str(share_id)) if isinstance(share_id, str) else share_id
            share = self._shares.get(sid)
            if share and share.dashboard_id == dashboard_id:
                share.is_active = False
                if share.share_token:
                    self._token_to_share.pop(share.share_token, None)
                revoked_count += 1
        else:
            share_ids = self._dashboard_shares.get(dashboard_id, [])
            for sid in share_ids:
                share = self._shares.get(sid)
                if share and share.is_active:
                    share.is_active = False
                    if share.share_token:
                        self._token_to_share.pop(share.share_token, None)
                    revoked_count += 1

        logger.info("Revoked %d share(s) on dashboard '%s'", revoked_count, dashboard_id)
        return revoked_count

    def validate_access(
        self,
        dashboard_id: str,
        user_id: Optional[uuid.UUID | str] = None,
        workspace_id: Optional[uuid.UUID | str] = None,
        team_ids: Optional[List[uuid.UUID | str]] = None,
        share_token: Optional[str] = None,
        required_permission: str = "VIEW",
    ) -> bool:
        """Validate if a user or external token has access to the dashboard."""
        now = datetime.now(timezone.utc)

        # 1. Token-based access
        if share_token:
            share_id = self._token_to_share.get(share_token)
            if not share_id:
                return False
            share = self._shares.get(share_id)
            if not share or not share.is_active or share.dashboard_id != dashboard_id:
                return False
            if share.expires_at and share.expires_at < now:
                return False
            # Check permission level
            if required_permission == "EDIT" and share.permission != "EDIT":
                return False
            return True

        uid = uuid.UUID(str(user_id)) if user_id else None
        wid = uuid.UUID(str(workspace_id)) if workspace_id else None
        user_teams: Set[uuid.UUID] = {
            uuid.UUID(str(t)) for t in (team_ids or [])
        }

        # Check existing shares
        active_shares = [
            self._shares[sid]
            for sid in self._dashboard_shares.get(dashboard_id, [])
            if self._shares[sid].is_active
        ]

        if not active_shares:
            # If no explicit shares set, default to private (only owner/system has access)
            return False

        for share in active_shares:
            # Check expiry
            if share.expires_at and share.expires_at < now:
                continue

            # Permission check
            if required_permission == "EDIT" and share.permission != "EDIT":
                continue

            # Owner check
            if uid and share.owner_id == uid:
                return True

            # Workspace scope
            if share.scope == "WORKSPACE" and wid and share.workspace_id == wid:
                return True

            # Team scope
            if share.scope == "TEAM" and share.team_id in user_teams:
                return True

        return False
