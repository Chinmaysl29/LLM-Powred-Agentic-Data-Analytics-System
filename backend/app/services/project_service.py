"""Project service managing project initiatives, statuses, and updates within a workspace."""

from __future__ import annotations

import logging
from typing import Any
import uuid

from backend.app.models.project import Project
from backend.app.repositories.project_repository import ProjectRepository

logger = logging.getLogger(__name__)


class ProjectService:
    """Service handling project initiative creation, lifecycle states, and updates."""

    def __init__(self, repository: ProjectRepository) -> None:
        self.repository = repository

    def create_project(
        self,
        workspace_id: uuid.UUID | str,
        project_name: str,
        description: str = "",
        status: str = "active",
    ) -> Project:
        """Create a new project within a workspace."""
        parsed_wid = uuid.UUID(str(workspace_id)) if isinstance(workspace_id, str) else workspace_id
        clean_name = project_name.strip()
        if len(clean_name) < 2:
            raise ValueError("Project name must be at least 2 characters long")

        project = Project(
            workspace_id=parsed_wid,
            project_name=clean_name,
            description=description.strip(),
            status=status,
        )
        return self.repository.create_project(project)

    def get_project(self, project_id: uuid.UUID | str) -> Project | None:
        """Retrieve a project by ID."""
        return self.repository.get_project(project_id)

    def list_projects(
        self,
        workspace_id: uuid.UUID | str,
        status: str | None = None,
    ) -> list[Project]:
        """List all projects in a workspace."""
        return self.repository.list_projects(workspace_id, status=status)

    def update_project(
        self,
        project_id: uuid.UUID | str,
        **updates: Any,
    ) -> Project | None:
        """Update fields of a project."""
        return self.repository.update_project(project_id, **updates)

    def archive_project(self, project_id: uuid.UUID | str) -> Project | None:
        """Archive a project."""
        return self.repository.update_project(project_id, status="archived")

    def delete_project(self, project_id: uuid.UUID | str) -> bool:
        """Delete a project by ID."""
        return self.repository.delete_project(project_id)
