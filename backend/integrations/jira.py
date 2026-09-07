"""
Phase 12.7.5 — Jira Integration
Atlassian Jira enterprise connector for analytics issue ticketing, automated anomaly bug creation,
ticket updating, and project synchronization.
"""

from typing import Dict, Any, Optional, List
import time
import uuid
from backend.integrations.base import (
    BaseEnterpriseIntegration,
    IntegrationHealthResult,
    IntegrationSyncResult,
)


class JiraIntegration(BaseEnterpriseIntegration):
    """
    Enterprise Jira integration client.
    Supports issue creation, status transitions, project sync, and analytics ticketing.
    """

    def __init__(self, integration_id: str, config: Optional[Dict[str, Any]] = None):
        super().__init__(integration_id, config)
        self.jira_url = self.config.get("jira_url", "https://company.atlassian.net")
        self.api_token = self.config.get("api_token", "mock-jira-token")
        self.email = self.config.get("email", "analyst@company.com")
        self.default_project = self.config.get("default_project", "DATA")

        # Mock / In-memory state
        self._projects: List[Dict[str, Any]] = [
            {"key": "DATA", "name": "Data Analytics Core", "id": "10001"},
            {"key": "FIN", "name": "Financial Analytics", "id": "10002"},
            {"key": "OPS", "name": "Operations Engine", "id": "10003"}
        ]
        self._issues: Dict[str, Dict[str, Any]] = {}

    def connect(self) -> bool:
        if not self.jira_url or not self.api_token:
            self.logger.error("Jira integration requires jira_url and api_token")
            self.is_connected = False
            return False
        self.is_connected = True
        self.logger.info("Jira integration %s connected to %s", self.integration_id, self.jira_url)
        return True

    def disconnect(self) -> bool:
        self.is_connected = False
        self.logger.info("Jira integration %s disconnected.", self.integration_id)
        return True

    def validate(self) -> bool:
        if not self.jira_url.startswith("http") or not self.api_token:
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
            message="Jira connection verified" if is_valid else "Authentication failed for Jira",
            details={"projects_count": len(self._projects), "issues_count": len(self._issues)}
        )

    def sync(self, payload: Optional[Dict[str, Any]] = None) -> IntegrationSyncResult:
        """Synchronize active Jira projects and boards."""
        if not self.is_connected:
            return IntegrationSyncResult(success=False, errors=["Jira integration not connected"])
        return IntegrationSyncResult(
            success=True,
            records_synced=len(self._projects),
            metadata={"projects": [p["key"] for p in self._projects]}
        )

    def fetch_projects(self) -> List[Dict[str, Any]]:
        """Retrieve list of available Jira projects."""
        return self._projects

    def create_issue(
        self,
        summary: str,
        description: str,
        issue_type: str = "Task",
        project_key: Optional[str] = None,
        priority: str = "Medium",
        labels: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Create a new Jira issue / ticket."""
        proj = project_key or self.default_project
        issue_num = len(self._issues) + 101
        issue_key = f"{proj}-{issue_num}"
        issue_data = {
            "key": issue_key,
            "id": str(uuid.uuid4()),
            "summary": summary,
            "description": description,
            "issue_type": issue_type,
            "project_key": proj,
            "priority": priority,
            "labels": labels or ["ai-data-analyst"],
            "status": "To Do",
            "created_at": time.time(),
            "updated_at": time.time()
        }
        self._issues[issue_key] = issue_data
        self.logger.info("Created Jira ticket %s: %s", issue_key, summary)
        return issue_data

    def update_issue(
        self,
        issue_key: str,
        status: Optional[str] = None,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        labels: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """Update existing Jira ticket fields or transition status."""
        issue = self._issues.get(issue_key)
        if not issue:
            self.logger.warning("Jira issue %s not found", issue_key)
            return None
        if status:
            issue["status"] = status
        if summary:
            issue["summary"] = summary
        if description:
            issue["description"] = description
        if labels:
            issue["labels"] = list(set(issue["labels"] + labels))
        issue["updated_at"] = time.time()
        self.logger.info("Updated Jira ticket %s status -> %s", issue_key, issue["status"])
        return issue

    def create_analytics_ticket(
        self,
        anomaly_metric: str,
        expected_value: float,
        actual_value: float,
        impact_level: str = "High"
    ) -> Dict[str, Any]:
        """Automated analytics discrepancy incident creation."""
        summary = f"[Anomaly Detected] Discrepancy in {anomaly_metric}"
        description = (
            f"AI Data Analyst OS has detected a statistically significant anomaly.\n"
            f"• Metric: {anomaly_metric}\n"
            f"• Expected Baseline: {expected_value}\n"
            f"• Observed Value: {actual_value}\n"
            f"• Impact Level: {impact_level}\n\n"
            f"Automated investigative ticket generated for data engineering team."
        )
        priority = "High" if impact_level.lower() in ["high", "critical"] else "Medium"
        return self.create_issue(
            summary=summary,
            description=description,
            issue_type="Bug",
            priority=priority,
            labels=["analytics-anomaly", "auto-generated"]
        )
