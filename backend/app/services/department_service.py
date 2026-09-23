"""Department service managing organizational department business logic."""

from __future__ import annotations

import logging
import uuid

from backend.app.models.department import Department
from backend.app.repositories.department_repository import DepartmentRepository

logger = logging.getLogger(__name__)


class DepartmentService:
    """Service handling department creation, validation, and listing within a workspace."""

    def __init__(self, repository: DepartmentRepository) -> None:
        self.repository = repository

    def create_department(
        self,
        workspace_id: uuid.UUID | str,
        department_name: str,
        description: str = "",
    ) -> Department:
        """Create a new department in a workspace."""
        parsed_wid = uuid.UUID(str(workspace_id)) if isinstance(workspace_id, str) else workspace_id
        clean_name = department_name.strip()
        if len(clean_name) < 2:
            raise ValueError("Department name must be at least 2 characters long")

        dept = Department(
            workspace_id=parsed_wid,
            department_name=clean_name,
            description=description.strip(),
        )
        return self.repository.create_department(dept)

    def get_department(self, department_id: uuid.UUID | str) -> Department | None:
        """Retrieve a department by ID."""
        return self.repository.get_department(department_id)

    def list_departments(self, workspace_id: uuid.UUID | str) -> list[Department]:
        """List all departments in a workspace."""
        return self.repository.list_departments(workspace_id)

    def delete_department(self, department_id: uuid.UUID | str) -> bool:
        """Delete a department by ID."""
        return self.repository.delete_department(department_id)
