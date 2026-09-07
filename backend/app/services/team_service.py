"""Team service managing team creation, validation, and listing within a department."""

from __future__ import annotations

import logging
import uuid

from backend.app.models.team import Team
from backend.app.repositories.team_repository import TeamRepository

logger = logging.getLogger(__name__)


class TeamService:
    """Service handling team business rules within a department."""

    def __init__(self, repository: TeamRepository) -> None:
        self.repository = repository

    def create_team(
        self,
        department_id: uuid.UUID | str,
        team_name: str,
        description: str = "",
    ) -> Team:
        """Create a new team within a department."""
        parsed_did = uuid.UUID(str(department_id)) if isinstance(department_id, str) else department_id
        clean_name = team_name.strip()
        if len(clean_name) < 2:
            raise ValueError("Team name must be at least 2 characters long")

        team = Team(
            department_id=parsed_did,
            team_name=clean_name,
            description=description.strip(),
        )
        return self.repository.create_team(team)

    def get_team(self, team_id: uuid.UUID | str) -> Team | None:
        """Retrieve a team by ID."""
        return self.repository.get_team(team_id)

    def list_teams(self, department_id: uuid.UUID | str) -> list[Team]:
        """List all teams in a department."""
        return self.repository.list_teams(department_id)

    def delete_team(self, team_id: uuid.UUID | str) -> bool:
        """Delete a team by ID."""
        return self.repository.delete_team(team_id)
