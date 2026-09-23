"""Team repository providing CRUD operations for teams within departments."""

from __future__ import annotations

import logging
import uuid

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.database.postgres import get_db_session
from backend.app.models.team import Team

logger = logging.getLogger(__name__)


class TeamRepository:
    """Repository managing persistence and retrieval of Team entities."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create_team(self, team: Team) -> Team:
        """Persist a new team record."""
        self.db.add(team)
        self.db.commit()
        self.db.refresh(team)
        logger.info("Created team id=%s name=%s department_id=%s", team.id, team.team_name, team.department_id)
        return team

    def get_team(self, team_id: uuid.UUID | str) -> Team | None:
        """Retrieve a team by its unique UUID."""
        parsed_id = uuid.UUID(str(team_id)) if isinstance(team_id, str) else team_id
        stmt = select(Team).where(Team.id == parsed_id)
        return self.db.scalars(stmt).first()

    def list_teams(self, department_id: uuid.UUID | str) -> list[Team]:
        """List all teams belonging to a department."""
        parsed_did = uuid.UUID(str(department_id)) if isinstance(department_id, str) else department_id
        stmt = select(Team).where(Team.department_id == parsed_did).order_by(Team.team_name.asc())
        return list(self.db.scalars(stmt).all())

    def delete_team(self, team_id: uuid.UUID | str) -> bool:
        """Delete a team."""
        team = self.get_team(team_id)
        if not team:
            return False
        self.db.delete(team)
        self.db.commit()
        logger.info("Deleted team id=%s", team_id)
        return True


def get_team_repository(db: Session = Depends(get_db_session)) -> TeamRepository:
    """FastAPI dependency yielding a TeamRepository instance."""
    return TeamRepository(db=db)
