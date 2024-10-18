# linear/migrators/team_migrator.py

from database import get_db
from models import Epic, Label

from ..api import LinearAPI
from ..exceptions import TeamCreationError
from ..linear_setup import LinearSetup
from ..logger import logger
from ..models import LinearTeam
from ..utils import sanitize_name, with_progress


class TeamMigrator:
    def __init__(self, linear_api: LinearAPI, linear_setup: LinearSetup):
        self.linear_api = linear_api
        self.linear_setup = linear_setup
        self.team_map = {}  # Map PT project IDs to Linear team objects

    @with_progress(desc="Migrating Teams")
    async def migrate_teams(self, pt_projects, pbar=None):
        """
        Migrate a list of Pivotal Tracker projects to Linear teams.

        :param pt_projects: List of Pivotal Tracker project objects from the database
        :param pbar: Progress bar object
        :return: Dictionary mapping PT project IDs to Linear team objects
        """
        logger.info(f"Starting migration for {len(pt_projects)} projects/teams")
        if pbar:
            pbar.total = len(pt_projects)
            pbar.refresh()

        for pt_project in pt_projects:
            try:
                linear_team = await self.migrate_team(pt_project)
                self.team_map[pt_project.id] = linear_team
                if pbar:
                    pbar.update(1)
            except TeamCreationError as e:
                logger.warning(f"Failed to migrate project {pt_project.name}: {str(e)}")
                # Continue with the next project

        logger.info(f"Team migration completed. Migrated {len(self.team_map)} teams")
        return self.team_map

    async def migrate_team(self, pt_project):
        """
        Migrate a single Pivotal Tracker project to a Linear team.

        :param pt_project: Pivotal Tracker project object from the database
        :return: LinearTeam object
        """
        logger.info(f"Migrating project to team: {pt_project.name}")

        try:
            # Sanitize the project name
            sanitized_name = sanitize_name(pt_project.name)

            # Use LinearSetup to create the team and set up workflow states
            linear_team_data = await self.linear_setup.setup_team(
                sanitized_name, pt_project.description
            )

            # Create LinearTeam object
            linear_team = LinearTeam(
                id=linear_team_data["id"],
                name=linear_team_data["name"],
                key=linear_team_data["key"],
                description=linear_team_data.get("description"),
            )

            # Set up labels for the team
            pt_labels = await self.get_pt_project_labels(pt_project.id)
            await self.linear_setup.setup_labels(linear_team.id, pt_labels)

            return linear_team

        except Exception as e:
            raise TeamCreationError(
                f"Failed to migrate project {pt_project.name}: {str(e)}"
            )

    def get_linear_team(self, pt_project_id):
        """
        Get the Linear team object for a given Pivotal Tracker project ID.

        :param pt_project_id: Pivotal Tracker project ID
        :return: LinearTeam object or None if not found
        """
        return self.team_map.get(pt_project_id)

    async def ensure_team(self, pt_project):
        """
        Ensure a team exists in Linear, migrating if necessary.

        :param pt_project: Pivotal Tracker project object
        :return: LinearTeam object
        """
        if pt_project.id not in self.team_map:
            linear_team = await self.migrate_team(pt_project)
            self.team_map[pt_project.id] = linear_team
        return self.team_map[pt_project.id]

    async def get_pt_project_labels(self, pt_project_id):
        """
        Get the labels for a Pivotal Tracker project.

        :param pt_project: Pivotal Tracker project object
        :return: Tuple of label names and boolean of epic or not
        """
        with get_db() as db:
            labels = db.query(Label).filter(Label.project_id == pt_project_id).all()

            results = []

            # if any labels are associated with an epic, return it with True
            for label in labels:
                epic = db.query(Epic).filter(Epic.label_id == label.id).first()
                if epic:
                    results.append((label.name, True))
                else:
                    results.append((label.name, False))

            db.expunge_all()
            return results
