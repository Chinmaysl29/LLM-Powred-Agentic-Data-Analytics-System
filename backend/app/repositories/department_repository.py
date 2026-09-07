"""Department repository providing CRUD operations for departments within workspaces."""

from __future__ import annotations

import logging
import uuid

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.database.postgres import get_db_session
from backend.app.models.department import Department

logger = logging.getLogger(__name__)


class DepartmentRepository:
    """Repository managing persistence and retrieval of Department entities."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create_department(self, department: Department) -> Department:
        """Persist a new department record."""
        self.db.add(department)
        self.db.commit()
        self.db.refresh(department)
        logger.info("Created department id=%s name=%s workspace_id=%s", department.id, department.department_name, department.workspace_id)
        return department

    def get_department(self, department_id: uuid.UUID | str) -> Department | None:
        """Retrieve a department by its unique UUID."""
        parsed_id = uuid.UUID(str(department_id)) if isinstance(department_id, str) else department_id
        stmt = select(Department).where(Department.id == parsed_id)
        return self.db.scalars(stmt).first()

    def list_departments(self, workspace_id: uuid.UUID | str) -> list[Department]:
        """List all departments belonging to a workspace."""
        parsed_wid = uuid.UUID(str(workspace_id)) if isinstance(workspace_id, str) else workspace_id
        stmt = select(Department).where(Department.workspace_id == parsed_wid).order_by(Department.department_name.asc())
        return list(self.db.scalars(stmt).all())

    def delete_department(self, department_id: uuid.UUID | str) -> bool:
        """Delete a department."""
        dept = self.get_department(department_id)
        if not dept:
            return False
        self.db.delete(dept)
        self.db.commit()
        logger.info("Deleted department id=%s", department_id)
        return True


def get_department_repository(db: Session = Depends(get_db_session)) -> DepartmentRepository:
    """FastAPI dependency yielding a DepartmentRepository instance."""
    return DepartmentRepository(db=db)
