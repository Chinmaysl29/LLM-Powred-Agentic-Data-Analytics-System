"""Project repository providing CRUD operations for projects within workspaces."""

from __future__ import annotations

import logging
from typing import Any
import uuid

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.database.postgres import get_db_session
from backend.app.models.project import Project

logger = logging.getLogger(__name__)


class ProjectRepository:
    """Repository managing persistence and retrieval of Project entities."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create_project(self, project: Project) -> Project:
        """Persist a new project record."""
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        logger.info("Created project id=%s name=%s workspace_id=%s", project.id, project.project_name, project.workspace_id)
        return project

    def get_project(self, project_id: uuid.UUID | str) -> Project | None:
        """Retrieve a project by its unique UUID."""
        parsed_id = uuid.UUID(str(project_id)) if isinstance(project_id, str) else project_id
        stmt = select(Project).where(Project.id == parsed_id)
        return self.db.scalars(stmt).first()

    def list_projects(
        self,
        workspace_id: uuid.UUID | str,
        status: str | None = None,
    ) -> list[Project]:
        """List all projects belonging to a workspace."""
        parsed_wid = uuid.UUID(str(workspace_id)) if isinstance(workspace_id, str) else workspace_id
        stmt = select(Project).where(Project.workspace_id == parsed_wid).order_by(Project.created_at.desc())
        if status:
            stmt = stmt.where(Project.status == status)
        return list(self.db.scalars(stmt).all())

    def update_project(
        self,
        project_id: uuid.UUID | str,
        **updates: Any,
    ) -> Project | None:
        """Update mutable fields of a project."""
        project = self.get_project(project_id)
        if not project:
            return None

        allowed = {"project_name", "description", "status"}
        applied = False
        for k, v in updates.items():
            if k in allowed and v is not None:
                setattr(project, k, v)
                applied = True

        if applied:
            self.db.commit()
            self.db.refresh(project)
            logger.info("Updated project id=%s", project_id)

        return project

    def delete_project(self, project_id: uuid.UUID | str) -> bool:
        """Delete a project."""
        project = self.get_project(project_id)
        if not project:
            return False
        self.db.delete(project)
        self.db.commit()
        logger.info("Deleted project id=%s", project_id)
        return True


def get_project_repository(db: Session = Depends(get_db_session)) -> ProjectRepository:
    """FastAPI dependency yielding a ProjectRepository instance."""
    return ProjectRepository(db=db)
